#!/usr/bin/python3
#
# setup.py - standard Python build-and-package program
#
# Copyright 2017 Vincent Sanders <vince@qvarnlabs.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import importlib.machinery

from setuptools import setup

version = (
    importlib.machinery.
    SourceFileLoader('version', 'qvarn/version.py').
    load_module()
)

setup(
    name='qvarn-jsonb',
    version=version.__version__,
    description='backend service for JSON and binary data storage',
    author='Lars Wirzenius',
    author_email='liw@qvarnlabs.com',
    packages=['qvarn', 'qvarnutils'],
    scripts=[
        'qvarn-access',
        'qvarn-copy',
        'qvarn-dump',
        'qvarn-stats',
    ],
    install_requires=[
        'apifw',
        'bottle',
        'cliapp',
        'cryptography',
        'gunicorn',
        'psycopg2',
        'pycryptodome',
        'pyjwt',
        'pyyaml',
        'requests',
        'slog',
        'ttystatus',
    ],
)
