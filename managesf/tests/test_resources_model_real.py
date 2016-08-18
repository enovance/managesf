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

from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resources.gitrepository import GitRepository


class RealResourcesTest(TestCase):
    """ Validate the resources model. This test
    only try to instanciate the resource.
    """

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
