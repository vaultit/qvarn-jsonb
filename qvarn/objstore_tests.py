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


class ObjectStoreTests(unittest.TestCase):

    def setUp(self):
        self.obj1 = {
            'name': 'this is my object',
        }
        self.obj2 = {
            'name': 'this is my other object',
        }
        self.blob1 = 'my first blob'
        self.blob2 = 'my other blob'

    def create_store(self, **keys):
        store = qvarn.MemoryObjectStore()
        with store.transaction() as t:
            store.create_store(t, **keys)
        return store

    def get_all_objects(self, store):
        with store.transaction() as t:
            return [obj for _, obj in store.get_matches(t, qvarn.Yes())]

    def sorted_dicts(self, dicts):
        return sorted(dicts, key=lambda d: sorted(d.items()))

    def sorted_matches(self, matches):
        return sorted(matches, key=lambda match: sorted(match[0].items()))

    def test_is_initially_empty(self):
        store = self.create_store(key=str)
        self.assertEqual(self.get_all_objects(store), [])

    def test_refurses_nonstr_keys(self):
        with self.assertRaises(qvarn.WrongKeyType):
            self.create_store(key=int)

    def test_adds_object(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj1])

    def test_adds_object_with_binary_data(self):
        store = self.create_store(key=str)
        self.obj1['data'] = bytes(range(0, 256))
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj1])

    def test_raises_error_for_surprising_keys(self):
        store = self.create_store(key=str)
        with self.assertRaises(qvarn.UnknownKey):
            with store.transaction() as t:
                store.create_object(t, self.obj1, surprise='1st')

    def test_raises_error_adding_object_with_existing_keys(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            with self.assertRaises(qvarn.KeyCollision):
                store.create_object(t, self.obj1, key='1st')

    def test_raises_error_adding_object_with_keys_of_wrong_type(self):
        store = self.create_store(key=str)
        with self.assertRaises(qvarn.KeyValueError):
            with store.transaction() as t:
                store.create_object(t, self.obj1, key=1)

    def test_adds_objects_with_two_keys_with_one_key_the_same(self):
        store = self.create_store(key1=str, key2=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key1='same', key2='1st')
            store.create_object(t, self.obj2, key1='same', key2='2nd')
        self.assertEqual(self.get_all_objects(store), [self.obj1, self.obj2])

    def test_removes_only_object(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.remove_objects(t, key='1st')
        self.assertEqual(self.get_all_objects(store), [])

    def test_gets_objects(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_object(t, self.obj2, key='2nd')
            self.assertEqual(
                store.get_matches(t, key='1st'),
                [
                    ({'key': '1st'}, self.obj1)
                ]
            )
            self.assertEqual(
                store.get_matches(t, key='2nd'),
                [
                    ({'key': '2nd'}, self.obj2)
                ]
            )

    def test_gets_objects_using_only_one_key(self):
        keys1 = {
            'key1': '1st',
            'key2': 'foo',
        }
        keys2 = {
            'key1': '2nd',
            'key2': 'foo',
        }

        match1 = (keys1, self.obj1)
        match2 = (keys2, self.obj2)

        store = self.create_store(key1=str, key2=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, **keys1)
            store.create_object(t, self.obj2, **keys2)
            self.assertEqual(store.get_matches(t, key1='1st'), [match1])
            self.assertEqual(store.get_matches(t, key1='2nd'), [match2])

            matches = store.get_matches(t, key2='foo')
            expected = [match1, match2]
            self.assertEqual(
                self.sorted_matches(matches),
                self.sorted_matches(expected)
            )

    def test_removes_only_one_object(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_object(t, self.obj2, key='2nd')
            store.remove_objects(t, key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj2])

    def test_finds_objects(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_object(t, self.obj2, key='2nd')

            cond = qvarn.Equal('name', self.obj1['name'])
            objs = store.get_matches(t, cond)
            self.assertEqual(
                objs,
                [({'key': '1st'}, self.obj1)]
            )

    def test_has_no_blob_initially(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            with self.assertRaises(qvarn.NoSuchObject):
                store.get_blob(t, key='1st', subpath='blob')

    def test_add_blob_to_nonexistent_parent_fails(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
        with self.assertRaises(qvarn.NoSuchObject):
            with store.transaction() as t:
                store.create_blob(t, self.blob1, key='2nd', subpath='blob')

    def test_adds_blob(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_blob(t, self.blob1, key='1st', subpath='blob')
            blob = store.get_blob(t, key='1st', subpath='blob')
        self.assertEqual(blob, self.blob1)

    def test_add_blob_twice_fails(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_blob(t, self.blob1, key='1st', subpath='blob')
            with self.assertRaises(qvarn.BlobKeyCollision):
                store.create_blob(t, self.blob1, key='1st', subpath='blob')

    def test_removes_blob(self):
        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, self.obj1, key='1st')
            store.create_blob(t, self.blob1, key='1st', subpath='blob')
            store.remove_blob(t, key='1st', subpath='blob')
            with self.assertRaises(qvarn.NoSuchObject):
                store.get_blob(t, key='1st', subpath='blob')


class FlattenObjectsTests(unittest.TestCase):

    def test_flattens_simple_dict(self):
        obj = {
            'foo': 'bar',
            'foobar': 42,
            'yo': True,
        }
        self.assertEqual(
            qvarn.flatten_object(obj),
            sorted([('foo', 'bar'), ('foobar', 42), ('yo', True)]))

    def test_flattens_deep_dict(self):
        obj = {
            'foo': 'bar',
            'foos': [
                {
                    'foo': 'bar2',
                    'foos': [
                        {
                            'foo': 'bar3',
                        },
                    ],
                },
            ],
        }
        self.assertEqual(
            qvarn.flatten_object(obj),
            sorted([
                ('foo', 'bar'),
                ('foo', 'bar2'),
                ('foo', 'bar3'),
            ]))


class FindObjectsTests(unittest.TestCase):

    def setUp(self):
        pass

    def create_store(self, **keys):
        store = qvarn.MemoryObjectStore()
        with store.transaction() as t:
            store.create_store(t, **keys)
        return store

    def test_finds_objects_matching_deeply_in_object(self):
        obj1 = {
            'foo': 'foo-1',
            'bar': 'blah',
            'bars': [
                {
                    'foo': 'bars.0',
                    'bar': 'yo',
                },
                {
                    'foo': 'bars.1',
                    'bar': 'bleurgh',
                },
            ],
        }

        obj2 = {
            'foo': 'foo-2',
            'bar': 'bother',
            'bars': [],
        }

        keys1 = {
            'key': '1st',
        }

        keys2 = {
            'key': '2nd',
        }

        store = self.create_store(key=str)
        with store.transaction() as t:
            store.create_object(t, obj1, **keys1)
            store.create_object(t, obj2, **keys2)

            cond = qvarn.Equal('bar', 'yo')
            objs = store.get_matches(t, cond)
            self.assertEqual(objs, [(keys1, obj1)])


class AllowRuleTests(unittest.TestCase):

    rule = {
        'client_id': 'test-client',
        'method': 'GET',
        'subpath': '',
        'user_id': 'test-user',
        'id': '123',
        'resource_type': 'person',
        'resource_field': None,
        'resource_value': None,
    }

    def create_store(self, **keys):
        store = qvarn.MemoryObjectStore()
        with store.transaction() as t:
            store.create_store(t, **keys)
        return store

    def test_has_no_rules_initially(self):
        store = self.create_store(obj_id=str)
        self.assertEqual(store.get_allow_rules(), [])

    def test_fine_grained_access_control_is_disabled_initially(self):
        store = self.create_store(obj_id=str)
        self.assertFalse(store.have_fine_grained_access_control())

    def test_fine_grained_access_control_can_be_enabled(self):
        store = self.create_store(obj_id=str)
        store.enable_fine_grained_access_control()
        self.assertTrue(store.have_fine_grained_access_control())

    def test_doesnt_have_allow_rule_initially(self):
        store = self.create_store(obj_id=str)
        with store.transaction() as t:
            self.assertFalse(store.has_allow_rule(t, self.rule))

    def test_adds_allow_rule(self):
        store = self.create_store(obj_id=str)
        with store.transaction() as t:
            store.add_allow_rule(t, self.rule)
            self.assertTrue(store.has_allow_rule(t, self.rule))

    def test_removes_allow_rule(self):
        store = self.create_store(obj_id=str)
        with store.transaction() as t:
            store.add_allow_rule(t, self.rule)
            store.remove_allow_rule(t, self.rule)
            self.assertFalse(store.has_allow_rule(t, self.rule))
