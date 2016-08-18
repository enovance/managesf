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


class ModelInvalidException(Exception):
    pass


class ResourceInvalidException(Exception):
    pass


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
        True, # Mandatory key
        None, # Default value
        "The unique ID of the resource", # Description
    ),

    """

    BASE_MODEL = {
        'id': (
            str,
            True,
            None,
            "The unique ID of the resource",
        ),
    }
    MODEL_TYPE = 'default'
    MODEL = {}
    PRIORITY = None
    CALLBACKS = {
        'update': None,
        'create': None,
        'delete': None,
    }

    def __init__(self, resource):
        self.__class__.MODEL.update(self.__class__.BASE_MODEL)
        self._model_definition_validate()
        assert "id" in resource
        assert isinstance(resource["id"], str)
        self.resource = resource
        self.mandatory_keys = set([k for k, v in self.__class__.MODEL.items()
                                   if v[1]])
        self.keys = set(self.__class__.MODEL)

    def _model_definition_validate(self):
        """ This validate the inherited model
        """
        try:
            assert isinstance(self.__class__.MODEL_TYPE, str)
            assert isinstance(self.__class__.PRIORITY, int)
            # Be sure default values are of the declared type
            for constraints in self.__class__.MODEL.values():
                if not constraints[1]:
                    assert isinstance(constraints[2],
                                      constraints[0])
        except:
            raise ModelInvalidException(
                "Model %s is invalid and not usable" % (
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
                    self.resource['id']))

        # Validate the resource does not contains extra keys
        if not set(self.resource).issubset(self.keys):
            raise ResourceInvalidException(
                "Resource [type: %s, ID: %s] contains "
                "extra keys. Please check the model." % (
                    self.__class__.MODEL_TYPE,
                    self.resource['id']))

        # Validate the resource value types
        for key, value in self.resource.items():
            if not isinstance(value, self.__class__.MODEL[key][0]):
                raise ResourceInvalidException(
                    "Resource [type: %s, ID: %s] has an invalid "
                    "key (%s) data type (expected: %s)" % (
                        self.__class__.MODEL_TYPE,
                        self.resource['id'],
                        key,
                        self.__class__.MODEL[key][0]))

    def enrich(self):
        """ Enrich the data MODEL. This method add
        missing field to the resource load. This ease
        data comparaison with the deepdiff module.
        """
        for key, constraints in self.__class__.MODEL.items():
            if key not in self.resource:
                self.resource[key] = constraints[2]

    def get_resource(self):
        return self.resource
