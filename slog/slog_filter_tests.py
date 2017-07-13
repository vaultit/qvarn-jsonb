# slog_filter_tests.py - unit tests for structured logging tests
#
# Copyright 2017  QvarnLabs Ab
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
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


class FilterHasFieldTests(unittest.TestCase):

    def test_allows_if_field_is_there(self):
        log_obj = {
            'foo': False,
        }
        rule = slog.FilterHasField('foo')
        self.assertTrue(rule.allow(log_obj))

    def test_doesnt_allow_if_field_is_not_there(self):
        log_obj = {
            'foo': False,
        }
        rule = slog.FilterHasField('bar')
        self.assertFalse(rule.allow(log_obj))


class FilterFieldHasValueTests(unittest.TestCase):

    def test_allows_when_field_has_wanted_value(self):
        log_obj = {
            'foo': 'bar',
        }
        rule = slog.FilterFieldHasValue('foo', 'bar')
        self.assertTrue(rule.allow(log_obj))

    def test_doesnt_allow_when_field_has_unwanted_value(self):
        log_obj = {
            'foo': 'bar',
        }
        rule = slog.FilterFieldHasValue('foo', 'yo')
        self.assertFalse(rule.allow(log_obj))


class FilterFieldValueRegexpTests(unittest.TestCase):

    def test_allows_when_value_matches_regexp(self):
        log_obj = {
            'foo': 'bar',
        }
        rule = slog.FilterFieldValueRegexp('foo', 'b.r')
        self.assertTrue(rule.allow(log_obj))

    def test_allows_when_value_matches_regexp_if_stringified(self):
        log_obj = {
            'foo': 400,
        }
        rule = slog.FilterFieldValueRegexp('foo', '4.*')
        self.assertTrue(rule.allow(log_obj))

    def test_doesnt_allow_when_field_isnt_there(self):
        log_obj = {
            'blarf': 'yo',
        }
        rule = slog.FilterFieldValueRegexp('foo', 'b.r')
        self.assertFalse(rule.allow(log_obj))

    def test_doesnt_allow_when_value_doesnt_match_regexp(self):
        log_obj = {
            'foo': 'yo',
        }
        rule = slog.FilterFieldValueRegexp('foo', 'b.r')
        self.assertFalse(rule.allow(log_obj))


class FilterAllowTests(unittest.TestCase):

    def test_allows_always(self):
        rule = slog.FilterAllow()
        self.assertTrue(rule.allow(None))


class FilterDenyTests(unittest.TestCase):

    def test_allows_denies(self):
        rule = slog.FilterDeny()
        self.assertFalse(rule.allow(None))


class FilterIncludeTests(unittest.TestCase):

    def test_allows_if_rule_allows_and_no_include(self):
        allow = slog.FilterAllow()
        include = slog.FilterInclude({}, allow)
        self.assertTrue(include.allow(None))

    def test_denies_if_rule_denies_and_no_include(self):
        deny = slog.FilterDeny()
        include = slog.FilterInclude({}, deny)
        self.assertFalse(include.allow(None))

    def test_allows_if_rule_allows_and_include_is_true(self):
        allow = slog.FilterAllow()
        include = slog.FilterInclude({'include': True}, allow)
        self.assertTrue(include.allow({}))

    def test_denies_if_rule_denies_and_include_is_true(self):
        deny = slog.FilterDeny()
        include = slog.FilterInclude({'include': True}, deny)
        self.assertFalse(include.allow({}))

    def test_denies_if_rule_allows_and_include_is_false(self):
        allow = slog.FilterAllow()
        include = slog.FilterInclude({'include': False}, allow)
        self.assertFalse(include.allow({}))

    def test_allows_if_rule_denies_and_include_is_false(self):
        deny = slog.FilterDeny()
        include = slog.FilterInclude({'include': False}, deny)
        self.assertTrue(include.allow({}))


class FilterAnyTests(unittest.TestCase):

    def test_allows_if_any_rule_allows(self):
        rules = [slog.FilterAllow()]
        any_rule = slog.FilterAny(rules)
        self.assertTrue(any_rule.allow(None))

    def test_denies_if_all_rules_deny(self):
        rules = [slog.FilterDeny(), slog.FilterAllow()]
        any_rule = slog.FilterAny(rules)
        self.assertTrue(any_rule.allow(None))


class ConstructFilterTests(unittest.TestCase):

    def test_raises_error_if_no_filters(self):
        filters = []
        with self.assertRaises(Exception):
            slog.construct_log_filter(filters)

    def test_handles_field_wanted(self):
        filters = [
            {
                'field': 'msg_type',
            },
        ]

        rule = slog.construct_log_filter(filters)

        allowed = {
            'msg_type': 'info',
        }
        self.assertTrue(rule.allow(allowed))

        denied = {
            'blah_blah': 'http-response',
        }
        self.assertFalse(rule.allow(denied))

    def test_handles_field_value_wanted(self):
        filters = [
            {
                'field': 'msg_type',
                'value': 'info',
            },
        ]

        rule = slog.construct_log_filter(filters)

        allowed = {
            'msg_type': 'info',
        }
        self.assertTrue(rule.allow(allowed))

        denied = {
            'msg_type': 'http-response',
        }
        self.assertFalse(rule.allow(denied))

    def test_handles_regexp_match_wanted(self):
        filters = [
            {
                'field': 'status',
                'regexp': '^4'
            },
        ]

        rule = slog.construct_log_filter(filters)

        allowed = {
            'status': 400,
        }
        self.assertTrue(rule.allow(allowed))

        denied = {
            'status': 200,
        }
        self.assertFalse(rule.allow(denied))

    def test_handles_not_included(self):
        filters = [
            {
                'field': 'status',
                'value': '400',
                'include': False,
            },
        ]

        rule = slog.construct_log_filter(filters)

        allowed = {
            'status': '200',
        }
        self.assertTrue(rule.allow(allowed))

        denied = {
            'status': '400',
        }
        self.assertFalse(rule.allow(denied))

    def test_returns_compound_filter(self):
        filters = [
            {
                'field': 'msg_type',
            },
            {
                'field': 'msg_type',
                'value': 'debug',
            },
            {
                'field': 'status',
                'regexp': '^4',
                'include': False,
            },
        ]

        rule = slog.construct_log_filter(filters)

        allowed = {
            'msg_type': 'info',
        }
        self.assertTrue(rule.allow(allowed))

        also_allowed = {
            'msg_type': 'debug',
        }
        self.assertTrue(rule.allow(also_allowed))

        denied = {
            'status': '400',
        }
        self.assertFalse(rule.allow(denied))
