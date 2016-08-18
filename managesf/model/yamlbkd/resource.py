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


class ModelInvalidException(Exception):
    def __init__(self, msg):
        self.msg = msg


class ResourceInvalidException(Exception):
    def __init__(self, msg):
        self.msg = msg


AUTHORIZED_CALLBACKS = ('update', 'create', 'delete')


class BaseResource(object):
    """ All resources to define for this backend
    must inherit from this class. This class
    cannot be initialized by itself.

    The resource data model description must
    contains a dictionnary where each key is a
    resource attribute and value a tuple that describes
    the attribute constraints.

    'key': (
        str, # Type
        regexp, # Value regex validator
        True, # Mandatory key
        None, # Default value
        True, # Is the value mutable
        "String", # Description
    ),

    """

    MODEL_TYPE = 'default'
    MODEL = {}
    PRIORITY = None
    CALLBACKS = {
        'update': NotImplementedError,
        'create': NotImplementedError,
        'delete': NotImplementedError,
    }

    def __init__(self, id, resource):
        self.id = id
        self._model_definition_validate()
        self.resource = resource
        self.mandatory_keys = set(
            [k for k, v in self.__class__.MODEL.items() if v[2]])
        self.keys = set(self.__class__.MODEL)

    def _model_definition_validate(self):
        """ This validate the inherited model. This is
        to validate resource model defined by inherited
        classes. We make sure the model is follow by the
        developper.
        """
        try:
            assert isinstance(self.__class__.MODEL_TYPE, str)
            assert isinstance(self.__class__.PRIORITY, int)
        except:
            raise ModelInvalidException(
                "Model %s is invalid and not usable" % (
                    self.__class__.MODEL_TYPE))

        for constraints in self.__class__.MODEL.values():
            if len(constraints) != 6:
                raise ModelInvalidException(
                    "Model %s is invalid and not usable "
                    "(missing field)" % (
                        self.__class__.MODEL_TYPE))

        try:
            # Be sure default values are of the declared type
            # make some others validation on default value
            for constraints in self.__class__.MODEL.values():
                # Only act on non-mandatory keys as default
                # is provided
                if not constraints[2]:
                    # Validate default value type
                    assert isinstance(constraints[3],
                                      constraints[0])
                    # Validate default value match the regexp
                    # if str type
                    if isinstance(constraints[0], str):
                        assert re.match(constraints[1],
                                        constraints[3])
                    # Validate list default values match the regexp
                    # if list type
                    if isinstance(constraints[0], list):
                        assert all([re.match(constraints[1], c) for
                                    c in constraints[3]]) is True
        except:
            raise ModelInvalidException(
                "Model %s is invalid and not usable "
                "(Wrong default value according to the type "
                "or regex)" % (
                    self.__class__.MODEL_TYPE))

        # Validate the callbacks of the inherited model
        try:
            # Be sure we have only the authorized callbacks
            assert len(set(AUTHORIZED_CALLBACKS).symmetric_difference(
                set(self.__class__.CALLBACKS))) is 0
            # Be sure the callbacks are callable or NotImplemented
            for key, callback in self.__class__.CALLBACKS.items():
                if (not callable(callback)
                        and callback is not NotImplementedError):
                    raise Exception
        except:
            raise ModelInvalidException(
                "Model %s callbacks are invalid, model is not usable" % (
                    self.__class__.MODEL_TYPE))

    def validate(self):
        """ Validate the data MODEL of the resource
        """
        # Validate all mandatory keys are present
        if not self.mandatory_keys.issubset(set(self.resource)):
            raise ResourceInvalidException(
                "Resource [type: %s, ID: %s] miss a "
                "mandatory key. Please check the model." % (
                    self.__class__.MODEL_TYPE,
                    self.id))

        # Validate the resource does not contains extra keys
        if not set(self.resource).issubset(self.keys):
            raise ResourceInvalidException(
                "Resource [type: %s, ID: %s] contains "
                "extra keys. Please check the model." % (
                    self.__class__.MODEL_TYPE,
                    self.id))

        # Validate the resource value type
        for key, value in self.resource.items():
            if not isinstance(value, self.__class__.MODEL[key][0]):
                raise ResourceInvalidException(
                    "Resource [type: %s, ID: %s] has an invalid "
                    "key (%s) data type (expected: %s)" % (
                        self.__class__.MODEL_TYPE,
                        self.id,
                        key,
                        self.__class__.MODEL[key][0]))
            # For str type validate the content as according the regex
            if self.__class__.MODEL[key][0] is str:
                if not re.match(self.__class__.MODEL[key][1], value):
                    raise ResourceInvalidException(
                        "Resource [type: %s, ID: %s] has an invalid "
                        "key (%s) data content (expected match : %s)" % (
                            self.__class__.MODEL_TYPE,
                            self.id,
                            key,
                            self.__class__.MODEL[key][1]))
            # For list type validate the content as according the regex
            if self.__class__.MODEL[key][0] is list:
                if not all([re.match(self.__class__.MODEL[key][1], v)
                            for v in value]):
                    raise ResourceInvalidException(
                        "Resource [type: %s, ID: %s] has an invalid "
                        "key (%s) data content (expected match : %s)" % (
                            self.__class__.MODEL_TYPE,
                            self.id,
                            key,
                            self.__class__.MODEL[key][1]))

    def is_mutable(self, key):
        return self.__class__.MODEL[key][4]

    def set_defaults(self):
        """ Enrich the data MODEL. This method add
        missing fields to the resource. Missing fields are
        initialized with their default value.
        """
        for key, constraints in self.__class__.MODEL.items():
            if key not in self.resource:
                self.resource[key] = constraints[3]

    def get_resource(self):
        return self.resource
