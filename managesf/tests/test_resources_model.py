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

from managesf.model.yamlbkd.resource import BaseResource
from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resource import ModelInvalidException


class ResourcesTest(TestCase):

    def test_base_resource(self):

        class R1(BaseResource):
            MODEL_TYPE = 'test'
            MODEL = {
                'key': (int, False, "string", "desc"),
            }
            PRIORITY = 10
        self.assertRaises(ModelInvalidException,
                          BaseResource, {})

        self.assertRaises(ModelInvalidException,
                          R1, {})

    def test_resource_model(self):
        class R1(BaseResource):
            MODEL_TYPE = 'test'
            MODEL = {
                'key': (int, True, None, "desc"),
                'key2': (str, False, "default", "desc"),
            }
            PRIORITY = 10
        res = R1({'id': 'the-id',
                  'key': 1})
        res.validate()
        res.enrich()
        resource = res.get_resource()
        self.assertIn('key2', resource)
        self.assertTrue(isinstance(resource['key2'],
                                   str))
        res = R1({'id': 'the-id',
                  'key': 'string'})
        self.assertRaises(ResourceInvalidException,
                          res.validate)
        res = R1({'id': 'the-id'})
        self.assertRaises(ResourceInvalidException,
                          res.validate)
        res = R1({'id': 'the-id',
                  'key': 1,
                  'extra': 'value'})
        self.assertRaises(ResourceInvalidException,
                          res.validate)
