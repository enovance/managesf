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

from managesf.model.yamlbkd.yamlbackend import YAMLBackend
from managesf.model.yamlbkd.yamlbackend import YAMLDBException
from managesf.model.yamlbkd.resource import ModelInvalidException
from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.project import Project

logger = logging.getLogger(__name__)

MAPPING = {'projects': Project}

# TODO: (fbo) be sure to use different workdir
# for the config-check and config-update. This
# need to be done in the managesf controller when
# instanciating this SFResourceBackendEngine.


class SFResourceBackendEngine(object):
    def __init__(self, workdir, subdir):
        self.workdir = workdir
        self.subdir = subdir
        logger.info('Resource engine is using %s as workdir' % (
                    self.workdir))

    def _get_update_change(self, prev, new, rids):
        r_key_changes = {}
        for rid in rids:
            changes = deepdiff.DeepDiff(prev[rid], new[rid])
            if not changes:
                continue
            r_key_changes[rid] = {'data': new[rid], 'changed': []}
            for ctype, _changes in changes.items():
                if ctype == 'values_changed':
                    for c in _changes:
                        key = re.search("root\['([a-zA-Z0-9]+)'\]$", c)
                        key = key.groups()[0]
                        r_key_changes[rid]['changed'].append(key)
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
                prev['resources'][rtype], new['resources'][rtype],
                changed_resources_ids[rtype])
        return sanitized_changes

    def _validate_changes(self, sanitized_changes, validation_logs):
        for rtype, changes in sanitized_changes.items():
            for ctype, scoped_changes in changes.items():
                if ctype == 'create':
                    for rid, data in scoped_changes.items():
                        # Full new resource validation
                        MAPPING[rtype](rid, data).validate()
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be created." % (rtype, rid))
                if ctype == 'update':
                    for rid, data in scoped_changes.items():
                        # Full new resource validation
                        r = MAPPING[rtype](rid, data['data'])
                        r.validate()
                        # Check key changes are possible
                        if not all([r.is_mutable(k) for
                                    k in data['changed']]):
                            raise YAMLDBException(
                                "Resource [type: %s, ID: %s] contains changed "
                                "resource keys (%s) that are immutable. "
                                "Please check the model." % (
                                    rtype, rid, data['changed']))
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be updated." % (rtype, rid))
                if ctype == 'delete':
                    for rid, data in scoped_changes.items():
                        validation_logs.append(
                            "Resource [type: %s, ID: %s] is going to "
                            "be deleted." % (rtype, rid))

    def _apply_changes(self, sanitized_changes, apply_logs):
        apply_logs.append('Not Implemented yet')
        return apply_logs

    def _load_resources_data(self, repo_prev_uri, prev_ref,
                             repo_new_uri, new_ref):
        prev_path = os.path.join(self.workdir, 'prev')
        new_path = os.path.join(self.workdir, 'new')
        for path in (prev_path, new_path):
            if not os.path.isdir(path):
                os.mkdir(path)

        # Load the previous state repository at prev_ref
        prev = YAMLBackend(repo_prev_uri, prev_ref,
                           self.subdir, prev_path,
                           "%s_cache" % prev_path)

        # Load the new state repository at new_ref
        new = YAMLBackend(repo_new_uri, new_ref,
                          self.subdir, new_path,
                          "%s_cache" % new_path)

        return prev.get_data(), new.get_data()

    def validate(self, repo_prev_uri, prev_ref,
                 repo_new_uri, new_ref):
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        validation_logs = []
        try:
            prev, new = self._load_resources_data(
                repo_prev_uri, prev_ref, repo_new_uri, new_ref)
            changes = self._get_data_diff(prev, new)
            self._validate_changes(changes, validation_logs)
        except (YAMLDBException,
                ModelInvalidException,
                ResourceInvalidException), e:
            validation_logs.append(e.msg)
            return False, validation_logs
        return True, validation_logs

    def apply(self, repo_prev_uri, prev_ref,
              repo_new_uri, new_ref):
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        apply_logs = []
        try:
            prev, new = self._load_resources_data(
                repo_prev_uri, prev_ref, repo_new_uri, new_ref)
            changes = self._get_data_diff(prev, new)
            self._apply_changes(changes, apply_logs)
        except (YAMLDBException), e:
            apply_logs.append(e.msg)
            return False, apply_logs
        return True, apply_logs

    def get(self, cur_uri, cur_ref):
        if not os.path.isdir(self.workdir):
            os.mkdir(self.workdir)
        current = YAMLBackend(cur_uri, cur_ref,
                              self.subdir, self.workdir,
                              "%s_cache" % self.workdir.rstrip('/'))
        return current.get_data()
