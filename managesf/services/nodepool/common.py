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


import re


def get_values(line):
    return [u.strip() for u in line.split('|') if u.strip() != '']


def get_age(age):
    days, hours, minutes, sec = age.split(':')
    return (((int(days) * 24) + int(hours))*60 + int(minutes))*60 + int(sec)


def validate_input(input):
    INPUT_FORMAT = re.compile("^[a-zA-Z0-9_-]+$", re.U)
    return INPUT_FORMAT.match(input)
