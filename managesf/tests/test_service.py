#!/usr/bin/env python
#
# Copyright (C) 2015  Red Hat <licensing@enovance.com>
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
import time

from managesf.services import base
from managesf.tests import dummy_conf


class BaseServiceForTest(base.BaseServicePlugin):
    def configure_plugin(self, conf):
        self.conf = conf

    def _get_client(self, cookie=None, **kwargs):
        if time.time() > 1000:
            return "client2"
        else:
            return "client1"


class TestService(TestCase):
    @classmethod
    def setupClass(cls):
        cls.conf = dummy_conf()
        cls.service = BaseServiceForTest(cls.conf)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_is_admin(self):
        self.assertEqual(True,
                         self.service.role.is_admin(self.conf.admin['name']))
        self.assertEqual(False,
                         self.service.role.is_admin('YOLO LMAO'))

    def test_cached_client(self):
        with patch('time.time') as t:
            t.return_value = 1
            self.assertEqual("client1",
                             self.service.get_client())
            # client has changed but we still use the cached version
            t.return_value = 2000
            self.assertEqual("client1",
                             self.service.get_client())
            self.assertEqual("client2",
                             self.service._get_client())
            t.return_value = 3700
            self.assertEqual("client2",
                             self.service.get_client())