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
import git
import logging
import yaml

from pecan import conf  # noqa

logger = logging.getLogger(__name__)

ID_FIELD = 'id'
RESOURCES_STRUCT = {'resources': {'rtype': [{}]}}


class YAMLDBException(Exception):
    def __init__(self, msg):
        logger.error(msg)


class YAMLBackend(object):
    def __init__(self, git_repo_url, git_branch, sub_dir, clone_path):
        self.git_repo_url = git_repo_url
        self.git_branch = git_branch
        self.clone_path = clone_path
        self.db_path = os.path.join(self.clone_path, sub_dir)
        self.refresh()

    def _update_git_clone(self):
        repo = git.Git(self.clone_path)
        repo.init()
        try:
            repo.execute(['git', 'remote', 'add',
                          'origin', self.git_repo_url])
        except Exception:
            logger.info("Re-using the remote %s." % self.git_repo_url)
        repo.execute(['git', 'fetch', 'origin'])
        repo.execute(['git', 'reset', '--hard',
                      'origin/%s' % self.git_branch])
        logger.info("Updated GIT repo %s branch %s." % (self.git_repo_url,
                                                        self.git_branch))

    def _load_db(self):
        check_ext = lambda f: f.endswith('.yaml') or f.endswith('.yml')
        yamlfiles = [f for f in os.listdir(self.db_path) if check_ext(f)]
        for f in yamlfiles:
            logger.info("Reading %s ..." % f)
            if not self.data:
                self.data = self.validate(yaml.load(
                    file(os.path.join(self.db_path, f))))
            else:
                data_to_append = self.validate(yaml.load(
                    file(os.path.join(self.db_path, f))))
                for rtype, resources in data_to_append['resources'].items():
                    if rtype not in self.data['resources']:
                        self.data['resources'][rtype] = []
                    self.data['resources'][rtype].extend(resources)

    def _validate_base_struct(self, data):
        try:
            assert isinstance(data, type(RESOURCES_STRUCT))
            assert isinstance(data['resources'],
                              type(RESOURCES_STRUCT['resources']))
        except (AssertionError, KeyError):
            raise YAMLDBException(
                "The main resource data structure is invalid")
        try:
            for rtype, resources in data['resources'].items():
                assert isinstance(rtype, str)
                assert isinstance(resources, list)
        except AssertionError:
            raise YAMLDBException(
                "Resource type %s structure is invalid" % rtype)
        try:
            for rtype, resources in data['resources'].items():
                for resource in data['resources'][rtype]:
                    assert isinstance(
                        resource,
                        type(RESOURCES_STRUCT['resources']['rtype'][0]))
        except AssertionError:
            raise YAMLDBException(
                "Resource %s of type %s is invalid" % (resource, rtype))

    def _validate_base_resource_constraint(self, data):
        for rtype, resources in data['resources'].items():
            for resource in resources:
                if ID_FIELD not in resource:
                    raise YAMLDBException('Mandatory "%s" key is missing'
                                          ' from the resource %s' % (
                                              ID_FIELD, resource))
                if rtype not in self.resources_ids:
                    self.resources_ids[rtype] = []
                if resource[ID_FIELD] in self.resources_ids[rtype]:
                    raise YAMLDBException('Resource %s (%s) duplicated' % (
                                          ID_FIELD, resource[ID_FIELD]))
                self.resources_ids[rtype].append(resource[ID_FIELD])

    def refresh(self):
        self.data = None
        self.resources_ids = {}
        self._update_git_clone()
        self._load_db()

    def validate(self, data):
        self._validate_base_struct(data)
        self._validate_base_resource_constraint(data)
        return data

    def get_data(self):
        return self.data
