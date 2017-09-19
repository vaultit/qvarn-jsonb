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

        for operator, args in pairs:
            if operator == 'show_all':
                sp.set_show_all()
            elif operator == 'show':
                for field in args:
                    sp.add_show_field(field)
            elif operator == 'sort':
                for field in args:
                    sp.add_sort_key(field)
            else:
                klass = self.conditions[operator][1]
                cond = klass(*args)
                sp.add_cond(cond)

        return sp

    def _parse_simple(self, path):
        # Yield operator, args pairs.
        words = path.split('/')
        assert len(words) > 0
        while words:
            operator, words = words[0], words[1:]
            if operator not in self.conditions:
                raise SearchParserError(
                    'Unknown condition {}'.format(operator))

            num_args = self.conditions[operator][0]
            if num_args > len(words):
                raise SearchParserError(
                    'Not enough args for {}'.format(operator))

            args, words = words[:num_args], words[num_args:]
            yield operator, args


class SearchParserError(Exception):

    def __init__(self, msg):
        super().__init__(self, msg)


class SearchParameters:

    def __init__(self):
        self.sort_keys = []
        self.show_fields = []
        self.show_all = False
        self.cond = None
        self.offset = None
        self.limit = None

    def set_offset(self, offset):
        if self.offset is not None:
            raise SearchParserError('/offset may only be used once')
        self.offset = offset

    def set_limit(self, limit):
        if self.limit is not None:
            raise SearchParserError('/limit may only be used once')
        self.limit = limit

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

    def add_cond(self, cond):
        if self.cond is None:
            self.cond = cond
        elif isinstance(self.cond, qvarn.All):
            self.cond.append_subcondition(cond)
        else:
            self.cond = qvarn.All(self.cond, cond)
