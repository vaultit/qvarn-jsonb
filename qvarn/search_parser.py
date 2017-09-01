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


import qvarn


class SearchParser:

    conditions = {
        'contains': (2, qvarn.Contains),
        'exact': (2, qvarn.Equal),
    }

    def parse(self, path):
        if not path:
            raise SearchParserError('No condition given')
        conds = list(self._parse_simple(path))
        if len(conds) == 1:
            return conds[0]
        return qvarn.All(*conds)

    def _parse_simple(self, path):
        words = path.split('/')
        assert len(words) > 0
        while words:
            len_before = len(words)
            if words[0] not in self.conditions:
                raise SearchParserError(
                    'Unknown condition {}'.format(words[0]))
            num, klass = self.conditions[words[0]]
            yield klass(*words[1:1+num])
            del words[:1+num]
            assert len_before == len(words) + num + 1
            assert len(words) < len_before


class SearchParserError(Exception):

    def __init__(self, msg):
        super().__init__(self, msg)
