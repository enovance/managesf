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
    def __init__(self, git_repo_url, git_branch, sub_dir,
                 clone_path, cache_path):
        """ Class to read and validate resources from YAML
        files from stored in a GIT repository. The main data
        structure as well as resources structure must follow
        specific constraints.

        This Class also maintains a cache file to avoid full
        re-load and validation at init when ref hash has not
        changed.

        :param git_repo_url: The URI of the GIT repository
        :param git_branch: The GIT repository branch
        :param sub_dir: The path from the GIT root to YAML files
        :param clone_path: The path where to clone the GIT repository
        :param cache_path: The path to the cached file
        """
        self.git_repo_url = git_repo_url
        self.git_branch = git_branch
        self.clone_path = clone_path
        self.cache_path = cache_path
        self.cache_path_hash = "%s_%s" % (cache_path, '_hash')
        self.db_path = os.path.join(self.clone_path, sub_dir)
        self.refresh()

    def _get_repo_hash(self):
        repo = git.Git(self.clone_path)
        repo_hash = repo.execute(['git', '--no-pager', 'log', '-1',
                                  '--pretty=%h', self.git_branch])
        return repo_hash

    def _get_cache_hash(self):
        return file(self.cache_path_hash).read().strip()

    def _update_cache(self):
        repo_hash = self._get_repo_hash()
        yaml.dump(self.data, file(self.cache_path, 'w'))
        file(self.cache_path_hash, 'w').write(repo_hash)
        logger.info("Cache file has been updated.")

    def _load_from_cache(self):
        if not os.path.isfile(self.cache_path_hash):
            logger.info("No DB cache file found.")
        else:
            repo_hash = self._get_repo_hash()
            cached_repo_hash = self._get_cache_hash()
            if cached_repo_hash == repo_hash:
                self.data = yaml.load(file(self.cache_path))
                logger.info("Load data from the cache.")
            else:
                logger.info("DB cache is outdated.")

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
        def check_ext(f):
            return f.endswith('.yaml') or f.endswith('.yml')
        logger.info("Load data from the YAML files.")
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
        """ Reload of the YAML files.
        """
        self.data = None
        self._update_git_clone()
        self._load_from_cache()
        # Do a load from the file as cache is not up to date
        if not self.data:
            self.resources_ids = {}
            self._load_db()
            self._update_cache()

    def validate(self, data):
        """ Validate the resource data structure.
        """
        self._validate_base_struct(data)
        self._validate_base_resource_constraint(data)
        return data

    def get_data(self):
        """ Return the full data structure.
        """
        return self.data