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


DEFAULT_CONFIG_FILE = '/dev/null'


def dict_logger(log, stack_info=None):
    logging.info('Start log entry')
    for key in sorted(log.keys()):
        logging.info('  %r=%r', key, log[key])
    logging.info('Endlog entry')
    if stack_info:
        logging.info('Traceback', exc_info=True)



def setup_logging(config):
    filename = config.get('log')
    if filename:
        logging.basicConfig(filename=filename, level=logging.DEBUG)


def read_config(config_filename):
    with open(config_filename) as f:
        return yaml.safe_load(f)


def check_config(config):
    for key in config:
        if config[key] is None:
            raise Exception('Configration %s should not be None' % key)



default_config = {
    'log': None,
    'token-public-key': None,
    'token-audience': None,
    'token-issuer': None,
}


actual_config = read_config(os.environ.get('QVARN_CONFIG', DEFAULT_CONFIG_FILE))
config = dict(default_config)
config.update(actual_config)
check_config(config)

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
                'full_name': '',
            }
        }
    ],
})

store = qvarn.MemoryObjectStore()

api = qvarn.QvarnAPI()
api.set_object_store(store)
api.add_resource_type(subject)
app = apifw.create_bottle_application(api, dict_logger, config)

# If we are running this program directly with Python, and not via
# gunicorn, we can use the Bottle built-in debug server, which can
# make some things easier to debug.

if __name__ == '__main__':
    print('running in debug mode')
    app.run(host='127.0.0.1', port=12765)
