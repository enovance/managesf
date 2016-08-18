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

    def _get_update_change(self, prev, new, rids):
        r_key_changes = {}
        for rid in rids:
            pr = [r for r in prev if r['id'] == rid][0]
            nr = [r for r in new if r['id'] == rid][0]
            changes = deepdiff.DeepDiff(pr, nr)
            if not changes:
                continue
            r_key_changes[rid] = []
            for ctype, _changes in changes.items():
                if ctype == 'values_changed':
                    for c in _changes:
                        key = re.search("root\['([a-zA-Z0-9]+)'\]$", c)
                        key = key.groups()[0]
                        r_key_changes[rid].append(key)
                else:
                    logger.info('Unexpected change type '
                                'detected for rid: %s' % rid)
            return r_key_changes

    def _get_data_diff(self, prev, new):
        previous_data_resources_ids = {}
        for rtype, resources in prev['resources'].items():
            previous_data_resources_ids[rtype] = set(
                [r['id'] for r in resources])
        new_data_resources_ids = {}
        for rtype, resources in new['resources'].items():
            new_data_resources_ids[rtype] = set(
                [r['id'] for r in resources])
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
                {'update': [], 'create': [], 'delete': []})
            sanitized_changes[rtype]['create'].extend([
                d for d in new['resources'][rtype]
                if d['id'] in new_resources_ids[rtype]])
            sanitized_changes[rtype]['delete'].extend([
                d for d in prev['resources'][rtype]
                if d['id'] in removed_resources_ids[rtype]])
            sanitized_changes[rtype]['update'] = self._get_update_change(
                prev['resources'][rtype], new['resources'][rtype],
                changed_resources_ids[rtype])
        return sanitized_changes

    def _validate_changes(self, sanitized_changes):
        for rtype, ctype in sanitized_changes.items():
            for change in ctype['create']:
                # Full new resource validation
                MAPPING[rtype](change).validate()

    def _apply_changes(self, sanitized_changes):
        pass

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
        prev, new = self._load_resources_data(
            repo_prev_uri, prev_ref, repo_new_uri, new_ref)
        changes = self._get_data_diff(prev, new)
        self._validate_changes(changes)

    def process(self, repo_prev_uri, prev_ref,
                repo_new_uri, new_ref):
        prev, new = self._load_resources_data(
            repo_prev_uri, prev_ref, repo_new_uri, new_ref)
        changes = self._get_data_diff(prev, new)
        self._apply_changes(changes)
