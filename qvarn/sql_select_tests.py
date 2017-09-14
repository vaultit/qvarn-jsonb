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

    def test_returns_simple_query_for_simple_equal(self):
        cond = qvarn.Equal('foo', 'bar')
        counter = slog.Counter()
        sql, values = qvarn.sql_select(counter, cond)
        self.assertEqual(
            sql,
            ("SELECT obj_id FROM _aux WHERE "
             "_field->>'name' = %(name1)s AND _field->>'value' = %(value2)s")
        )
        self.assertEqual(
            values,
            {
                'name1': 'foo',
                'value2': 'bar',
            }
        )

    def test_returns_simple_query_for_simple_not_equal(self):
        cond = qvarn.NotEqual('foo', 'bar')
        counter = slog.Counter()
        sql, values = qvarn.sql_select(counter, cond)
        self.assertEqual(
            sql,
            ("SELECT obj_id FROM _aux WHERE "
             "_field->>'name' = %(name1)s AND _field->>'value' != %(value2)s")
        )
        self.assertEqual(
            values,
            {
                'name1': 'foo',
                'value2': 'bar',
            }
        )

    def test_returns_query_for_anded_conditions(self):
        cond1 = qvarn.Equal('foo1', 'bar1')
        cond2 = qvarn.NotEqual('foo2', 'bar2')
        cond = qvarn.All(cond1, cond2)
        counter = slog.Counter()
        sql, values = qvarn.sql_select(counter, cond)
        self.maxDiff = None
        self.assertEqual(
            sql,
            ("SELECT _temp.obj_id, _obj FROM _objects, ("
             "SELECT obj_id, count(obj_id) AS _hits FROM _aux WHERE "
             "(_field->>'name' = %(name1)s AND "
             "_field->>'value' = %(value2)s) OR "
             "(_field->>'name' = %(name3)s AND "
             "_field->>'value' != %(value4)s) "
             "GROUP BY obj_id) WHERE _hits = %(count)s")
        )
        self.assertEqual(
            values,
            {
                'name1': 'foo1',
                'value2': 'bar1',
                'name3': 'foo2',
                'value4': 'bar2',
                'count': 2,
            }
        )
