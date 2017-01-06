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

from managesf.services.storyboard import SoftwareFactoryStoryboard


NAME_RE = "^[a-zA-Z0-9]+([_\-\./]?[a-zA-Z0-9]+)*$"
PROJECT_NAME_RE = re.compile(NAME_RE)
NAME_MIN_LEN = 5


class StoryboardOps(object):

    def __init__(self, conf):
        self.conf = conf
        self.client = None

    def _set_client(self):
        if not self.client:
            stb = SoftwareFactoryStoryboard(self.conf)
            self.client = stb.get_client()

    def extra_validations(self, **kwargs):
        logs = []
        name = kwargs['name']
        if len(name) < NAME_MIN_LEN:
            logs.append(
                "Storyboard project name length is invalid"
                " (Minimal len is %s)" % NAME_MIN_LEN)
        if not PROJECT_NAME_RE.match(name):
            logs.append(
                "Storyboard project name length is invalid"
                " (It should match the RE(%s))" % NAME_RE)

        return logs

    def update_project(self, **kwargs):
        name = kwargs['name']
        description = kwargs['description']
        self._set_client()
        project = self.client.projects.get_all(name=name)
        if project:
            project = project[0]
            self.client.projects.update(
                id=project.id, description=description)
        else:
            # Create the project
            self.client.projects.create(
                name=name, description=description)

    def delete_project(self, name):
        raise NotImplementedError('Not supported by Storyboard')

if __name__ == '__main__':
    from pecan import configuration
    conf = configuration.conf_from_file('/etc/managesf/config.py')
    c = StoryboardOps(conf)
    c._set_client()
    # Warn there is a minimal name length for project name
    c.update_project('project1', 'the project p1')