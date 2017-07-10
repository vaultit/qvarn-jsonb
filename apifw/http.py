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


class HttpTransaction(object):

    def __init__(self):
        self._logger = lambda log, **kwargs: None

    def construct_request_log(self):
        return {}

    def construct_response_log(self):
        return {}

    def amend_response(self):
        pass

    def set_dict_logger(self, logger):
        self._logger = logger

    def _log_request(self):
        log = {
            'msg_type': 'http-request',
        }
        self._logger(self._combine_dicts(log, self.construct_request_log()))

    def _log_response(self):
        log = {
            'msg_type': 'http-response',
        }
        self._logger(self._combine_dicts(log, self.construct_response_log()))


    def _log_error(self, exc):
        log = {
            'msg_type': 'error',
            'msg_text': str(exc),
        }
        self._logger(self._combine_dicts(log), stack_info=True)

    def _combine_dicts(self, *dicts):
        log = {}
        for d in dicts:
            log.update(d)
        return log

    def perform_transaction(self, callback, *args, **kwargs):
        try:
            self._log_request()
            data = callback(*args, **kwargs)
            self.amend_response()
            self._log_response()
            return data
        except SystemExit:
            raise
        except BaseException as e:
            self._log_error(e)
            raise
