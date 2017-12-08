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


import time


import qvarn


class Stopwatch:

    def __init__(self, msg, **kwargs):
        self.started = None
        self.msg = msg
        self.kwargs = kwargs

    def __enter__(self):
        self.started = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            duration = time.time() - self.started
            qvarn.log.log(
                'stopwatch', msg_text=self.msg, ms=duration * 1000.0,
                **self.kwargs)


def stopwatch(callback, msg, **swkwargs):  # pragma: no cover
    def stopwatch_wrapper(content_type, body, *args, **kwargs):
        with qvarn.Stopwatch(msg, **swkwargs):
            return callback(content_type, body, *args, **kwargs)
    return stopwatch_wrapper
