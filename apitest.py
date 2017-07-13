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

# This is a test application for apifw, used by the apifw.yarn test
# suite. It also acts as an example of how apifw can be used.

import logging
import os

import yaml

import apifw


# apifw requires a class to define routes on demand. This interface is provided
# by the apifw.Api class. This interface consists of a single method
# find_missing_route. In addition callback methods for particular routes
# may also be present.

class Api(apifw.Api):

    def find_missing_route(self, path):
        logging.info('find_missing_route called!\n')
        return [
            {
                'path': '/version',
                'callback': self.version,
            },
        ]

    def version(self):
        logging.info('/version called!\n')
        return 'version: 4.2'


# We want logging. gunicorn provides logging, but only of its own
# stuff, and if we log something ourselves, using logging.debug and
# its sibling functions, they don't end up in the log file defined by
# gunicorn.
#
# Instead a separate logger is defined. The logging in
# apifw.HttpTransaction are based on logging *dicts*, with arbitrary
# key/value pairs. This is because Lars liked log files that are easy
# to process programmatically. To use this, we define a "dict logger"
# function, which we tell apifw to use; by default, there is no
# logging. We also configure the Python logging library to write a log
# file; the name of the log file will be gotten from the APITEST_LOG
# environment variable.
#
# Ideally, we would parse command line arguments and a configuration
# file here, instead of using environment variables. Unfortunately,
# gunicorn wants to hog all of the command line for itself.
#
# It has been concluded that the sensible way is for a web app to no
# have command line options and to read configuration file from a
# fixed location, or have the name of the configuration file given
# using an environment variable.
#
# See also <https://stackoverflow.com/questions/8495367/>.

def dict_logger(log, stack_info=None):
    logging.info('Start log entry')
    for key in sorted(log.keys()):
        logging.info('  %r=%r', key, log[key])
    logging.info('Endlog entry')
    if stack_info:
        logging.info('Traceback', exc_info=True)


logfile = os.environ.get('APITEST_LOG')
if logfile:
    logging.basicConfig(filename=logfile, level=logging.DEBUG)



# Here is some configuaration for the framework.
#
# To validate the access tokens we'll be using in the API, we need to
# tell apifw which public key to use. We get that from an environment
# variable. It should be in OpenSSH public key format.
#
# The framework also needs to know the "audience" for which a token is
# created. We get that from the environment as well.

config = {
    'token-public-key': os.environ['APITEST_PUBKEY'],
    'token-audience': os.environ['APITEST_AUD'],
    'token-issuer': os.environ['APITEST_ISS'],
}


# Here is the magic part. We create an instance of our Api class, and
# create a new Bottle application, using the
# apifw.create_bottle_application function. We assign the Bottle app
# to the variable "app", and when we start this program using
# gunicorn, we tell it to use the "app" variable.
#
#    gunicorn3 --bind 127.0.0.1:12765 apitest:app
#
# gunicorn and Bottle then collaborate, using mysterious, unclear, and
# undocumented magic to run a web service. We don't know, and
# hopefully don't need to care, how the magic works.

api = Api()
app = apifw.create_bottle_application(api, dict_logger, config)

# If we are running this program directly with Python, and not via
# gunicorn, we can use the Bottle built-in debug server, which can
# make some things easier to debug.

if __name__ == '__main__':
    print('running in debug mode')
    app.run(host='127.0.0.1', port=12765)
