# -*- coding: utf-8 -*-
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

from unittest import TestCase
from mock import patch
from contextlib import nested

from managesf.tests import dummy_conf

from managesf.model.yamlbkd.resource import ResourceInvalidException
from managesf.model.yamlbkd.resources.gitrepository import GitRepository
from managesf.model.yamlbkd.resources.group import Group
from managesf.model.yamlbkd.resources.gitacls import ACL


class RealResourcesTest(TestCase):
    """ Validate the resources model. This test
    only try to instanciate the resource.
    """

    def setUp(self):
        self.conf = dummy_conf()

    def test_repo_resource(self):
        p = GitRepository('id', {})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software-factory',
                           'badkey': None,
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software factory',
                           'description': 'SF'})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = GitRepository('id',
                          {'namespace': 'sf',
                           'name': 'software-factory',
                           'description': 'SF'})
        p.validate()

    def test_repo_callbacks(self):
        # TODO(fbo): To be completed
        patches = [
            patch('managesf.services.gerrit.get_cookie'),
            patch('pysflib.sfgerrit.GerritUtils.create_project'),
            patch("managesf.model.yamlbkd.resources."
                  "gitrepository.GitRepositoryOps.install_acl"),
        ]
        with nested(*patches) as (gc, cp, ia):
            GitRepository.CALLBACKS['create'](
                self.conf, {},
                {'name': 'p1',
                 'namespace': 'awesome',
                 'description': 'An awesome project',
                 'acl': 'aclid1'}
            )
            self.assertTrue(cp.called)
            self.assertTrue(ia.called)

    def test_group_resource(self):
        p = Group('id', {})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders'})
        p.validate()
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders',
                   'members': ['a@megacorp.com', 'b@megacorp.com']})
        p.validate()
        p = Group('id',
                  {'namespace': 'sf',
                   'name': 'ptl-group',
                   'description': 'Project Team Leaders',
                   'members': ['a@megacorp.com', 'abc']})
        self.assertRaises(ResourceInvalidException,
                          p.validate)

    def test_group_callbacks(self):
        # TODO(fbo): To be completed
        pass

    def test_acl_resource(self):
        p = ACL('id', {})
        self.assertRaises(ResourceInvalidException,
                          p.validate)
        p = ACL('id',
                {'file': """This is a wrong git
config file !
""",
                 'groups': ['gid1', 'gid2']
                 })
        logs = ACL.CALLBACKS['extra_validations'](
            None, None, p.get_resource())
        self.assertTrue(logs[0].startswith("File contains no section headers"))
        p = ACL('id',
                {'file': """[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
[remote "origin"]
        url = http://softwarefactory-project.io/r/software-factory
        fetch = +refs/heads/*:refs/remotes/origin/*
""",
                 'groups': ['gid1', 'gid2']
                 })
        logs = ACL.CALLBACKS['extra_validations'](
            None, None, p.get_resource())
        self.assertEqual(len(logs), 0)
