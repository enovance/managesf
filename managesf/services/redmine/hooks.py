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


import logging
import re
from six.moves import urllib_parse

from managesf.services import base
# from managesf.services import exceptions as exc


logger = logging.getLogger(__name__)


gitweb_url_suffix = "/r/gitweb?p=%(project)s;a=commit;h=%(commit)s"
CREATED = """Fix proposed to branch: %(branch)s by %(submitter)s
Review: %(url)s
"""
MERGED = """The following change on Gerrit has been merged to: %(branch)s
Review: %(url)s
Submitter: %(submitter)s

Commit message:
%(commit)s

gitweb: %(gitweb)s
"""

# Common patterns used in our hooks
CLOSING_ISSUE_REGEX = """(
[Bb]ug|
[Ff]ix|
[Ss]tory|
[Ii]ssue|
[Cc]loses?)
:\s+
\#?(\d+)"""
CLOSING_ISSUE = re.compile(CLOSING_ISSUE_REGEX, re.VERBOSE)
RELATED_ISSUE_REGEX = """(
[Rr]elated|
[Rr]elated[ -][Tt]o)
:\s+
\#?(\d+)"""
RELATED_ISSUE = re.compile(RELATED_ISSUE_REGEX, re.VERBOSE)
XXXIMPACT_REGEX = """^(\w+)Impact$"""
XXXIMPACT = re.compile(XXXIMPACT_REGEX, re.VERBOSE | re.UNICODE)


def parse_commit_message(message, issue_reg):
    """Parse the commit message

    :returns: The redmine issue ID
              or None if there is no Issue reference
    """
    m = issue_reg.findall(message)
    if not m:
        return None
    # Only match the first mentionned bug
    return m[0][1]


def generic_redmine_hook(kwargs, status_closing, status_related,
                         gitweb_url, template_message, client):
    if str(kwargs.get('patchset', 1)) != "1":
        msg = 'Do nothing as the patchset is not the first'
        return msg
    gitweb = gitweb_url % {'project': kwargs.get('project') + '.git',
                           'commit': kwargs.get('commit')}
    submitter = kwargs.get('submitter',
                           kwargs.get('uploader', ''))
    message = template_message % {'branch': kwargs.get('branch'),
                                  'url': kwargs.get('change_url'),
                                  'submitter': submitter,
                                  'commit': kwargs.get('commit_message', ''),
                                  'gitweb': gitweb}
    closing_issue = parse_commit_message(kwargs.get('commit_message', ''),
                                         CLOSING_ISSUE)
    related_issue = parse_commit_message(kwargs.get('commit_message', ''),
                                         RELATED_ISSUE)
    if closing_issue:
        if not client.set_issue_status(closing_issue,
                                       status_closing,
                                       message=message):
            msg = "Could not change status of issue #%s" % closing_issue
            # TODO(mhu) more precise exceptions ?
            raise Exception(msg)
    if related_issue and related_issue != closing_issue:
        if not client.set_issue_status(related_issue,
                                       status_related,
                                       message=message):
            msg = "Could not change status of issue #%s" % related_issue
            # TODO(mhu) more precise exceptions ?
            raise Exception(msg)
    if not related_issue and not closing_issue:
        msg = "No issue found in the commit message, nothing to do."
        return msg
    return 'Issue(s) successfully modified'


class RedmineHooksManager(base.BaseHooksManager):

    def patchset_created(self, *args, **kwargs):
        """Set tickets impacted by the patch to 'In Progress'."""
        status_closing = 2
        status_related = 2
        gitweb_url = urllib_parse.urljoin(self.plugin.conf['url'],
                                          gitweb_url_suffix)
        try:
            msg = generic_redmine_hook(kwargs, status_closing,
                                       status_related, gitweb_url,
                                       template_message=CREATED,
                                       client=self.plugin.get_client())
            logger.debug('[%s] %s: %s' % (self.plugin.service_name,
                                          'patchset_created',
                                          msg))
            return msg
        except Exception as e:
            logger.error('[%s] %s: %s' % (self.plugin.service_name,
                                          'patchset_created',
                                          e.message))
            # re-raise
            raise e

    def change_merged(self, *args, **kwargs):
        a = self._close_patch_ticket(*args, **kwargs)
        b = self._create_impact_ticket(*args, **kwargs)
        return '\n'.join((a, b))

    def _create_impact_ticket(self, *args, **kwargs):
        """Create 'XXXImpact' follow-up ticket."""
        msg = kwargs.get('commit_message', '')
        impacts = sum([XXXIMPACT.findall(m) for m in msg.split('\n')
                       if XXXIMPACT.findall(m)], [])
        to_return = []
        # ensure unicity
        impacts = dict((u, None) for u in impacts).keys()
        client = self.plugin.get_client()
        if not impacts:
            return 'No XXXImpact, nothing to do.'
        for impact in impacts:
            issue_title = u"[%s] %s" % (impact, msg.split('\n')[0])
            desc = ("This issue was automatically created as a "
                    "follow-up to merging %s" % kwargs.get('change_url'))
            try:
                id = client.create_issue(kwargs.get('project'),
                                         subject=issue_title,
                                         description=desc)
                dbg = '%sImpact issue #%s created' % (impact, id)
                logger.debug('[%s] %s: %s' % (self.plugin.service_name,
                                              'impact_ticket',
                                              dbg))
                to_return.append(dbg)
            except Exception as e:
                logger.error('[%s] %s: %s' % (self.plugin.service_name,
                                              'impact_ticket',
                                              e.message))
                to_return.append('%sImpact not created' % impact)
        return '\n'.join(to_return)

    def _close_patch_ticket(self, *args, **kwargs):
        """Set tickets impacted by the patch to 'Closed' if the patch
        resolves the issue."""
        status_closing = 5
        status_related = 2
        gitweb_url = urllib_parse.urljoin(self.plugin.conf['url'],
                                          gitweb_url_suffix)
        try:
            msg = generic_redmine_hook(kwargs, status_closing,
                                       status_related, gitweb_url,
                                       template_message=MERGED,
                                       client=self.plugin.get_client())
            logger.debug('[%s] %s: %s' % (self.plugin.service_name,
                                          'close_patch_ticket',
                                          msg))
            return msg
        except Exception as e:
            logger.error('[%s] %s: %s' % (self.plugin.service_name,
                                          'close_patch_ticket',
                                          e.message))
            # re-raise
            raise e
