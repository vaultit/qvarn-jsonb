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
        sp = p.parse('exact/foo/bar')
        self.assertEqual(sp.sort_keys, [])
        self.assertEqual(sp.show_fields, [])
        self.assertEqual(sp.show_all, False)
        self.assertTrue(isinstance(sp.cond, qvarn.Equal))
        self.assertEqual(sp.cond.name, 'foo')
        self.assertEqual(sp.cond.pattern, 'bar')

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
        sp = p.parse('exact/foo/bar/show/foo')
        self.assertEqual(sp.sort_keys, [])
        self.assertEqual(sp.show_fields, ['foo'])
        self.assertTrue(isinstance(sp.cond, qvarn.Equal))
        self.assertEqual(sp.cond.name, 'foo')
        self.assertEqual(sp.cond.pattern, 'bar')

    def test_returns_show_all_if_specified(self):
        p = qvarn.SearchParser()
        sp = p.parse('exact/foo/bar/show_all')
        self.assertEqual(sp.sort_keys, [])
        self.assertEqual(sp.show_all, True)
        self.assertTrue(isinstance(sp.cond, qvarn.Equal))
        self.assertEqual(sp.cond.name, 'foo')
        self.assertEqual(sp.cond.pattern, 'bar')

    def test_returns_all_condition(self):
        p = qvarn.SearchParser()
        sp = p.parse('exact/foo/bar/exact/foobar/yo')
        self.assertEqual(sp.sort_keys, [])
        self.assertEqual(sp.show_fields, [])
        self.assertTrue(isinstance(sp.cond, qvarn.All))
        self.assertEqual(len(sp.cond.conds), 2)
        first, second = sp.cond.conds
        self.assertTrue(isinstance(first, qvarn.Equal))
        self.assertEqual(first.name, 'foo')
        self.assertEqual(first.pattern, 'bar')
        self.assertTrue(isinstance(second, qvarn.Equal))
        self.assertEqual(second.name, 'foobar')
        self.assertEqual(second.pattern, 'yo')

    def test_returns_sort_keys(self):
        p = qvarn.SearchParser()
        sp = p.parse('exact/foo/bar/exact/foobar/yo/sort/a/sort/b')
        self.assertEqual(sp.sort_keys, ['a', 'b'])

    def test_returns_sort_keys_with_show_all(self):
        p = qvarn.SearchParser()
        sp = p.parse('show_all/exact/foo/bar/exact/foobar/yo/sort/a/sort/b')
        self.assertEqual(sp.sort_keys, ['a', 'b'])


class SearchParametersTest(unittest.TestCase):

    def test_has_correct_initial_state(self):
        sp = qvarn.SearchParameters()
        self.assertEqual(sp.sort_keys, [])
        self.assertEqual(sp.show_fields, [])
        self.assertEqual(sp.show_all, False)
        self.assertEqual(sp.cond, None)

    def test_sets_offset(self):
        sp = qvarn.SearchParameters()
        sp.set_offset(42)
        self.assertEqual(sp.offset, 42)

    def test_raises_error_if_setting_offset_a_second_time(self):
        sp = qvarn.SearchParameters()
        sp.set_offset(42)
        with self.assertRaises(qvarn.SearchParserError):
            sp.set_offset(42)

    def test_sets_limit(self):
        sp = qvarn.SearchParameters()
        sp.set_limit(42)
        self.assertEqual(sp.limit, 42)

    def test_raises_error_if_setting_limit_a_second_time(self):
        sp = qvarn.SearchParameters()
        sp.set_limit(42)
        with self.assertRaises(qvarn.SearchParserError):
            sp.set_limit(42)

    def test_adds_sort_key(self):
        sp = qvarn.SearchParameters()
        sp.add_sort_key('foo')
        self.assertEqual(sp.sort_keys, ['foo'])

    def test_adds_show_field(self):
        sp = qvarn.SearchParameters()
        sp.add_show_field('foo')
        self.assertEqual(sp.show_fields, ['foo'])

    def test_set_show_all(self):
        sp = qvarn.SearchParameters()
        sp.set_show_all()
        self.assertEqual(sp.show_all, True)

    def test_show_when_show_all_is_set_raises_error(self):
        sp = qvarn.SearchParameters()
        sp.set_show_all()
        with self.assertRaises(qvarn.SearchParserError):
            sp.add_show_field('foo')

    def test_setting_show_all_when_fields_are_set_raises_error(self):
        sp = qvarn.SearchParameters()
        sp.add_show_field('foo')
        with self.assertRaises(qvarn.SearchParserError):
            sp.set_show_all()

    def test_adds_cond(self):
        cond = qvarn.Yes()
        sp = qvarn.SearchParameters()
        self.assertEqual(sp.cond, None)
        sp.add_cond(cond)
        self.assertEqual(sp.cond, cond)
        sp.add_cond(cond)
        self.assertTrue(isinstance(sp.cond, qvarn.All))
        self.assertEqual(len(sp.cond.conds), 2)
        self.assertEqual(sp.cond.conds, [cond, cond])
        sp.add_cond(cond)
        self.assertTrue(isinstance(sp.cond, qvarn.All))
        self.assertEqual(len(sp.cond.conds), 3)
        self.assertEqual(sp.cond.conds, [cond, cond, cond])
