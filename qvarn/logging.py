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


import slog


# We are probably run under gunicorn, which sets up logging via the
# logging library. Hijack that so actual logging happens via the slog
# library. For this, we need to know the logger names gunicorn uses.
gunicorn_loggers = ['gunicorn.access', 'gunicorn.error']


# This sets up a global log variable that doesn't actually log
# anything anywhere. This is useful so that code can unconditionally
# call log.log(...) from anywhere. See setup_logging() for setting up
# actual logging to somewhere persistent.

log = slog.StructuredLog()
log.add_log_writer(slog.NullSlogWriter(), slog.FilterAllow())
slog.hijack_logging(log, logger_names=gunicorn_loggers)


def setup_logging(config):
    for target in config.get('log', []):
        setup_logging_to_target(target)


def setup_logging_to_target(target):
    rule = get_filter_rules(target)
    if 'filename' in target:
        setup_logging_to_file(target, rule)
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
