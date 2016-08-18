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
import re

from managesf.services.gerrit import SoftwareFactoryGerrit
from managesf.model.yamlbkd.resource import BaseResource
from managesf.services.gerrit import utils

# ## DEBUG statements to ease run that standalone ###
# import logging
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
#
# from pecan import configuration
# from managesf.model.yamlbkd.resources.gitrepository import GitRepositoryOps
# conf = configuration.conf_from_file('/var/www/managesf/config.py')
# g = GroupOps(conf)
# g._set_client()
# ###


class GitRepositoryOps(object):

    def __init__(self, conf, new):
        self.conf = conf
        self.new = new
        self.client = None

    def _set_client(self):
        gerrit = SoftwareFactoryGerrit(self.conf)
        self.client = gerrit.get_client()

    def create(self, **kwargs):
        logs = []
        namespace = kwargs['namespace']
        name = kwargs['name']
        description = kwargs['description']
        kwargs['acl']

        self._set_client()
        name = os.path.join(namespace, name)

        try:
            ret = self.client.create_project(name,
                                             description,
                                             ['Administrators'])
            if ret is False:
                logs.append("Repo create: err API returned HTTP 404/409")
        except Exception, e:
            logs.append("Repo create: err API returned %s" % e)

        # TODO(fbo): Be sure in the engine when an update of a resource
        # is detected by a deps that we make sure we don't that that
        # resource update if the resource is known to be created in the
        # same run
        install_acl_logs = self.install_acl(**kwargs)
        logs.extend(install_acl_logs)

        return logs

    def delete(self, **kwargs):
        logs = []
        namespace = kwargs['namespace']
        name = kwargs['name']

        self._set_client()
        name = os.path.join(namespace, name)

        try:
            ret = self.client.delete_project(name, True)
            if ret is False:
                logs.append("Repo delete: err API returned HTTP 404/409")
        except Exception, e:
            logs.append("Repo delete: err API returned %s" % e)

        return logs

    def update(self, **kwargs):
        logs = []

        self._set_client()

        install_acl_logs = self.install_acl(**kwargs)
        logs.extend(install_acl_logs)

        return logs

    def install_acl(self, **kwargs):
        logs = []
        namespace = kwargs['namespace']
        name = kwargs['name']
        description = kwargs['description']
        acl_id = kwargs['acl']

        if not acl_id:
            return logs

        if not self.client:
            self._set_client()

        name = os.path.join(namespace, name)

        # Fetch the ACL
        acl_data = self.new['resources']['acls'][acl_id]['file']
        acl_group_ids = set(self.new['resources']['acls'][acl_id]['groups'])

        # Fetch groups name
        group_names = set([])
        for group_id in acl_group_ids:
            _namespace = self.new['resources']['groups'][group_id]['namespace']
            _name = self.new['resources']['groups'][group_id]['name']
            group_names.add(os.path.join(_namespace, _name))

        # Add default groups implicitly
        for default_group in ('Non-Interactive Users',
                              'Administrators',
                              'Anonymous Users'):
            group_names.add(default_group)

        # Fill a groups file
        groups_file = """# UUID Group Name
global:Registered-Users\tRegistered Users"""
        for group in group_names:
            gid = self.client.get_group_id(group)
            groups_file += "\n%s\t%s" % (gid, group)

        # Overwrite the description if given in the ACL file
        if 'description' in acl_data:
            acl_data = re.sub('description =.*',
                              'description = %s' % description,
                              acl_data)
        else:
            acl_data += """
[project]
        description = %s
"""
            acl_data = acl_data % description

        # Clone the meta/config branch and push the ACL
        try:
            r = utils.GerritRepo(name, self.conf)
            r.clone()
            paths = {}
            paths['project.config'] = acl_data
            paths['groups'] = groups_file
            r.push_config(paths)
        except Exception, e:
            logs.append(str(e))
        return logs


class GitRepository(BaseResource):

    MODEL_TYPE = 'git'
    MODEL = {
        'namespace': (
            str,
            '^([a-zA-Z0-9\-_\.])+$',
            True,
            None,
            False,
            "The repository name prefix",
        ),
        'name': (
            str,
            '^([a-zA-Z0-9\-_\.])+$',
            True,
            None,
            False,
            "The repository name",
        ),
        'description': (
            str,
            '.*',
            False,
            "",
            True,
            "The repository description",
        ),
        'acl': (
            str,
            '.*',
            False,
            "",
            True,
            "The ACLs id",
        ),
    }
    PRIORITY = 20
    CALLBACKS = {
        'update': lambda conf, new, kwargs:
            GitRepositoryOps(conf, new).update(**kwargs),
        'create': lambda conf, new, kwargs:
            GitRepositoryOps(conf, new).create(**kwargs),
        'delete': lambda conf, new, kwargs:
            GitRepositoryOps(conf, new).delete(**kwargs),
        'extra_validations': lambda conf, new, kwargs: [],
    }

    def get_deps(self):
        if self.resource['acl']:
            return {'acls': set([self.resource['acl']])}
        else:
            return {'acls': set([])}
