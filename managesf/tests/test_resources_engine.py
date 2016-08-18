# -*- coding: utf-8 -*-
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
import yaml
import shutil
import tempfile

from unittest import TestCase

from managesf.model.yamlbkd.engine import SFResourceBackendEngine

# TODO(fbo): remove duplicated code between this file and
# YAMLBackendTest


class EngineTest(TestCase):
    def setUp(self):
        self.db_path = []

    def tearDown(self):
        for db_path in self.db_path:
            if os.path.isdir(db_path):
                shutil.rmtree(db_path)
            else:
                os.unlink(db_path)

    def prepare_git_repo(self):
        repo_path = tempfile.mkdtemp()
        self.db_path.append(repo_path)
        repo = git.Git(repo_path)
        repo.init()
        return repo_path

    def prepare_db_env(self):
        clone_path = tempfile.mkdtemp()
        self.db_path.append(clone_path)
        return clone_path

    def add_yaml_data(self, repo_path, data):
        repo = git.Git(repo_path)
        sub_dir = "resources"
        db_path = os.path.join(repo_path, sub_dir)
        if not os.path.isdir(db_path):
            os.mkdir(db_path)
        filename = "%s.yaml" % id(data)
        with open(os.path.join(db_path, filename), 'w') as dbfile:
            yaml.safe_dump(data,
                           dbfile,
                           allow_unicode=True,
                           default_flow_style=False)
        repo.execute(['git', 'add', sub_dir])
        repo.update_environment(GIT_AUTHOR_EMAIL='test@test.com')
        repo.update_environment(GIT_AUTHOR_NAME='test')
        repo.update_environment(GIT_COMMITTER_EMAIL='test@test.com')
        repo.update_environment(GIT_COMMITTER_NAME='test')
        repo.execute(['git', 'commit', '-m', 'add %s' % filename])
        return repo_path

    def test_validate(self):
        # Prepare a GIT repo with content
        repo_path = self.prepare_git_repo()
        data = {'resources': {'projects': []}}
        self.add_yaml_data(repo_path, data)
        data = {'resources': {'projects': [
            {'id': 'myprojectid',
             'namespace': 'sf',
             'name': 'myproject'},
        ]}}
        self.add_yaml_data(repo_path, data)
        workdir = self.prepare_db_env()
        engine = SFResourceBackendEngine(workdir, 'resources')
        engine.validate(repo_path, 'master^1', repo_path, 'master')
