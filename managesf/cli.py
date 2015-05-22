#!/usr/bin/env python
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

import argparse
import base64
import getpass
import json
import os
import requests
import sys


def die(msg):
    print "Error: %s" % msg
    sys.exit(1)


def split_and_strip(s):
    l = s.split(',')
    return [x.strip() for x in l]


def default_arguments(parser):
    parser.add_argument('--url',
                        help='Softwarefactory public gateway URL',
                        required=True)
    parser.add_argument('--auth', metavar='username[:password]',
                        help='Authentication information', required=True)
    parser.add_argument('--auth-server-url', metavar='central-auth-server',
                        default=None,
                        help='URL of the central auth server')
    parser.add_argument('--cookie', metavar='Authentication cookie',
                        help='cookie of the user if known')


def backup_command(sp):
    sp.add_parser('backup_get')
    sp.add_parser('backup_start')


def restore_command(sp):
    rst = sp.add_parser('restore')
    rst.add_argument('--filename', '-n', nargs='?', metavar='tarball-name',
                     required=True, help='Tarball used to restore SF')


def project_user_command(sp):
    dup = sp.add_parser('delete_user')
    dup.add_argument('--name', '-n', nargs='?', metavar='project-name',
                     required=True)
    dup.add_argument('--user', '-u', nargs='?', metavar='user-name',
                     required=True)
    dup.add_argument('--group', '-g', nargs='?', metavar='group-name')

    aup = sp.add_parser('add_user')
    aup.add_argument('--name', '-n', nargs='?', metavar='project-name',
                     required=True)
    aup.add_argument('--user', '-u', nargs='?', metavar='user-name',
                     required=True)
    aup.add_argument('--groups', '-p', nargs='?', metavar='ptl-group-members',
                     help='group names serarated by comma, allowed group names'
                     ' are core-group, dev-group, ptl-group',
                     required=True)

    sp.add_parser('list_active_users', help='Print a list of active users')


def user_management_command(sp):
    cump = sp.add_parser('create')
    cump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=True, help='A unique username/login')
    cump.add_argument('--password', '-p', nargs='?', metavar='password',
                      required=False,
                      help='The user password, can be provided later')
    cump.add_argument('--email', '-e', nargs='?', metavar='email',
                      required=True, help='The user email')
    cump.add_argument('--fullname', '-f', nargs='?', metavar='John Doe',
                      required=False,
                      help="The user's full name, defaults to username")
    cump.add_argument('--ssh-key', '-s', nargs='?', metavar='/path/to/pub_key',
                      required=False, help="The user's ssh public key file")
    uump = sp.add_parser('update')
    uump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=False,
                      help='the user to update, defaults to current user')
    uump.add_argument('--password', '-p', action='store_false',
                      help='Set this flag to change the user password')
    uump.add_argument('--email', '-e', nargs='?', metavar='email',
                      required=False, help='The user email')
    uump.add_argument('--fullname', '-f', nargs='?', metavar='John Doe',
                      required=False,
                      help="The user's full name")
    uump.add_argument('--ssh-key', '-s', nargs='?', metavar='/path/to/pub_key',
                      required=False, help="The user's ssh public key file")
    dump = sp.add_parser('delete', help='Delete user. Admin rights required')
    dump.add_argument('--username', '-u', nargs='?', metavar='username',
                      required=True, help='the user to delete')


def project_command(sp):
    cp = sp.add_parser('create')
    cp.add_argument('--name', '-n', nargs='?', metavar='project-name',
                    required=True)
    cp.add_argument('--description', '-d', nargs='?',
                    metavar='project-description')
    cp.add_argument('--upstream', '-u', nargs='?', metavar='GIT link')
    cp.add_argument('--upstream-ssh-key', metavar='upstream-ssh-key',
                    help='SSH key for upstream repository')
    cp.add_argument('--core-group', '-c', metavar='core-group-members',
                    help='member ids separated by comma', nargs='?')
    cp.add_argument('--ptl-group', '-p', metavar='ptl-group-members',
                    help='member ids serarated by comma', nargs='?')
    cp.add_argument('--dev-group', '-e', metavar='dev-group-members',
                    help='member ids serarated by comma'
                    ' (only relevant for private project)',
                    nargs='?')
    cp.add_argument('--private', action='store_true',
                    help='set if the project is private')

    dp = sp.add_parser('delete')
    dp.add_argument('--name', '-n', nargs='?', metavar='project-name',
                    required=True)


def section_command(sp):
    rp = sp.add_parser('replication_config')
    rps = rp.add_subparsers(dest="rep_command")

    rps.add_parser('list', help='List the sections and its content accessible'
                   ' to this user')

    repa = rps.add_parser('add', help='Add a setting value to the section')
    repa.add_argument('--section',  nargs='?', required=True,
                      help='section to which this setting belongs to')
    repa.add_argument('name', metavar='name', nargs='?',
                      help='Setting name. Supported settings - project, url')
    repa.add_argument('value',  nargs='?', help='Value of the setting')

    repg = rps.add_parser('get-all',
                          help='Get all the values of a section setting')
    repg.add_argument('--section',  nargs='?', required=True,
                      help='section to which this setting belongs to')
    repg.add_argument('name', metavar='name', nargs='?',
                      help='Setting name. Supported settings - project, url')

    repu = rps.add_parser('unset-all',
                          help='Remove the setting from the section')
    repu.add_argument('--section',  nargs='?', required=True,
                      help='section to which this setting belongs to')
    settings = 'projects, url, push, receivepack, uploadpack, timeout,'
    settings = settings + ' replicationDelay, threads'
    repu.add_argument('name', metavar='name', nargs='?',
                      help='Setting name. Supported settings - ' + settings)

    repr = rps.add_parser('replace-all',
                          help='replaces all the current values with '
                          'the given value for a setting')
    repr.add_argument('--section',  nargs='?', required=True,
                      help='section to which this setting belongs to')
    repr.add_argument('name', metavar='name', nargs='?',
                      help='Setting name. Supported settings - project, url')
    repr.add_argument('value',  nargs='?', help='Value of the setting')

    reprn = rps.add_parser('rename-section',  help='Rename the section')
    reprn.add_argument('--section',  nargs='?', required=True,
                       help='old section name')
    reprn.add_argument('value',  nargs='?', help='new section name')

    reprm = rps.add_parser('remove-section', help='Remove the section')
    reprm.add_argument('--section',  nargs='?', required=True,
                       help='section to be removed')


def trigger_command(sp):
    trp = sp.add_parser('trigger_replication')
    trp.add_argument('--wait', default=False, action='store_true')
    trp.add_argument('--project', metavar='project-name')
    trp.add_argument('--url', metavar='repo-url')


def command_options(parser):
    sp = parser.add_subparsers(dest="command")
    project_commands = sp.add_parser('project',
                                     help='project-related commands')
    spc = project_commands.add_subparsers(dest="subcommand")
    user_commands = sp.add_parser('user',
                                  help='project users-related commands')
    suc = user_commands.add_subparsers(dest="subcommand")
    backup_command(sp)
    restore_command(sp)
    project_user_command(spc)
    project_command(spc)
    user_management_command(suc)
    # for compatibility purpose, until calls in SF are modified
    project_user_command(sp)
    project_command(sp)
    section_command(sp)
    trigger_command(sp)


def get_cookie(args):
    if args.cookie is not None:
        return args.cookie
    (username, password) = args.auth.split(':')
    url = '%s/auth/login' % args.auth_server_url.rstrip('/')
    r = requests.post(url,
                      params={'username': username,
                              'password': password,
                              'back': '/'},
                      allow_redirects=False)
    if r.status_code == 401:
        die("Access denied, wrong login or password")
    elif r.status_code != 303:
        die("Could not access url %s" % url)
    elif len(r.cookies) < 1:
        die("Unknown error, server didn't set any cookie")
    return r.cookies['auth_pubtkt']


def response(resp):
    if resp.status_code >= 200 and resp.status_code < 206:
        print resp.text
        return True
    else:
        die(resp.text)


def project_user_action(args, base_url, headers):
    if args.command in ['add_user', 'delete_user', 'list_active_users']:
        subcommand = args.command
        print "Deprecated syntax, please use project %s ..." % subcommand
    elif args.command == 'project':
        subcommand = args.subcommand
    else:
        return False

    if subcommand in ['add_user', 'delete_user']:
        url = "{}/project/membership/{}/{}/".format(base_url, args.name,
                                                    args.user)
    elif subcommand == 'list_active_users':
        url = base_url + '/project/membership/'
    if subcommand == 'add_user':
        groups = split_and_strip(args.groups)
        data = json.dumps({'groups': groups})
        resp = requests.put(url, headers=headers, data=data,
                            cookies=dict(auth_pubtkt=get_cookie(args)))

    elif subcommand == 'delete_user':
        # if a group name is provided, delete user from that group,
        # otherwise delete user from all groups
        if args.group:
            url = url + args.group
        resp = requests.delete(url, headers=headers,
                               cookies=dict(auth_pubtkt=get_cookie(args)))

    elif subcommand == 'list_active_users':
        resp = requests.get(url, headers=headers,
                            cookies=dict(auth_pubtkt=get_cookie(args)))

    return response(resp)


def project_action(args, base_url, headers):
    if args.command in ['delete', 'create']:
        subcommand = args.command
        print "Deprecated syntax, please use project %s ..." % subcommand
    elif args.command == 'project':
        subcommand = args.subcommand
    else:
        return False

    url = base_url + "/project/%s" % args.name
    if subcommand == 'create':
        if getattr(args, 'core_group'):
            args.core_group = split_and_strip(args.core_group)
        if getattr(args, 'ptl_group'):
            args.ptl_group = split_and_strip(args.ptl_group)
        if getattr(args, 'dev_group'):
            args.dev_group = split_and_strip(args.dev_group)
        if getattr(args, 'upstream_ssh_key'):
            with open(args.upstream_ssh_key) as ssh_key_file:
                args.upstream_ssh_key = ssh_key_file.read()
        substitute = {'description': 'description',
                      'core_group': 'core-group-members',
                      'ptl_group': 'ptl-group-members',
                      'dev_group': 'dev-group-members',
                      'upstream': 'upstream',
                      'upstream_ssh_key': 'upstream-ssh-key',
                      'private': 'private'}
        info = {}
        for key, word in substitute.iteritems():
            if getattr(args, key):
                info[word] = getattr(args, key)

        data = None
        if len(info.keys()):
            data = json.dumps(info)

        resp = requests.put(url, headers=headers, data=data,
                            cookies=dict(auth_pubtkt=get_cookie(args)))

    elif subcommand == 'delete':
        resp = requests.delete(url, headers=headers,
                               cookies=dict(auth_pubtkt=get_cookie(args)))

    return response(resp)


def backup_action(args, base_url, headers):
    if args.command in ['backup_get', 'backup_start']:
        url = base_url + '/backup'
    else:
        return False

    if args.command == 'backup_get':
        resp = requests.get(url, headers=headers,
                            cookies=dict(auth_pubtkt=get_cookie(args)))
        if resp.status_code != 200:
            print "backup_get failed with status_code " + str(resp.status_code)
            sys.exit("error")
        chunk_size = 1024
        with open('sf_backup.tar.gz', 'wb') as fd:
            for chunk in resp.iter_content(chunk_size):
                fd.write(chunk)
        return True
    elif args.command == 'backup_start':
        url = base_url + '/backup'
        resp = requests.post(url, headers=headers,
                             cookies=dict(auth_pubtkt=get_cookie(args)))

    return response(resp)


def replication_action(args, base_url, headers):
    if args.command in ['restore', 'replication_config',
                        'trigger_replication']:
        pass
    else:
        return False

    if args.command == 'restore':
        url = base_url + '/restore'
        filename = args.filename
        if not os.path.isfile(filename):
            print "file %s not exist" % filename
            sys.exit("error")
        files = {'file': open(filename, 'rb')}
        resp = requests.post(url, headers=headers, files=files,
                             cookies=dict(auth_pubtkt=get_cookie(args)))

    elif args.command == 'replication_config':
        headers['Content-Type'] = 'application/json'
        settings = ['projects', 'url', 'push', 'receivepack', 'uploadpack',
                    'timeout', 'replicationDelay', 'threads']
        url = '%s/replication' % base_url
        data = {}
        if args.rep_command != "list":
            if getattr(args, 'section'):
                url = url + '/%s' % args.section
            else:
                sys.exit(0)
        if args.rep_command not in {'list', 'rename-section',
                                    'remove-section'}:
            if getattr(args, 'name') and (args.name not in settings):
                print "Invalid setting %s" % args.name
                print "Valid settings are " + " , ".join(settings)
                sys.exit(0)
            url = url + '/%s' % args.name
        else:
            sys.exit(0)
        if args.rep_command in {'add', 'replace-all', 'rename-section'}:
            if getattr(args, 'value'):
                data = {'value': args.value}
            else:
                sys.exit(0)

        if args.rep_command in {'unset-all', 'replace-all', 'remove-section'}:
            meth = requests.delete
        elif args.rep_command in {'add', 'rename-section'}:
            meth = requests.put
        elif args.rep_command in {'get-all', 'list'}:
            meth = requests.get
        resp = meth(url, headers=headers, data=json.dumps(data),
                    cookies=dict(auth_pubtkt=get_cookie(args)))
        if args.rep_command == 'replace-all':
            resp = requests.put(url, headers=headers, data=json.dumps(data),
                                cookies=dict(auth_pubtkt=get_cookie(args)))
            # These commands need json as output,
            # if server has no valid json it will send {}
            # for other commands print status
            if args.rep_command in {'get-all', 'list'}:
                print resp.json()
                return True

    elif args.command == 'trigger_replication':
        headers['Content-Type'] = 'application/json'
        url = '%s/replication' % base_url
        info = {}
        if args.wait:
            info['wait'] = 'true'
        else:
            info['wait'] = 'false'
        if getattr(args, 'url'):
            info['url'] = args.url
        if getattr(args, 'project'):
            info['project'] = args.project
        resp = requests.post(url, headers=headers, data=json.dumps(info),
                             cookies=dict(auth_pubtkt=get_cookie(args)))

    response(resp)


def user_management_action(args, base_url, headers):
    if args.command != 'user':
        return False
    if args.subcommand not in ['create', 'update', 'delete']:
        return False
    url = '%s/user/%s' % (base_url, args.username)
    if args.subcommand in ['create', 'update']:
        password = None
        if not getattr(args, 'password', False):
            password = getpass.getpass("Enter password: ")
        elif args.password is not True:
            password = args.password
        info = {}
        if getattr(args, 'email'):
            info['email'] = args.email
        if getattr(args, 'sshkey'):
            with open(args.sshkey, 'r') as f:
                info['sshkey'] = f.read()
        if getattr(args, 'fullname'):
            info['fullname'] = args.fullname
        if password:
            info['password'] = password
        resp = requests.post(url, headers=headers, data=json.dumps(info),
                             cookies=dict(auth_pubtkt=get_cookie(args)))
    if args.subcommand == 'delete':
        resp = requests.delete(url, headers=headers,
                               cookies=dict(auth_pubtkt=get_cookie(args)))
    response(resp)


def main():
    parser = argparse.ArgumentParser(description="Tool to manage software"
                                     " factory projects")
    default_arguments(parser)
    command_options(parser)
    args = parser.parse_args()
    base_url = "%s/manage" % args.url.rstrip('/')

    if args.auth_server_url is None:
        args.auth_server_url = args.url

    if ":" not in args.auth:
        password = getpass.getpass("%s's password: " % args.auth)
        args.auth = "%s:%s" % (args.auth, password)

    headers = {'Authorization': 'Basic ' + base64.b64encode(args.auth)}
    if not(project_user_action(args, base_url, headers) or
           project_action(args, base_url, headers) or
           backup_action(args, base_url, headers) or
           replication_action(args, base_url, headers) or
           user_management_action(args, base_url, headers)):
        print "ManageSF failed to execute your command"

if __name__ == '__main__':
    main()
