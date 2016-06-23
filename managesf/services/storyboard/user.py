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


import datetime
import logging
import sqlalchemy
from sqlalchemy import Table, Column, Integer, DateTime, String, MetaData

from managesf.services import base
import storyboardclient.openstack.common.apiclient.exceptions as sbexc


logger = logging.getLogger(__name__)


class StoryboardUserManager(base.UserManager):
    """User management"""

    def __init__(self, plugin):
        super(StoryboardUserManager, self).__init__(plugin)
        db_uri = 'mysql://%s:%s@%s/%s' % (self.plugin.conf['db_user'],
                                          self.plugin.conf['db_password'],
                                          self.plugin.conf['db_host'],
                                          self.plugin.conf['db_name'],)
        engine = sqlalchemy.create_engine(db_uri, echo=False,
                                          pool_recycle=600)
        Session = sqlalchemy.orm.sessionmaker(bind=engine)
        self.sql_session = Session()
        metadata = MetaData()
        self.users = Table(
            'users',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('created_at', DateTime),
            Column('updated_at', DateTime),
            Column('email', String),
            Column('is_staff', Integer),
            Column('is_superuser', Integer),
            Column('last_login', DateTime),
            Column('openid', String),
            Column('full_name', String),
            Column('enable_login', Integer),
        )
        self.client = self.plugin.get_client()

    def create_update_user(self, userid, email, fullname):
        # Use SQL instead of API to force userid
        if userid == 1:
            superuser = True
        else:
            superuser = False
        stm = self.users.select().where(self.users.c.id == userid)

        user = self.sql_session.execute(stm).fetchone()
        if user:
            values = {'updated_at': datetime.datetime.now()}
            if email:
                values['email'] = email
            if fullname:
                values['full_name'] = fullname

            stm = self.users.update(). \
                where(self.users.c.id == userid). \
                values(**values)
        else:
            stm = self.users.insert().values(
                id=userid,
                created_at=datetime.datetime.now(),
                email=email,
                is_superuser=superuser,
                openid="None",
                full_name=fullname,
            )
        logging.debug(u"Storyboard user create sql: [%s]" % unicode(stm))
        try:
            self.sql_session.execute(stm)
            self.sql_session.commit()
        except Exception as e:
            logger.error(u"Storyboard SQL failed %s [%s]" % (e, stm))
            self.sql_session.rollback()

    def create_update_user_token(self, userid, username):
        user = self.client.users.get(userid)
        try:
            user.user_tokens.create(user_id=userid, access_token=username,
                                    expires_in=315360000)
        except sbexc.Conflict:
            # token already exist
            pass
        return user

    def create(self, username, email, full_name, ssh_keys=None, user_id=None):
        self.create_update_user(user_id, email, full_name)
        user = self.create_update_user_token(user_id, username)
        logger.debug(u'[%s] uid=%s %s created' % (self.plugin.service_name,
                                                  user_id, unicode(user)))
        return user_id

    def update(self, uid, username=None, full_name=None, email=None, **kwargs):
        user = self.create_update_user_token(uid, username)
        logger.debug(u'[%s] user %s updated' % (self.plugin.service_name,
                                                unicode(user)))

    def get(self, mail=None, username=None):
        logger.debug(u'[%s] get mail=%s username=%s' % (
            self.plugin.service_name, mail, username))
        raise NotImplementedError

    def delete(self, email=None, username=None):
        logger.debug(u'[%s] delete email=%s username=%s' % (
            self.plugin.service_name, email, username))
        raise NotImplementedError
