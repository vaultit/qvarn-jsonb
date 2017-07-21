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


class QvarnAPITests(unittest.TestCase):

    def test_returns_routes_for_version_path(self):
        api = qvarn.QvarnAPI()
        self.assertNotEqual(api.find_missing_route('/version'), [])

    def test_version_returns_sensible_data(self):
        api = qvarn.QvarnAPI()
        v = api.version(None, None)
        self.assertTrue(isinstance(v, dict))
        self.assertTrue('api' in v)
        self.assertTrue('version' in v['api'])
        self.assertTrue('implementation' in v)
        self.assertTrue('name' in v['implementation'])
        self.assertTrue('version' in v['implementation'])

    def test_returns_no_routes_for_unknown_resource_type(self):
        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)
        self.assertEqual(api.find_missing_route('/subjects'), [])

    def test_returns_routes_for_known_resource_type(self):
        spec = {
            'type': 'subject',
            'path': '/subjects',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'id': '',
                        'revision': '',
                        'name': '',
                    },
                },
            ],
        }

        rt = qvarn.ResourceType()
        rt.from_spec(spec)

        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)
        api.add_resource_type(rt)
        self.assertNotEqual(api.find_missing_route('/subjects'), [])

    def test_get_resource_type_raises_error_for_unknown_path(self):
        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)
        with self.assertRaises(qvarn.NoSuchResourceType):
            api.get_resource_type('/subjects')

    def test_get_resource_type_returns_it_when_it_is_known(self):
        spec = {
            'type': 'subject',
            'path': '/subjects',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'id': '',
                        'revision': '',
                        'name': '',
                    },
                },
            ],
        }

        rt = qvarn.ResourceType()
        rt.from_spec(spec)

        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)
        api.add_resource_type(rt)
        self.assertEqual(api.get_resource_type('/subjects'), rt)

    def test_get_resource_type_raises_error_adding_type_again(self):
        spec = {
            'type': 'subject',
            'path': '/subjects',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'id': '',
                        'revision': '',
                        'name': '',
                    },
                },
            ],
        }

        rt = qvarn.ResourceType()
        rt.from_spec(spec)

        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)
        api.add_resource_type(rt)
        with self.assertRaises(qvarn.ResourceTypeAlreadyExists):
            api.add_resource_type(rt)
