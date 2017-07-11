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

    # This class executes HTTP transactions. It is called by the web
    # framework, by some method that we don't specify. See the
    # BottleLoggingPlugin to use Bottle. This class is independent
    # from Bottle. The entry point is the "perform_tranaction" method,
    # which is tgiven the callback to call for the HTTP request that
    # has been made. This class makes the call, but also logs the
    # request and response, and catches and logs any excpetion.
    # Actually, the request and response get logged by a sub-class of
    # this class, which is supposed to define the
    # "construct_request_log" and "construct_response_log" methods.
    #
    # Log messages, as used by this class, are dicts, with no
    # particular specified keys, although "msg_type" is added by this
    # class. The request and response methods are supposed to return
    # dicts that get merged with what this class provides. The merged
    # result is then actually logged.

    def __init__(self):
        self._logger = lambda log, **kwargs: None

    def construct_request_log(self):
        # Override in subclass, as necessary.
        return {}

    def construct_response_log(self):
        # Override in subclass, as necessary.
        return {}

    def amend_response(self):
        # Make any necessary changes to the response.
        # Override in subclass, as necessary.
        pass

    def set_dict_logger(self, logger):
        # Set function to actually do logging.
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
            # If we're exiting, we exit. No need to log an error.
            raise
        except BaseException as e:
            # Everything else results in an error logged.
            self._log_error(e)
            raise
