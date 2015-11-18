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

import json
import os

from unittest import TestCase
from webtest import TestApp
from pecan import load_app
from contextlib import nested
from mock import patch

from basicauth import encode

from managesf.tests import dummy_conf

# plugins imports
# TODO: should be done dynamically depending on what plugins we want
from managesf.services.base import BackupManager
from managesf.services.gerrit import project
from managesf.services.gerrit.membership import SFGerritMembershipManager
from managesf.services.gerrit.project import SFGerritProjectManager
from managesf.services.gerrit.review import SFGerritReviewManager
from managesf.services.redmine import SoftwareFactoryRedmine
from managesf.services.redmine.membership import SFRedmineMembershipManager
from managesf.services.redmine.project import SFRedmineProjectManager


def raiseexc(*args, **kwargs):
    raise Exception('FakeExcMsg')


class FunctionalTest(TestCase):
    def setUp(self):
        c = dummy_conf()
        self.config = {'services': c.services,
                       'gerrit': c.gerrit,
                       'redmine': c.redmine,
                       'app': c.app,
                       'admin': c.admin,
                       'sqlalchemy': c.sqlalchemy,
                       'auth': c.auth,
                       'htpasswd': c.htpasswd,
                       'sshconfig': c.sshconfig,
                       'managesf': c.managesf,
                       'jenkins': c.jenkins,
                       'mysql': c.mysql}
        # deactivate loggin that polute test output
        # even nologcapture option of nose effetcs
        # 'logging': c.logging}
        self.app = TestApp(load_app(self.config))

    def tearDown(self):
        # Remove the sqlite db
        os.unlink(self.config['sqlalchemy']['url'][len('sqlite:///'):])


class TestManageSFIntrospectionController(FunctionalTest):

    def test_instrospection(self):
        response = self.app.get('/about/').json
        self.assertEqual('managesf',
                         response['service']['name'])
        self.assertEqual(set(['zuul', 'jenkins', 'lodgeit',
                              'etherpad', 'managesf']),
                         set(response['service']['services']))
        self.assertEqual(set(['gerrit', 'redmine']),
                         set(response['service']['auth_services']))


class TestManageSFAppLocaluserController(FunctionalTest):

    def test_add_or_update_user(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        infos = {'email': 'john@tests.dom', 'sshkey': 'sshkey',
                 'fullname': 'John Doe', 'password': 'secret'}
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 201)
        infos = {'email': 'john2@tests.dom', 'sshkey': 'sshkey',
                 'fullname': 'John Doe', 'password': 'bigsecret'}
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 200)
        infos = {'wrongkey': 'heyhey'}
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 400)

        # Only admin can add user to that database
        environ = {'REMOTE_USER': 'boss'}
        infos = {'email': 'john2@tests.dom', 'sshkey': 'sshkey',
                 'fullname': 'John Doe 2', 'password': 'secret'}
        response = self.app.post_json('/user/john2', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 403)

    def test_get_user(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        infos = {'email': 'john@tests.dom', 'sshkey': 'sshkey',
                 'fullname': 'John Doe', 'password': 'secret'}
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 201)

        response = self.app.get('/user/john',
                                extra_environ=environ, status="*")
        expected = {u'sshkey': u'sshkey',
                    u'username': u'john',
                    u'email': u'john@tests.dom',
                    u'fullname': u'John Doe'}
        self.assertEqual(response.status_int, 200)
        self.assertDictEqual(response.json, expected)

        response = self.app.get('/user/notexists',
                                extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 404)

        environ = {'REMOTE_USER': 'john'}
        response = self.app.get('/user/john',
                                extra_environ=environ, status="*")
        expected = {u'sshkey': u'sshkey',
                    u'username': u'john',
                    u'email': u'john@tests.dom',
                    u'fullname': u'John Doe'}
        self.assertEqual(response.status_int, 200)
        self.assertDictEqual(response.json, expected)

        environ = {'REMOTE_USER': 'boss'}
        response = self.app.get('/user/john',
                                extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 403)

    def test_delete_user(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        infos = {'email': 'john@tests.dom', 'sshkey': 'sshkey',
                 'fullname': 'John Doe', 'password': 'secret'}
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 201)

        environ = {'REMOTE_USER': 'boss'}
        response = self.app.delete('/user/john',
                                   extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 403)

        environ = {'REMOTE_USER': self.config['admin']['name']}
        response = self.app.delete('/user/john',
                                   extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 200)
        response = self.app.get('/user/john',
                                extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 404)

    def test_bind_user(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        base_infos = {'email': 'john@tests.dom', 'sshkey': 'sshkey',
                      'fullname': 'John Doe', }
        infos = {'password': 'secret'}
        public_infos = {'username': 'john'}
        infos.update(base_infos)
        public_infos.update(base_infos)
        response = self.app.post_json('/user/john', infos,
                                      extra_environ=environ, status="*")
        self.assertEqual(response.status_int, 201)

        headers = {"Authorization": encode("john", "secret")}
        response = self.app.get('/bind', headers=headers,
                                status="*")
        self.assertEqual(response.status_int, 200)
        self.assertEqual(public_infos,
                         response.json,
                         response.json)

        headers = {"Authorization": encode("john", "badsecret")}
        response = self.app.get('/bind', headers=headers,
                                status="*")
        self.assertEqual(response.status_int, 401)

        headers = {"Authorization": encode("boss", "secret")}
        response = self.app.get('/bind', headers=headers,
                                status="*")
        self.assertEqual(response.status_int, 401)


def project_get(*args, **kwargs):
    if kwargs.get('by_user'):
        return ['p1', ]
    return ['p0', 'p1']


class TestManageSFAppProjectController(FunctionalTest):

    def test_project_get_all(self):
        ctx = [patch.object(SFGerritProjectManager, 'get'),
               patch.object(SFGerritProjectManager, 'get_groups'),
               patch.object(SFGerritReviewManager, 'get'),
               patch.object(SoftwareFactoryRedmine,
                            'get_open_issues')]
        with nested(*ctx) as (p_get, get_groups, r_get, goi):
            p_get.side_effect = project_get
            r_get.return_value = [{'project': 'p1'}]
            goi.return_value = {'issues': [{'project': {'name': 'p1'}}]}
            get_groups.return_value = [{'name': 'p0-ptl'}, {'name': 'p0-dev'}]
            # Cookie is only required for the internal cache
            response = self.app.set_cookie('auth_pubtkt', 'something')
            response = self.app.get('/project/')
            self.assertEqual(200, response.status_int)
            body = json.loads(response.body)
            self.assertIn('p0', body)
            self.assertTrue(body['p1']['open_reviews'] and
                            body['p1']['open_issues'])
            self.assertEqual({'ptl': {'name': 'p0-ptl'},
                              'dev': {'name': 'p0-dev'}},
                             body['p0']['groups'])
            for _mock in (p_get, get_groups, r_get, goi):
                self.assertTrue(_mock.called)

            # Second request, will be cached - no internal calls
            for _mock in (p_get, get_groups, r_get, goi):
                _mock.reset_mock()
            response = self.app.get('/project/')
            for _mock in (p_get, get_groups, r_get, goi):
                self.assertFalse(_mock.called)
            self.assertEqual(200, response.status_int)

    def test_project_get_one(self):
        ctx = [patch.object(SFGerritProjectManager, 'get'),
               patch.object(SFGerritProjectManager, 'get_groups'),
               patch.object(SFGerritReviewManager, 'get'),
               patch.object(SoftwareFactoryRedmine,
                            'get_open_issues')]
        with nested(*ctx) as (p_get, get_groups, r_get, goi):
            p_get.side_effect = project_get
            r_get.return_value = [{'project': 'p1'}, ]
            goi.return_value = {'issues': [{'project': {'name': 'p1'}}]}
            response = self.app.set_cookie('auth_pubtkt', 'something')
            response = self.app.get('/project/p1')
            self.assertEqual(200, response.status_int)
            self.assertTrue('"open_issues": 1', response.body)
            self.assertTrue('"admin": 1', response.body)
            self.assertTrue('"open_reviews": 1', response.body)

    def test_project_put(self):
        # Create a project with no name
        with patch('managesf.controllers.root.is_admin') as gia:
            response = self.app.put('/project/', status="*")
            self.assertEqual(response.status_int, 400)
        # Create a project with name, but without administrator status
        with patch('managesf.controllers.root.is_admin') as gia:
            gia.return_value = False
            response = self.app.put('/project/p1', status="*")
            self.assertEqual(response.status_int, 401)
        # Create a project with name
        ctx = [patch.object(project.SFGerritProjectManager, 'create'),
               patch('managesf.controllers.root.is_admin'),
               patch.object(SFRedmineProjectManager,
                            'create')]
        with nested(*ctx) as (gip, gia, rip):
            response = self.app.put('/project/p1', status="*",
                                    extra_environ={'REMOTE_USER': 'bob'})
            self.assertTupleEqual(('p1', 'bob', {}), gip.mock_calls[0][1])
            self.assertTupleEqual(('p1', 'bob', {}), rip.mock_calls[0][1])
            self.assertEqual(response.status_int, 201)
            self.assertEqual(json.loads(response.body),
                             'Project p1 has been created.')
        # Create a project with name - an error occurs
        ctx = [patch.object(project.SFGerritProjectManager, 'create'),
               patch('managesf.controllers.root.is_admin'),
               patch.object(SFRedmineProjectManager,
                            'create',
                            side_effect=raiseexc)]
        with nested(*ctx) as (gip, gia, rip):
            response = self.app.put('/project/p1', status="*",
                                    extra_environ={'REMOTE_USER': 'bob'})
            self.assertEqual(response.status_int, 500)
            self.assertEqual(json.loads(response.body),
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')

    def test_project_delete(self):
        # Delete a project with no name
        response = self.app.delete('/project/', status="*")
        self.assertEqual(response.status_int, 400)
        # Deletion of config project is not possible
        response = self.app.delete('/project/config', status="*")
        self.assertEqual(response.status_int, 400)
        # Delete a project with name
        ctx = [patch.object(SFGerritProjectManager, 'delete'),
               patch.object(SFRedmineProjectManager, 'delete')]
        with nested(*ctx) as (gdp, rdp):
            response = self.app.delete('/project/p1', status="*",
                                       extra_environ={'REMOTE_USER': 'testy'})
            self.assertTupleEqual(('p1', 'testy'), gdp.mock_calls[0][1])
            self.assertTupleEqual(('p1', 'testy'), rdp.mock_calls[0][1])
            self.assertEqual(response.status_int, 200)
            self.assertEqual(json.loads(response.body),
                             'Project p1 has been deleted.')
        # Delete a project with name - an error occurs
        ctx = [patch.object(SFGerritProjectManager, 'delete'),
               patch.object(SFRedmineProjectManager, 'delete',
                            side_effect=raiseexc)]
        with nested(*ctx) as (gip, rip):
            response = self.app.delete('/project/p1', status="*")
            self.assertEqual(response.status_int, 500)
            self.assertEqual(json.loads(response.body),
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')


class TestManageSFAppRestoreController(FunctionalTest):
    def tearDown(self):
        if os.path.isfile('/var/www/managesf/sf_backup.tar.gz'):
            os.unlink('/var/www/managesf/sf_backup.tar.gz')

    def test_restore_post(self):
        files = [('file', 'useless', 'backup content')]
        # restore a provided backup
        ctx = [patch('managesf.controllers.backup.backup_restore'),
               patch('managesf.controllers.backup.backup_unpack'),
               patch.object(BackupManager,
                            'restore'), ]
        with nested(*ctx) as (backup_restore, backup_unpack, restore):
            response = self.app.post('/restore', status="*",
                                     upload_files=files)
            self.assertTrue(os.path.isfile(
                '/var/www/managesf/sf_backup.tar.gz'))
            self.assertTrue(backup_unpack.called)
            self.assertTrue(backup_restore.called)
            self.assertEqual(3, len(restore.mock_calls))
            self.assertEqual(response.status_int, 204)
        # restore a provided backup - an error occurs
        with nested(*ctx) as (backup_restore, backup_unpack, restore):
            backup_restore.side_effect = raiseexc
            response = self.app.post('/restore', status="*",
                                     upload_files=files)
            self.assertTrue(os.path.isfile(
                '/var/www/managesf/sf_backup.tar.gz'))
            self.assertEqual(response.status_int, 500)
            self.assertEqual(json.loads(response.body),
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')


class TestManageSFAppBackupController(FunctionalTest):
    def tearDown(self):
        if os.path.isfile('/var/www/managesf/sf_backup.tar.gz'):
            os.unlink('/var/www/managesf/sf_backup.tar.gz')

    def test_backup_get(self):
        file('/var/www/managesf/sf_backup.tar.gz', 'w').write('backup content')
        response = self.app.get('/backup', status="*")
        self.assertEqual(response.body, 'backup content')
        os.unlink('/var/www/managesf/sf_backup.tar.gz')
        response = self.app.get('/backup', status="*")
        self.assertEqual(response.status_int, 404)

    def test_backup_post(self):
        ctx = [patch('managesf.controllers.backup.backup_start'),
               patch.object(BackupManager,
                            'backup'),
               patch('managesf.controllers.root.is_admin'), ]
        with nested(*ctx) as (backup_start, backup, is_admin):
            is_admin.return_value = False
            response = self.app.post('/backup', status="*")
            self.assertEqual(response.status_int, 401)
            is_admin.return_value = True
            response = self.app.post('/backup', status="*")
            self.assertEqual(response.status_int, 204)
            self.assertEqual(3, len(backup.mock_calls))
            self.assertTrue(backup_start.called)


class TestManageSFAppMembershipController(FunctionalTest):
    def test_get_all_users(self):
        with patch.object(SoftwareFactoryRedmine,
                          'get_active_users') as au:
            au.return_value = [[1, "a"], [2, "b"]]
            response = self.app.get('/project/membership/', status="*")
            self.assertEqual(200, response.status_int)
            body = json.loads(response.body)
            self.assertEqual([[1, "a"], [2, "b"]], body)

    def test_put_empty_values(self):
        response = self.app.put_json('/project/membership/', {}, status="*")
        self.assertEqual(response.status_int, 400)
        response = self.app.put_json('/project/p1/membership/', {}, status="*")
        self.assertEqual(response.status_int, 400)
        response = self.app.put_json('/project/p1/membership/john', {},
                                     status="*")
        self.assertEqual(response.status_int, 400)

    def test_put(self):
        ctx = [patch.object(SFRedmineMembershipManager,
                            'create'),
               patch.object(SFGerritMembershipManager,
                            'create')]
        with nested(*ctx) as (gaupg, raupg):
            response = self.app.put_json(
                '/project/p1/membership/john@tests.dom',
                {'groups': ['ptl-group', 'core-group']},
                status="*")
            self.assertEqual(response.status_int, 201)
            self.assertEqual(json.loads(response.body),
                             "User john@tests.dom has been added in group(s):"
                             " ptl-group, core-group for project p1")
        ctx = [patch.object(SFGerritMembershipManager,
                            'create'),
               patch.object(SFRedmineMembershipManager,
                            'create',
                            side_effect=raiseexc)]
        with nested(*ctx) as (gaupg, raupg):
            response = self.app.put_json(
                '/project/p1/membership/john@tests.dom',
                {'groups': ['ptl-group', 'core-group']},
                status="*")
            self.assertEqual(response.status_int, 500)
            self.assertEqual(json.loads(response.body),
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')

    def test_delete(self):
        response = self.app.delete('/project/p1/membership/john', status="*")
        self.assertEqual(response.status_int, 400)
        ctx = [
            patch.object(SFGerritMembershipManager,
                         'delete'),
            patch.object(SFRedmineMembershipManager,
                         'delete')]
        with nested(*ctx) as (gdupg, rdupg):
            response = self.app.delete(
                '/project/p1/membership/john',
                status="*")
            self.assertEqual(response.status_int, 400)
            self.assertEqual(json.loads(response.body),
                             "User must be identified by its email address")
            response = self.app.delete(
                '/project/p1/membership/john@tests.dom',
                status="*")
            self.assertEqual(response.status_int, 200)
            self.assertEqual(json.loads(response.body),
                             "User john@tests.dom has been deleted from all "
                             "groups for project p1.")
            response = self.app.delete(
                '/project/p1/membership/john@tests.dom/core-group',
                status="*")
            self.assertEqual(response.status_int, 200)
            self.assertEqual(json.loads(response.body),
                             "User john@tests.dom has been deleted from group "
                             "core-group for project p1.")
        ctx = [
            patch.object(SFGerritMembershipManager,
                         'delete'),
            patch.object(SFRedmineMembershipManager,
                         'delete',
                         side_effect=raiseexc)]
        with nested(*ctx) as (gdupg, rdupg):
            response = self.app.delete(
                '/project/p1/membership/john@tests.dom',
                status="*")
            self.assertEqual(response.status_int, 500)
            self.assertEqual(json.loads(response.body),
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')


class TestManageSFAppReplicationController(FunctionalTest):
    def test_put(self):
        response = self.app.put_json('/replication/', {}, status="*")
        self.assertEqual(response.status_int, 400)
        response = self.app.put_json('/replication/repl', {}, status="*")
        self.assertEqual(response.status_int, 400)
        with patch('managesf.controllers.gerrit.replication_apply_config'):
            response = self.app.put_json(
                '/replication/repl', {'value': 'val'}, status="*")
            self.assertEqual(response.status_int, 204)
        with patch('managesf.controllers.gerrit.replication_apply_config',
                   side_effect=raiseexc):
            response = self.app.put_json(
                '/replication/repl', {'value': 'val'}, status="*")
            self.assertEqual(response.status_int, 500)
            msg = json.loads(response.body)
            self.assertEqual(msg,
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')

    def test_delete(self):
        response = self.app.delete('/replication/', status="*")
        self.assertEqual(response.status_int, 400)
        with patch('managesf.controllers.gerrit.replication_apply_config'):
            response = self.app.delete(
                '/replication/repl', status="*")
            self.assertEqual(response.status_int, 204)
        with patch('managesf.controllers.gerrit.replication_apply_config',
                   side_effect=raiseexc):
            response = self.app.delete(
                '/replication/repl', status="*")
            self.assertEqual(response.status_int, 500)
            msg = json.loads(response.body)
            self.assertEqual(msg,
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')

    def test_get(self):
        with patch('managesf.controllers.gerrit.replication_get_config') \
                as rgc:
            rgc.return_value = 'ret val'
            response = self.app.get('/replication/', status="*")
            self.assertEqual(response.status_int, 200)
            response = self.app.get(
                '/replication/repl/', status="*")
            self.assertEqual(response.status_int, 200)
            msg = json.loads(response.body)
            self.assertEqual(msg, 'ret val')
        with patch('managesf.controllers.gerrit.replication_get_config',
                   side_effect=raiseexc):
            response = self.app.get(
                '/replication/repl/', status="*")
            self.assertEqual(response.status_int, 500)
            msg = json.loads(response.body)
            self.assertEqual(msg,
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')

    def test_post(self):
        with patch('managesf.controllers.gerrit.replication_trigger'):
            response = self.app.post_json(
                '/replication/',
                {},
                status="*")
            self.assertEqual(response.status_int, 204)
        with patch('managesf.controllers.gerrit.replication_trigger',
                   side_effect=raiseexc):
            response = self.app.post_json(
                '/replication/', status="*")
            self.assertEqual(response.status_int, 500)
            msg = json.loads(response.body)
            self.assertEqual(msg,
                             'Unable to process your request, failed '
                             'with unhandled error (server side): FakeExcMsg')


class TestManageSFHtpasswdController(FunctionalTest):
    def test_unauthenticated(self):
        resp = self.app.put_json('/htpasswd/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

        resp = self.app.get('/htpasswd/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

        resp = self.app.delete('/htpasswd/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

    def test_authenticated(self):
        env = {'REMOTE_USER': self.config['admin']['name']}

        resp = self.app.get('/htpasswd/', extra_environ=env, status="*")
        self.assertEqual(404, resp.status_int)

        resp = self.app.put_json('/htpasswd/', {}, extra_environ=env)
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(len(resp.body) >= 12)

        # Create new password
        old_password = resp.body
        resp = self.app.put_json('/htpasswd/', {}, extra_environ=env)
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(len(resp.body) >= 12)

        self.assertTrue(old_password != resp.body)

        # Create password for a different user
        newenv = {'REMOTE_USER': 'random'}
        resp = self.app.put_json('/htpasswd/', {}, extra_environ=newenv)
        self.assertEqual(resp.status_int, 201)
        self.assertTrue(len(resp.body) >= 12)

        # Ensure there are password entries for both users
        resp = self.app.get('/htpasswd/', extra_environ=env)
        self.assertEqual(204, resp.status_int)
        self.assertEqual(resp.body, 'null')

        resp = self.app.get('/htpasswd/', extra_environ=newenv)
        self.assertEqual(204, resp.status_int)
        self.assertEqual(resp.body, 'null')

        # Delete passwords
        resp = self.app.delete('/htpasswd/', extra_environ=env)
        self.assertEqual(204, resp.status_int)

        resp = self.app.delete('/htpasswd/', extra_environ=newenv)
        self.assertEqual(204, resp.status_int)

        resp = self.app.get('/htpasswd/', extra_environ=env, status="*")
        self.assertEqual(404, resp.status_int)

    def test_missing_htpasswd_file(self):
        os.remove(self.config['htpasswd']['filename'])
        env = {'REMOTE_USER': self.config['admin']['name']}

        resp = self.app.put('/htpasswd/', extra_environ=env, status="*")
        self.assertEqual(resp.status_int, 406)

        resp = self.app.get('/htpasswd/', extra_environ=env, status="*")
        self.assertEqual(resp.status_int, 406)

        resp = self.app.delete('/htpasswd/', extra_environ=env, status="*")
        self.assertEqual(resp.status_int, 406)


class TestManageSFSSHConfigController(FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(TestManageSFSSHConfigController, self).setUp(*args, **kwargs)
        self.adminenv = {'REMOTE_USER': self.config['admin']['name']}
        self.sample_config = {
            'hostname': 'Hostname',
            'identityfile_content': 'TheActualKeyOfTheHost',
            'userknownhostsfile': 'UserKnownHostsFile',
            'preferredauthentications': 'PreferredAuthentications',
            'stricthostkeychecking': 'StrictHostKeyChecking',
            'username': 'Username'
        }
        self.reference = """Host "firsthost"
    Hostname Hostname
    IdentityFile ~/.ssh/firsthost.key
    PreferredAuthentications PreferredAuthentications
    StrictHostKeyChecking StrictHostKeyChecking
    UserKnownHostsFile UserKnownHostsFile
    Username Username

"""
        confdir = self.config['sshconfig']['confdir']
        self.filename = os.path.join(confdir, "config")
        with open(self.filename, "w") as outf:
            outf.write(self.reference)

    def test_unauthenticated(self):
        resp = self.app.put_json('/sshconfig/name/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

        resp = self.app.get('/sshconfig/name/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

        resp = self.app.delete('/sshconfig/name/', {}, status="*")
        self.assertEqual(resp.status_int, 403)

    def test_add_entry(self):
        c2g = 'managesf.controllers.root.SSHConfigController._copy2gerrit'
        with patch(c2g):
            resp = self.app.put_json('/sshconfig/secondhost',
                                     self.sample_config,
                                     extra_environ=self.adminenv, status="*")

        self.assertEqual(resp.status_int, 201)

        with open(self.filename) as inf:
            content = inf.read()

        secondhost = self.reference.replace("firsthost", "secondhost")
        self.assertTrue(self.reference in content)
        self.assertTrue(secondhost in content)

    def test_delete_entry(self):
        resp = self.app.delete('/sshconfig/firsthost',
                               extra_environ=self.adminenv, status="*")

        self.assertEqual(resp.status_int, 204)

        with open(self.filename) as inf:
            content = inf.read()
        self.assertEqual("", content)


class TestProjectTestsController(FunctionalTest):
    def test_init_project_test(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        ctx = [patch.object(SFGerritProjectManager, 'get'),
               patch('managesf.controllers.gerrit.propose_test_definition')]
        with nested(*ctx) as (gp, ptd):
            gp.return_value = 'p1'
            resp = self.app.put_json('/tests/toto', {'project-scripts': False},
                                     extra_environ=environ, status="*")
            self.assertEqual(resp.status_int, 201)

    def test_init_project_test_with_project_scripts(self):
        environ = {'REMOTE_USER': self.config['admin']['name']}
        ctx = [patch.object(SFGerritProjectManager, 'get'),
               patch('managesf.controllers.gerrit.propose_test_definition'),
               patch('managesf.controllers.gerrit.propose_test_scripts')]
        with nested(*ctx) as (gp, ptd, pts):
            gp.return_value = 'p1'
            resp = self.app.put_json('/tests/toto', {'project-scripts': True},
                                     extra_environ=environ, status="*")
            self.assertEqual(resp.status_int, 201)
