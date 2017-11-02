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


import copy
import os
import unittest


import qvarn


class QvarnAPITests(unittest.TestCase):

    def test_returns_routes_for_version_path(self):
        api = qvarn.QvarnAPI()
        self.assertNotEqual(api.find_missing_route('/version'), [])

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
                    'subpaths': {
                        'sub': {
                            'prototype': {
                                'subfoo': '',
                            },
                        },
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
        api.set_base_url('https://qvarn.example.com')

        dirname = os.path.dirname(qvarn.__file__)
        dirname = os.path.join(dirname, '../resource_type')
        resource_types = qvarn.load_resource_types(dirname)
        for rt in resource_types:
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
        rt2 = api.get_resource_type(spec['path'])
        self.assertTrue(isinstance(rt2, qvarn.ResourceType))
        self.assertEqual(rt2.as_dict(), spec)

    def test_add_resource_type_is_ok_adding_type_again(self):
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
        self.assertEqual(api.add_resource_type(rt), None)

    def test_updating_resource_type_with_new_version_works(self):
        spec1 = {
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

        spec2 = copy.deepcopy(spec1)
        spec2['versions'].append({
            'version': 'v1',
            'prototype': {
                'id': '',
                'revision': '',
                'name': '',
                'newfield': '',
            },
        })

        store = qvarn.MemoryObjectStore()
        api = qvarn.QvarnAPI()
        api.set_object_store(store)

        rt1 = qvarn.ResourceType()
        rt1.from_spec(spec1)
        api.add_resource_type(rt1)

        rt2 = qvarn.ResourceType()
        rt2.from_spec(spec2)
        api.add_resource_type(rt2)

        rt = api.get_resource_type(spec1['path'])
        self.assertEqual(rt.as_dict(), spec2)
