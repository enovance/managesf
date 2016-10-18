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

import json
import urllib
import sqlalchemy

from requests.exceptions import HTTPError

from managesf.services.gerrit import SoftwareFactoryGerrit
from managesf.model.yamlbkd.resource import BaseResource

# ## DEBUG statements to ease run that standalone ###
# import logging
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
#
# from pecan import configuration
# from managesf.model.yamlbkd.resources.group import GroupOps
# conf = configuration.conf_from_file('/var/www/managesf/config.py')
# g = GroupOps(conf)
# g._set_client()
# ###


class GroupOps(object):

    def __init__(self, conf, new):
        self.conf = conf
        self.new = new

    def _set_client(self):
        gerrit = SoftwareFactoryGerrit(self.conf)
        self.client = gerrit.get_client()

    def group_update_description(self, name, description):
        data = json.dumps({
            "description": description,
        })
        try:
            name = urllib.quote_plus(name)
            self.client.g.put('groups/%s/description' % name,
                              data=data)
        except HTTPError as e:
            return self.client._manage_errors(e)

    def create(self, **kwargs):
        logs = []
        name = kwargs['name']
        members = kwargs['members']
        description = kwargs['description']

        self._set_client()

        try:
            ret = self.client.create_group(name,
                                           description)
            if ret is False:
                logs.append("Group create: err API returned HTTP 404/409")
        except Exception, e:
            logs.append("Group create: err API returned %s" % e)

        # Remove auto added admin
        try:
            ret = self.client.delete_group_member(
                name, self.conf.admin['email'])
            if ret is False:
                logs.append("Group create [del member: %s]: "
                            "err API returned HTTP 404/409" % (
                                self.conf.admin['email']))
        except Exception, e:
            logs.append("Group create [del member: admin]: "
                        "err API returned %s" % (
                            self.conf.admin['email'], e))

        if members:
            for member in members:
                try:
                    ret = self.client.add_group_member(member, name)
                    if ret is False:
                        logs.append("Group create [add member: %s]: "
                                    "err API returned HTTP 404/409" % member)
                except Exception, e:
                    logs.append("Group create [add member: %s]: "
                                "err API returned %s" % (member, e))

        return logs

    def delete(self, **kwargs):
        logs = []
        name = kwargs['name']

        self._set_client()

        # Needed for the final group delete
        db_uri = 'mysql://%s:%s@%s/%s?charset=utf8' % (
            self.conf.gerrit['db_user'],
            self.conf.gerrit['db_password'],
            self.conf.gerrit['db_host'],
            self.conf.gerrit['db_name'],
        )
        engine = sqlalchemy.create_engine(db_uri, echo=False,
                                          pool_recycle=600)
        Session = sqlalchemy.orm.sessionmaker(bind=engine)
        ses = Session()

        # Remove all group members to avoid left overs in the DB
        gid = self.client.get_group_id(name)
        current_members = [u['email'] for u in
                           self.client.get_group_members(gid)]
        for member in current_members:
            try:
                ret = self.client.delete_group_member(name, member)
                if ret is False:
                    logs.append("Group delete [del member: %s]: "
                                "err API returned HTTP 404/409" % member)
            except Exception, e:
                logs.append("Group delete [del member: %s]: "
                            "err API returned %s" % (member, e))

        # Remove all included groups members to avoid left overs in the DB
        grps = [g['name'] for
                g in self.client.get_group_group_members(gid)]
        for grp in grps:
            try:
                ret = self.client.delete_group_group_member(gid, grp)
                if ret is False:
                    logs.append("Group delete [del included group %s]: "
                                "err API returned HTTP 404/409" % grp)
            except Exception, e:
                logs.append("Group delete [del included group %s]: "
                            "err API returned %s" % (grp, e))

        # Final group delete (Gerrit API does not provide such action)
        sql = (u"DELETE FROM account_groups WHERE name='%s';"
               u"DELETE FROM account_group_names WHERE name='%s';" %
               (name, name))
        try:
            ses.execute(sql)
            ses.commit()
        except Exception as e:
            logs.append("Group delete: err SQL returned %s" % e)

        return logs

    def update(self, **kwargs):
        logs = []
        name = kwargs['name']
        members = kwargs['members']
        description = kwargs['description']

        self._set_client()

        gid = self.client.get_group_id(name)
        current_members = [u['email'] for u in
                           self.client.get_group_members(gid)]
        to_add = set(members) - set(current_members)
        to_del = set(current_members) - set(members)

        for mb in to_add:
            try:
                ret = self.client.add_group_member(mb, name)
                if ret is False:
                    logs.append("Group update [add member: %s]: "
                                "err API returned HTTP 404/409" % mb)
            except Exception, e:
                logs.append("Group update [add member: %s]: "
                            "err API returned %s" % (mb, e))

        for mb in to_del:
            try:
                ret = self.client.delete_group_member(name, mb)
                if ret is False:
                    logs.append("Group update [del member: %s]: "
                                "err API returned HTTP 404/409" % mb)
            except Exception, e:
                logs.append("Group update [del member: %s]: "
                            "err API returned %s" % (mb, e))

        try:
            ret = self.group_update_description(name, description)
            if ret is False:
                logs.append("Group update [update description]: "
                            "err API returned HTTP 404/409")
        except Exception, e:
            logs.append("Group update [update description]: "
                        "err API returned %s" % e)

        # Remove included groups if exist ! We are not supporting that
        grps = [g['name'] for
                g in self.client.get_group_group_members(gid)]
        for grp in grps:
            try:
                ret = self.client.delete_group_group_member(gid, grp)
                if ret is False:
                    logs.append("Group update [del included group %s]: "
                                "err API returned HTTP 404/409" % grp)
            except Exception, e:
                logs.append("Group update [del included group %s]: "
                            "err API returned %s" % (grp, e))

        return logs

    def extra_validations(self, **kwargs):
        """ This checks that requested members exists
        inside the backend.
        """
        logs = []
        members = kwargs['members']

        self._set_client()

        for member in members:
            ret = self.client.get_account(member)
            if not isinstance(ret, dict):
                logs.append("Check group members [%s does not exists]: "
                            "err API unable to find the member" % member)
        return logs


class Group(BaseResource):

    MODEL_TYPE = 'group'
    MODEL = {
        'name': (
            str,
            '^([a-zA-Z0-9\-_\./])+$',
            True,
            None,
            False,
            "The group name",
        ),
        'description': (
            str,
            '.*',
            False,
            "",
            True,
            "The group description",
        ),
        'members': (
            list,
            '.+@.+',
            False,
            [],
            True,
            "The group member list",
        ),
    }
    PRIORITY = 40
    PRIMARY_KEY = 'name'
    CALLBACKS = {
        'update': lambda conf, new, kwargs:
            GroupOps(conf, new).update(**kwargs),
        'create': lambda conf, new, kwargs:
            GroupOps(conf, new).create(**kwargs),
        'delete': lambda conf, new, kwargs:
            GroupOps(conf, new).delete(**kwargs),
        'extra_validations': lambda conf, new, kwargs:
            GroupOps(conf, new).extra_validations(**kwargs),
    }
