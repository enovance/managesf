#
# Copyright (C) 2016 Red Hat
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
# -*- coding: utf-8 -*-


from oslo_policy import policy

from managesf.policies import base


BASE_POLICY_NAME = 'managesf.membership'
POLICY_ROOT = BASE_POLICY_NAME + ':%s'


CREATE_OR_DELETE = '%s or %s ' % (base.RULE_ADMIN_API, base.RULE_PTL_API)
# cores can add/delete to core or dev groups
CREATE_OR_DELETE += 'or (%s and ' % base.RULE_CORE_API
CREATE_OR_DELETE += ('(target.group:%(project)s-core or ')
CREATE_OR_DELETE += ('target.group:%(project)s-dev))')
# devs can add/delete to dev groups
CREATE_OR_DELETE += ' or (%s and ' % base.RULE_DEV_API
CREATE_OR_DELETE += ('target.group:%(project)s-dev)')


rules = [
    policy.RuleDefault(
        name=POLICY_ROOT % 'get',
        check_str=base.RULE_ANY),
    policy.RuleDefault(
        name=POLICY_ROOT % 'create',
        check_str=CREATE_OR_DELETE),
    policy.RuleDefault(
        name=POLICY_ROOT % 'delete',
        check_str=CREATE_OR_DELETE),
]


def list_rules():
    return rules
