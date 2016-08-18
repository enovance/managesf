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
import git
import logging
import yaml
import copy
import tempfile
import deepdiff

from pecan import conf  # noqa

logger = logging.getLogger(__name__)

# Some explanation about concept of this backend
# ==============================================
#
# According to the mini spec from this ML message
# https://www.redhat.com/archives/softwarefactory-dev/2016-August/msg00005.html
# This is the implementaion of the SF YAML resources backend.
# We want as a final goal let SF users/operators define projects,
# groups, roles, ... via a bunch of YAML file stored in a GIT repository.
#
# As of today the management of such resources are done via the manageSF
# REST API. We expect to create a smooth technical transition
# between managing SF resources via the REST API and via the GIT repository.
# Managing resources like projects, groups will be discarded at the
# end of the transition.
#
# This backend has been designed to support both:
# - A use within the REST API.
# - A use "outside the REST API" with the data input limitated
#   to the a git current state.
#
# The big picture of that backend is:
# There is the current backend data, that is supposed to be
# the current state of resources in each SF services. When
# a change is requested a data diff is done between the current
# state to the new state, then a list of callbacks ops is returned
# to let the calling library to run services operations to
# create/delete/update resources.
#
# Integration details
# ===================
#
# The first usage of this backend will be via the REST API and
# its behavior will be as follow. The YAML DB will be woth write access
# via this library methods. The manageSF REST controler will receive
# POST/PUT/GET on resources and will use this backend to write/read resources
# data. For the case of an create/update if the resource data is right
# regarding the resource schema and if the operation is known as feasable
# by the backend then the resource is written in the backend yaml file.
# And finally a list of callback ops is return to the manageSF controller
# and then it is up to the controller to call the callbacks. A callback
# is such ("managesf.controller.project.create", **kwargs).
#
# Note that if some callback exec failed the backend will not
# reflect the current services resources status.
#
# As said above this backend already implements the base to be used
# with a GIT repository input only. When initialized like that, the
# YAML DB files become read-only. A method can then be call to retrieve
# callbacks ops to run compare to the resources definition change between
# the GIT repo HEAD and HEAD^1.
# In this context a manageSF REST endpoint (/managesf/resources/) will
# be created where a client can request the read of the DB, and the POST
# on /managesf/resources/apply to trigger a sync of the GIT repo and an
# apply of the callbacks. The latter will be use only by the config-update job.
# Finally in the config-check job we want to verify the modified data are
# correct regarding the schema and input constraints then we will need an
# endpoint /managesf/resources/validate where we can POST a merged YAML
# of the config repo to return a validation or a list of constraints violation.
# To do that a part "load_db_from_git_directory" should be callable outside
# of manageSF to be run by the config-check job before the job call the
# validate endpoint.


# TODO: If used in mode GIT directory then use the config file
# to define the clone path for the SF config repo

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


class YAMLDBIsReadOnly(YAMLDBException):
    pass


class YAMLDBIsNotGitType(YAMLDBException):
    pass


class YAMLBackend(object):
    def __init__(self, db_path):
        self.data = None
        self.db_path = db_path
        # If git_dir_type become true. The backend library
        # will be read-only on the DB files.
        self.git_dir_type = False
        if os.path.isdir(db_path) and \
                os.path.isdir(os.path.join(db_path, '.git')):
            logger.info("Load a pre-existing DB from a GIT directory")
            self.git_dir_type = True
            self.load_db()
        elif os.path.isfile(db_path):
            logger.info("Load a pre-existing DB from a flat file")
            self.load_db()
            if not self.data:
                logger.info("Pre-existing DB (flat file) was empty. Init it")
                self.data = DB_SCHEMA
                self.save_db()
        elif not os.path.isdir(os.path.dirname(db_path)):
            logger.info(
                "Creating base directory %s for storing the DB (flat file)" % (
                    os.path.dirname(db_path)))
            os.mkdir(os.path.dirname(db_path))
            logger.info("Creating new empty DB")
            self.data = DB_SCHEMA
            self.save_db()
        else:
            raise YAMLDBPathNotFound("DB path not valid. Init failed")

    def enrich_data(self, data=None):
        data_to_enrich = data or self.data
        for resource_cat, resources in data_to_enrich['resources'].items():
            for resource in resources.values():
                for rk in RESOURCES_SCHEMA[resource_cat].keys():
                    if rk not in resource.keys():
                        resource[rk] = None
        return data_to_enrich

    def load_db_from_git_directory(self, external_db_path=None):
        if not external_db_path:
            db_path = self.db_path
            repo = git.Git(self.db_path)
            repo.execute(['git', 'pull', 'origin', 'master'])
        else:
            db_path = external_db_path
        subdir = '.'
        yamlfiles = [f for f in
                     os.listdir(
                         os.path.join(subdir,
                                      db_path)) if f.endswith('.yaml')]
        data = None
        for f in yamlfiles:
            logger.info("Reading %s ..." % f)
            if not data:
                data = yaml.load(
                    file(os.path.join(subdir, db_path, f)))
            else:
                data_to_append = yaml.load(
                    file(os.path.join(subdir, db_path, f)))
                for rtype, resources in data_to_append['resources'].items():
                    if rtype in data['resources']:
                        for r, v in resources.items():
                            if r in data['resources'][rtype].keys():
                                logger.warning("Duplicate resource %s:%s" % (
                                    rtype, r))
                            data['resources'][rtype][r] = v
        if not external_db_path:
            self.data = data
        else:
            return data

    def load_db(self, directory=False):
        if self.git_dir_type:
            self.load_db_from_git_directory()
            self.data = self.enrich_data()
            return
        self.data = yaml.load(file(self.db_path))
        if self.data:
            self.data = self.enrich_data()

    def save_db(self):
        with open(self.db_path, 'w') as dbfile:
            yaml.safe_dump(self.data,
                           dbfile,
                           allow_unicode=True,
                           default_flow_style=False)

    def validate_resource_schema(self, data):
        for rtype, resources in data['resources'].items():
            schema = RESOURCES_SCHEMA[rtype]
            mandatory_keys = [k for k, v in schema.items() if v[1]]
            allowed_keys = schema.keys()
            for resource in resources.values():
                if not set(mandatory_keys).issubset(set(resource.keys())):
                    raise YAMLDBResourceBadSchema(
                        "%s keys have not be found in "
                        "resource %s (type %s)" % (
                            mandatory_keys, resource, rtype))
                for k, v in resource.items():
                    if k not in allowed_keys:
                        raise YAMLDBResourceBadSchema(
                            "%s resource key %s is not allowed" % (rtype, k))
                    if k in mandatory_keys and not isinstance(v, schema[k][0]):
                        raise YAMLDBResourceBadSchema(
                            "%s resource key %s must be %s" % (
                                rtype, k, schema[k][0]))
                    if k not in mandatory_keys and not (
                            isinstance(v, schema[k][0]) or v is None):
                        raise YAMLDBResourceBadSchema(
                            "%s resource key %s must be %s or None" % (
                                rtype, k, schema[k][0]))

    def get_resource_create_kargs(self, path, rtype, keys, new_data):
        resource_id = re.search(".*\['(.*)'\]$", path)
        resource_id = resource_id.groups()[0]
        path = path.replace('root', 'new_data')
        data = eval(path)
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
                                ctype, path))
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
                                ctype, path))
                else:
                    raise YAMLDBUnsupportedOp(
                        "Not supported resource for this op (%s:%s)" % (
                            ctype, path))
        return callbacks

    def get_leafs_changes(self, new_data, previous_data=None):
        if previous_data:
            return deepdiff.DeepDiff(previous_data, new_data)
        return deepdiff.DeepDiff(self.data, new_data)

    def get_changes_callback_ops(self, new_data, previous_data=None):
        changes = self.get_leafs_changes(new_data, previous_data)
        return self.get_callback_ops(changes, new_data)

    def get_previous_git_db_leafs(self):
        # Create another repository to keep the base repo in a sane state
        temp = tempfile.mkdtemp()
        repo = git.Git(temp)
        repo.init()
        repo.execute(['git', 'remote', 'add',
                      'origin', 'file://%s' % self.db_path])
        repo.execute(['git', 'pull', 'origin', 'master'])
        repo.execute(['git', 'checkout', 'HEAD^1'])
        data = self.load_db_from_git_directory(temp)
        return data

    # From here are the real methods we should use as input
    def get_leafs(self):
        """ Return the full copy of the BD content
        """
        return copy.deepcopy(self.data)

    def validate(self, new_data, previous_data=None):
        """ Validate the data passed as argument.
        This should be callable also during a config-check
        """
        new_data = self.enrich_data(new_data)
        if previous_data:
            previous_data = self.enrich_data(previous_data)
        self.validate_resource_schema(new_data)
        return self.get_changes_callback_ops(new_data, previous_data)

    def set_leafs(self, new_data):
        """ If the DB is fully managed (I/O) the this
        method allow to write a tree a resources and
        return callbacks that need to be run to update
        resources on SF services.
        """
        if self.git_dir_type:
            raise YAMLDBIsReadOnly(
                "The DB has been open in read-only mode (git_dir_type)")
        ops = self.validate(new_data)
        # Here we are good let's save the data into the DB
        self.data = copy.deepcopy(new_data)
        self.save_db()
        return ops

    def get_ops_from_head_1(self):
        """ If the DB is GIT managed the this method
        return callbacks to run on SF services according
        to the changes between HEAD and HEAD^1
        """
        if not self.git_dir_type:
            raise YAMLDBIsNotGitType(
                "The DB has been open in read-only mode (git_dir_type)")
        # Refresh the data from the SF
        self.load_db()
        # Load the current tree
        current_data = self.get_leafs()
        # We need to copy the repo and then checkout it with HEAD^1
        # Then read the previous state
        previous_data = self.get_previous_git_db_leafs()
        return self.validate(current_data, previous_data=previous_data)
