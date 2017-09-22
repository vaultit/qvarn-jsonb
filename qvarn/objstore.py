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


import json


import qvarn


class ObjectStoreInterface:  # pragma: no cover

    '''Store and retrieve JSON-like objects.

    A JSON-like object is a Python dict whose keys are strings, and
    values corresponding to they keys can serialised into JSON, so
    they're strings, integers, booleans, or JSON-like objects, or
    lists of such values. JSON would support more types, but Qvarn
    doesn't need them. Value strings (but not key names) may be
    Unicode text or binary strings.

    The object store stores the JSON-like object, and a set of keys
    that identify the object. The caller gets to define the keys. The
    keys must be strings. There can be any number of keys, but there
    must be at least one. The caller gets to define the keys and their
    meaning. The allowed keys (and their types) are set when the store
    is created, using the create_store method.

    Objects may be retrieved or removed using any subset of keys. All
    maching objects are retrieved or removed.

    Objects mey be found using conditions, implemented by subclasses
    of the qvarn.Condition class. Various condidions may be combined
    arbitrarily.

    This class is for defining the ObjectStore interface. There is an
    in-memory variant, for use in unit tests, and a version using
    PostgreSQL for production use.

    '''

    def create_store(self, **keys):
        raise NotImplementedError()

    def check_keys_have_str_type(self, **keys):
        for key in keys:
            if keys[key] != str:
                raise WrongKeyType(key, keys[key])

    def get_known_keys(self):
        raise NotImplementedError()

    def check_all_keys_are_allowed(self, **keys):
        known_keys = self.get_known_keys()
        for key in keys:
            if key not in known_keys:
                raise UnknownKey(key)

    def create_object(self, obj, auxtable=True, **keys):
        raise NotImplementedError()

    def remove_objects(self, **keys):
        raise NotImplementedError()

    def get_objects(self, **keys):
        raise NotImplementedError()

    def find_objects(self, cond):
        raise NotImplementedError()


class MemoryObjectStore(ObjectStoreInterface):

    def __init__(self):
        self._objs = []
        self._known_keys = {}

    def get_known_keys(self):
        return self._known_keys

    def create_store(self, **keys):
        self.check_keys_have_str_type(**keys)
        qvarn.log.log(
            'trace', msg_text='Creating store', keys=repr(keys), exc_info=True)
        self._known_keys = keys

    def create_object(self, obj, auxtable=True, **keys):
        self.check_all_keys_are_allowed(**keys)
        qvarn.log.log(
            'trace', msg_text='Creating object', object=repr(obj), keys=keys)
        for key in keys:
            if type(keys[key]) is not self._known_keys[key]:
                raise KeyValueError(key, keys[key])

        for _, k in self._objs:
            if self._keys_match(k, keys):
                raise KeyCollision(k)
        self._objs.append((obj, keys))

    def remove_objects(self, **keys):
        self.check_all_keys_are_allowed(**keys)
        self._objs = [
            (o, k) for o, k in self._objs if not self._keys_match(k, keys)]

    def get_objects(self, **keys):
        self.check_all_keys_are_allowed(**keys)
        return [o for o, k in self._objs if self._keys_match(k, keys)]

    def _keys_match(self, got_keys, wanted_keys):
        for key in wanted_keys.keys():
            if got_keys.get(key) != wanted_keys[key]:
                return False
        return True

    def find_objects(self, cond):
        return [(keys, obj) for obj, keys in self._objs if cond.matches(obj)]


class PostgresObjectStore(ObjectStoreInterface):  # pragma: no cover

    _table = '_objects'
    _auxtable = '_aux'
    _strtable = '_strings'
    _inttable = '_ints'
    _booltable = '_bools'

    def __init__(self, sql):
        self._sql = sql
        self._keys = None

    def get_known_keys(self):
        return self._keys

    def create_store(self, **keys):
        self.check_keys_have_str_type(**keys)
        self._keys = dict(keys)
        qvarn.log.log(
            'info', msg_text='PostgresObjectStore.create_store',
            keys=repr(keys))

        # Create main table for objects.
        self._create_table(self._table, self._keys, '_obj', dict)

        # Create helper tables for fields at all depths.
        self._create_table(self._auxtable, self._keys, '_field', dict)

    def _create_table(self, name, col_dict, col_name, col_type):
        columns = dict(col_dict)
        columns[col_name] = col_type
        with self._sql.transaction() as t:
            query = t.create_table(name, **columns)
            t.execute(query, {})

    def create_object(self, obj, auxtable=True, **keys):
        qvarn.log.log(
            'info', msg_text='PostgresObjectStore.create_object',
            obj=obj, keys=keys)
        with self._sql.transaction() as t:
            self._remove_objects_in_transaction(t, **keys)
            self._insert_into_object_table(t, self._table, obj, **keys)
            if auxtable:
                self._insert_into_helper(t, self._auxtable, obj, **keys)

    def _insert_into_object_table(self, t, table_name, obj, **keys):
        keys['_obj'] = json.dumps(obj)
        column_names = list(keys.keys())
        query = t.insert_object(table_name, *column_names)
        t.execute(query, keys)

    def _insert_into_helper(self, t, table_name, obj, **keys):
        type_name = obj.get('type', '')
        for field, value in flatten_object(obj):
            x = {
                'type': type_name,
                'name': field,
                'value': value,
            }
            keys['_field'] = json.dumps(x)
            column_names = list(keys.keys())
            query = t.insert_object(table_name, *column_names)
            t.execute(query, keys)

    def remove_objects(self, **keys):
        qvarn.log.log(
            'info', msg_text='PostgresObjectStore.remove_objects',
            keys=keys)
        with self._sql.transaction() as t:
            query = t.remove_objects(self._table, *keys.keys())
            t.execute(query, keys)

            query = t.remove_objects(self._auxtable, *keys.keys())
            t.execute(query, keys)

    def _remove_objects_in_transaction(self, t, **keys):
        qvarn.log.log(
            'info',
            msg_text='PostgresObjectStore._remove_objects_in_transaction',
            keys=keys)
        query = t.remove_objects(self._table, *keys.keys())
        t.execute(query, keys)
        query = t.remove_objects(self._auxtable, *keys.keys())
        t.execute(query, keys)

    def get_objects(self, **keys):
        qvarn.log.log(
            'info', msg_text='PostgresObjectStore.get_objects',
            keys=keys)
        with self._sql.transaction() as t:
            return self._get_objects_in_transaction(t, **keys)

    def _get_objects_in_transaction(self, t, **keys):
        query = t.select_objects(self._table, '_obj', *keys.keys())
        qvarn.log.log(
            'debug', msg_text='PostgresObjectStore.get_objects',
            query=query, keys=keys)
        cursor = t.execute(query, keys)
        return [row['_obj'] for row in t.get_rows(cursor)]

    def find_objects(self, cond):
        qvarn.log.log(
            'info', msg_text='PostgresObjectStore.find_objects',
            cond=repr(cond))
        with self._sql.transaction() as t:
            rows = self._find_helper(t, cond)
            return [
                self._split_row(row)
                for row in rows
                if row['subpath'] == ''
            ]

    def _find_helper(self, t, cond):
        keys_columns = [key for key in self._keys if key != '_obj']
        query, values = t.select_objects_on_cond(
            self._auxtable, cond, *keys_columns)
        cursor = t.execute(query, values)
        return t.get_rows(cursor)

    def _split_row(self, row):
        keys = dict(row)
        obj = row.pop('_obj')
        return keys, obj


class KeyCollision(Exception):

    def __init__(self, keys):
        super().__init__('Cannot add object with same keys: %r' % keys)


class UnknownKey(Exception):

    def __init__(self, key):
        super().__init__('ObjectStore is not prepared for key %r' % key)


class WrongKeyType(Exception):

    def __init__(self, key, key_type):
        super().__init__(
            'ObjectStore is not prepared for key %r of type %r, must be str' %
            (key, key_type))


class KeyValueError(Exception):

    def __init__(self, key, value):
        super().__init__('Key %r value %r has the wrong type' % (key, value))


def flatten_object(obj):
    return list(sorted(set(_flatten(obj))))


def _flatten(obj, obj_key=None):
    if isinstance(obj, dict):
        for key, value in obj.items():
            for x in _flatten(value, obj_key=key):
                yield x
    elif isinstance(obj, list):
        for item in obj:
            for x in _flatten(item, obj_key=obj_key):
                yield x
    else:
        yield obj_key, obj
