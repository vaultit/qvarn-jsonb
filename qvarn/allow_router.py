# Copyright (C) 2018  Lars Wirzenius
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


import qvarn


class AllowRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._store = None

    def set_store(self, store):
        self._store = store

    def get_routes(self):
        path = '/allow'
        return [
            {
                'method': 'POST',
                'path': path,
                'callback': self._add_rule,
            },
            {
                'method': 'GET',
                'path': path,
                'callback': self._has_rule,
            },
            {
                'method': 'DELETE',
                'path': path,
                'callback': self._remove_rule,
            },
        ]

    def _transaction(self):
        return self._store.transaction()

    def _add_rule(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        with self._transaction() as t:
            self._store.add_allow_rule(t, body)
        return qvarn.ok_response(None)

    def _has_rule(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        with self._transaction() as t:
            if self._store.has_allow_rule(t, body):
                return qvarn.ok_response(None)
        return qvarn.no_such_resource_response('')

    def _remove_rule(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        with self._transaction() as t:
            self._store.remove_allow_rule(t, body)
        return qvarn.ok_response(None)
