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
import deepdiff
import tempfile

from unittest import TestCase

from managesf.model import yamlbackend


class YAMLBackendTest(TestCase):
    def setUp(self):
        self.db_path = []

    def tearDown(self):
        for db_path in self.db_path:
            if os.path.isdir(db_path):
                shutil.rmtree(db_path)
            else:
                os.unlink(db_path)

    def test_flat_file_init(self):
        _, db_path = tempfile.mkstemp()
        self.db_path.append(db_path)
        yamlbackend.YAMLBackend(db_path)
        self.assertTrue(os.path.isfile(db_path))
        self.assertEqual(
            len(deepdiff.DeepDiff(yamlbackend.DB_SCHEMA,
                                  yaml.load(file(db_path))
                                  ).keys()),
            0)

    def test_flat_file_init_pre_existing(self):
        _, db_path = tempfile.mkstemp()
        self.db_path.append(db_path)
        # Init the backend with a resource
        db = yamlbackend.YAMLBackend(db_path)
        data = db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
            'description': 'A CI project',
        }}
        data['resources']['projects'].update(p)
        db.set_leafs(data)
        del db
        # Re-init the backend
        db = yamlbackend.YAMLBackend(db_path)
        data2 = db.get_leafs()
        # Check DB data has been loaded
        self.assertIn('SF/software-factory', data2['resources']['projects'])
        self.assertEqual(
            len(deepdiff.DeepDiff(data, data2).keys()),
            0)

    def test_git_dir_init(self):
        # Prepare a GIT repo with content
        db_path = tempfile.mkdtemp()
        self.db_path.append(db_path)
        repo = git.Git(db_path)
        repo.init()
        data = {'resources': {'projects': {
                'SF/software-factory': {
                    'git-repo': 'software-factory',
                    'description': 'A next gen CI project',
                    'gitweb': 'http://gitweb.com/',
                }}}}
        with open(os.path.join(db_path, '1.yaml'), 'w') as dbfile:
            yaml.safe_dump(data,
                           dbfile,
                           allow_unicode=True,
                           default_flow_style=False)
        repo.execute(['git', 'add', '1.yaml'])
        repo.update_environment(GIT_AUTHOR_EMAIL='test@test.com')
        repo.update_environment(GIT_COMMITTER_EMAIL='test@test.com')
        repo.execute(['git', 'commit', '-m', 'cmt1'])
        # Init the YAML DB
        db = yamlbackend.YAMLBackend(db_path)
        # Check the content has been loaded
        self.assertIn("resources", db.get_leafs())
        # Test to write directly
        data['resources']['projects']['SF/software-factory']['gitweb'] = ''
        self.assertRaises(yamlbackend.YAMLDBIsReadOnly,
                          lambda: db.set_leafs(data))

    def test_flat_file_set_project_resource(self):
        _, db_path = tempfile.mkstemp()
        self.db_path.append(db_path)
        db = yamlbackend.YAMLBackend(db_path)
        # Get original db data
        data = db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
            'description': 'A CI project',
        }}
        data['resources']['projects'].update(p)
        ops = db.set_leafs(data)
        # Verify the backend return the right operation callbacks
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0][0], 'controllers.projects.create')
        self.assertDictEqual(ops[0][1],
                             {'description': 'A CI project',
                              'git-repo': 'software-factory',
                              'name': 'SF/software-factory'}
                             )
        # Get original db data
        data = db.get_leafs()
        # Change a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
            'description': 'A next gen CI project',
            'gitweb': 'http://gitweb.com/',
            'website': 'http://softwarefactory-project.io',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBUnsupportedOp,
                          db.set_leafs, data)

        # Get original db data
        data = db.get_leafs()
        # Del a project definition
        del data['resources']['projects']['SF/software-factory']
        ops = db.set_leafs(data)
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0][0], 'controllers.projects.delete')
        self.assertDictEqual(ops[0][1],
                             {'name': 'SF/software-factory'})

        # Get original db data
        data = db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBResourceBadSchema,
                          lambda: db.set_leafs(data))

        # Get original db data
        data = db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'description': 'A next gen CI project',
            'git-repo': 'software-factory',
            'wrongkey': 'software-factory',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBResourceBadSchema,
                          lambda: db.set_leafs(data))

        # Get original db data
        data = db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {}}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBResourceBadSchema,
                          lambda: db.set_leafs(data))
