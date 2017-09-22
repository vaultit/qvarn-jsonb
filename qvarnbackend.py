#!/usr/bin/python3
# Copyright (C) 2017  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# This is a Qvarn backend program that serves all the API requests. It is based on
# apifw, which takes care of routing, logging, and authorization.


import logging
import os
import sys

import yaml

import apifw
import qvarn
import slog


DEFAULT_CONFIG_FILE = '/dev/null'


def dict_logger(log, stack_info=None):
    qvarn.log.log(exc_info=stack_info, **log)


def read_config(config_filename):
    with open(config_filename) as f:
        return yaml.safe_load(f)


def check_config(config):
    for key in config:
        if config[key] is None:
            raise Exception('Configration %s should not be None' % key)


_counter = slog.Counter()
def counter():
    new_context = 'HTTP transaction {}'.format(_counter.increment())
    qvarn.log.set_context(new_context)


default_config = {
    'baseurl': 'https://unconfigured-base-url/',
    'log': None,
    'token-public-key': None,
    'token-audience': None,
    'token-issuer': None,
    'log': [],
    'resource-type-dir': None,
    'memory-database': True,
    'database': {
        'host': None,
        'port': 5432,
        'database': None,
        'user': None,
        'min_conn': 1,
        'max_conn': 1,
        'password': None,
    },
}


actual_config = read_config(os.environ.get('QVARN_CONFIG', DEFAULT_CONFIG_FILE))
config = dict(default_config)
config.update(actual_config or {})
check_config(config)
qvarn.setup_logging(config)
qvarn.log.log('info', msg_text='Qvarn backend starting')

subject = qvarn.ResourceType()
subject.from_spec({
    'type': 'subject',
    'path': '/subjects',
    'versions': [
        {
            'version': 'v0',
            'prototype': {
                'id': '',
                'type': '',
                'revision': '',
                'random_id': '',
                'names': [
                    {
                        'full_name': '',
                        'sort_key': '',
                        'titles': [''],
                        'given_names': [''],
                        'surnames': [''],
                    },
                ],
            },
            'subpaths': {
                'sub': {
                    'prototype': {
                        'subfield': '',
                    },
                },
            },
        },
    ],
})

resource_types = qvarn.load_resource_types(config['resource-type-dir'])

if config['memory-database']:
    store = qvarn.MemoryObjectStore()
else:
    sql = qvarn.PostgresAdapter()
    sql.connect(**config['database'])
    store = qvarn.PostgresObjectStore(sql)

api = qvarn.QvarnAPI()
api.set_base_url(config['baseurl'])
api.set_object_store(store)
api.add_resource_type(subject)
for rt in resource_types:
    api.add_resource_type(rt)


app = apifw.create_bottle_application(api, counter, dict_logger, config)

# If we are running this program directly with Python, and not via
# gunicorn, we can use the Bottle built-in debug server, which can
# make some things easier to debug.

if __name__ == '__main__':
    print('running in debug mode')
    app.run(host='127.0.0.1', port=12765)
