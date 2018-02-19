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


import unittest

import slog

import qvarn


class SqlSelectTests(unittest.TestCase):

    def test_returns_query_for_simple_equal(self):
        cond = qvarn.Equal('foo', 'bar')
        counter = slog.Counter()
        all_cond = qvarn.All()
        query, values = qvarn.sql_select(counter, cond, all_cond, 'TRUE')
        self.assertTrue(isinstance(query, str))
        self.assertTrue(isinstance(values, dict))

    def test_returns_query_for_anded_conditions(self):
        cond1 = qvarn.Equal('foo1', 'bar1')
        cond2 = qvarn.NotEqual('foo2', 'bar2')
        cond = qvarn.All(cond1, cond2)
        counter = slog.Counter()
        all_cond = qvarn.All()
        query, values = qvarn.sql_select(counter, cond, all_cond, 'TRUE')
        self.assertTrue(isinstance(query, str))
        self.assertTrue(isinstance(values, dict))
