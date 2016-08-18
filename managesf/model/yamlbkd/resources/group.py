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


from managesf.services.gerrit import SoftwareFactoryGerrit
from managesf.model.yamlbkd.resource import BaseResource


class GroupOps(object):

    def __init__(self, conf):
        self.conf = conf

    def _set_client(self):
        gerrit = SoftwareFactoryGerrit(self.conf)
        self.client = gerrit.get_client()

    def create(self, **kwargs):
        pass

    def delete(self, **kwargs):
        pass

    def update(self, **kwargs):
        pass


class Group(BaseResource):

    MODEL_TYPE = 'group'
    MODEL = {
        'namespace': (
            str,
            '^([a-zA-Z0-9\-_\.])+$',
            True,
            None,
            False,
            "The group name prefix",
        ),
        'name': (
            str,
            '^([a-zA-Z0-9\-_\.])+$',
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
    PRIORITY = 50
    CALLBACKS = {
        'update': lambda conf, kwargs: GroupOps(conf).update(**kwargs),
        'create': lambda conf, kwargs: GroupOps(conf).create(**kwargs),
        'delete': lambda conf, kwargs: GroupOps(conf).delete(**kwargs),
    }
