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

from managesf.model.yamlbkd import yamlbackend


class YAMLBackendTest(TestCase):
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

    def test_load_valid_db_data(self):
        # Prepare a GIT repo with content
        repo_path = self.prepare_git_repo()
        # Add a file of data
        data = {'resources': {'projects': [{
                'id': 'resource_a',
                }]}}
        self.add_yaml_data(repo_path, data)
        # Init the YAML DB
        clone_path = tempfile.mkdtemp()
        db = yamlbackend.YAMLBackend("file://%s" % repo_path,
                                     "master", "resources",
                                     clone_path)
        self.assertIn('resource_a', [p['id'] for p in
                      db.get_data()['resources']['projects']])
        # Add another file of data
        data = {'resources': {'projects': [{
                'id': 'resource_b',
                }]}}
        self.add_yaml_data(repo_path, data)
        db.refresh()
        project_ids = [p['id'] for p in
                       db.get_data()['resources']['projects']]
        self.assertIn('resource_a', project_ids)
        self.assertIn('resource_b', project_ids)
        self.assertEqual(len(project_ids), 2)
        # Add another file of data for another resource
        data = {'resources': {'groups': [{
                'id': 'resource_b',
                }]}}
        self.add_yaml_data(repo_path, data)
        db.refresh()
        group_ids = [p['id'] for p in
                     db.get_data()['resources']['groups']]
        self.assertIn('resource_b', group_ids)

    def test_load_invalid_db_data(self):
        # Prepare a GIT repo with content
        repo_path = self.prepare_git_repo()
        # Add a file of invalid data
        data = {'resources': {'projects': [
                {'id': 'resource_b'},
                {'id': 'resource_b'}
                ]}}
        self.add_yaml_data(repo_path, data)
        # Init the YAML DB
        clone_path = tempfile.mkdtemp()
        with self.assertRaises(yamlbackend.YAMLDBException):
            yamlbackend.YAMLBackend("file://%s" % repo_path,
                                    "master", "resources",
                                    clone_path)

    def test_db_data_struct(self):
        # Init the DB with validate data
        repo_path = self.prepare_git_repo()
        data = {'resources': {'projects': []}}
        self.add_yaml_data(repo_path, data)
        clone_path = tempfile.mkdtemp()
        db = yamlbackend.YAMLBackend("file://%s" % repo_path,
                                     "master", "resources",
                                     clone_path)
        # Try to validate a bunch a invalid data
        for data in [
            42,
            [],
            {'wrong': {}},
            {'resources': {4: []}},
            {'resources': {'projects': [None]}},
        ]:
            self.assertRaises(yamlbackend.YAMLDBException,
                              db.validate, data)
