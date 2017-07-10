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


class Api(object):

    def find_missing_route(self, path):
        # Return list of dicts to describe "routes" that should be
        # added when client requests the missing path given as an
        # argument. The dicts should look like:
        #
        #       {
        #           "method": "GET",
        #           "path": "/foo/bar",
        #           "callback": foo_bar_db,
        #       }
        #
        # The "method" is the HTTP method, and defaults to "GET" if not given.
        # "path" is the path component of the URL being requested. It may use
        # Bottle.py patterns such as "/foo/<id>" for more powerful matching.
        # (Note that this means that if Bottle gets replaced, the patterns may
        # have to be reimplemented.)
        #
        # The list may be empty if no routes are to be added.

        return []
