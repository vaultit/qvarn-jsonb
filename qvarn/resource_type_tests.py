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


class ResourceTypeTests(unittest.TestCase):

    def test_initially_has_no_type(self):
        rt = qvarn.ResourceType()
        self.assertEqual(rt.get_type(), None)

    def test_sets_type(self):
        rt = qvarn.ResourceType()
        rt.set_type('subject')
        self.assertEqual(rt.get_type(), 'subject')

    def test_initially_has_no_path(self):
        rt = qvarn.ResourceType()
        self.assertEqual(rt.get_path(), None)

    def test_sets_path(self):
        rt = qvarn.ResourceType()
        rt.set_path('/subjects')
        self.assertEqual(rt.get_path(), '/subjects')

    def test_initially_has_no_latest_version(self):
        rt = qvarn.ResourceType()
        self.assertEqual(rt.get_latest_version(), None)

    def test_load_resource_spec(self):
        spec = {
            'type': 'subject',
            'path': '/subjects',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'foo': '',
                    },
                },
                {
                    'version': 'v1',
                    'prototype': {
                        'foo': '',
                        'bar': '',
                    },
                },
            ],
        }
        rt = qvarn.ResourceType()
        rt.from_spec(spec)
        self.assertEqual(rt.get_type(), spec['type'])
        self.assertEqual(rt.get_path(), spec['path'])
        self.assertEqual(
            rt.get_latest_version(), spec['versions'][-1]['version'])
        self.assertEqual(
            rt.get_latest_prototype(), spec['versions'][-1]['prototype'])
        self.assertEqual(rt.as_dict(), spec)
