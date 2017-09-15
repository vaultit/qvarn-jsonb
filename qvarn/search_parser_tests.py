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


import qvarn


class SearchParserTests(unittest.TestCase):

    def test_raises_error_path_is_empty(self):
        p = qvarn.SearchParser()
        with self.assertRaises(qvarn.SearchParserError):
            p.parse('')

    def test_raises_error_if_condition_is_unknown(self):
        p = qvarn.SearchParser()
        with self.assertRaises(qvarn.SearchParserError):
            p.parse('unknown/foo/bar')

    def test_returns_exact_condition(self):
        p = qvarn.SearchParser()
        cond, show = p.parse('exact/foo/bar')
        self.assertTrue(isinstance(cond, qvarn.Equal))
        self.assertFalse(show)
        self.assertEqual(cond.name, 'foo')
        self.assertEqual(cond.pattern, 'bar')

    def test_raises_error_if_only_show_specified(self):
        p = qvarn.SearchParser()
        with self.assertRaises(qvarn.SearchParserError):
            p.parse('show')

    def test_raises_error_if_show_specified_but_without_operand(self):
        p = qvarn.SearchParser()
        with self.assertRaises(qvarn.SearchParserError):
            p.parse('exact/foo/bar/show')

    def test_returns_show_if_specified(self):
        p = qvarn.SearchParser()
        cond, show = p.parse('exact/foo/bar/show/foo')
        self.assertTrue(isinstance(cond, qvarn.Equal))
        self.assertEqual(show, ['foo'])
        self.assertEqual(cond.name, 'foo')
        self.assertEqual(cond.pattern, 'bar')

    def test_returns_show_all_if_specified(self):
        p = qvarn.SearchParser()
        cond, show = p.parse('exact/foo/bar/show_all')
        self.assertEqual(show, 'show_all')
        self.assertTrue(isinstance(cond, qvarn.Equal))
        self.assertEqual(cond.name, 'foo')
        self.assertEqual(cond.pattern, 'bar')

    def test_returns_all_condition(self):
        p = qvarn.SearchParser()
        cond, show = p.parse('exact/foo/bar/exact/foobar/yo')
        self.assertEqual(show, None)
        self.assertTrue(isinstance(cond, qvarn.All))
        self.assertEqual(len(cond.conds), 2)
        first, second = cond.conds
        self.assertTrue(isinstance(first, qvarn.Equal))
        self.assertEqual(first.name, 'foo')
        self.assertEqual(first.pattern, 'bar')
        self.assertTrue(isinstance(second, qvarn.Equal))
        self.assertEqual(second.name, 'foobar')
        self.assertEqual(second.pattern, 'yo')
