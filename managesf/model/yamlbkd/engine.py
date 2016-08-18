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

from managesf.model.yamlbkd.yamlbackend import YAMLBackend
from managesf.model.yamlbkd.project import Project

MAPPING = {'projects': Project}


class SFResourceBackendEngine(object):
    def __init__(self, workdir, subdir):
        self.workdir = workdir
        self.subdir = subdir

    def _get_data_diff(self, prev, new):
        changes = deepdiff.DeepDiff(prev, new)
        sanitized_changes = {}
        for ctype, elm in changes.items():
            for path, value in elm.items():
                rtype = re.search("root\['resources'\]\['([a-zA-Z]+)'\].*",
                                  path)
                rtype = rtype.groups()[0]
                assert rtype in MAPPING
                if rtype not in sanitized_changes:
                    sanitized_changes[rtype] = {}
                if ctype == 'iterable_item_added':
                    if 'create' not in sanitized_changes[rtype]:
                        sanitized_changes[rtype]['create'] = []
                    sanitized_changes[rtype]['create'].append(value)
                else:
                    raise NotImplementedError
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
