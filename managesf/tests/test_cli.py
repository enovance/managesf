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
from mock import patch, MagicMock, mock_open

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
        expected_url = self.base_url + 'project/proj1/'
        self.assert_secure('put', args, cli.project_action, expected_url)

    def test_create_private_project(self):
        args = self.default_args
        args += 'project create --name p1 --private'.split()
        expected_url = self.base_url + 'project/p1/'
        data = {'private': True}
        self.assert_secure('put', args, cli.project_action, expected_url, data)

    def test_create_project_with_groups(self):
        args = self.default_args
        args += 'project create --name p2 --core-group u1,u2,u3'.split()
        expected_url = self.base_url + 'project/p2/'
        data = {'core-group-members': ['u1', 'u2', 'u3']}
        self.assert_secure('put', args, cli.project_action, expected_url, data)

    def test_delete_project(self):
        args = self.default_args
        args += 'project delete --name proj1'.split()
        expected_url = self.base_url + 'project/proj1/'
        self.assert_secure('delete', args, cli.project_action, expected_url)


class TestTestsActions(BaseFunctionalTest):
    def test_init_test_project(self):
        args = self.default_args
        args += 'tests init --project toto'.split()
        expected_url = self.base_url + 'tests/toto/'
        self.assert_secure('put', args, cli.tests_action, expected_url,
                           {'project-scripts': True})

    def test_init_test_project_no_scripts(self):
        args = self.default_args
        args += 'tests init --project toto --no-scripts'.split()
        expected_url = self.base_url + 'tests/toto/'
        self.assert_secure('put', args, cli.tests_action, expected_url,
                           {'project-scripts': False})


class TestMembershipAction(BaseFunctionalTest):
    def test_project_add_user_to_groups(self):
        args = self.default_args
        c = 'membership add --user u --project p --groups dev-group,ptl-group'
        args += c.split()
        expected_url = self.base_url + 'project/membership/p/u/'
        self.assert_secure('put', args, cli.membership_action, expected_url,
                           {'groups': ['dev-group', 'ptl-group']})

        c = 'membership add --user u --project p --groups dev-group ptl-group'
        args += c.split()
        expected_url = self.base_url + 'project/membership/p/u/'
        self.assert_secure('put', args, cli.membership_action, expected_url,
                           {'groups': ['dev-group', 'ptl-group']})

    def test_project_remove_user_from_all_groups(self):
        args = self.default_args
        args += 'membership remove --user user1 --project proj1'.split()
        expected_url = self.base_url + 'project/membership/proj1/user1/'
        self.assert_secure('delete', args, cli.membership_action,
                           expected_url)

    def test_project_remove_user_from_group(self):
        args = self.default_args
        cmd = 'membership remove --user u1 --project proj1 --group dev-group'
        args += cmd.split()
        expected_url = self.base_url + 'project/membership/proj1/u1/dev-group/'
        self.assert_secure('delete', args, cli.membership_action,
                           expected_url)

    def test_list_users_per_project(self):
        args = self.default_args
        args += 'membership list'.split()
        expected_url = self.base_url + 'project/membership/'
        self.assert_secure('get', args, cli.membership_action, expected_url)


class TestUserActions(BaseFunctionalTest):
    def test_user_create(self):
        args = self.default_args
        data = {'email': 'e@test.com',
                'password': 'abc123',
                'fullname': 'toto the tester'}
        cmd = 'user create -f {fullname} -u u1 -p {password} --email {email}'
        args += cmd.format(**data).split()
        expected_url = self.base_url + 'user/u1/'
        self.assert_secure('post', args, cli.user_management_action,
                           expected_url, data)

    def test_user_delete(self):
        args = self.default_args
        args += 'user delete --user test2'.split()
        expected_url = self.base_url + 'user/test2/'
        self.assert_secure('delete', args, cli.user_management_action,
                           expected_url)

    def test_user_update(self):
        args = self.default_args
        data = {'email': 'e@test.com', 'password': 'abc123'}
        cmd = 'user update --username t3 --password {password} --email {email}'
        args += cmd.format(**data).split()
        expected_url = self.base_url + 'user/t3/'
        self.assert_secure('post', args, cli.user_management_action,
                           expected_url, data)


class TestReplicationActions(BaseFunctionalTest):
    def test_replication(self):
        data = {'wait': 'true', 'url': 'git://ex.com', 'project': 'p1'}
        args = self.default_args
        args += 'replication trigger --wait -p p1 --url git://ex.com'.split()
        expected_url = self.base_url + 'replication/'
        self.assert_secure('post', args, cli.replication_action, expected_url,
                           data)

    def test_configure_list(self):
        args = self.default_args
        args += 'replication configure list'.split()
        expected_url = self.base_url + 'replication/'
        self.assert_secure('get', args, cli.replication_action, expected_url)

    def test_configure_get_all(self):
        args = self.default_args
        args += 'replication configure get-all --section toto'.split()
        expected_url = self.base_url + 'replication/toto/'
        self.assert_secure('get', args, cli.replication_action, expected_url)

    def test_configure_add(self):
        args = self.default_args
        x = 'replication configure add --section mysql_config projects config'
        args += x.split()
        expected_url = self.base_url + 'replication/mysql_config/projects/'
        self.assert_secure('put', args, cli.replication_action, expected_url,
                           {'value': 'config'})

    def test_configure_remove(self):
        args = self.default_args
        args += 'replication configure remove --section BBB'.split()
        expected_url = self.base_url + 'replication/BBB/'
        self.assert_secure('delete', args, cli.replication_action,
                           expected_url)

    def test_rename_section(self):
        args = self.default_args
        args += 'replication configure rename --section CCC AAA'.split()
        expected_url = self.base_url + 'replication/CCC/'
        self.assert_secure('put', args, cli.replication_action, expected_url,
                           {'value': 'AAA'})

    def test_replace_all(self):
        return
        args = self.default_args
        args += 'replication configure replace-all --section B url DD'.split()
        expected_url = self.base_url + '/replication/B/url/'
        self.assert_secure('delete', args, cli.replication_action,
                           expected_url, {})


class TestSystemActions(BaseFunctionalTest):
    def test_backup(self):
        args = self.default_args
        args += 'system backup_start'.split()
        expected_url = self.base_url + 'backup/'
        self.assert_secure('post', args, cli.backup_action, expected_url)

    def test_restore(self):
        args = self.default_args
        args += 'system restore --filename tmp_backup'.split()
        expected_url = self.base_url + 'restore/'
        with open('tmp_backup', 'a') as toto:
            toto.write(' ')

        with patch('managesf.cli.get_cookie') as c:
            c.return_value = 'fake_cookie'
            test_mock = 'managesf.cli.open'
            with patch(test_mock, create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=file)
                with patch('requests.post') as method:
                    method.return_value = FakeResponse()
                    parsed = self.parser.parse_args(args)
                    params = {'headers': self.headers, 'cookies': self.cookies}
                    params['files'] = {'file': mock_open.return_value}
                    self.assertTrue(cli.backup_action(parsed,
                                                      self.base_url,
                                                      self.headers))
                    method.assert_called_with(expected_url, **params)


class TestGerrit(BaseFunctionalTest):
    def test_generate_htpasswd(self):
        args = self.default_args
        args += 'gerrit generate_password'.split()
        expected_url = self.base_url + 'htpasswd/'
        self.assert_secure('put', args, cli.gerrit_api_htpasswd_action,
                           expected_url)

    def test_remove_htpasswd(self):
        args = self.default_args
        args += 'gerrit delete_password'.split()
        expected_url = self.base_url + 'htpasswd/'
        self.assert_secure('delete', args, cli.gerrit_api_htpasswd_action,
                           expected_url)

    def test_add_ssh_config(self):
        args = self.default_args
        x = 'gerrit add_sshkey --alias u1 --hostname localhost --keyfile k.pub'
        args += x.split()
        expected_url = self.base_url + 'sshconfig/u1/'

        with patch('managesf.cli.get_cookie') as c:
            c.return_value = 'fake_cookie'
            test_mock = 'managesf.cli.open'
            with patch(test_mock, mock_open(read_data='tt'), create=True):
                with patch('requests.put') as method:
                    method.return_value = FakeResponse()
                    parsed = self.parser.parse_args(args)
                    params = {'headers': self.headers, 'cookies': self.cookies}
                    params['data'] = json.dumps({
                        "hostname": "localhost",
                        "userknownHostsfile": "/dev/null",
                        "preferredauthentications": "publickey",
                        "stricthostkeychecking": "no",
                        "identityfile_content": "tt"
                    })
                    self.assertTrue(cli.gerrit_ssh_config_action(parsed,
                                                                 self.base_url,
                                                                 self.headers))
                    method.assert_called_with(expected_url, **params)

    def test_remove_ssh_config(self):
        args = self.default_args
        args += 'gerrit delete_sshkey --alias u3'.split()
        expected_url = self.base_url + 'sshconfig/u3/'
        self.assert_secure('delete', args, cli.gerrit_ssh_config_action,
                           expected_url)
