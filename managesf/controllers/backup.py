#
# Copyright (C) 2014 eNovance SAS <licensing@enovance.com>
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

from pecan import conf
import logging
from utils import RemoteUser

logger = logging.getLogger(__name__)


class Backup(object):
    def __init__(self):
        c = conf.managesf
        self.client = RemoteUser('root', c['host'], c['sshkey_update_path'])

    def start(self):
        logger.debug("start backup")
        self.client._ssh('sf_backup')

    def restore(self):
        logger.debug("start backup")
        self.client._ssh('sf_restore')


def backup_start():
    bkp = Backup()
    bkp.start()


def backup_restore():
    bkp = Backup()
    bkp.restore()
