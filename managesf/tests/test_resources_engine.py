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
import shutil
import tempfile

from unittest import TestCase
from mock import patch
from contextlib import nested

from managesf.model.yamlbkd.engine import SFResourceBackendEngine

from managesf.model.yamlbkd.project import Project


class EngineTest(TestCase):
    def setUp(self):
        self.to_delete = []

    def tearDown(self):
        for d in self.to_delete:
            shutil.rmtree(d)

    def test_init_engine(self):
        SFResourceBackendEngine('/tmp/dir',
                                'resources')

    def test_load_resources_data(self):
        path = tempfile.mkdtemp()
        self.to_delete.append(path)
        patches = [
            patch('managesf.model.yamlbkd.yamlbackend.'
                  'YAMLBackend.__init__'),
            patch('managesf.model.yamlbkd.yamlbackend.'
                  'YAMLBackend.get_data')]
        with nested(*patches) as (i, g):
            i.return_value = None
            g.return_value = {}
            en = SFResourceBackendEngine(path,
                                         'resources')
            en._load_resources_data(
                'http://sftests.com/r/config.git',
                'heads/master',
                'http://sftests.com/r/config.git',
                'changes/99/899/1')
        self.assertTrue(os.path.isdir(
            os.path.join(path, 'prev')))
        self.assertTrue(os.path.isdir(
            os.path.join(path, 'new')))
        self.assertEqual(len(i.mock_calls), 2)
        self.assertEqual(len(g.mock_calls), 2)

    def test_validate(self):
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._get_data_diff'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._validate_changes')]
        with nested(*patches) as (l, g, v):
            l.return_value = (None, None)
            engine = SFResourceBackendEngine(None, None)
            engine.validate(None, None, None, None)
            self.assertTrue(l.called)
            self.assertTrue(g.called)
            self.assertTrue(v.called)

    def test_apply(self):
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._get_data_diff'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._apply_changes')]
        with nested(*patches) as (l, g, a):
            l.return_value = (None, None)
            engine = SFResourceBackendEngine(None, None)
            engine.process(None, None, None, None)
            self.assertTrue(l.called)
            self.assertTrue(g.called)
            self.assertTrue(a.called)

    def test_get_data_diff(self):
        # Test add resource change detected
        prev = {'resources': {'projects': []}}
        new = {'resources': {'projects': [
            {'id': 'myprojectid',
             'namespace': 'sf',
             'name': 'myproject'},
        ]}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('projects', ret)
        self.assertIn('create', ret['projects'])
        self.assertEqual(ret['projects']['create'][0]['id'],
                         'myprojectid')
        # Test delete resource change detected
        prev = {'resources': {'projects': [
            {'id': 'myprojectid',
             'namespace': 'sf',
             'name': 'myproject'},
        ]}}
        new = {'resources': {'projects': []}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertEqual(ret['projects']['delete'][0]['id'],
                         'myprojectid')
        # Test update resource change detected
        prev = {'resources': {'projects': [
            {'id': 'myprojectid',
             'namespace': 'sf',
             'name': 'myproject'},
        ]}}
        new = {'resources': {'projects': [
            {'id': 'myprojectid',
             'namespace': 'sf',
             'name': 'mynewproject'},
        ]}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('myprojectid',
                      ret['projects']['update'])
        self.assertEqual(
            ret['projects']['update']['myprojectid'][0],
            'name')
        # Test that multiple resource changes are detected
        prev = {'resources': {
            'projects': [
                {'id': 'myprojectid',
                 'namespace': 'sf',
                 'name': 'myproject'},
                {'id': 'superid',
                 'namespace': 'super',
                 'name': 'project'}],
            'groups': []
        }}
        new = {'resources': {
            'projects': [
                {'id': 'myprojectid',
                 'namespace': 'sfnew',
                 'name': 'mynewproject'},
                {'id': 'myproject2id',
                 'namespace': 'sfnew',
                 'name': 'newproject'}],
            'groups': [
                {'id': 'mygroupid',
                 'name': 'mynewgroup'},
            ]
        }}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertDictEqual(ret['projects']['delete'][0],
                             prev['resources']['projects'][1])
        self.assertDictEqual(ret['projects']['create'][0],
                             new['resources']['projects'][1])
        self.assertIn('namespace',
                      ret['projects']['update']['myprojectid'])
        self.assertIn('name',
                      ret['projects']['update']['myprojectid'])
        self.assertDictEqual(ret['groups']['create'][0],
                             new['resources']['groups'][0])

    def test_validate_resources_changes(self):
        p = {'id': 'myprojectid'}
        changes = {'projects': {'create': [p]}}
        engine = SFResourceBackendEngine(None, None)
        with patch.object(Project, 'validate') as v:
            engine._validate_changes(changes)
            self.assertTrue(v.called)
