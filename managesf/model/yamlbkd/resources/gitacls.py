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

from managesf.model.yamlbkd.resource import BaseResource


class ACLsOps(object):

    def __init__(self, conf, new):
        self.conf = conf
        self.new = new

    def extra_validations(self, **kwargs):
        return []


class ACLs(BaseResource):

    MODEL_TYPE = 'acl'
    MODEL = {
        'file': (
            str,
            '.*',
            True,
            None,
            True,
            "The Gerrit ACL content",
        ),
        'groups': (
            list,
            '^([a-zA-Z0-9])+$',
            False,
            [],
            True,
            "The list of groups on which this ACL depends on",
        ),
    }
    PRIORITY = 30
    CALLBACKS = {
        'update': lambda conf, new, kwargs: [],
        'create': lambda conf, new, kwargs: [],
        'delete': lambda conf, new, kwargs: [],
        'extra_validations': lambda conf, new, kwargs:
            ACLsOps(conf, new).extra_validations(**kwargs),
    }
