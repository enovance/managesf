#!/usr/bin/env python
#
# Copyright (C) 2016 Red Hat <licensing@enovance.com>
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


import time

from pysflib.sfjenkins import SFJenkins
from pysflib.sfauth import get_cookie

from managesf.services import base
from managesf.services.jenkins import job


class Jenkins(base.BaseJobRunnerServicePlugin):
    """Plugin managing the Jenkins job runner service."""

    _config_section = "jenkins"
    service_name = "jenkins"

    def __init__(self, conf):
        super(Jenkins, self).__init__(conf)
        self.project = None
        self.user = None
        self.membership = None
        self.role = None
        self.repository = None
        self.job = None

    def get_client(self, cookie=None):
        raise NotImplementedError


ADMIN_COOKIE = None
ADMIN_COOKIE_DATE = 0
COOKIE_VALIDITY = 60


class SoftwareFactoryJenkins(Jenkins):

    def __init__(self, conf):
        super(SoftwareFactoryJenkins, self).__init__(conf)
        self.job = job.SFJenkinsJobManager(self)

    def get_client(self, cookie=None):
        if not cookie:
            if int(time.time()) - globals()['ADMIN_COOKIE_DATE'] > \
                    globals()['COOKIE_VALIDITY']:
                cookie = get_cookie(self._full_conf.auth['host'],
                                    self._full_conf.admin['name'],
                                    self._full_conf.admin['http_password'])
                globals()['ADMIN_COOKIE'] = cookie
                globals()['ADMIN_COOKIE_DATE'] = int(time.time())
            else:
                cookie = globals()['ADMIN_COOKIE']
        return SFJenkins(self.conf['url'],
                         cookie=cookie)
