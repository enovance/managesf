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

import argparse
import json
from tempfile import mkstemp

from unittest import TestCase
from mock import patch, MagicMock

from managesf import cli


class FakeResponse(object):
    def __init__(self, status_code=200, text='fake'):
        self.status_code = status_code
        self.text = text


class BaseFunctionalTest(TestCase):
    def setUp(self):
        _, self.temp_path = mkstemp()
        with open(self.temp_path, 'w') as f:
            f.write('dummy data')
        self.parser = argparse.ArgumentParser(description="test")
        cli.default_arguments(self.parser)
        cli.command_options(self.parser)
        self.base_url = "http://tests.dom/"
        self.headers = {'Authorization': 'Basic blipblop'}
        default_args = '--url {url} --auth titi:toto --auth-server-url {url}'
        self.default_args = default_args.format(url=self.base_url).split()
        self.cookies = {'auth_pubtkt': 'fake_cookie'}

    def tearDown(self):
        pass

    def assert_secure(self, method_verb, cmd_args, action_func,
                      expected_url, expected_data=None):
        with patch('managesf.cli.get_cookie') as c:
            c.return_value = 'fake_cookie'
            with patch('requests.' + method_verb) as method:
                method.return_value = FakeResponse()
                parsed = self.parser.parse_args(cmd_args)
                params = {'headers': self.headers, 'cookies': self.cookies}
                if expected_data is not None:
                    params['data'] = json.dumps(expected_data)

                self.assertTrue(action_func(parsed, self.base_url,
                                            self.headers))

                method.assert_called_with(expected_url, **params)


class TestProjectUserAction(BaseFunctionalTest):
    def test_create_project(self):
        args = self.default_args
        args += 'project create --name proj1'.split()
        expected_url = self.base_url + '/project/proj1'
        self.assert_secure('put', args, cli.project_action, expected_url)

    def test_delete_project(self):
        args = self.default_args
        args += 'project delete --name proj1'.split()
        expected_url = self.base_url + '/project/proj1'
        self.assert_secure('delete', args, cli.project_action, expected_url)


class TestMembershipAction(BaseFunctionalTest):
    def test_project_add_user_to_groups(self):
        args = self.default_args
        cmd = 'membership add --user u1 --project p1 --groups dev-group'
        args += cmd.split()
        expected_url = self.base_url + '/project/membership/p1/u1/'
        self.assert_secure('post', args, cli.project_user_action, expected_url,
                           {'groups': ['dev-group']})

    def test_project_remove_user_from_all_groups(self):
        args = self.default_args
        args += 'membership remove --user user1 --project proj1'.split()
        expected_url = self.base_url + '/project/membership/proj1/user1/'
        self.assert_secure('delete', args, cli.project_user_action,
                           expected_url)

    def test_list_users_per_project(self):
        args = self.default_args
        args += 'membership list'.split()
        expected_url = self.base_url + '/project/membership/'
        self.assert_secure('get', args, cli.project_user_action, expected_url)


class TestUserActions(BaseFunctionalTest):
    def test_user_add(self):
        args = self.default_args
        data = {'email': 'e@test.com', 'password': 'abc123'}
        cmd = 'user create --username u1 --password {password} --email {email}'
        args += cmd.format(**data).split()
        expected_url = self.base_url + '/user/u1/'
        self.assert_secure('post', args, cli.user_management_action,
                           expected_url, data)

    def test_user_delete(self):
        args = self.default_args
        args += 'user delete --user test2'.split()
        expected_url = self.base_url + '/user/test2/'
        self.assert_secure('delete', args, cli.user_management_action,
                           expected_url)

    def test_user_update(self):
        args = self.default_args
        data = {'email': 'e@test.com', 'password': 'abc123'}
        cmd = 'user update --username t3 --password {password} --email {email}'
        args += cmd.format(**data).split()
        expected_url = self.base_url + '/user/t3/'
        self.assert_secure('post', args, cli.user_management_action,
                           expected_url, data)


class TestGerritActions(BaseFunctionalTest):
    def test_replication(self):
        data = {'wait': 'true', 'url': 'git://ex.com', 'project': 'p1'}
        args = self.default_args
        args += 'gerrit trigger --wait --project p1 --url git://ex.com'.split()
        expected_url = self.base_url + '/replication/'
        self.assert_secure('post', args, cli.replication_action, expected_url,
                           data)

    def test_configure_list(self):
        args = self.default_args
        args += 'gerrit configure list'.split()
        expected_url = self.base_url + '/replication/'
        self.assert_secure('get', args, cli.replication_action, expected_url,
                           {})

    def test_configure_get_all(self):
        args = self.default_args
        args += 'gerrit configure get-all --section toto'.split()
        expected_url = self.base_url + '/replication/toto/'
        self.assert_secure('get', args, cli.replication_action, expected_url,
                           {})

    def test_configure_add(self):
        args = self.default_args
        args += 'gerrit configure add --section AAA timeout bbb'.split()
        expected_url = self.base_url + '/replication/AAA/timeout/'
        self.assert_secure('put', args, cli.replication_action, expected_url,
                           {'value': 'bbb'})

    def test_configure_remove(self):
        args = self.default_args
        args += 'gerrit configure remove-section --section BBB'.split()
        expected_url = self.base_url + '/replication/BBB/'
        self.assert_secure('delete', args, cli.replication_action,
                           expected_url, {})

    def test_rename_section(self):
        args = self.default_args
        args += 'gerrit configure rename-section --section CCC AAA'.split()
        expected_url = self.base_url + '/replication/CCC/'
        self.assert_secure('put', args, cli.replication_action, expected_url,
                           {'value': 'AAA'})

    def test_replace_all(self):
        return
        args = self.default_args
        args += 'gerrit configure replace-all --section BBB url DDD'.split()
        expected_url = self.base_url + '/replication/BBB/url/'
        self.assert_secure('delete', args, cli.replication_action,
                           expected_url, {})

    def test_restore(self):
        data = {'filename': '/tmp/toto'}
        args = self.default_args
        args += 'gerrit restore --filename /tmp/toto'.split()
        # expected_url = self.base_url + '/restore/'
        with open('/tmp/toto', 'a') as toto:
            toto.write(' ')

        with patch('managesf.cli.get_cookie') as c:
            c.return_value = 'fake_cookie'
            test_mock = '%s.open' % __name__
            with patch(test_mock, create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=file)
                with patch('requests.post') as method:
                    method.return_value = FakeResponse()
                    parsed = self.parser.parse_args(args)
                    params = {'headers': self.headers, 'cookies': self.cookies}
                    params['data'] = json.dumps(data)
                    self.assertTrue(cli.replication_action(parsed,
                                                           self.base_url,
                                                           self.headers))
                    # method.assert_called_with(expected_url, **params)


class TestSystemActions(BaseFunctionalTest):
    def test_backup(self):
        args = self.default_args
        args += 'system backup_start'.split()
        expected_url = self.base_url + '/backup/'
        self.assert_secure('post', args, cli.backup_action, expected_url)
