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
import yaml
import deepdiff
import tempfile

from unittest import TestCase

from managesf.model import yamlbackend


class YAMLBackendTest(TestCase):
    def setUp(self):
        _, self.db_path = tempfile.mkstemp()
        self.db = yamlbackend.YAMLBackend(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_init(self):
        self.assertTrue(os.path.isfile(self.db_path))
        self.assertEqual(
            len(deepdiff.DeepDiff(yamlbackend.DB_SCHEMA,
                                  yaml.load(file(self.db_path))
                                  ).keys()),
            0)

    def test_set_project_resource(self):
        # Get original db data
        data = self.db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
            'description': 'A CI project',
        }}
        data['resources']['projects'].update(p)
        ops = self.db.set_leafs(data)
        # Verify the backend return the right operation callbacks
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0][0], 'controllers.projects.create')
        self.assertDictEqual(ops[0][1],
                             {'description': 'A CI project',
                              'git-repo': 'software-factory',
                              'name': 'SF/software-factory'}
                             )
        # Get original db data
        data = self.db.get_leafs()
        # Change a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
            'description': 'A next gen CI project',
            'gitweb': 'http://gitweb.com/',
            'website': 'http://softwarefactory-project.io',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBUnsupportedOp,
                          lambda: self.db.set_leafs(data))

        # Get original db data
        data = self.db.get_leafs()
        # Del a project definition
        del data['resources']['projects']['SF/software-factory']
        ops = self.db.set_leafs(data)
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0][0], 'controllers.projects.delete')
        self.assertDictEqual(ops[0][1],
                             {'name': 'SF/software-factory'})

        # Get original db data
        data = self.db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'git-repo': 'software-factory',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBResourceBadSchema,
                          lambda: self.db.set_leafs(data))

        # Get original db data
        data = self.db.get_leafs()
        # Add a project definition
        p = {'SF/software-factory': {
            'description': 'A next gen CI project',
            'git-repo': 'software-factory',
            'wrongkey': 'software-factory',
        }}
        data['resources']['projects'].update(p)
        self.assertRaises(yamlbackend.YAMLDBResourceBadSchema,
                          lambda: self.db.set_leafs(data))
