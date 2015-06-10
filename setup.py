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
# -*- coding: utf-8 -*-
try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

try:
    import multiprocessing  # noqa
except:
    pass


VERSION = '0.3.0'


setup(
    name='managesf',
    version=VERSION,
    description=('A python client/server used to centralize management '
                 'of services deployed under Software Factory'),
    author='Software Factory',
    author_email='softwarefactory@enovance.com',
    test_suite='managesf',
    zip_safe=False,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup']),
    entry_points={
        "console_scripts": ['sfmanager = managesf.cli:main']
        },
    url='http://softwarefactory.enovance.com/r/gitweb?p=managesf.git;a=summary',
    download_url='https://github.com/enovance/managesf/tarball/%s' % VERSION,
    keywords=['software factory', 'CI', 'continuous integration'],
)
