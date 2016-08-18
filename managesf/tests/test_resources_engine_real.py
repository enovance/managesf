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

from managesf.model.yamlbkd import engine


class EngineRealResourcesTest(TestCase):
    def test_group_validation(self):
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('os.path.isdir'),
            patch('os.mkdir'),
            patch('managesf.model.yamlbkd.resources.group.'
                  'GroupOps.extra_validations'),
        ]
        master = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a cool group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }

        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: groups, ID: g1] is going to be updated.',
                logs)
            self.assertEqual(len(logs), 1)

        master = {
            'resources': {
                'groups': {}
                }
            }
        new = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a cool group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }

        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: groups, ID: g1] is going to be created.',
                logs)
            self.assertEqual(len(logs), 1)

        master = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: groups, ID: g1] is going to be updated.',
                logs)
            self.assertEqual(len(logs), 1)

        master = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'groups': {
                    'g2': {
                        'namespace': 'sf',
                        'name': 'g2',
                        'description': 'This is a group',
                        'members': [
                            'user4@sftests.com'
                            ]
                        }
                    }
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: groups, ID: g1] is going to be deleted.',
                logs)
            self.assertIn(
                'Resource [type: groups, ID: g2] is going to be created.',
                logs)
            self.assertEqual(len(logs), 2)

        master = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g2',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertFalse(valid)
            self.assertIn(
                "Resource [type: groups, ID: g1] contains changed "
                "resource keys that are immutable. Please check the model.",
                logs)
            self.assertEqual(len(logs), 1)

    def test_acls_validation(self):
        patches = [
            patch('managesf.model.yamlbkd.engine.'
                  'SFResourceBackendEngine._load_resources_data'),
            patch('os.path.isdir'),
            patch('os.mkdir'),
            patch('managesf.model.yamlbkd.resources.gitacls.'
                  'ACLOps.extra_validations'),
        ]
        master = {
            'resources': {
                'acls': {}
                }
            }
        new = {
            'resources': {
                'acls': {
                    'a1': {
                        'file': "this is a\nfake acls",
                        'groups': ['g1'],
                        }
                    }
                }
            }

        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertFalse(valid)
            self.assertIn(
                'Resource [type: acls, ID: a1] is going to be created.',
                logs)
            self.assertIn(
                'Resource [type: acls, ID: a1] depends on an unknown '
                'resource [type: groups, ID: g1]',
                logs)
            self.assertEqual(len(logs), 2)

        master = {
            'resources': {
                'acls': {},
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'acls': {
                    'a1': {
                        'file': "this is a\nfake acls",
                        'groups': ['g1'],
                        }
                    },
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: acls, ID: a1] is going to be created.',
                logs)
            self.assertEqual(len(logs), 1)

        master = {
            'resources': {
                'acls': {
                    'a1': {
                        'file': "this is a\nfake acls",
                        'groups': ['g1'],
                        }
                    },
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'acls': {},
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertTrue(valid)
            self.assertIn(
                'Resource [type: acls, ID: a1] is going to be deleted.',
                logs)
            self.assertEqual(len(logs), 1)

        master = {
            'resources': {
                'acls': {
                    'a1': {
                        'file': "this is a\nfake acls",
                        'groups': ['g1'],
                        }
                    },
                'groups': {
                    'g1': {
                        'namespace': 'sf',
                        'name': 'g1',
                        'description': 'This is a group',
                        'members': [
                            'user1@sftests.com'
                            'user2@sftests.com'
                            ]
                        }
                    }
                }
            }
        new = {
            'resources': {
                'acls': {
                    'a1': {
                        'file': "this is a\nfake acls",
                        'groups': ['g1'],
                        }
                    },
                'groups': {},
                }
            }
        with nested(*patches) as (l, i, m, xv):
            l.return_value = (master, new)
            xv.return_value = []
            eng = engine.SFResourceBackendEngine('fake', 'resources')
            valid, logs = eng.validate(None, None, None, None)
            self.assertFalse(valid)
            self.assertIn(
                'Resource [type: groups, ID: g1] is going to be deleted.',
                logs)
            self.assertIn(
                'Resource [type: acls, ID: a1] depends on an unknown '
                'resource [type: groups, ID: g1]',
                logs)
            self.assertEqual(len(logs), 2)

    # TODO: WIP
