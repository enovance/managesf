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


import logging
import re
from six.moves import urllib_parse

from managesf.services import base


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
STORIES = re.compile(r"([Ss]tory):\s+\#?(\d+)", re.VERBOSE)
CLOSING_ISSUE = re.compile("""(
[Bb]ug|
[Ff]ix|
[Ii]ssue|
[Tt]ask|
)
:\s+
\#?(\d+)""", re.VERBOSE)

RELATED_ISSUE = re.compile("""(
[Rr]elated|
[Rr]elated[ -][Tt]o)
:\s+
\#?(\d+)""", re.VERBOSE)


def parse_commit_message(message, issue_reg):
    """Parse the commit message

    :returns: The redmine issue ID
              or None if there is no Issue reference
    """
    m = issue_reg.findall(message)
    if not m:
        return []
    # Only match the first mentionned bug
    return [y for x, y in m]


def generic_storyboard_hook(kwargs, task_status,
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
    closing_issues = parse_commit_message(kwargs.get('commit_message', ''),
                                          CLOSING_ISSUE)
    related_issues = parse_commit_message(kwargs.get('commit_message', ''),
                                          RELATED_ISSUE)
    stories = parse_commit_message(kwargs.get('commit_message', ''),
                                   STORIES)
    for task in closing_issues:
        client.tasks.update(id=task, status=task_status)
    for task in related_issues and task_status == 'inprogress':
        client.tasks.update(id=task, status='inprogress')
    for story in stories:
        client.stories.get(story).comments.create(content=message)
    if not related_issues and not closing_issues and not stories:
        return "No issue found in the commit message, nothing to do."
    return 'Success'


class StoryboardHooksManager(base.BaseHooksManager):

    def patchset_created(self, *args, **kwargs):
        """Set tickets impacted by the patch to 'In Progress'."""
        gitweb_url = urllib_parse.urljoin(self.plugin.conf['base_url'],
                                          gitweb_url_suffix)
        try:
            msg = generic_storyboard_hook(kwargs, "inprogress", gitweb_url,
                                          template_message=CREATED,
                                          client=self.plugin.get_client())
            logger.debug(u'[%s] %s: %s' % (self.plugin.service_name,
                                           'patchset_created',
                                           msg))
            return msg
        except Exception as e:
            logger.error(u'[%s] %s: %s' % (self.plugin.service_name,
                                           'patchset_created',
                                           unicode(e)))
            # re-raise
            raise e

    def change_merged(self, *args, **kwargs):
        """Set tickets impacted by the patch to 'Closed' if the patch
        resolves the issue."""
        gitweb_url = urllib_parse.urljoin(self.plugin.conf['base_url'],
                                          gitweb_url_suffix)
        try:
            msg = generic_storyboard_hook(kwargs, "merged", gitweb_url,
                                          template_message=MERGED,
                                          client=self.plugin.get_client())
            logger.debug('[%s] %s: %s' % (self.plugin.service_name,
                                          'patchset_created',
                                          msg))
            return msg
        except Exception as e:
            logger.error(u'[%s] %s: %s' % (self.plugin.service_name,
                                           'patchset_created',
                                           unicode(e)))
            # re-raise
            raise e
