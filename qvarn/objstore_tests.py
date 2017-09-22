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

    def create_store(self, **keys):
        store = qvarn.MemoryObjectStore()
        store.create_store(**keys)
        return store

    def get_all_objects(self, store):
        return [obj for _, obj in store.find_objects(qvarn.Yes())]

    def sorted_dicts(self, dicts):
        return sorted(dicts, key=lambda d: sorted(d.items()))

    def test_is_initially_empty(self):
        store = self.create_store(key=str)
        self.assertEqual(self.get_all_objects(store), [])

    def test_refurses_nonstr_keys(self):
        with self.assertRaises(qvarn.WrongKeyType):
            self.create_store(key=int)

    def test_adds_object(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj1])

    def test_adds_object_with_binary_data(self):
        store = self.create_store(key=str)
        self.obj1['data'] = bytes(range(0, 256))
        store.create_object(self.obj1, key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj1])

    def test_raises_error_for_surprising_keys(self):
        store = self.create_store(key=str)
        with self.assertRaises(qvarn.UnknownKey):
            store.create_object(self.obj1, surprise='1st')

    def test_raises_error_adding_object_with_existing_keys(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        with self.assertRaises(qvarn.KeyCollision):
            store.create_object(self.obj1, key='1st')

    def test_raises_error_adding_object_with_keys_of_wrong_type(self):
        store = self.create_store(key=str)
        with self.assertRaises(qvarn.KeyValueError):
            store.create_object(self.obj1, key=1)

    def test_adds_objects_with_two_keys_with_one_key_the_same(self):
        store = self.create_store(key1=str, key2=str)
        store.create_object(self.obj1, key1='same', key2='1st')
        store.create_object(self.obj2, key1='same', key2='2nd')
        self.assertEqual(self.get_all_objects(store), [self.obj1, self.obj2])

    def test_removes_only_object(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.remove_objects(key='1st')
        self.assertEqual(self.get_all_objects(store), [])

    def test_gets_objects(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.create_object(self.obj2, key='2nd')
        self.assertEqual(store.get_objects(key='1st'), [self.obj1])
        self.assertEqual(store.get_objects(key='2nd'), [self.obj2])

    def test_gets_objects_using_only_one_key(self):
        store = self.create_store(key1=str, key2=str)
        store.create_object(self.obj1, key1='1st', key2='foo')
        store.create_object(self.obj2, key1='2nd', key2='foo')
        self.assertEqual(store.get_objects(key1='1st'), [self.obj1])
        self.assertEqual(store.get_objects(key1='2nd'), [self.obj2])
        self.assertEqual(
            self.sorted_dicts(store.get_objects(key2='foo')),
            self.sorted_dicts([self.obj1, self.obj2]))

    def test_removes_only_one_object(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.create_object(self.obj2, key='2nd')
        store.remove_objects(key='1st')
        self.assertEqual(self.get_all_objects(store), [self.obj2])

    def test_finds_objects(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.create_object(self.obj2, key='2nd')

        cond = qvarn.Equal('name', self.obj1['name'])
        objs = store.find_objects(cond)
        self.assertEqual(
            objs,
            [({'key': '1st'}, self.obj1)]
        )


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
        store.create_store(**keys)
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
        store.create_object(obj1, **keys1)
        store.create_object(obj2, **keys2)

        cond = qvarn.Equal('bar', 'yo')
        objs = store.find_objects(cond)
        self.assertEqual(objs, [(keys1, obj1)])
