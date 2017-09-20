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


import itertools
import unittest

import qvarn


class CollectionAPITests(unittest.TestCase):

    def setUp(self):
        self.store = qvarn.MemoryObjectStore()

        spec = {
            'type': 'subject',
            'path': '/subjects',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'type': '',
                        'id': '',
                        'revision': '',
                        'full_name': '',
                        'names': [
                            {
                                'sort_key': '',
                            },
                        ],
                        'things': [
                            {
                                'things': '',
                                'other': '',
                            },
                        ],
                    },
                },
            ],
        }
        self.rt = qvarn.ResourceType()
        self.rt.from_spec(spec)

        self.coll = qvarn.CollectionAPI()
        self.coll.set_object_store(self.store)
        self.coll.set_resource_type(self.rt)

    def test_returns_specified_type(self):
        self.assertEqual(self.coll.get_type(), self.rt)

    def test_returns_specified_type_name(self):
        self.assertEqual(self.coll.get_type_name(), self.rt.get_type())

    def test_post_raises_error_if_type_not_given(self):
        obj = {
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.NoType):
            self.coll.post(obj)

    def test_post_raises_error_if_type_is_not_expected_one(self):
        obj = {
            'type': 'unperson',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.WrongType):
            self.coll.post(obj)

    def test_post_raises_error_if_id_given(self):
        obj = {
            'id': 'object-1',
            'type': 'subject',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.HasId):
            self.coll.post(obj)

    def test_post_raises_error_if_revision_given(self):
        obj = {
            'revision': 'rev-1',
            'type': 'subject',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.HasRevision):
            self.coll.post(obj)

    def test_post_creates_a_new_resource(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        self.assertTrue(new_obj['id'])
        self.assertTrue(new_obj['revision'])
        self.assertEqual(new_obj['things'], [])
        self.assertEqual(new_obj, self.coll.get(new_obj['id']))

    def test_post_creates_a_new_resource_with_dict_list(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
            'things': [
                {
                    'other': 'foo',
                },
            ],
        }
        new_obj = self.coll.post(obj)
        self.assertTrue(new_obj['id'])
        self.assertTrue(new_obj['revision'])
        self.assertEqual(
            new_obj['things'],
            [
                {
                    'things': '',
                    'other': 'foo',
                },
            ]
        )
        self.assertEqual(new_obj, self.coll.get(new_obj['id']))

    def test_post_creates_a_new_id_revision_every_time(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj1 = self.coll.post(obj)
        new_obj2 = self.coll.post(obj)
        self.assertNotEqual(new_obj1, new_obj2)

    def test_get_raise_error_if_not_found(self):
        with self.assertRaises(qvarn.NoSuchResource):
            self.coll.get('no-such-object-id')

    def test_deleting_nonexisent_resource_raise_error(self):
        with self.assertRaises(qvarn.NoSuchResource):
            self.coll.delete('no-such-object-id')

    def test_deleting_resource_makes_it_go_away(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        self.coll.delete(new_obj['id'])
        with self.assertRaises(qvarn.NoSuchResource):
            self.coll.get(new_obj['id'])

    def test_listing_objects_returns_empty_list_initially(self):
        self.assertEqual(self.coll.list(), {'resources': []})

    def test_listing_objects_returns_list_of_existing_object(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)

        # Add an object of a different type so that we can make sure
        # only objects of the right type are returned.
        wrong_type = {
            'type': 'unperson',
            'full_name': 'James Bond',
        }
        self.store.create_object(wrong_type, obj_id='007')

        self.assertEqual(
            self.coll.list(),
            {
                'resources': [
                    {
                        'id': new_obj['id']
                    }
                ]
            }
        )

    def test_putting_resource_without_id_raises_error(self):
        obj = {
            'revision': 'revision-1',
            'type': 'subject',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.NoId):
            self.coll.put(obj)

    def test_putting_resource_without_type_raises_error(self):
        obj = {
            'id': 'object-id-1',
            'revision': 'revision-1',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.NoType):
            self.coll.put(obj)

    def test_putting_resource_with_wrong_type_raises_error(self):
        obj = {
            'id': 'object-id-1',
            'type': 'notasubject',
            'revision': 'revision-1',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.WrongType):
            self.coll.put(obj)

    def test_putting_resource_without_revision_raises_error(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        del new_obj['revision']
        with self.assertRaises(qvarn.NoRevision):
            self.coll.put(new_obj)

    def test_putting_resource_with_wrong_revision_raises_error(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        obj2 = dict(new_obj)
        obj2['revision'] = 'this-revision-never-happens-randomly'
        with self.assertRaises(qvarn.WrongRevision):
            self.coll.put(obj2)

    def test_putting_nonexistent_resource_raises_error(self):
        obj = {
            'id': 'object-id-1',
            'revision': 'revision-1',
            'type': 'subject',
            'full_name': 'James Bond',
        }
        with self.assertRaises(qvarn.NoSuchResource):
            self.coll.put(obj)

    def test_putting_resource_updates_resource(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        obj2 = dict(new_obj)
        obj2['full_name'] = 'Alfred Newman'
        newer_obj = self.coll.put(obj2)
        self.assertNotEqual(new_obj['revision'], newer_obj['revision'])
        self.assertEqual(self.revisionless(obj2), self.revisionless(newer_obj))

    def revisionless(self, obj):
        return {
            key: value
            for key, value in obj.items()
            if key != 'revision'
        }

    def test_search_with_empty_criteria_raises_error(self):
        with self.assertRaises(qvarn.NoSearchCriteria):
            self.coll.search('')

    def test_search_without_matches_returns_empty_list(self):
        self.assertEqual(self.coll.search('exact/foo/nomatch'), [])

    def test_search_return_matching_resource_ids(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        matches = self.coll.search('exact/full_name/James Bond')
        self.assertEqual(matches, [{'id': new_obj['id']}])

    def test_search_return_matching_resources_themselves(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        wanted = {
            'id': new_obj['id'],
            'full_name': new_obj['full_name'],
        }
        matches = self.coll.search('exact/full_name/James Bond/show/full_name')
        self.assertEqual(matches, [wanted])

    def test_search_return_full_resources(self):
        obj = {
            'type': 'subject',
            'full_name': 'James Bond',
        }
        new_obj = self.coll.post(obj)
        matches = self.coll.search('exact/full_name/James Bond/show_all')
        self.assertEqual(matches, [new_obj])

    def test_search_sorts(self):
        names = ['Alfred Pennyweather', 'James Bond', 'Jason Bourne']
        for perm in itertools.permutations(names):
            self.setUp()
            for name in perm:
                obj = {
                    'type': 'subject',
                    'full_name': 'Spy',
                    'names': [
                        {
                            'sort_key': name,
                        },
                    ],
                }
                self.coll.post(obj)

            matches = self.coll.search(
                'exact/full_name/Spy/show_all/sort/sort_key')
            self.assertEqual(len(matches), 3)
            self.assertEqual(
                [m['names'][0]['sort_key'] for m in matches],
                names)

    def test_limit_without_sort(self):
        with self.assertRaises(qvarn.SearchParserError):
            self.coll.search('/limit/1')

    def test_offset_without_sort(self):
        with self.assertRaises(qvarn.SearchParserError):
            self.coll.search('/offset/1')

    def test_search_with_limit_only(self):
        objs = self.create_objects(['1', '2', '3'])
        search = 'sort/full_name/show_all'
        matches = self.coll.search(search + '/limit/2')
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches, objs[:2])

    def test_search_with_offset_only(self):
        objs = self.create_objects(['1', '2', '3'])
        search = 'sort/full_name/show_all'
        matches = self.coll.search(search + '/offset/2')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, objs[2:])

    def test_search_with_offset_and_limit(self):
        objs = self.create_objects(['1', '2', '3'])
        search = 'sort/full_name/show_all'
        matches = self.coll.search(search + '/offset/1/limit/1')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches, objs[1:2])

    def create_objects(self, names):
        objs = []
        for name in names:
            obj = {
                'type': 'subject',
                'full_name': name,
            }
            new_obj = self.coll.post(obj)
            objs.append(new_obj)
        return objs
