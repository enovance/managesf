#
# Copyright (c) 2016 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import re
import deepdiff
import logging

from pecan import conf

from managesf.model.yamlbkd.yamlbackend import YAMLBackend
from managesf.model.yamlbkd.yamlbackend import YAMLDBException
from managesf.model.yamlbkd.resource import ModelInvalidException
from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resource import KEY_RE_CONSTRAINT

from managesf.model.yamlbkd.resources.gitrepository import GitRepository
from managesf.model.yamlbkd.resources.group import Group
from managesf.model.yamlbkd.resources.gitacls import ACL
from managesf.model.yamlbkd.resources.project import Project

logger = logging.getLogger(__name__)

MAPPING = {'repos': GitRepository,
           'groups': Group,
           'projects': Project,
           'acls': ACL}


class ResourceDepsException(Exception):
    def __init__(self, msg):
        self.msg = msg


class SFResourceBackendEngine(object):
    def __init__(self, workdir, subdir):
        self.workdir = workdir
        self.subdir = subdir
        logger.info('Resource engine is using %s as workdir' % (
                    self.workdir))

    def _get_update_change(self, rtype, prev, new, rids):
        r_key_changes = {}
        for rid in rids:
            n = MAPPING[rtype](rid, new[rid])
            p = MAPPING[rtype](rid, prev[rid])
            n.set_defaults()
            p.set_defaults()
            new_data = n.get_resource()
            prev_data = p.get_resource()
            changes = deepdiff.DeepDiff(prev_data, new_data)
            if not changes:
                continue
            r_key_changes[rid] = {'data': new_data, 'changed': set()}
            for ctype, _changes in changes.items():
                if ctype in ('values_changed', 'iterable_item_removed',
                             'iterable_item_added'):
                    for c in _changes:
                        key = re.search(
                            "root\['(" + KEY_RE_CONSTRAINT + ")'\].*$", c)
                        key = key.groups()[0]
                        r_key_changes[rid]['changed'].add(key)
                else:
                    logger.info('Unexpected change type '
                                'detected for rid: %s' % rid)
        return r_key_changes

    def _get_data_diff(self, prev, new):
        previous_data_resources_ids = {}
        for rtype, resources in prev['resources'].items():
            previous_data_resources_ids[rtype] = set(resources.keys())
        new_data_resources_ids = {}
        for rtype, resources in new['resources'].items():
            new_data_resources_ids[rtype] = set(resources.keys())
        changed_resources_ids = {}
        new_resources_ids = {}
        removed_resources_ids = {}
        rtype_list = (set(previous_data_resources_ids.keys()) |
                      set(new_data_resources_ids.keys()))
        for rtype in rtype_list:
            changed_resources_ids[rtype] = (
                previous_data_resources_ids[rtype] &
                new_data_resources_ids[rtype])
            new_resources_ids[rtype] = (
                new_data_resources_ids[rtype] -
                previous_data_resources_ids[rtype])
            removed_resources_ids[rtype] = (
                previous_data_resources_ids[rtype] -
                new_data_resources_ids[rtype])
        sanitized_changes = {}
        for rtype in rtype_list:
            sanitized_changes.setdefault(
                rtype,
                {'update': {}, 'create': {}, 'delete': {}})
            sanitized_changes[rtype]['create'].update(dict([
                (rid, d) for rid, d in new['resources'][rtype].items()
                if rid in new_resources_ids[rtype]]))
            sanitized_changes[rtype]['delete'].update(dict([
                (rid, d) for rid, d in prev['resources'][rtype].items()
                if rid in removed_resources_ids[rtype]]))
            sanitized_changes[rtype]['update'] = self._get_update_change(
                rtype, prev['resources'][rtype], new['resources'][rtype],
                changed_resources_ids[rtype])
        return sanitized_changes

    def _check_deps_constraints(self, new_data):
        for rtype, resources in new_data['resources'].items():
            for rid, data in resources.items():
                r = MAPPING[rtype](rid, data)
                deps = r.get_deps()
                for deps_type, deps_ids in deps.items():
                    for deps_id in deps_ids:
                        try:
                            assert deps_type in new_data['resources']
                            assert deps_id in tuple(
                                new_data['resources'][deps_type])
                        except AssertionError:
                            raise ResourceDepsException(
                                "Resource [type: %s, ID: %s] depends on an "
                                "unknown resource [type: %s, ID: %s]" % (
                                    rtype, rid, deps_type, deps_id))

    def _validate_changes(self, sanitized_changes, validation_logs):
        for rtype, changes in sanitized_changes.items():
            for ctype, scoped_changes in changes.items():
                if ctype == 'create':
                    for rid, data in scoped_changes.items():
                        # Full new resource validation
                        r = MAPPING[rtype](rid, data)
                        r.validate()
                        r.set_defaults()
                        xv = MAPPING[rtype].CALLBACKS['extra_validations']
                        logs = xv(conf, {}, r.get_resource())
                        if logs:
                            validation_logs.extend(logs)
                            raise ResourceInvalidException(
                                "Resource [type: %s, ID: %s] extra "
                                "validations failed" % (rtype, rid))
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be created." % (rtype, rid))
                if ctype == 'update':
                    for rid, data in scoped_changes.items():
                        # Full new resource validation
                        r = MAPPING[rtype](rid, data['data'])
                        r.validate()
                        xv = MAPPING[rtype].CALLBACKS['extra_validations']
                        logs = xv(conf, {}, data['data'])
                        if logs:
                            validation_logs.extend(logs)
                            raise ResourceInvalidException(
                                "Resource [type: %s, ID: %s] extra "
                                "validations failed")
                        # Check key changes are possible
                        if not all([r.is_mutable(k) for
                                    k in data['changed']]):
                            raise YAMLDBException(
                                "Resource [type: %s, ID: %s] contains changed "
                                "resource keys that are immutable. "
                                "Please check the model." % (
                                    rtype, rid))
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be updated." % (rtype, rid))
                if ctype == 'delete':
                    for rid, data in scoped_changes.items():
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be deleted." % (rtype, rid))

    def _get_resources_priority(self):
        priorities = [(rtype, obj.PRIORITY) for
                      rtype, obj in MAPPING.items()]
        return sorted(priorities, key=lambda p: p[1], reverse=True)

    def _apply_changes(self, sanitized_changes, apply_logs, new):
        partial = False
        priorities = self._get_resources_priority()
        for rtype, priority in priorities:
            if rtype not in sanitized_changes:
                continue
            for ctype, datas in sanitized_changes[rtype].items():
                for rid, data in datas.items():
                    apply_logs.append(
                        "Resource [type: %s, ID: %s] will be %s." % (
                            rtype, rid, ctype + 'd'))
                    logs = []
                    if ctype == 'update':
                        logs = MAPPING[rtype].CALLBACKS[ctype](
                            conf, new, data['data'])
                    else:
                        r = MAPPING[rtype](rid, data)
                        r.set_defaults()
                        _data = r.get_resource()
                        logs = MAPPING[rtype].CALLBACKS[ctype](
                            conf, new, _data)
                    if logs:
                        # We have logs here meaning callback call
                        # has encountered some troubles
                        apply_logs.extend(logs)
                        partial = True
                        apply_logs.append(
                            "Resource [type: %s, ID: %s] %s op failed." % (
                                rtype, rid, ctype))
                    else:
                        apply_logs.append(
                            "Resource [type: %s, ID: %s] has been %s." % (
                                rtype, rid, ctype + 'd'))
        return partial

    def _resolv_resources_need_refresh(self, sanitized_changes, tree):
        def scan(logs):
            u_resources = {}
            for rtype in sanitized_changes:
                u_resources[rtype] = sanitized_changes[rtype]['update'].keys()

            if not any([len(ids) for ids in u_resources.values()]):
                return logs

            for rtype, resources in tree['resources'].items():
                for rid, data in resources.items():
                    r = MAPPING[rtype](rid, data)
                    deps = r.get_deps()
                    for deps_type, deps_ids in deps.items():
                        if (deps_type in u_resources and
                                deps_ids & set(u_resources[deps_type])):
                            sanitized_changes.setdefault(rtype, {'update': {}})
                            if rid not in sanitized_changes[rtype]['update']:
                                logs.append(
                                    "Resource [type: %s, ID: %s] need a "
                                    "refresh as at least one of its "
                                    "dependencies has been updated" % (
                                        rtype, rid))
                                sanitized_changes[rtype]['update'][rid] = {
                                    'data': data}
        logs = []
        # Do it 3 times to resolv deps of max 3 depths
        for _ in xrange(3):
            scan(logs)
        return logs

    def _load_resource_data(self, repo_uri, ref, mark):
        cpath = os.path.join(self.workdir, mark)
        if not os.path.isdir(cpath):
            os.mkdir(cpath)

        bkd = YAMLBackend(repo_uri, ref,
                          self.subdir, cpath,
                          "%s_cache" % cpath)

        return bkd.get_data()

    def _load_resources_data(self, repo_prev_uri, prev_ref,
                             repo_new_uri, new_ref):
        prev_data = self._load_resource_data(
            repo_prev_uri, prev_ref, 'prev')
        new_data = self._load_resource_data(
            repo_new_uri, new_ref, 'new')
        return prev_data, new_data

    def validate(self, repo_prev_uri, prev_ref,
                 repo_new_uri, new_ref):
        logger.info("Resources engine: validate resources requested"
                    "(old ref: %s, new ref: %s)" % (prev_ref, new_ref))
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        validation_logs = []
        try:
            prev, new = self._load_resources_data(
                repo_prev_uri, prev_ref, repo_new_uri, new_ref)
            changes = self._get_data_diff(prev, new)
            self._validate_changes(changes, validation_logs)
            self._check_deps_constraints(new)
            validation_logs.extend(
                self._resolv_resources_need_refresh(changes, new))
        except (YAMLDBException,
                ModelInvalidException,
                ResourceInvalidException,
                ResourceDepsException), e:
            validation_logs.append(e.msg)
            for l in validation_logs:
                logger.info(l)
            return False, validation_logs
        for l in validation_logs:
            logger.info(l)
        return True, validation_logs

    def apply(self, repo_prev_uri, prev_ref,
              repo_new_uri, new_ref):
        logger.info("Resources engine: apply resources requested"
                    "(old ref: %s, new ref: %s)" % (prev_ref, new_ref))
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        apply_logs = []
        try:
            prev, new = self._load_resources_data(
                repo_prev_uri, prev_ref, repo_new_uri, new_ref)
            changes = self._get_data_diff(prev, new)
            logs = self._resolv_resources_need_refresh(changes, new)
            apply_logs.extend(logs)
            partial = self._apply_changes(changes, apply_logs, new)
        except YAMLDBException, e:
            apply_logs.append(e.msg)
            for l in apply_logs:
                logger.info(l)
            return False, apply_logs
        for l in apply_logs:
            logger.info(l)
        return not partial, apply_logs

    def get(self, cur_uri, cur_ref):
        logger.info("Resources engine: get resource tree requested")
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        current = YAMLBackend(cur_uri, cur_ref,
                              self.subdir, self.workdir,
                              "%s_cache" % self.workdir.rstrip('/'))
        return current.get_data()
