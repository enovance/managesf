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

import re
import os
import logging
import yaml
import copy
import deepdiff

from pecan import conf  # noqa

logger = logging.getLogger(__name__)

DB_SCHEMA = {
    'resources': {
        'projects': {}
    }
}

RESOURCES_SCHEMA = {
    'projects': {
        'description': (str, 1),
        'git-repo': (str, 1),
        'gitweb': (str, 0),
        'website': (str, 0),
        'tracker': (str, 0),
        'git-replica': (str, 0),
    }
}

ON_CREATE_CALLBACKS = {
    'projects': (
        'controllers.projects.create', (
            'name',
            'git-repo',
            'description')
    ),
}

ON_CHANGE_CALLBACKS = {
}

ON_DELETE_CALLBACKS = {
    'projects': ('controllers.projects.delete'),
}


class YAMLDBException(Exception):
    def __init__(self, msg):
        logger.error(msg)


class YAMLDBPathNotFound(YAMLDBException):
    pass


class YAMLDBUnsupportedOp(YAMLDBException):
    pass


class YAMLDBResourceBadSchema(YAMLDBException):
    pass


class YAMLBackendResourcesMerger(object):
    pass


class YAMLBackend(object):
    def __init__(self, db_path=None):
        self.data = None
        self.db_path = db_path
        self.git_dir = None
        if not db_path:
            raise YAMLDBPathNotFound(db_path)
        if not os.path.isdir(os.path.dirname(db_path)):
            os.mkdir(os.path.dirname(db_path))
        self.load_db()
        if self.data == None:
            self.data = DB_SCHEMA
            self.save_db()

    def load_db(self):
        self.data = yaml.load(file(self.db_path))

    def save_db(self):
        with open(self.db_path, 'w') as dbfile:
            yaml.safe_dump(self.data,
                           dbfile,
                           allow_unicode=True,
                           default_flow_style=False)

    def get_leafs(self):
        return copy.deepcopy(self.data)

    def validate_resource_schema(self, rtype, data):
        schema = RESOURCES_SCHEMA[rtype]
        mandatory_keys = [k for k, v in schema.items() if v[1]]
        allowed_keys = schema.keys()
        if not set(mandatory_keys).issubset(set(data.keys())):
            raise YAMLDBResourceBadSchema(
                "%s keys have not be found in resource %s (type %s)" % (
                    mandatory_keys, data, rtype))
        for k, v in data.items():
            if k not in allowed_keys:
                raise YAMLDBResourceBadSchema(
                    "%s resource key %s is not allowed" % (rtype, k))
            if not isinstance(v, schema[k][0]):
                raise YAMLDBResourceBadSchema(
                    "%s resource key %s must be %s" % (rtype, k, schema[k][0]))

    def get_resource_create_kargs(self, path, rtype, keys, new_data):
        resource_id = re.search(".*\['(.*)'\]$", path)
        resource_id = resource_id.groups()[0]
        path = path.replace('root', 'new_data')
        data = eval(path)
        self.validate_resource_schema(rtype, data)
        ret = {}
        for key in keys:
            ret.update({key: data.get(key, None)})
        ret['name'] = resource_id
        return ret

    def get_resource_delete_kargs(self, path):
        resource_id = re.search(".*\['(.*)'\]$", path)
        resource_id = resource_id.groups()[0]
        return {'name': resource_id}

    def get_callback_ops(self, changes, new_data):
        callbacks = []
        for ctype, elm in changes.items():
            for path in elm:
                rtype = re.search("root\['resources'\]\['([a-zA-Z]+)'\].*",
                                  path)
                rtype = rtype.groups()[0]
                if ctype == 'dictionary_item_added':
                    if rtype in ON_CREATE_CALLBACKS:
                        callbacks.append(
                            (ON_CREATE_CALLBACKS[rtype][0],
                             self.get_resource_create_kargs(
                                 path,
                                 rtype,
                                 ON_CREATE_CALLBACKS[rtype][1],
                                 new_data)
                             )
                        )
                    else:
                        raise YAMLDBUnsupportedOp(
                            "Not supported resource for this op (%s:%s)" % (
                                ctype, elm))
                elif ctype == 'dictionary_item_removed':
                    if rtype in ON_DELETE_CALLBACKS:
                        callbacks.append(
                            (ON_DELETE_CALLBACKS[rtype],
                             self.get_resource_delete_kargs(path)
                             )
                        )
                    else:
                        raise YAMLDBUnsupportedOp(
                            "Not supported resource for this op (%s:%s)" % (
                                ctype, elm))
                else:
                    raise YAMLDBUnsupportedOp(
                        "Not supported resource for this op (%s:%s)" % (
                            ctype, elm))
        return callbacks

    def validate(self, new_data):
        changes = self.get_leafs_changes(new_data)
        return self.get_callback_ops(changes, new_data)

    def set_leafs(self, new_data):
        ops = self.validate(new_data)
        self.data = new_data
        self.save_db()
        return ops

    def get_leafs_changes(self, newdata=None):
        if newdata:
            return deepdiff.DeepDiff(self.data, newdata)
        elif self.git_dir:
            newdata = self.get_previous_version()
            return self.get_leafs_changes(newdata)
        else:
            return None
