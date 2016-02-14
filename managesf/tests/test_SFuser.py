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

from mock import patch
from unittest import TestCase

from managesf.controllers import SFuser
from managesf.tests import dummy_conf


class SFuserController(TestCase):
    @classmethod
    def setupClass(cls):
        cls.conf = dummy_conf()
        SFuser.model.conf = cls.conf

    def setUp(self):
        SFuser.model.init_model()

    def tearDown(self):
        os.unlink(self.conf.sqlalchemy['url'][len('sqlite:///'):])

    def test_create(self):
        u = SFuser.SFUserManager()
        id = u.create(username='SpongeBob',
                      email='SquarePants',
                      fullname='Sp. Sq.',
                      cauth_id=17)
        self.assertEqual(str(id),
                         SFuser.crud.get(username='SpongeBob').get('id'))
        # recreating the same user returns the same id
        id1 = u.create(username='SpongeBob',
                       email='SquarePants',
                       fullname='Sp. Sq.',
                       cauth_id=17)
        self.assertEqual(str(id1),
                         str(id))
        # if cauth_id is reset, it is updated
        id2 = u.create(username='SpongeBob',
                       email='SquarePants',
                       fullname='Sp. Sq.',
                       cauth_id=24)
        self.assertEqual(str(id2),
                         str(id))
        self.assertEqual('24',
                         SFuser.crud.get(id2).get('cauth_id'))
        # cauth_id acts as Authoritah
        id3 = u.create(username='Jake',
                       email='the Dog',
                       fullname='J. the Dog',
                       cauth_id=24)
        self.assertEqual(str(id3),
                         str(id))
        self.assertEqual('Jake',
                         SFuser.crud.get(id3).get('username'))
        self.assertEqual('the Dog',
                         SFuser.crud.get(id3).get('email'))
        self.assertEqual('J. the Dog',
                         SFuser.crud.get(id3).get('fullname'))
        # create another user, default cauth_id is -1
        id4 = u.create(username='Finn',
                       email='the Human',
                       fullname='F. The Human')
        self.assertTrue(str(id4) != str(id))
        self.assertEqual('-1',
                         SFuser.crud.get(id4).get('cauth_id'))
        # create another user, make sure it does not update Finn
        id5 = u.create(username='Bonnibel',
                       email='Bubblegum',
                       fullname='Princess Bubblegum')
        self.assertTrue(str(id4) != str(id5))

    def test_get(self):
        u = SFuser.SFUserManager()
        u.create(username='Bonnibel',
                 email='Bubblegum',
                 fullname='Princess Bubblegum')
        u.create(username='Finn',
                 email='the Human',
                 fullname='F. The Human')
        id = u.create(username='Jake',
                      email='the Dog',
                      fullname='J. the Dog',
                      cauth_id=24)
        self.assertEqual('Bonnibel',
                         u.get(username='Bonnibel')['username'])
        self.assertEqual('Bubblegum',
                         u.get(username='Bonnibel',
                               fullname='Princess Bubblegum')['email'])
        self.assertEqual('Finn',
                         u.get(email='the Human')['username'])
        self.assertEqual('the Human',
                         u.get(email='the Human')['email'])
        self.assertEqual('Jake',
                         u.get(fullname='J. the Dog')['username'])
        self.assertEqual('the Dog',
                         u.get(fullname='J. the Dog')['email'])
        self.assertEqual('Jake',
                         u.get(cauth_id=24)['username'])
        self.assertEqual({},
                         u.get(username='BMO'))
        self.assertRaises(KeyError,
                          u.get, cauth_id=-1)

    def test_all(self):
        u = SFuser.SFUserManager()
        u.create(username='Bonnibel',
                 email='Bubblegum',
                 fullname='Princess Bubblegum')
        u.create(username='Finn',
                 email='the Human',
                 fullname='F. The Human')
        u.create(username='Jake',
                 email='the Dog',
                 fullname='J. the Dog',
                 cauth_id=24)        
        u.create(username='Gunther',
                 email='the Penguin',
                 fullname='Orgalorg the Destroyer')
        self.assertEqual(4,
                         len(u.all()))

    def test_update(self):
        u = SFuser.SFUserManager()
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum')
        bonnibel = u.get(pb)
        # updating a non existing user does nothing
        self.assertEqual(None,
                         u.update(pb+2))
        u.update(pb, username='Marceline')
        self.assertEqual('Marceline', u.get(pb)['username'])
        u.update(pb, email='The Vampire')
        self.assertEqual('The Vampire', u.get(pb)['email'])
        u.update(pb, fullname='M the V')
        self.assertEqual('M the V', u.get(pb)['fullname'])
        u.update(pb, username='Bonnibel',
                 email='Bubblegum', fullname='Princess Bubblegum')
        self.assertEqual(bonnibel,
                         u.get(pb))

    def test_reset_cauth_id(self):
        u = SFuser.SFUserManager()
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        bonnibel = u.get(pb)
        self.assertEqual('23',
                         bonnibel['cauth_id'])
        u.reset_cauth_id(pb, 42)
        bonnibel = u.get(pb)
        self.assertEqual('42',
                         bonnibel['cauth_id'])

    def test_delete(self):
        u = SFuser.SFUserManager()
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        u.delete(pb)
        self.assertEqual({},
                         u.get(username='Bonnibel'))
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        u.delete(username='Bonnibel')
        self.assertEqual({},
                         u.get(username='Bonnibel'))
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        u.delete(email='Bubblegum')
        self.assertEqual({},
                         u.get(username='Bonnibel'))
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        u.delete(fullname='Princess Bubblegum')
        self.assertEqual({},
                         u.get(username='Bonnibel'))
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        u.delete(cauth_id=23)
        self.assertEqual({},
                         u.get(username='Bonnibel'))
        pb = u.create(username='Bonnibel',
                      email='Bubblegum',
                      fullname='Princess Bubblegum',
                      cauth_id=23)
        self.assertFalse(u.delete(username='SusanStrong'))
        u.delete(cauth_id=23, email='Bubblegum')
        self.assertEqual({},
                         u.get(username='Bonnibel'))
