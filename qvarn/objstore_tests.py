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
        return store.find_objects(qvarn.All())

    def sorted_dicts(self, dicts):
        return sorted(dicts, key=lambda d: sorted(d.items()))
    
    def test_is_initially_empty(self):
        store = self.create_store(key=str)
        self.assertEqual(self.get_all_objects(store), [])

    def test_adds_object(self):
        store = self.create_store(key=str)
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
        self.assertEqual(objs, [self.obj1])

    def test_finds_ids_of_objects(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.create_object(self.obj2, key='2nd')

        cond = qvarn.Equal('name', self.obj1['name'])
        ids = store.find_object_ids(cond)
        self.assertEqual(ids, [{'key': '1st'}])

    def test_finds_ids_of_multipl_objects(self):
        store = self.create_store(key=str)
        store.create_object(self.obj1, key='1st')
        store.create_object(self.obj2, key='2nd')

        ids = store.find_object_ids(qvarn.All())
        self.assertEqual(
            self.sorted_dicts(ids),
            self.sorted_dicts([{'key': '1st'}, {'key': '2nd'}])
        )
