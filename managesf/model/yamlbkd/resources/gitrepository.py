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
import json
import urllib

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
# from managesf.model.yamlbkd.resources.gitrepository import GitRepositoryOps
# conf = configuration.conf_from_file('/var/www/managesf/config.py')
# g = GroupOps(conf)
# g._set_client()
# ###


class GitRepositoryOps(object):

    def __init__(self, conf):
        self.conf = conf

    def _set_client(self):
        gerrit = SoftwareFactoryGerrit(self.conf)
        self.client = gerrit.get_client()

    def create(self, **kwargs):
        logs = []
        namespace = kwargs.get('namespace')
        name = kwargs.get('name')
        description = kwargs.get('description')

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

        return logs

    def delete(self, **kwargs):
        logs = []
        namespace = kwargs.get('namespace')
        name = kwargs.get('name')

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

        # TODO; Should go in pysflib ?
        def project_update_description(name, description):
            data = json.dumps({
                "description": description,
                "commit_message": "Project description update",
            })
            try:
                name = urllib.quote_plus(name)
                self.client.g.put('projects/%s/description' % name,
                                  data=data)
            except HTTPError as e:
                return self.client._manage_errors(e)

        namespace = kwargs.get('namespace')
        name = kwargs.get('name')
        description = kwargs.get('description')

        self._set_client()
        name = os.path.join(namespace, name)

        try:
            ret = project_update_description(name, description)
            if ret is False:
                logs.append("Repo update [description]: err API returned "
                            "HTTP 404/409")
        except Exception, e:
            logs.append("Repo update [description]: err API returned %s" % e)

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
    }
    PRIORITY = 50
    CALLBACKS = {
        'update': lambda conf, kwargs: GitRepositoryOps(conf).update(**kwargs),
        'create': lambda conf, kwargs: GitRepositoryOps(conf).create(**kwargs),
        'delete': lambda conf, kwargs: GitRepositoryOps(conf).delete(**kwargs),
        'extra_validations': lambda conf, kwargs: [],
    }
