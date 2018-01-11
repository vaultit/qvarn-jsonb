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


class AllConditionTests(unittest.TestCase):

    def test_returns_true_without_subconditions(self):
        self.assertTrue(qvarn.All().matches(None))

    def test_returns_false_without_false_subcondition(self):
        cond = qvarn.All(qvarn.No())
        self.assertFalse(cond.matches(None))

    def test_returns_appended_subcondition(self):
        cond = qvarn.All()
        yes = qvarn.Yes()
        cond.append_subcondition(yes)
        self.assertEqual(cond.get_subconditions(), [yes])

    def test_returns_true_with_true_subconditions(self):
        cond = qvarn.All()
        yes = qvarn.Yes()
        cond.append_subcondition(yes)
        self.assertTrue(cond.matches(None))


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
        self.assertEqual(qvarn.ResourceTypeIs('foo').matches(restype), True)
