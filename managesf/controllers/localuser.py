#
# Copyright (c) 2015 Red Hat, Inc.
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

from pecan import conf
from pecan import request

from managesf import model
from basicauth import decode, DecodeError
from passlib.hash import pbkdf2_sha256


logger = logging.getLogger(__name__)


class AddUserForbidden(Exception):
    pass


class DeleteUserForbidden(Exception):
    pass


class UpdateUserForbidden(Exception):
    pass


class GetUserForbidden(Exception):
    pass


class UserNotFound(Exception):
    pass


class BadUserInfos(Exception):
    pass


class BindForbidden(Exception):
    pass


class InvalidInfosInput(Exception):
    pass


AUTHORIZED_KEYS = ('username',
                   'password',
                   'sshkey',
                   'email',
                   'fullname')


def verify_input(infos):
    for key in infos.keys():
        if key not in AUTHORIZED_KEYS:
            raise InvalidInfosInput()


def hash_password(infos):
    password = infos.get('password', None)
    if password is None:
        return
    del infos['password']
    hash = pbkdf2_sha256.encrypt(password,
                                 rounds=200,
                                 salt_size=16)
    infos['hashed_password'] = hash


def update_user(username, infos):
    if not model.get_user(username):
        if request.remote_user != conf.admin['name']:
            raise AddUserForbidden()
        infos['username'] = username
        verify_input(infos)
        hash_password(infos)
        ret = model.add_user(infos)
    else:
        if request.remote_user != conf.admin['name'] and \
                request.remote_user != username:
            raise UpdateUserForbidden()
        verify_input(infos)
        hash_password(infos)
        ret = model.update_user(username, infos)
    if not ret:
        raise BadUserInfos()
    else:
        return ret


def delete_user(username):
    if request.remote_user != conf.admin['name']:
        raise DeleteUserForbidden()
    ret = model.delete_user(username)
    if not ret:
        raise UserNotFound()
    return ret


def get_user(username):
    if request.remote_user != conf.admin['name'] and \
            request.remote_user != username:
        raise GetUserForbidden()
    ret = model.get_user(username)
    if not ret:
        raise UserNotFound()
    return ret


def bind_user(username, authorization):
    try:
        user, password = decode(authorization)
    except DecodeError:
        raise BindForbidden()
    if username != user:
        raise BindForbidden()
    ret = model.get_user(username)
    if not ret:
        raise UserNotFound()
    if pbkdf2_sha256.verify(password, ret['hashed_password']):
        return True
    else:
        raise BindForbidden()
