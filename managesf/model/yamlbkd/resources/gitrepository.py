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


class GitRepositoryOps(object):

    def create(self, namespace, name, description):
        pass

    def delete(self, namespace, name):
        pass

    def update(self, namespace, name, description):
        pass


class GitRepository(BaseResource):

    MODEL_TYPE = 'git'
    MODEL = {
        'namespace': (
            str,
            '^([a-zA-Z0-9\-_])+$',
            True,
            None,
            False,
            "The repository name prefix",
        ),
        'name': (
            str,
            '^([a-zA-Z0-9\-_])+$',
            True,
            None,
            False,
            "The repository name",
        ),
        'description': (
            str,
            '^([a-zA-Z0-9\-_ ])+$',
            False,
            "",
            True,
            "The repository description",
        ),
    }
    PRIORITY = 50
    CALLBACKS = {
        'update': GitRepositoryOps.update,
        'create': GitRepositoryOps.create,
        'delete': GitRepositoryOps.delete,
    }
