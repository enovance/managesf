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

from managesf.model.yamlbkd import engine
from managesf.model.yamlbkd.engine import SFResourceBackendEngine
from managesf.model.yamlbkd.engine import ResourceDepsException

from managesf.model.yamlbkd.yamlbackend import YAMLDBException
from managesf.model.yamlbkd.resource import BaseResource
from managesf.model.yamlbkd.resource import ModelInvalidException
from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resources.dummy import Dummy


engine.MAPPING = {'dummies': Dummy}


class EngineTest(TestCase):
    def setUp(self):
        self.to_delete = []

    def tearDown(self):
        for d in self.to_delete:
            shutil.rmtree(d)

    def test_init_engine(self):
        SFResourceBackendEngine('/tmp/dir',
                                'resources')

    def test_get_resources_priority(self):
        class A(BaseResource):
            PRIORITY = 60

        class B(BaseResource):
            PRIORITY = 40

        class C(BaseResource):
            PRIORITY = 55

        en = SFResourceBackendEngine(None, None)
        with patch.dict(engine.MAPPING,
                        {'dummies': Dummy,
                         'A': A,
                         'B': B,
                         'C': C}):
            # Resource callback will be called in that
            # order A, C, dummies, B
            self.assertEqual([('A', 60),
                              ('C', 55),
                              ('dummies', 50),
                              ('B', 40)],
                             en._get_resources_priority())
            self.assertTrue(len(en._get_resources_priority()), 4)

    def test_load_resource_data(self):
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
            en._load_resource_data(
                'http://sftests.com/r/config.git',
                'heads/master', 'mark')
        self.assertTrue(os.path.isdir(
            os.path.join(path, 'mark')))
        self.assertTrue(i.called)
        self.assertTrue(g.called)

    def test_load_resources_data(self):
        with patch('managesf.model.yamlbkd.engine.'
                   'SFResourceBackendEngine._load_resource_data') as l:
            l.return_value = {}
            en = SFResourceBackendEngine(None, None)
            en._load_resources_data(
                'http://sftests.com/r/config.git',
                'heads/master',
                'http://sftests.com/r/config.git',
                'changes/99/899/1')
        self.assertEqual(len(l.mock_calls), 2)

    def test_validate(self):
        path = tempfile.mkdtemp()
        self.to_delete.append(path)
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._get_data_diff'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._check_deps_constraints'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._validate_changes')]
        with nested(*patches) as (l, g, c, v):
            l.return_value = (None, None)
            engine = SFResourceBackendEngine(path, None)
            status, _ = engine.validate(None, None, None, None)
            self.assertTrue(l.called)
            self.assertTrue(g.called)
            self.assertTrue(c.called)
            self.assertTrue(v.called)
            self.assertTrue(status)
        with nested(*patches) as (l, g, c, v):
            l.side_effect = YAMLDBException('')
            engine = SFResourceBackendEngine(path, None)
            status, logs = engine.validate(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)
        with nested(*patches) as (l, g, c, v):
            l.return_value = (None, None)
            v.side_effect = ResourceInvalidException('')
            engine = SFResourceBackendEngine(path, None)
            status, logs = engine.validate(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)
        with nested(*patches) as (l, g, c, v):
            l.return_value = (None, None)
            c.side_effect = ResourceDepsException('')
            engine = SFResourceBackendEngine(path, None)
            status, logs = engine.validate(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)

    def test_apply(self):
        path = tempfile.mkdtemp()
        self.to_delete.append(path)
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._get_data_diff'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine.'
                  '_resolv_resources_need_refresh'),
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._apply_changes')]
        with nested(*patches) as (l, g, r, a):
            l.return_value = (None, None)
            a.return_value = False
            r.return_value = []
            engine = SFResourceBackendEngine(path, None)
            status, logs = engine.apply(None, None, None, None)
            self.assertTrue(l.called)
            self.assertTrue(g.called)
            self.assertTrue(r.called)
            self.assertTrue(a.called)
            self.assertTrue(status)
        with nested(*patches) as (l, g, r, v):
            l.side_effect = YAMLDBException('')
            engine = SFResourceBackendEngine(path, None)
            status, logs = engine.apply(None, None, None, None)
            self.assertEqual(len(logs), 1)
            self.assertFalse(status)

    def test_get(self):
        patches = [
            patch('managesf.model.yamlbkd.yamlbackend.'
                  'YAMLBackend.__init__'),
            patch('managesf.model.yamlbkd.yamlbackend.'
                  'YAMLBackend.get_data')]
        with nested(*patches) as (i, g):
            i.return_value = None
            g.return_value = True
            engine = SFResourceBackendEngine('/tmp/adir', None)
            data = engine.get(None, None)
            self.assertTrue(data)

    def test_get_data_diff(self):
        # Test add resource change detected
        prev = {'resources': {'dummies': {}}}
        new = {'resources': {'dummies': {'myprojectid': {
               'namespace': 'sf',
               'name': 'myproject'},
        }}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('dummies', ret)
        self.assertIn('create', ret['dummies'])
        self.assertIn('myprojectid', ret['dummies']['create'])
        self.assertDictEqual(new['resources']['dummies']['myprojectid'],
                             ret['dummies']['create']['myprojectid'])
        self.assertEqual(len(ret['dummies']['delete'].keys()), 0)
        self.assertEqual(len(ret['dummies']['update'].keys()), 0)
        # Test delete resource change detected
        prev = {'resources': {'dummies': {'myprojectid': {
                'namespace': 'sf',
                'name': 'myproject'},
        }}}
        new = {'resources': {'dummies': {}}}
        engine = SFResourceBackendEngine(None, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('myprojectid', ret['dummies']['delete'])
        self.assertEqual(len(ret['dummies']['create'].keys()), 0)
        self.assertEqual(len(ret['dummies']['update'].keys()), 0)
        # Test update resource change detected
        prev = {'resources': {'dummies': {'myprojectid': {
                'namespace': 'sf',
                'name': 'myproject'},
        }}}
        new = {'resources': {'dummies': {'myprojectid': {
               'namespace': 'sf',
               'name': 'mynewproject'},
        }}}
        path = tempfile.mkdtemp()
        self.to_delete.append(path)
        engine = SFResourceBackendEngine(path, None)
        ret = engine._get_data_diff(prev, new)
        self.assertIn('myprojectid', ret['dummies']['update'])
        self.assertIn(
            'name',
            ret['dummies']['update']['myprojectid']['changed'])
        self.assertDictEqual(
            new['resources']['dummies']['myprojectid'],
            ret['dummies']['update']['myprojectid']['data'])
        # Test that multiple resource changes are detected
        prev = {'resources': {
            'dummies': {
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
            'dummies': {
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
        self.assertDictEqual(ret['dummies']['delete']['superid'],
                             prev['resources']['dummies']['superid'])
        self.assertDictEqual(ret['dummies']['create']['myproject2id'],
                             new['resources']['dummies']['myproject2id'])
        self.assertIn('namespace',
                      ret['dummies']['update']['myprojectid']['changed'])
        self.assertIn('name',
                      ret['dummies']['update']['myprojectid']['changed'])
        self.assertDictEqual(ret['dummies']['update']['myprojectid']['data'],
                             new['resources']['dummies']['myprojectid'])
        self.assertDictEqual(ret['groups']['create']['mygroupid'],
                             new['resources']['groups']['mygroupid'])
        # Test update resource change detected on a list
        prev = {'resources': {'dummies': {'myprojectid': {
                'members': ['joe', 'paul']}}}}
        new = {'resources': {'dummies': {'myprojectid': {
               'members': ['paul']}}}}
        path = tempfile.mkdtemp()
        self.to_delete.append(path)
        engine = SFResourceBackendEngine(path, None)
        ret = engine._get_data_diff(prev, new)
        self.assertSetEqual(
            ret['dummies']['update']['myprojectid']['changed'],
            set(['members']))

    def test_validate_changes(self):
        engine = SFResourceBackendEngine(None, None)
        validation_logs = []
        with patch.object(Dummy, 'validate') as v:
            changes = {'dummies': {'create': {'myprojectid': {}}}}
            engine._validate_changes(changes, validation_logs)
            self.assertTrue(v.called)
            v.reset_mock()
            changes = {'dummies': {'update': {
                'myprojectid': {'data': {}, 'changed': []}}}}
            engine._validate_changes(changes, validation_logs)
            self.assertTrue(v.called)
            with patch.object(Dummy, 'is_mutable') as i:
                v.reset_mock()
                changes = {'dummies': {'update': {
                    'myprojectid': {'data': {}, 'changed': ['name']}}}}
                engine._validate_changes(changes, validation_logs)
                self.assertTrue(v.called)
                self.assertTrue(i.called)
        # Be sure we have 3 validation msgs
        self.assertTrue(len(validation_logs), 3)
        validation_logs = []
        with patch.object(Dummy, 'validate') as v:
            v.side_effect = ResourceInvalidException('')
            changes = {'dummies': {'create': {'myprojectid': {}}}}
            self.assertRaises(ResourceInvalidException,
                              engine._validate_changes,
                              changes,
                              validation_logs)
        with patch.object(Dummy, 'validate') as v:
            v.side_effect = ModelInvalidException('')
            changes = {'dummies': {'create': {'myprojectid': {}}}}
            self.assertRaises(ModelInvalidException,
                              engine._validate_changes,
                              changes,
                              validation_logs)
        # Verify extra validations will be handled
        validation_logs = []
        with patch('managesf.model.yamlbkd.resources.'
                   'dummy.DummyOps.extra_validations') as xv:
            xv.return_value = ['error msg1', ' error msg2']
            changes = {'dummies': {'create': {'myprojectid': {
                'namespace': 'sf', 'name': 'p1'}}}}
            self.assertRaises(ResourceInvalidException,
                              engine._validate_changes,
                              changes,
                              validation_logs)
            self.assertTrue(xv.called)
            self.assertListEqual(['error msg1', ' error msg2'],
                                 validation_logs)

    def test_check_deps_constraints(self):
        class Master(BaseResource):
            MODEL_TYPE = 'master'
            MODEL = {
                'key1': (str, "+*", True, None, True, "desc"),
                'key2': (list, "+*", True, None, True, "desc"),
            }
            PRIORITY = 40

            def get_deps(self):
                deps = {'dummies': set([])}
                deps['dummies'].add(self.resource['key1'])
                for e in self.resource['key2']:
                    deps['dummies'].add(e)
                return deps

        new = {
            'resources': {
                'dummies': {
                    'd1': {
                        'name': 'dummy1',
                        'namespace': 'space',
                    },
                    'd2': {
                        'name': 'dummy2',
                        'namespace': 'space',
                    },
                    'd3': {
                        'name': 'dummy3',
                        'namespace': 'space',
                    },
                },
                'masters': {
                    'm1': {
                        'key1': 'd1',
                        'key2': ['d1', 'd2'],
                    }
                }
            }
        }

        en = SFResourceBackendEngine(None, None)
        with patch.dict(engine.MAPPING,
                        {'dummies': Dummy,
                         'masters': Master}):
            en._check_deps_constraints(new)
            # Add an unknown dependency
            new['resources']['masters']['m1']['key1'] = 'd4'
            self.assertRaises(ResourceDepsException,
                              en._check_deps_constraints,
                              new)

    def test_resolv_resources_need_refresh(self):
        class Master(BaseResource):
            MODEL_TYPE = 'master'
            MODEL = {
                'key': (list, "+*", True, None, True, "desc"),
            }
            PRIORITY = 40

            def get_deps(self):
                deps = {'dummies': set([])}
                deps['dummies'].add(self.resource['key'])
                return deps

        # Engine dectected dummies:d1 has been updated
        changes = {'dummies': {'update': {'d1': {}}}}

        # But masters:m1:key depends on d1
        tree = {
            'resources': {
                'dummies': {
                    'd1': {
                        'name': 'dummy1',
                        'namespace': 'space',
                    },
                },
                'masters': {
                    'm1': {
                        'key': 'd1',
                    }
                }
            }
        }

        en = SFResourceBackendEngine(None, None)
        with patch.dict(engine.MAPPING,
                        {'dummies': Dummy,
                         'masters': Master}):
            logs = en._resolv_resources_need_refresh(changes, tree)
            self.assertIn('m1', changes['masters']['update'])
            self.assertIn('d1', changes['dummies']['update'])
            self.assertIn('Resource [type: masters, ID: m1] need a '
                          'refresh as at least one of its dependencies '
                          'has been updated', logs)

    def test_apply_changes(self):
        engine = SFResourceBackendEngine(None, None)
        apply_logs = []
        with patch('managesf.model.yamlbkd.resources.'
                   'dummy.DummyOps.create') as c:
            c.return_value = []
            changes = {'dummies': {'create': {'myprojectid': {}}}}
            engine._apply_changes(changes, apply_logs, {})
            self.assertTrue(c.called)
        self.assertIn(
            'Resource [type: dummies, ID: myprojectid] '
            'will be created.',
            apply_logs)
        self.assertIn(
            'Resource [type: dummies, ID: myprojectid] '
            'has been created.',
            apply_logs)
        self.assertTrue(len(apply_logs), 2)

        apply_logs = []
        with patch('managesf.model.yamlbkd.resources.'
                   'dummy.DummyOps.create') as c:
            c.return_value = ["Resource API error"]
            changes = {'dummies': {'create': {'myprojectid': {}}}}
            self.assertTrue(engine._apply_changes(changes, apply_logs, {}))

        apply_logs = []
        with patch('managesf.model.yamlbkd.resources.'
                   'dummy.DummyOps.create') as c:
            c.return_value = ["Resource API error"]
            changes = {
                'dummies': {
                    'create': {
                        'myprojectid': {}
                    },
                    'update': {
                        'myprojectid2': {
                            'data': {'key': 'value'},
                            'changed': ['key']
                        }
                    }
                }
            }
            self.assertTrue(engine._apply_changes(changes, apply_logs, {}))
            self.assertIn('Resource [type: dummies, ID: myprojectid] '
                          'will be created.',
                          apply_logs)
            self.assertIn('Resource API error',
                          apply_logs)
            self.assertIn('Resource [type: dummies, ID: myprojectid] '
                          'create op failed.',
                          apply_logs)
            self.assertIn('Resource [type: dummies, ID: myprojectid2] '
                          'will be updated.',
                          apply_logs)
            self.assertIn('Resource [type: dummies, ID: myprojectid2] '
                          'has been updated.',
                          apply_logs)
