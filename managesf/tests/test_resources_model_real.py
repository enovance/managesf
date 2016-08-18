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

from managesf.tests import dummy_conf

from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resources.gitrepository import GitRepository
from managesf.model.yamlbkd.resources.group import Group


class RealResourcesTest(TestCase):
    """ Validate the resources model. This test
    only try to instanciate the resource.
    """

    def setUp(self):
        self.conf = dummy_conf()

    def test_repo_resource(self):
        p = GitRepository('id', {})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software-factory',
                           'badkey': None,
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software factory',
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software-factory',
                           'description': 'SF'})
        p.validate()

    def test_repo_callbacks(self):
        with patch('managesf.services.gerrit.get_cookie'):
            with patch('pysflib.sfgerrit.GerritUtils.create_project') as cp:
                GitRepository.CALLBACKS['create'](
                    self.conf,
                    {'name': 'p1',
                     'namespace': 'awesome',
                     'description': 'An awesome project'}
                )
                self.assertTrue(cp.called)

    def test_group_resource(self):
        p = Group('id', {})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders'})
        p.validate()
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders',
                   'members': ['a@megacorp.com', 'b@megacorp.com']})
        p.validate()
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders',
                   'members': ['a@megacorp.com', 'abc']})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
