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
from managesf.model.yamlbkd.operations import ProjectOps


# TODO(fbo): Add a for each resource an unicity constraint
# Here namespace + name should be unique over the set of projects
# This need to be implemented in the BaseResource class.

class Project(BaseResource):

    MODEL_TYPE = 'project'
    MODEL = {
        'namespace': (
            str,
            '^([a-zA-Z0-9\-_])+$',
            True,
            None,
            False,
            "The project prefix (project's group)",
        ),
        'name': (
            str,
            '^([a-zA-Z0-9\-_])+$',
            True,
            None,
            False,
            "The project name",
        ),
        'description': (
            str,
            '^([a-zA-Z0-9\-_ ])+$',
            False,
            "",
            True,
            "The project description sentence",
        ),
    }
    PRIORITY = 50
    CALLBACKS = {
        'update': NotImplementedError,
        'create': ProjectOps.create,
        'delete': ProjectOps.delete,
    }
