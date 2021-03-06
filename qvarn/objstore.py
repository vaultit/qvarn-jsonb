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

    def __init__(self):
        self._fine_grained_access_control = False

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

    def check_value_types(self, **keys):
        known_keys = self.get_known_keys()
        for key in keys:
            if type(keys[key]) is not known_keys[key]:
                raise KeyValueError(key, keys[key])

    def create_object(self, obj, auxtable=True, **keys):
        raise NotImplementedError()

    def remove_objects(self, **keys):
        raise NotImplementedError()

    def get_matches(self, cond=None, allow_cond=None, **keys):
        raise NotImplementedError()

    def create_blob(self, blob, subpath=None, **keys):
        raise NotImplementedError()

    def get_blob(self, subpath=None, **keys):
        raise NotImplementedError()

    def remove_blob(self, subpath=None, **keys):
        raise NotImplementedError()

    def have_fine_grained_access_control(self):
        return self._fine_grained_access_control

    def enable_fine_grained_access_control(self):
        self._fine_grained_access_control = True

    def get_allow_rules(self):
        raise NotImplementedError()

    def has_allow_rule(self, rule):
        raise NotImplementedError()

    def add_allow_rule(self, rule):
        raise NotImplementedError()

    def remove_allow_rule(self, rule):
        raise NotImplementedError()


class MemoryObjectStore(ObjectStoreInterface):

    def __init__(self):
        super().__init__()
        self._objs = []
        self._blobs = []
        self._known_keys = {}
        self._fine_grained_access_control = False
        self._allow = []

    def get_known_keys(self):
        return self._known_keys

    def create_store(self, **keys):
        self.check_keys_have_str_type(**keys)
        qvarn.log.log(
            'trace', msg_text='Creating store', keys=repr(keys), exc_info=True)
        self._known_keys = keys

    def create_object(self, obj, auxtable=True, **keys):
        qvarn.log.log(
            'trace', msg_text='Creating object', object=repr(obj), keys=keys)
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)
        self._check_unique_object(**keys)
        self._objs.append((obj, keys))

    def _check_unique_object(self, **keys):
        for _, k in self._objs:
            if self._keys_match(k, keys):
                raise KeyCollision(k)

    def create_blob(self, blob, subpath=None, **keys):
        qvarn.log.log('trace', msg_text='Creating blob', keys=keys)
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)
        self._check_unique_blob(subpath, **keys)
        if not self.get_matches(**keys):
            raise NoSuchObject(keys)
        self._blobs.append((blob, subpath, keys))

    def _check_unique_blob(self, subpath, **keys):
        for _, s, k in self._blobs:
            if self._keys_match(k, keys) and s == subpath:
                raise BlobKeyCollision(subpath, k)

    def get_blob(self, subpath=None, **keys):
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)
        blobs = [
            b
            for b, s, k in self._blobs
            if self._keys_match(k, keys) and s == subpath
        ]
        assert len(blobs) <= 1
        if not blobs:
            raise NoSuchObject(keys)
        return blobs[0]

    def remove_blob(self, subpath=None, **keys):
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)
        self._blobs = [
            b
            for b, s, k in self._blobs
            if not self._keys_match(k, keys) or s != subpath
        ]

    def remove_objects(self, **keys):
        self.check_all_keys_are_allowed(**keys)
        self._objs = [
            (o, k) for o, k in self._objs if not self._keys_match(k, keys)]

    def get_matches(self, cond=None, allow_cond=None, **keys):
        assert cond is not None or len(keys) > 0
        self.check_all_keys_are_allowed(**keys)
        if cond is None:
            cond = qvarn.Yes()
        if allow_cond is None:
            allow_cond = qvarn.Yes()
        return [
            (k, o)
            for o, k in self._objs
            if (self._keys_match(k, keys) and cond.
                matches(o, k) and
                allow_cond.matches(o, k))
        ]

    def _keys_match(self, got_keys, wanted_keys):
        for key in wanted_keys.keys():
            if got_keys.get(key) != wanted_keys[key]:
                return False
        return True

    def get_allow_rules(self):
        return list(self._allow)

    def has_allow_rule(self, rule):
        return rule in self._allow

    def add_allow_rule(self, rule):
        self._allow.append(dict(rule))

    def remove_allow_rule(self, rule):
        self._allow = [r for r in self._allow if r != rule]


class PostgresObjectStore(ObjectStoreInterface):  # pragma: no cover

    _table = '_objects'
    _auxtable = '_aux'
    _blobtable = '_blobs'
    _allowtable = '_allow'

    def __init__(self, sql):
        super().__init__()
        self._sql = sql
        self._keys = None

    def get_known_keys(self):
        return self._keys

    def create_store(self, **keys):
        self.check_keys_have_str_type(**keys)
        self._keys = dict(keys)

        # Create main table for objects.
        self._create_table(self._table, self._keys, '_obj', dict, index=True)

        # Create helper table for fields at all depths. Needed by searches.
        self._create_table(
            self._auxtable, self._keys, '_field', dict, jsonb_index=True)

        # Create helper table for blobs.
        self._create_table(self._blobtable, self._keys, '_blob', bytes)

        # Create table for fine-grained access control rules.
        self._create_allow_table()

    def _create_allow_table(self):
        columns = {
            'method': str,
            'client_id': str,
            'user_id': str,
            'subpath': str,
            'resource_id': str,
            'resource_type': str,
            'resource_field': str,
            'resource_value': str,
        }
        with self._sql.transaction() as t:
            query = t.create_table(self._allowtable, **columns)
            t.execute(query, {})

    def _create_table(
            self, name, col_dict, col_name, col_type, index=False,
            jsonb_index=False):
        columns = dict(col_dict)
        columns[col_name] = col_type
        with self._sql.transaction() as t:
            query = t.create_table(name, **columns)
            t.execute(query, {})

            for index_col in col_dict:
                index_name = self._index_name(name, index_col, '')
                query = t.create_index(name, index_name, index_col)
                t.execute(query, {})

            if index:
                index_name = self._index_name(name, col_name, '')
                query = t.create_index(name, index_name, col_name)
                t.execute(query, {})
            elif jsonb_index:
                index_name = self._index_name(name, col_name, 'name')
                query = t.create_jsonb_index(
                    name, index_name, col_name, 'name')
                t.execute(query, {})

                index_name = self._index_name(name, col_name, 'value')
                query = t.create_jsonb_index(
                    name, index_name, col_name, 'value')
                t.execute(query, {})

    def _index_name(self, table_name, column_name, field_name):
        name = '_'.join([table_name, column_name, field_name])
        return '{}_idx'.format(name)

    def create_object(self, obj, auxtable=True, **keys):
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
        for field, value in flatten_object(obj):
            x = {
                'name': field,
                'value': value,
            }
            keys['_field'] = json.dumps(x)
            column_names = list(keys.keys())
            query = t.insert_object(table_name, *column_names)
            t.execute(query, keys)

    def remove_objects(self, **keys):
        with self._sql.transaction() as t:
            query = t.remove_objects(self._table, *keys.keys())
            t.execute(query, keys)

            query = t.remove_objects(self._auxtable, *keys.keys())
            t.execute(query, keys)

    def _remove_objects_in_transaction(self, t, **keys):
        query = t.remove_objects(self._table, *keys.keys())
        t.execute(query, keys)
        query = t.remove_objects(self._auxtable, *keys.keys())
        t.execute(query, keys)

    def get_matches(self, cond=None, allow_cond=None, **keys):
        if cond is None:
            cond = qvarn.Yes()

        with self._sql.transaction() as t:
            query, values = t.select_objects_with_keys_and_cond(
                self._table, cond, allow_cond, **keys)
            cursor = t.execute(query, values)
            return [
                (self.get_keys_from_row(row), row['_obj'])
                for row in t.get_rows(cursor)
            ]

    def get_keys_from_row(self, row):
        return {
            key: row[key]
            for key in self._keys
        }

    def _split_row(self, row):
        keys = dict(row)
        obj = row.pop('_obj')
        return keys, obj

    def create_blob(self, blob, subpath=None, **keys):
        keys['subpath'] = subpath
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)
        if not self.get_matches(**keys):
            raise NoSuchObject(keys)

        with self._sql.transaction() as t:
            column_names = list(keys.keys()) + ['_blob']
            query = t.insert_object(self._blobtable, *column_names)

            values = dict(keys)
            values['_blob'] = blob

            t.execute(query, values)

    def get_blob(self, subpath=None, **keys):
        keys['subpath'] = subpath
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)

        column_names = list(keys.keys())

        with self._sql.transaction() as t:
            query = t.select_objects(self._blobtable, '_blob', *column_names)
            blobs = [bytes(row['_blob']) for row in t.execute(query, keys)]
            if not blobs:
                raise NoSuchObject(keys)
            return blobs

    def remove_blob(self, subpath=None, **keys):
        keys['subpath'] = subpath
        self.check_all_keys_are_allowed(**keys)
        self.check_value_types(**keys)

        column_names = list(keys.keys())
        with self._sql.transaction() as t:
            query = t.remove_objects(self._blobtable, *column_names)
            t.execute(query, keys)

    def get_allow_rules(self):
        return None

    def has_allow_rule(self, rule):
        with self._sql.transaction() as t:
            query = t.has_allow_rule(self._allowtable, rule)
            for row in t.execute(query, rule):
                return True
        return False

    def add_allow_rule(self, rule):
        with self._sql.transaction() as t:
            column_names = list(rule.keys())
            query = t.insert_object(self._allowtable, *column_names)
            qvarn.log.log(
                'trace', msg_text='add_allow_rule, SQL',
                query=query, rule=rule)
            t.execute(query, rule)

    def remove_allow_rule(self, rule):
        column_names = list(rule.keys())
        with self._sql.transaction() as t:
            query = t.remove_allow_rule(self._allowtable, rule)
            t.execute(query, rule)


class KeyCollision(Exception):

    def __init__(self, keys):
        super().__init__('Cannot add object with same keys: %r' % keys)


class BlobKeyCollision(Exception):

    def __init__(self, subpath, keys):
        super().__init__(
            'Cannot add blob with same keys: subpath=%s %r' % (subpath, keys))


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


class NoSuchObject(Exception):

    def __init__(self, keys):
        super().__init__('No object/blob with keys {}'.format(keys))


def flatten_object(obj):
    # We sort only by the name, not the object in each pair in the
    # list. Otherwise, if there are two fields with the same name but
    # incompatible value types this will break. However, to guarantee
    # that objects always result in the same flattened representation,
    # we also compare the second field. For this, we convert the
    # second value to a string with repr. This allows the second
    # fields to be compared regardless of type.

    pairs = _flatten(obj)
    unique_pairs = set(pairs)
    sorted_pairs = sorted(unique_pairs, key=repr)
    return list(sorted_pairs)


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
