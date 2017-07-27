# slog.py - structured logging
#
# Copyright 2016-2017  QvarnLabs Ab
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


import datetime
import json
import logging
import os
import time
import traceback
import _thread
import syslog

import slog


class StructuredLog:

    '''A structured logging system.

    A structured log is one that can be easily parsed
    programmatically. Traditional logs are free form text, usually
    with a weakly enforced line structure and some minimal metadata
    prepended to each file. This class produces JSON records instead.

    See the separate manual for more background and examples of how to
    use this system.

    '''

    def __init__(self):
        self._msg_counter = slog.Counter()
        self._context = {}
        self._writers = []

    def close(self):
        for writer, _ in self._writers:
            writer.close()
        self._writers = []

    def add_log_writer(self, writer, filter_rule):
        self._writers.append((writer, filter_rule))

    def set_context(self, new_context):
        thread_id = self._get_thread_id()
        self._context[thread_id] = new_context

    def reset_context(self):
        thread_id = self._get_thread_id()
        self._context[thread_id] = None

    def log(self, msg_type, **kwargs):
        exc_info = kwargs.pop('exc_info', False)

        log_obj = {
            'msg_type': msg_type,
        }
        for key, value in kwargs.items():
            log_obj[key] = self._convert_value(value)

        self._add_extra_fields(log_obj, exc_info)
        for writer, filter_rule in self._writers:
            if filter_rule.allow(log_obj):
                writer.write(log_obj)

    def _convert_value(self, value):
        # Convert a value into an form that's safe to write. Meaning,
        # it can't be binary data, and it is UTF-8 compatible, if it's
        # a string of any sort.
        #
        # Note that we do not need to be able to parse the value back
        # again, we just need to write it to a log file in a form that
        # the user will understand. At least for now.
        #
        # We can't do this while encoding JSON, because the Python
        # JSON library doesn't seem to allow us to override how
        # encoding happens for types it already knows about, only for
        # other types of values.

        converters = {
            int: self._nop_conversion,
            float: self._nop_conversion,
            bool: self._nop_conversion,
            str: self._nop_conversion,
            type(None): self._nop_conversion,

            list: self._convert_list_value,
            dict: self._convert_dict_value,
            tuple: self._convert_tuple_value,
        }

        value_type = type(value)
        assert value_type in converters, \
            'Unknown data type {}'.format(value_type)
        func = converters[type(value)]
        converted = func(value)
        return converted

    def _nop_conversion(self, value):
        return value

    def _convert_list_value(self, value):
        return [self._convert_value(item) for item in value]

    def _convert_tuple_value(self, value):
        return tuple(self._convert_value(item) for item in value)

    def _convert_dict_value(self, value):
        return {
            self._convert_value(key): self._convert_value(value[key])
            for key in value
        }

    def _add_extra_fields(self, log_obj, stack_info):
        log_obj['_msg_number'] = self._get_next_message_number()
        log_obj['_timestamp'] = self._get_current_timestamp()
        log_obj['_process_id'] = self._get_process_id()
        log_obj['_thread_id'] = self._get_thread_id()
        log_obj['_context'] = self._context.get(self._get_thread_id())
        if stack_info:
            log_obj['_traceback'] = self._get_traceback()

    def _get_next_message_number(self):
        return self._msg_counter.increment()

    def _get_current_timestamp(self):
        return datetime.datetime.utcnow().isoformat(' ')

    def _get_process_id(self):
        return os.getpid()

    def _get_thread_id(self):
        return _thread.get_ident()

    def _get_traceback(self):
        return traceback.format_exc()


class SlogWriter:  # pragma: no cover

    def write(self, log_obj):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()


class NullSlogWriter(SlogWriter):  # pragma: no cover

    def write(self, log_obj):
        pass

    def close(self):
        pass


class FileSlogWriter(SlogWriter):

    def __init__(self):
        self._log_filename = None
        self._log_file = None
        self._bytes_max = None
        self._encoder = json.JSONEncoder(sort_keys=True)

    def set_max_file_size(self, bytes_max):
        self._bytes_max = bytes_max

    def get_filename(self):
        return self._log_filename

    def get_rotated_filename(self, now=None):
        prefix, suffix = os.path.splitext(self._log_filename)
        if now is None:  # pragma: no cover
            now = time.localtime()
        else:
            now = tuple(list(now) + [0]*9)[:9]
        timestamp = time.strftime('%Y%m%dT%H%M%S', now)
        return '{}-{}{}'.format(prefix, timestamp, suffix)

    def set_filename(self, filename):
        self._log_filename = filename
        self._log_file = open(filename, 'a')

    def write(self, log_obj):
        if self._log_file:
            self._write_message(log_obj)
            if self._bytes_max is not None:
                self._rotate()

    def _write_message(self, log_obj):
        msg = self._encoder.encode(log_obj)
        self._log_file.write(msg + '\n')
        self._log_file.flush()

    def _rotate(self):
        pos = self._log_file.tell()
        if pos >= self._bytes_max:
            self._log_file.close()
            rotated = self.get_rotated_filename()
            os.rename(self._log_filename, rotated)
            self.set_filename(self._log_filename)

    def close(self):
        self._log_file.close()
        self._log_file = None


class SyslogSlogWriter(SlogWriter):  # pragma: no cover

    def write(self, log_obj):
        encoder = json.JSONEncoder(sort_keys=True)
        s = encoder.encode(log_obj)
        syslog.syslog(s)

    def close(self):
        pass


class SlogHandler(logging.Handler):  # pragma: no cover

    '''A handler for the logging library to capture into a slog.

    In order to capture all logging.* log messages into a structured
    log, configure the logging library to use this handler.

    '''

    def __init__(self, log):
        super(SlogHandler, self).__init__()
        self.log = log

    def emit(self, record):
        attr_names = {
            'msg': 'msg_text',
        }

        log_args = dict()
        for attr in dir(record):
            if not attr.startswith('_'):
                value = getattr(record, attr)
                if not isinstance(value, (str, int, bool, float)):
                    value = repr(value)
                log_args[attr_names.get(attr, attr)] = value
        self.log.log('logging.' + record.levelname, **log_args)


def hijack_logging(log, logger_names=None):  # pragma: no cover
    '''Hijack log messages that come via logging.* into a slog.'''

    handler = SlogHandler(log)

    for name in logger_names or []:
        logger = logging.getLogger(name)
        hijack_logger_handlers(logger, handler)

    logger = logging.getLogger()
    hijack_logger_handlers(logger, handler)


def hijack_logger_handlers(logger, handler):  # pragma: no cover
    logger.setLevel(logging.DEBUG)
    for h in logger.handlers:
        logger.removeHandler(h)
    logger.addHandler(handler)
