#!/usr/bin/env python
#
# Copyright (C) 2015 Red Hat <licensing@enovance.com>
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


from managesf.services import base


# TODO(mhu) add a heartbeat
heartbeat = None


class Nodepool(base.BaseServicePlugin):
    """Very simple nodepool plugin only used for backups."""

    _config_section = "nodepool"
    service_name = "nodepool"

    def __init__(self, conf):
        super(Nodepool, self).__init__(conf)
        self.backup.heartbeat_cmd = heartbeat

    def get_client(self, cookie=None):
        return None
