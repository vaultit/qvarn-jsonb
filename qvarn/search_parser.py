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
        'ge': (2, qvarn.GreaterOrEqual),
        'gt': (2, qvarn.GreaterThan),
        'le': (2, qvarn.LessOrEqual),
        'lt': (2, qvarn.LessThan),
        'ne': (2, qvarn.NotEqual),
        'startswith': (2, qvarn.Startswith),
        'show': (1, 'show'),
        'show_all': (0, 'show_all'),
        'sort': (1, 'sort'),
    }

    def parse(self, path):
        if not path:
            raise SearchParserError('No condition given')

        sp = qvarn.SearchParameters()

        pairs = list(self._parse_simple(path))
        conds = [cond for cond, _ in pairs if cond is not None]

        show_what = []
        for thing, fields in pairs:
            if thing == 'sort':
                for field in fields:
                    sp.add_sort_key(field)
            if fields == 'show_all':
                sp.set_show_all()
            elif fields and isinstance(show_what, list):
                for field in fields:
                    sp.add_show_field(field)

        if len(conds) == 1:
            sp.set_cond(conds[0])
        else:
            sp.set_cond(qvarn.All(*conds))

        return sp

    def _parse_simple(self, path):
        words = path.split('/')
        assert len(words) > 0
        while words:
            len_before = len(words)
            if words[0] not in self.conditions:
                raise SearchParserError(
                    'Unknown condition {}'.format(words[0]))
            num, klass = self.conditions[words[0]]
            if num > len(words) - 1:
                raise SearchParserError(
                    'Not enough args for {}'.format(words[0]))
            args = words[1:1+num]
            if klass == 'sort':
                yield 'sort', args
            elif klass == 'show':
                yield None, args
            elif klass == 'show_all':
                yield None, klass
            else:
                yield klass(*args), None
            del words[:1+num]
            assert len_before == len(words) + num + 1
            assert len(words) < len_before


class SearchParserError(Exception):

    def __init__(self, msg):
        super().__init__(self, msg)


class SearchParameters:

    def __init__(self):
        self.sort_keys = []
        self.show_fields = []
        self.show_all = False
        self.cond = None

    def add_sort_key(self, field_name):
        self.sort_keys.append(field_name)

    def add_show_field(self, field_name):
        if self.show_all:
            raise SearchParserError('/show_all and /show conflict')
        self.show_fields.append(field_name)

    def set_show_all(self):
        if self.show_fields:
            raise SearchParserError('/show_all and /show conflict')
        self.show_all = True

    def set_cond(self, cond):
        self.cond = cond
