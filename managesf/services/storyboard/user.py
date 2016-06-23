#!/usr/bin/env python
#
# Copyright (C) 2016 Red Hat
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


import logging

from managesf.services import base


logger = logging.getLogger(__name__)


class StoryboardUserManager(base.UserManager):
    """User management"""
    def create(self, username, email, lastname, **kwargs):
        client = self.plugin.get_client()
        is_superuser = False
        if username == "admin":
            is_superuser = True
        user = client.users.create(
            username=username,
            full_name=lastname,
            openid="None",
            is_superuser=is_superuser,
            enable_login=1)
        # Create fake access_token
        user.user_tokens.create(user_id=user.id, access_token=username,
                                expires_in=315360000)
        logger.debug(u'[%s] user %s created' % (self.plugin.service_name,
                                                unicode(user)))

    def get(self, mail=None, username=None):
        raise NotImplementedError

    def update(self, uid, full_name=None, username=None, email=None,
               **kwargs):
        raise NotImplementedError

    def delete(self, email=None, username=None):
        raise NotImplementedError
