#!/usr/bin/python3

import logging
import os

import yaml

import apifw


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

api = Api()
app = apifw.create_bottle_application(api, dict_logger)

if __name__ == '__main__':
    print('running in debug mode')
    app.run(host='127.0.0.1', port=12765)
