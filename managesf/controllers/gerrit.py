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
from pecan import abort
from pecan import request
from gerritlib import gerrit
from managesf.controllers.utils import template
from subprocess import Popen, PIPE

import os
import stat
import re
import shlex
import shutil
import time
import subprocess
import logging
import tempfile
import yaml

from pysflib.sfgerrit import GerritUtils
from pysflib.sfauth import get_cookie

logger = logging.getLogger(__name__)

ADMIN_COOKIE = None
ADMIN_COOKIE_DATE = 0
COOKIE_VALIDITY = 60


def get_client(cookie=None):
    if not cookie:
        # Use an admin cookie
        if int(time.time()) - globals()['ADMIN_COOKIE_DATE'] > \
                globals()['COOKIE_VALIDITY']:
            cookie = get_cookie(conf.auth['host'],
                                conf.admin['name'],
                                conf.admin['http_password'])
            globals()['ADMIN_COOKIE'] = cookie
            globals()['ADMIN_COOKIE_DATE'] = int(time.time())
        else:
            cookie = globals()['ADMIN_COOKIE']
    return GerritUtils(conf.gerrit['url'],
                       auth_cookie=cookie)


def get_projects_by_user():
    ge = get_client()
    projects = ge.get_projects()
    if user_is_administrator():
        return projects
    names = []
    for project in projects:
        if user_owns_project(project):
            names.append(project)
    return names


def get_projects():
    ge = get_client()
    return ge.get_projects()


def get_project(project_name):
    ge = get_client()
    return ge.get_project(project_name)


def create_group(grp_name, grp_desc):
    logger.info('[gerrit] creating group %s' % grp_name)
    ge = get_client()
    ge.create_group(grp_name, grp_desc)
    ge.add_group_member(request.remote_user, grp_name)


def get_my_groups():
    user_cookie = request.cookies['auth_pubtkt']
    ge = get_client(cookie=user_cookie)
    return ge.get_my_groups_id()


def user_owns_project(prj_name):
    grps = get_my_groups()
    ge = get_client()
    owner = ge.get_project_owner(prj_name)
    return owner in grps


def get_project_groups(project_name):
    ge = get_client()
    groups = ge.get_project_groups(project_name)
    if isinstance(groups, bool):
        logger.info("Could not find project %s: %s" % (
            project_name, str(groups)))
        groups = []
    return groups


def user_is_administrator():
    ge = get_client()
    grps = get_my_groups()
    admin_id = ge.get_group_id('Administrators')
    if admin_id in grps:
        return True
    return False


def get_core_group_name(prj_name):
    return "%s-core" % prj_name


def get_ptl_group_name(prj_name):
    return "%s-ptl" % prj_name


def get_dev_group_name(prj_name):
    return "%s-dev" % prj_name


def get_open_changes():
    ge = get_client()
    return ge.get_open_changes()


class GerritRepo(object):
    def __init__(self, prj_name):
        # TODO: manage to destroy temp dir/file after usage
        self.prj_name = prj_name
        self.infos = {}
        self.infos['localcopy_path'] = os.path.join(
            tempfile.mkdtemp(), 'clone-%s' % prj_name)
        if os.path.isdir(self.infos['localcopy_path']):
            shutil.rmtree(self.infos['localcopy_path'])
        self.email = "%(admin)s <%(email)s>" % \
                     {'admin': conf.admin['name'],
                      'email': conf.admin['email']}
        wrapper_path = self._ssh_wraper_setup(conf.gerrit['sshkey_priv_path'])
        self.env = os.environ.copy()
        self.env['GIT_SSH'] = wrapper_path
        # Commit will be reject by gerrit if the commiter info
        # is not a registered user (author can be anything else)
        self.env['GIT_COMMITTER_NAME'] = conf.admin['name']
        self.env['GIT_COMMITTER_EMAIL'] = conf.admin['email']
        # This var is used by git-review to set the remote via git review -s
        self.env['USERNAME'] = conf.admin['name']

    def _ssh_wraper_setup(self, filename):
        ssh_wrapper = "ssh -o StrictHostKeyChecking=no -i %s \"$@\"" % filename
        wrapper_path = os.path.join(tempfile.mkdtemp(), 'ssh_wrapper.sh')
        file(wrapper_path, 'w').write(ssh_wrapper)
        os.chmod(wrapper_path, stat.S_IRWXU)
        self.env = os.environ.copy()
        return wrapper_path

    def _exec(self, cmd, cwd=None):
        cmd = shlex.split(cmd)
        ocwd = os.getcwd()
        if cwd:
            os.chdir(cwd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             env=self.env, cwd=cwd)
        p.wait()
        std_out, std_err = p.communicate()
        # logging std_out also logs std_error as both use same pipe
        if std_out:
            logger.info("[gerrit] cmd %s output" % cmd)
            logger.info(std_out)
        os.chdir(ocwd)

    def clone(self):
        logger.info("[gerrit] Clone repository %s" % self.prj_name)
        cmd = "git clone ssh://%(admin)s@%(gerrit-host)s" \
              ":%(gerrit-host-port)s/%(name)s %(localcopy_path)s" % \
              {'admin': conf.admin['name'],
               'gerrit-host': conf.gerrit['host'],
               'gerrit-host-port': conf.gerrit['ssh_port'],
               'name': self.prj_name,
               'localcopy_path': self.infos['localcopy_path']
               }
        self._exec(cmd)

    def add_file(self, path, content):
        logger.info("[gerrit] Add file %s to index" % path)
        if path.split('/') > 1:
            d = re.sub(os.path.basename(path), '', path)
            try:
                os.makedirs(os.path.join(self.infos['localcopy_path'], d))
            except OSError:
                pass
        file(os.path.join(self.infos['localcopy_path'],
             path), 'w').write(content)
        cmd = "git add %s" % path
        self._exec(cmd, cwd=self.infos['localcopy_path'])

    def push_config(self, paths):
        logger.info("[gerrit] Prepare push on config for repository %s" %
                    self.prj_name)
        cmd = "git fetch origin " + \
              "refs/meta/config:refs/remotes/origin/meta/config"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git checkout meta/config"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        for path, content in paths.items():
            self.add_file(path, content)
        cmd = "git commit -a --author '%s' -m'Provides ACL and Groups'" % \
              self.email
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git push origin meta/config:meta/config"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        logger.info("[gerrit] Push on config for repository %s" %
                    self.prj_name)

    def push_master(self, paths):
        logger.info("[gerrit] Prepare push on master for repository %s" %
                    self.prj_name)
        cmd = "git checkout master"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        for path, content in paths.items():
            self.add_file(path, content)
        cmd = "git commit -a --author '%s' -m'ManageSF commit'" % self.email
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git push origin master"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        logger.info("[gerrit] Push on master for repository %s" %
                    self.prj_name)

    def push_master_from_git_remote(self, remote, ssh_key=None):
        if ssh_key:
            tmpf = tempfile.NamedTemporaryFile(delete=False)
            tmpf.close()
            fname = tmpf.name
            with open(fname, "wb") as f:
                f.write(ssh_key)
            os.chmod(f.name, 0600)
            wrapper_path = self._ssh_wraper_setup(fname)
            self.env = os.environ.copy()
            self.env['GIT_SSH'] = wrapper_path
        logger.info("[gerrit] Fetch git objects from a remote and push "
                    "to master for repository %s" % self.prj_name)
        cmd = "git checkout master"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git remote add upstream %s" % remote
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git fetch upstream"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        if ssh_key:
            wrapper_path = self._ssh_wraper_setup(
                conf.gerrit['sshkey_priv_path'])
            self.env = os.environ.copy()
            self.env['GIT_SSH'] = wrapper_path
            os.remove(f.name)
        logger.info("[gerrit] Push remote (master branch) of %s to the "
                    "Gerrit repository" % remote)
        cmd = "git push -f origin upstream/master:master"
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git reset --hard origin/master"
        self._exec(cmd, cwd=self.infos['localcopy_path'])

    def review_changes(self, commit_msg):
        logger.info("[gerrit] Send a review via git review")
        cmd = "ssh-agent bash -c 'ssh-add %s; git review -s'" %\
              conf.gerrit['sshkey_priv_path']
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = "git commit -a --author '%s' -m'%s'" % (self.email,
                                                      commit_msg)
        self._exec(cmd, cwd=self.infos['localcopy_path'])
        cmd = 'git review'
        self._exec(cmd, cwd=self.infos['localcopy_path'])


class CustomGerritClient(gerrit.Gerrit):
    def deleteGroup(self, name):
        # TODO(mhu) remove this method
        logger.info("[gerrit] Deleting group " + name)
        grp_id = "select group_id from account_group_names " \
                 "where name=\"%s\"" % name
        tables = ['account_group_members',
                  'account_group_members_audit',
                  'account_group_by_id',
                  'account_group_by_id_aud',
                  'account_groups']
        for t in tables:
            cmd = 'gerrit gsql -c \'delete from %(table)s where ' \
                  'group_id=(%(grp_id)s)\'' % {'table': t, 'grp_id': grp_id}
            out, err = self._ssh(cmd)
        cmd = 'gerrit gsql -c \'delete from account_group_names ' \
              'where name=\"%s\"' % (name)
        out, err = self._ssh(cmd)

    def reload_replication_plugin(self):
        cmd = 'gerrit plugin reload replication'
        out, err = self._ssh(cmd)

    def trigger_replication(self, cmd):
        logger.info("[gerrit] Triggering Replication")
        out, err = self._ssh(cmd)
        if err:
            logger.info("[gerrit] Replication Trigger error - %s" % err)


def init_git_repo(prj_name, prj_desc, upstream, private,
                  ssh_key=None, readonly=False):
    logger.info("[gerrit] Init gerrit project repo: %s" % prj_name)
    ge = get_client()
    grps = {}
    grps['project-description'] = prj_desc
    grps['core-group-uuid'] = ge.get_group_id(get_core_group_name(prj_name))
    grps['ptl-group-uuid'] = ge.get_group_id(get_ptl_group_name(prj_name))
    if private:
        grps['dev-group-uuid'] = ge.get_group_id(get_dev_group_name(prj_name))
    grps['non-interactive-users'] = ge.get_group_id('Non-Interactive%20Users')
    grps['core-group'] = get_core_group_name(prj_name)
    grps['ptl-group'] = get_ptl_group_name(prj_name)
    if private:
        grps['dev-group'] = get_dev_group_name(prj_name)
    grepo = GerritRepo(prj_name)
    grepo.clone()
    paths = {}

    prefix = ''
    if private:
        prefix = 'private-'
    if readonly:
        prefix = 'readonly-%s' % prefix
    paths['project.config'] = file(template(prefix +
                                   'project.config')).read() % grps
    paths['groups'] = file(template(prefix + 'groups')).read() % grps
    grepo.push_config(paths)
    if upstream:
        grepo.push_master_from_git_remote(upstream, ssh_key)
    paths = {}
    paths['.gitreview'] = file(template('gitreview')).read() % \
        {'gerrit-host': conf.gerrit['top_domain'],
         'gerrit-host-port': conf.gerrit['ssh_port'],
         'name': prj_name
         }
    grepo.push_master(paths)


def init_project(name, json):
    logger.info("[gerrit] Init gerrit project: %s" % name)
    upstream = None if 'upstream' not in json else json['upstream']
    ssh_key = (False if 'upstream-ssh-key' not in json
               else json['upstream-ssh-key'])
    description = "" if 'description' not in json else json['description']
    private = False if 'private' not in json else json['private']
    readonly = False if 'readonly' not in json else json['readonly']
    ge = get_client()
    core = get_core_group_name(name)
    core_desc = "Core developers for project " + name
    create_group(core, core_desc)
    if 'core-group-members' in json:
        for m in json['core-group-members']:
            add_user_to_projectgroups(name, m, ["core-group"])

    ptl = get_ptl_group_name(name)
    ptl_desc = "Project team lead for project " + name
    create_group(ptl, ptl_desc)
    if 'ptl-group-members' in json:
        for m in json['ptl-group-members']:
            add_user_to_projectgroups(name, m, ["ptl-group"])

    if private:
        dev = get_dev_group_name(name)
        dev_desc = "Developers for project " + name
        create_group(dev, dev_desc)
        if 'dev-group-members' in json:
            for m in json['dev-group-members']:
                if m != request.remote_user:
                    add_user_to_projectgroups(name, m, ["dev-group"])

    owner = [get_ptl_group_name(name)]
    ge.create_project(name, description, owner)
    init_git_repo(name, description, upstream, private, ssh_key, readonly)


def add_user_to_projectgroups(project, user, groups):
    logger.info("[gerrit] Add user %s in groups %s for project %s" %
                (user, str(groups), project))
    ge = get_client()
    for g in groups:
        if g not in ['ptl-group', 'core-group', 'dev-group']:
            abort(400)
    grps = get_my_groups()
    ptl_gid = ge.get_group_id(get_ptl_group_name(project))
    core_gid = ge.get_group_id(get_core_group_name(project))
    # only PTL can add user to ptl group
    if 'ptl-group' in groups:
        if (ptl_gid not in grps) and (not user_is_administrator()):
            logger.info("[gerrit] Current user is not ptl or admin")
            abort(401)
        ptl = get_ptl_group_name(project)
        ge.add_group_member(user, ptl)
    if 'core-group' in groups:
        if (core_gid not in grps) and (ptl_gid not in grps) and \
           (not user_is_administrator()):
            logger.info("[gerrit] Current user is not core,ptl, or admin")
            abort(401)
        core = get_core_group_name(project)
        ge.add_group_member(user, core)
    if 'dev-group' in groups:
        dev = get_dev_group_name(project)
        if ge.group_exists(dev):
            dev_gid = ge.get_group_id(dev)
            if (core_gid not in grps) and (ptl_gid not in grps) and \
               (dev_gid not in grps) and (not user_is_administrator()):
                logger.info("[gerrit] Current user is "
                            "not ptl,core,dev,admin")
                abort(401)
            ge.add_group_member(user, dev)


def delete_user_from_projectgroups(project, user, group):
    if group:
        if group not in ['ptl-group', 'core-group', 'dev-group']:
            abort(400)
        groups = [group]
    else:
        groups = ['ptl-group', 'core-group', 'dev-group']

    logger.info("[gerrit] Remove user %s from groups %s for project %s" %
                (user, groups, project))

    ge = get_client()
    core_gid = ge.get_group_id(get_core_group_name(project))
    ptl_gid = ge.get_group_id(get_ptl_group_name(project))
    # get the groups of the current user
    grps = get_my_groups()
    dev = get_dev_group_name(project)
    # delete dev group if requested
    if ('dev-group' in groups) and ge.group_exists(dev):
        dev_gid = ge.get_group_id(dev)
        if (dev_gid not in grps) and (core_gid not in grps) and \
           (ptl_gid not in grps) and (not user_is_administrator()):
            logger.info("[gerrit] User is not dev, core, ptl, admin")
            abort(401)
        dev_mid = ge.get_group_member_id(dev_gid, mail=user)
        # not found ? try by user
        if not dev_mid:
            dev_mid = ge.get_group_member_id(dev_gid, username=user)
        if dev_mid:
            ge.delete_group_member(dev_gid, dev_mid)

    # delete ptl group if requested
    if 'ptl-group' in groups:
        if (ptl_gid not in grps) and (not user_is_administrator()):
            logger.info("[gerrit] User is not ptl, admin")
            abort(401)
        ptl_mid = ge.get_group_member_id(ptl_gid, mail=user)
        if not ptl_mid:
            ptl_mid = ge.get_group_member_id(ptl_gid, username=user)
        if ptl_mid:
            ge.delete_group_member(ptl_gid, ptl_mid)

    # delete core group if requested
    if 'core-group' in groups:
        if (ptl_gid not in grps) and (core_gid not in grps) and \
           (not user_is_administrator()):
            logger.info("[gerrit] User is not core, ptl, admin")
            abort(401)
        core_mid = ge.get_group_member_id(core_gid, mail=user)
        if core_mid:
            ge.delete_group_member(core_gid, core_mid)


def delete_project(name):
    logger.info("[gerrit] Delete project %s" % name)
    if not user_owns_project(name) and not user_is_administrator():
        logger.debug("[gerrit] User is neither an Administrator"
                     " nor does own project")
        abort(401)

    # user owns the project, so delete it now
    gerrit_client = CustomGerritClient(conf.gerrit['host'],
                                       conf.admin['name'],
                                       keyfile=conf.gerrit['sshkey_priv_path'])
    gerrit_client.deleteGroup(get_core_group_name(name))
    gerrit_client.deleteGroup(get_ptl_group_name(name))
    try:
        # if dev group exists, no exception will be thrown
        gerrit_client.deleteGroup(get_dev_group_name(name))
    except Exception:
        pass
    ge = get_client()
    ge.delete_project(name, force=True)


def replication_ssh_run_cmd(subcmd, shell=False):
    host = '%s@%s' % (conf.gerrit['user'], conf.gerrit['host'])
    sshcmd = ['ssh', '-o', 'LogLevel=ERROR', '-o', 'StrictHostKeyChecking=no',
              '-o', 'UserKnownHostsFile=/dev/null', '-i',
              conf.gerrit['sshkey_priv_path'], host]
    cmd = sshcmd + subcmd

    if shell:
        cmd = " ".join(cmd)
    p1 = Popen(cmd, stdout=PIPE, stderr=subprocess.STDOUT, shell=shell)
    out, err = p1.communicate()
    return out, err, p1.returncode


def replication_fill_knownhosts(url):
    try:
        host = url.split(':')[0]
        host = host.split('@')[1]
    except Exception, e:
        logger.info("[gerrit] Unable to parse %s %s. Will not scan !" %
                    (url, str(e)))
        return
    logger.info("[gerrit] ssh-keyscan on %s" % host)
    cmd = \
        [" \"ssh-keyscan -v -T5 %s >> /home/gerrit/.ssh/known_hosts_gerrit\"" %
         host]
    out, err, code = replication_ssh_run_cmd(cmd, shell=True)
    logger.info(code)
    if code:
        logger.info("[gerrit] ssh-keyscan failed on %s" % host)
        logger.debug("[gerrit] ssh-keyscan stdout: %s" % out)
    else:
        logger.info("[gerrit] ssh-keyscan succeed on %s" % host)


def replication_read_config():
    lines = []
    cmd = ['git', 'config', '-f', conf.gerrit['replication_config_path'], '-l']
    out, err, code = replication_ssh_run_cmd(cmd)
    if code:
        logger.info("[gerrit] Reading config file err %s " % err)
        logger.info("[gerrit] --[\n%s\n]--" % out)
        abort(500)
    elif out:
        logger.info("[gerrit] Contents of replication config file ... \n%s " %
                    out)
        out = out.strip()
        lines = out.split("\n")
    config = {}
    for line in lines:
        setting, value = line.split("=")
        section = setting.split(".")[1]
        setting = setting.split(".")[2]
        if setting == 'projects':
            if (len(value.split()) != 1):
                logger.info("[gerrit] Invalid Replication config file.")
                abort(500)
            elif section in config and 'projects' in config[section]:
                logger.info("[gerrit] Invalid Replication config file.")
                abort(500)
        if section not in config.keys():
            config[section] = {}
        config[section].setdefault(setting, []).append(value)
    logger.info("(gerrit] Contents of the config file - " + str(config))
    return config


def replication_validate(projects, config, section=None, setting=None):
    settings = ['push', 'projects', 'url', 'receivepack', 'uploadpack',
                'timeout', 'replicationDelay', 'threads']
    if setting and (setting not in settings):
        logger.info("[gerrit] Setting %s is not supported." % setting)
        logger.info("[gerrit] Supported settings - " + " , ".join(settings))
        abort(400)
    if len(projects) == 0:
        logger.info("[gerrit] User doesn't own any project.")
        abort(403)
    if section and (section in config):
        for project in config[section].get('projects', []):
            if project not in projects:
                logger.info("[gerrit] User unauthorized for this section %s" %
                            section)
                abort(403)


def replication_apply_config(section, setting=None, value=None):
    projects = get_projects_by_user()
    config = replication_read_config()
    replication_validate(projects, config, section, setting)
    gitcmd = ['git', 'config', '-f', conf.gerrit['replication_config_path']]
    _section = 'remote.' + section
    if value:
        if setting:
            if setting == 'url' and ('$' in value):
                # To allow $ in url
                value = "\$".join(value.rsplit("$", 1))
            if setting == 'url':
                # Get the remote fingerprint
                replication_fill_knownhosts(value)
            cmd = ['--add', '%s.%s' % (_section, setting), value]
        else:
            cmd = ['--rename-section', _section, 'remote.%s' % value]
    elif setting:
        cmd = ['--unset-all', '%s.%s' % (_section, setting)]
    else:
        cmd = ['--remove-section', _section]
    str_cmd = " ".join(cmd)
    logger.info("[gerrit] Requested command is ... \n%s " % str_cmd)
    cmd = gitcmd + cmd
    out, err, code = replication_ssh_run_cmd(cmd)
    if code:
        logger.info("[gerrit] apply_config err %s " % err)
        return err
    else:
        logger.info("[gerrit] Reload the replication plugin to pick up"
                    " the new configuration")
        gerrit_client = CustomGerritClient(
            conf.gerrit['host'],
            conf.admin['name'],
            keyfile=conf.gerrit['sshkey_priv_path'])
        gerrit_client.reload_replication_plugin()


def replication_get_config(section=None, setting=None):
    projects = get_projects_by_user()
    config = replication_read_config()
    replication_validate(projects, config, section, setting)
    userConfig = {}

    # First, filter out any project the user has no access to
    for _section in config:
        for project in config[_section].get('projects', []):
            if project in projects:
                userConfig[_section] = config[_section]

    # Limit response to section if set
    if section:
        userConfig = userConfig.get(section, {})

    # Limit response to setting if set
    if setting:
        userConfig = userConfig.get(setting, {})

    logger.info("[gerrit] Config for user: %s" % str(userConfig))
    if userConfig:
        return userConfig


def replication_trigger(json):
    logger.info("[gerrit] Replication_trigger %s" % str(json))
    wait = True if 'wait' not in json else json['wait'] in ['True', 'true', 1]
    url = None if 'url' not in json else json['url']
    project = None if 'project' not in json else json['project']
    cmd = " replication start"
    projects = get_projects_by_user()
    config = replication_read_config()
    find_section = None
    for section in config:
        if url and 'url' in config[section]:
            if url in config[section]['url']:
                find_section = section
                cmd = cmd + " --url %s" % url
                break
        elif project and 'projects' in config[section]:
            if project in config[section]['projects']:
                find_section = section
                cmd = cmd + " %s" % project
                break
    if find_section:
        replication_validate(projects, config, find_section)
    elif wait:
        cmd = cmd + " --wait"
    elif user_is_administrator():
        cmd = cmd + " --all"
    else:
        logger.info("[gerrit] Trigger replication for"
                    " all projects owned by user")
        if len(projects) == 0:
            logger.info("[gerrit] User doesn't own any projects, "
                        "so unauthorized to trigger repilication")
            abort(403)
        cmd = cmd + "  " + "  ".join(projects)
    logger.info("[gerrit] Replication cmd - %s " % cmd)
    gerrit_client = CustomGerritClient(conf.gerrit['host'],
                                       conf.admin['name'],
                                       keyfile=conf.gerrit['sshkey_priv_path'])
    gerrit_client.trigger_replication(cmd)


def propose_test_definition(project_name, requester):
    config_git = GerritRepo('config')
    config_git.clone()
    job_file = os.path.join(config_git.infos['localcopy_path'],
                            'jobs', 'projects.yaml')
    zuul_file = os.path.join(config_git.infos['localcopy_path'],
                             'zuul', 'projects.yaml')
    unit_test = '%s-unit-tests' % project_name

    with open(job_file, 'r') as fd:
        job_yaml = yaml.load(fd)
        projects = [x['project']['name'] for x in job_yaml
                    if x.get('project')]
    if project_name not in projects:
        with open(job_file, 'w') as fd:
            project = {'project':
                       {'name': project_name,
                        'jobs': ['{name}-unit-tests', ],
                        'node': 'master'}}
            job_yaml.append(project)
            fd.write(yaml.safe_dump(job_yaml))

    with open(zuul_file, 'r') as fd:
        zuul_yaml = yaml.load(fd)
        projects = [x['name'] for x in zuul_yaml['projects']]

    if project_name not in projects:
        with open(zuul_file, 'w') as fd:
            project = {'name': project_name,
                       'check': [unit_test, ],
                       'gate': [unit_test, ]}
            zuul_yaml['projects'].append(project)
            fd.write(yaml.safe_dump(zuul_yaml))

    config_git.review_changes(
        '%s proposes initial test definition for project %s' %
        (requester, project_name))


def propose_test_scripts(project_name, requester):
    test_script_template = '''#!/bin/bash

echo "Modify this script to run your project's unit tests."
exit 0;'''
    project_git = GerritRepo(project_name)
    project_git.clone()
    project_git.add_file('run_tests.sh', test_script_template)
    os.chmod(os.path.join(project_git.infos['localcopy_path'],
                          'run_tests.sh'), stat.S_IRWXU)
    project_git.review_changes(
        '%s proposes initial test scripts for project %s' %
        (requester, project_name))
