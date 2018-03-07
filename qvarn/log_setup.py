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

import json

import slog
import slog.slog


def drop_get_message(log_obj):
    # These are useless and annoying in gunicorn log messages.
    if 'getMessage' in log_obj:
        del log_obj['getMessage']
    return log_obj


# We are probably run under gunicorn, which sets up logging via the
# logging library. Hijack that so actual logging happens via the slog
# library. For this, we need to know the logger names gunicorn uses.
gunicorn_loggers = ['gunicorn.access', 'gunicorn.error']


def setup_logging(config):
    for target in config.get('log', []):
        setup_logging_to_target(target)


def setup_logging_to_target(target):
    rule = get_filter_rules(target)
    if 'filename' in target:
        setup_logging_to_file(target, rule)
    elif 'syslog' in target:
        setup_logging_to_syslog(target, rule)
    elif 'stdout' in target:
        setup_logging_to_stdout(target, rule)
    else:
        raise Exception('Do not understand logging target %r' % target)


def get_filter_rules(target):
    if 'filter' in target:
        return slog.construct_log_filter(target['filter'])
    return slog.FilterAllow()


def setup_logging_to_file(target, rule):
    writer = slog.FileSlogWriter()
    writer.set_filename(target['filename'])
    if 'max_bytes' in target:
        writer.set_max_file_size(target['max_bytes'])
    log.add_log_writer(writer, rule)


def setup_logging_to_syslog(target, rule):
    writer = slog.SyslogSlogWriter()
    log.add_log_writer(writer, rule)


class StdoutSlogWriter(slog.slog.SlogWriter):  # pragma: no cover

    def __init__(self, pretty=False):
        self._pretty = pretty

    def write(self, log_obj):
        if self._pretty:
            print(json.dumps(log_obj, sort_keys=True, indent=4), flush=True)
        else:
            print(json.dumps(log_obj, sort_keys=True), flush=True)

    def close(self):
        pass


def setup_logging_to_stdout(target, rule):
    writer = StdoutSlogWriter(target.get('pretty', False))
    log.add_log_writer(writer, rule)


# This sets up a global log variable that doesn't actually log
# anything anywhere. This is useful so that code can unconditionally
# call log.log(...) from anywhere. See setup_logging() for setting up
# actual logging to somewhere persistent.

log = slog.StructuredLog()
log.add_log_writer(StdoutSlogWriter(), slog.FilterAllow())
log.add_log_massager(drop_get_message)
slog.hijack_logging(log, logger_names=gunicorn_loggers)
