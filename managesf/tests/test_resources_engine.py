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

from managesf.model.yamlbkd.yamlbackend import YAMLDBException
from managesf.model.yamlbkd.resource import ModelInvalidException
from managesf.model.yamlbkd.resource import ResourceInvalidException


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
            status, _ = engine.validate(None, None, None, None)
            self.assertTrue(l.called)
            self.assertTrue(g.called)
            self.assertTrue(v.called)
            self.assertTrue(status)
        with nested(*patches) as (l, g, v):
            l.side_effect = YAMLDBException('')
            engine = SFResourceBackendEngine(None, None)
            status, logs = engine.validate(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)
        with nested(*patches) as (l, g, v):
            l.return_value = (None, None)
            v.side_effect = ResourceInvalidException('')
            engine = SFResourceBackendEngine(None, None)
            status, logs = engine.validate(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)

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
        prev = {'resources': {'projects': {}}}
        new = {'resources': {'projects': {'myprojectid': {
               'namespace': 'sf',
               'name': 'myproject'},
        }}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('projects', ret)
        self.assertIn('create', ret['projects'])
        self.assertIn('myprojectid', ret['projects']['create'])
        self.assertDictEqual(new['resources']['projects']['myprojectid'],
                             ret['projects']['create']['myprojectid'])
        self.assertEqual(len(ret['projects']['delete'].keys()), 0)
        self.assertEqual(len(ret['projects']['update'].keys()), 0)
        # Test delete resource change detected
        prev = {'resources': {'projects': {'myprojectid': {
                'namespace': 'sf',
                'name': 'myproject'},
        }}}
        new = {'resources': {'projects': {}}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('myprojectid', ret['projects']['delete'])
        self.assertEqual(len(ret['projects']['create'].keys()), 0)
        self.assertEqual(len(ret['projects']['update'].keys()), 0)
        # Test update resource change detected
        prev = {'resources': {'projects': {'myprojectid': {
                'namespace': 'sf',
                'name': 'myproject'},
        }}}
        new = {'resources': {'projects': {'myprojectid': {
               'namespace': 'sf',
               'name': 'mynewproject'},
        }}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('myprojectid', ret['projects']['update'])
        self.assertIn(
            'name',
            ret['projects']['update']['myprojectid']['changed'])
        self.assertDictEqual(
            new['resources']['projects']['myprojectid'],
            ret['projects']['update']['myprojectid']['data'])
        # Test that multiple resource changes are detected
        prev = {'resources': {
            'projects': {
                'myprojectid': {
                    'namespace': 'sf',
                    'name': 'myproject'},
                'superid': {
                    'namespace': 'super',
                    'name': 'project'}
            },
            'groups': {}
        }}
        new = {'resources': {
            'projects': {
                'myprojectid': {
                    'namespace': 'sfnew',
                    'name': 'mynewproject'},
                'myproject2id': {
                    'namespace': 'sfnew',
                    'name': 'newproject'}
                },
            'groups': {
                'mygroupid': {
                    'name': 'mynewgroup'},
            }
        }}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertDictEqual(ret['projects']['delete']['superid'],
                             prev['resources']['projects']['superid'])
        self.assertDictEqual(ret['projects']['create']['myproject2id'],
                             new['resources']['projects']['myproject2id'])
        self.assertIn('namespace',
                      ret['projects']['update']['myprojectid']['changed'])
        self.assertIn('name',
                      ret['projects']['update']['myprojectid']['changed'])
        self.assertDictEqual(ret['projects']['update']['myprojectid']['data'],
                             new['resources']['projects']['myprojectid'])
        self.assertDictEqual(ret['groups']['create']['mygroupid'],
                             new['resources']['groups']['mygroupid'])

    def test_validate_changes(self):
        engine = SFResourceBackendEngine(None, None)
        validation_logs = []
        with patch.object(Project, 'validate') as v:
            changes = {'projects': {'create': {'myprojectid': {}}}}
            engine._validate_changes(changes, validation_logs)
            self.assertTrue(v.called)
            v.reset_mock()
            changes = {'projects': {'update': {
                'myprojectid': {'data': {}, 'changed': []}}}}
            engine._validate_changes(changes, validation_logs)
            self.assertTrue(v.called)
            with patch.object(Project, 'is_mutable') as i:
                v.reset_mock()
                changes = {'projects': {'update': {
                    'myprojectid': {'data': {}, 'changed': ['name']}}}}
                engine._validate_changes(changes, validation_logs)
                self.assertTrue(v.called)
                self.assertTrue(i.called)
        # Be sure we have 3 validation msgs
        self.assertTrue(len(validation_logs), 3)
        with patch.object(Project, 'validate') as v:
            v.side_effect = ResourceInvalidException('')
            changes = {'projects': {'create': {'myprojectid': {}}}}
            self.assertRaises(ResourceInvalidException,
                              engine._validate_changes,
                              changes,
                              validation_logs)
        with patch.object(Project, 'validate') as v:
            v.side_effect = ModelInvalidException('')
            changes = {'projects': {'create': {'myprojectid': {}}}}
            self.assertRaises(ModelInvalidException,
                              engine._validate_changes,
                              changes,
                              validation_logs)
