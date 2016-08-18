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


class ResourceInvalidException(Exception):
    pass


class BaseResource(object):
    """ All resource to define for this backend
    must inherite from this Class. This class
    cannot be initialized.
    """

    BASE_MODEL = {
        'id': (
            str,
            True,
            None,
            "The unique ID of the resource",
        ),
    }
    MODEL_TYPE = None
    MODEL = {}
    PRIORITY = None
    CALLBACKS = {
        'update': None,
        'create': None,
        'delete': None,
    }

    def __init__(self, resource):
        assert isinstance(self.__class__.MODEL_TYPE, str)
        assert isinstance(self.__class__.PRIORITY, int)
        assert "id" in resource
        assert isinstance(resource["id"], str)
        self.resource = resource
        self.__class__.MODEL.update(self.__class__.BASE_MODEL)

    def validate(self):
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
        raise NotImplemented
