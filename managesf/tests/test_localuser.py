# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Red Hat, Inc.
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

from unittest import TestCase

from basicauth import encode

from managesf.controllers import localuser
from managesf.tests import dummy_conf


class TestLocaluserController(TestCase):
    @classmethod
    def setupClass(cls):
        cls.conf = dummy_conf()
        localuser.conf = cls.conf
        localuser.model.conf = cls.conf

    def setUp(self):
        localuser.model.init_model()

    def tearDown(self):
        os.unlink(self.conf.sqlalchemy['url'][len('sqlite:///'):])

    # TODO The access control logic is not in the localuser controller anymore,
    # most of these tests are probably redundant

    def test_add_user_as_admin(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        expected = {'username': 'john',
                    'fullname': 'John Doe',
                    'email': 'john@tests.dom',
                    'sshkey': 'None'}
        ret = localuser.model.get_user('john')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)

    def test_add_update_user_bad_input(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'hashed_password': "abc"}
        self.assertRaises(localuser.InvalidInfosInput,
                          lambda: localuser.update_user('john', infos))

    def test_update_user_as_admin(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        infos = {'fullname': 'Maria Doe',
                 'email': 'maria@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        expected = {'username': 'john',
                    'fullname': 'Maria Doe',
                    'email': 'maria@tests.dom',
                    'sshkey': 'None'}
        ret = localuser.model.get_user('john')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)

    def test_update_user_as_owner(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        # John trying to update its account

        infos = {'fullname': 'Maria Doe',
                 'email': 'maria@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        expected = {'username': 'john',
                    'email': 'maria@tests.dom',
                    'fullname': 'Maria Doe',
                    'sshkey': 'None'}
        ret = localuser.model.get_user('john')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)

    def test_delete_user_as_admin(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        self.assertIsInstance(localuser.model.get_user('john'), dict)
        localuser.delete_user('john')
        self.assertFalse(localuser.model.get_user('john'))
        # Also test good behavior trying to remove user that not exixt
        self.assertRaises(localuser.UserNotFound,
                          lambda: localuser.delete_user('john'))

    def test_get_user(self):
        infos = {'fullname': 'John Doe',
                 'email': 'john@tests.dom',
                 'password': "abc"}
        localuser.update_user('john', infos)
        expected = {'username': 'john',
                    'email': 'john@tests.dom',
                    'fullname': 'John Doe',
                    'sshkey': 'None'}
        ret = localuser.model.get_user('john')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)
        ret = localuser.model.get_user('john')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)
        self.assertRaises(localuser.UserNotFound,
                          lambda: localuser.get_user('maria'))

    def test_bind_user(self):
        base_infos = {'fullname': 'John Doe',
                      'email': 'john@tests.dom', }
        infos = {'password': "abc"}
        public_infos = {'username': 'john', 'sshkey': 'None'}
        infos.update(base_infos)
        public_infos.update(base_infos)
        localuser.update_user('john', infos)
        authorization = encode('john', "abc")
        self.assertEqual(public_infos,
                         localuser.bind_user(authorization),
                         localuser.bind_user(authorization))
        authorization = encode('john', "abc123")
        self.assertRaises(localuser.BindForbidden,
                          lambda: localuser.bind_user(authorization))
        authorization = encode('denis', "abc")
        self.assertRaises(localuser.UserNotFound,
                          lambda: localuser.bind_user(authorization))

    def test_unicode_user(self):
        infos = {'fullname': u'うずまきナルト',
                 'email': 'hokage@konoha',
                 'password': "abc"}
        localuser.update_user(u'七代目火影4lyf', infos)
        expected = {'username': u'七代目火影4lyf',
                    'fullname': u'うずまきナルト',
                    'email': 'hokage@konoha',
                    'sshkey': 'None'}
        ret = localuser.model.get_user(u'七代目火影4lyf')
        del ret['hashed_password']
        self.assertDictEqual(ret, expected)
        authorization = encode(u'七代目火影4lyf'.encode('utf8'), "abc")
        self.assertDictEqual(expected,
                             localuser.bind_user(authorization),
                             localuser.bind_user(authorization))
