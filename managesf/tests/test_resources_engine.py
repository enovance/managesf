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


from unittest import TestCase
from mock import patch

from managesf.model.yamlbkd.engine import SFResourceBackendEngine

from managesf.model.yamlbkd.project import Project


class EngineTest(TestCase):

    def test_init_engine(self):
        SFResourceBackendEngine('/tmp/dir',
                                'resources')

    def test_load_resources_data(self):
        pass

    def test_validate(self):
        pass

    def test_apply(self):
        pass

    def test_get_data_diff(self):
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
        # TODO(fbo): add more action, update, delete

    def test_validate_resources_changes(self):
        p = {'id': 'myprojectid'}
        changes = {'projects': {'create': [p]}}
        engine = SFResourceBackendEngine(None, None)
        with patch.object(Project, 'validate') as v:
            engine._validate_changes(changes)
            self.assertTrue(v.called)
