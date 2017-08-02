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
import sys


import qvarn


class SchemaTests(unittest.TestCase):

    def test_generates_schema_for_simple_resource_type(self):
        resource_type = {
            'type': '',
        }
        self.assertEqual(
            qvarn.schema(resource_type),
            [
                (['type'], str),
            ]
        )

    def test_generates_schema_with_simple_list(self):
        resource_type = {
            'type': '',
            'foos': [''],
        }
        self.assertEqual(
            qvarn.schema(resource_type),
            [
                (['foos'], list, str),
                (['type'], str),
            ]
        )

    def test_generates_schema_with_dict_list(self):
        resource_type = {
            'type': '',
            'foos': [
                {
                    'yos': '',
                    'bars': [''],
                },
            ],
        }
        self.assertEqual(
            qvarn.schema(resource_type),
            [
                (['foos'], list, dict),
                (['foos', 'bars'], list, str),
                (['foos', 'yos'], str),
                (['type'], str),
            ]
        )

    def test_generates_schema_from_deep_resource_type(self):
        N = sys.getrecursionlimit() + 1
        resource_type = {
            'foos': '',
        }
        for _ in range(N):
            resource_type = {
                'foos': [resource_type],
            }
        self.assertTrue(isinstance(qvarn.schema(resource_type), list))
