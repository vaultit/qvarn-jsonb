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


import unittest

import qvarn
from qvarn.sql import Transaction


class AllConditionTests(unittest.TestCase):

    def test_returns_true_without_subconditions(self):
        self.assertTrue(qvarn.All().matches(None, None))

    def test_returns_false_without_false_subcondition(self):
        cond = qvarn.All(qvarn.No())
        self.assertFalse(cond.matches(None, None))

    def test_returns_appended_subcondition(self):
        cond = qvarn.All()
        yes = qvarn.Yes()
        cond.append_subcondition(yes)
        self.assertEqual(cond.get_subconditions(), [yes])

    def test_returns_true_with_true_subconditions(self):
        cond = qvarn.All()
        yes = qvarn.Yes()
        cond.append_subcondition(yes)
        self.assertTrue(cond.matches(None, None))


class CmpTests(unittest.TestCase):

    def cmp_test(self, klass, pattern, actual, expected):
        obj = klass(None, pattern)
        self.assertEqual(obj.cmp_py(actual), expected)

    def test_equal(self):
        self.cmp_test(qvarn.Equal, 'foo', 'foo', True)
        self.cmp_test(qvarn.Equal, 'foo', 'bar', False)

    def test_not_equal(self):
        self.cmp_test(qvarn.NotEqual, 'foo', 'foo', False)
        self.cmp_test(qvarn.NotEqual, 'foo', 'bar', True)

    def test_greater_than(self):
        self.cmp_test(qvarn.GreaterThan, 'foo', 'bar', False)
        self.cmp_test(qvarn.GreaterThan, 'foo', 'foo', False)
        self.cmp_test(qvarn.GreaterThan, 'foo', 'yo', True)

        self.cmp_test(qvarn.GreaterThan, 1, 0, False)
        self.cmp_test(qvarn.GreaterThan, 1, 1, False)
        self.cmp_test(qvarn.GreaterThan, 1, 2, True)

    def test_greater_than_or_equal(self):
        self.cmp_test(qvarn.GreaterOrEqual, 'foo', 'bar', False)
        self.cmp_test(qvarn.GreaterOrEqual, 'foo', 'foo', True)
        self.cmp_test(qvarn.GreaterOrEqual, 'foo', 'yo', True)

        self.cmp_test(qvarn.GreaterOrEqual, 1, 0, False)
        self.cmp_test(qvarn.GreaterOrEqual, 1, 1, True)
        self.cmp_test(qvarn.GreaterOrEqual, 1, 2, True)

    def test_less_than(self):
        self.cmp_test(qvarn.LessThan, 'foo', 'bar', True)
        self.cmp_test(qvarn.LessThan, 'foo', 'foo', False)
        self.cmp_test(qvarn.LessThan, 'foo', 'yo', False)

        self.cmp_test(qvarn.LessThan, 1, 0, True)
        self.cmp_test(qvarn.LessThan, 1, 1, False)
        self.cmp_test(qvarn.LessThan, 1, 2, False)

    def test_less_than_or_equal(self):
        self.cmp_test(qvarn.LessOrEqual, 'foo', 'bar', True)
        self.cmp_test(qvarn.LessOrEqual, 'foo', 'foo', True)
        self.cmp_test(qvarn.LessOrEqual, 'foo', 'yo', False)

        self.cmp_test(qvarn.LessOrEqual, 1, 0, True)
        self.cmp_test(qvarn.LessOrEqual, 1, 1, True)
        self.cmp_test(qvarn.LessOrEqual, 1, 2, False)

    def test_contains(self):
        self.cmp_test(qvarn.Contains, 'o', 'foo', True)
        self.cmp_test(qvarn.Contains, 'foo', 'foo', True)
        self.cmp_test(qvarn.Contains, 'foo', 'bar', False)

    def test_starts_with(self):
        self.cmp_test(qvarn.Startswith, 'foo', 'o', False)
        self.cmp_test(qvarn.Startswith, 'foo', 'foo', True)
        self.cmp_test(qvarn.Startswith, 'foo', 'foobar', True)

    def test_resource_type_is(self):
        restype = {
            'type': 'foo',
        }
        self.assertTrue(qvarn.ResourceTypeIs('foo').matches(restype, None))


class DummySQL:

    class DummyConnection:
        def __init__(self, sql, fail_on_commit, fail_on_rollback):
            self.sql = sql
            self._fail_on_commit = fail_on_commit
            self._fail_on_rollback = fail_on_rollback

        def commit(self):
            self.sql.commits += 1
            if self._fail_on_commit:
                raise RuntimeError
            return True

        def rollback(self):
            self.sql.rollbacks += 1
            if self._fail_on_rollback:
                raise RuntimeError
            return True

    def __init__(self, fail_on_commit=False, fail_on_rollback=False):
        self._fail_on_commit = fail_on_commit
        self._fail_on_rollback = fail_on_rollback
        self.returned_conns = 0
        self.closed_conns = 0
        self.rollbacks = 0
        self.commits = 0

    def get_conn(self):
        return self.DummyConnection(self,
                                    self._fail_on_commit,
                                    self._fail_on_rollback)

    def put_conn(self, conn, close=False):
        self.returned_conns += 1
        if close:
            self.closed_conns += 1


class TransactionErrorHandlingTestCase(unittest.TestCase):

    def test_transaction_returns_conn_after_transaction(self):
        sql = DummySQL()
        with Transaction(sql):
            pass
        self.assertEqual(sql.returned_conns, 1)
        self.assertEqual(sql.closed_conns, 0)
        self.assertEqual(sql.commits, 1)
        self.assertEqual(sql.rollbacks, 0)

    def test_conn_closed_after_error_in_rollback(self):
        sql = DummySQL(fail_on_rollback=True)
        with self.assertRaises(RuntimeError):
            with Transaction(sql):
                raise ValueError
        self.assertEqual(sql.returned_conns, 1)
        self.assertEqual(sql.closed_conns, 1)
        self.assertEqual(sql.commits, 0)
        self.assertEqual(sql.rollbacks, 1)

    def test_conn_closed_after_error_in_commit(self):
        sql = DummySQL(fail_on_commit=True)
        with self.assertRaises(RuntimeError):
            with Transaction(sql):
                pass
        self.assertEqual(sql.returned_conns, 1)
        self.assertEqual(sql.closed_conns, 1)
        self.assertEqual(sql.commits, 1)
        self.assertEqual(sql.rollbacks, 0)

    def test_conn_intact_after_code_error(self):
        sql = DummySQL()
        with self.assertRaises(ValueError):
            with Transaction(sql):
                raise ValueError
        self.assertEqual(sql.returned_conns, 1)
        self.assertEqual(sql.closed_conns, 0)
        self.assertEqual(sql.commits, 0)
        self.assertEqual(sql.rollbacks, 1)
