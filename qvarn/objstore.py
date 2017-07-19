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

    def create_object(self, obj, **keys):
        raise NotImplementedError()

    def remove_objects(self, **keys):
        raise NotImplementedError()

    def get_objects(self, **keys):
        raise NotImplementedError()

    def _keys_match(self, got_keys, wanted_keys):
        raise NotImplementedError()

    def find_objects(self, cond):
        raise NotImplementedError()

    def find_object_ids(self, cond):
        raise NotImplementedError()
    


class MemoryObjectStore(ObjectStoreInterface):

    def __init__(self):
        self._objs = []
        self._known_keys = {}

    def create_store(self, **keys):
        self._known_keys = keys

    def create_object(self, obj, **keys):
        for key in keys.keys():
            if key not in self._known_keys:
                raise UnknownKey(key=key)
            if type(keys[key]) is not self._known_keys[key]:
                raise KeyValueError(key, keys[key])

        for _, k in self._objs:
            if self._keys_match(k, keys):
                raise KeyCollision(k)
        self._objs.append((obj, keys))

    def remove_objects(self, **keys):
        self._objs = [
            (o,k) for o, k in self._objs if not self._keys_match(k, keys)]

    def get_objects(self, **keys):
        return [o for o, k in self._objs if self._keys_match(k, keys)]

    def _keys_match(self, got_keys, wanted_keys):
        for key in wanted_keys.keys():
            if got_keys.get(key) != wanted_keys[key]:
                return False
        return True

    def find_objects(self, cond):
        return [obj for obj, _ in self._objs if cond.matches(obj)]

    def find_object_ids(self, cond):
        return [keys for obj, keys in self._objs if cond.matches(obj)]


class KeyCollision(Exception):

    def __init__(self, keys):
        super().__init__('Cannot add object with same keys: %r' % keys)


class UnknownKey(Exception):

    def __init__(self, key):
        super().__init__('ObjectStore is not prepared for key %r' % key)


class KeyValueError(Exception):

    def __init__(self, key, value):
        super().__init__('Key %r value %r has the wrong type' % (key, value))


class Condition:

    def matches(self, obj):  # pragma: no cover
        raise NotImplementedError()


class Equal(Condition):

    def __init__(self, name, value):
        self._name = name
        self._value = value

    def matches(self, obj):
        return obj.get(self._name) == self._value


class All(Condition):

    def matches(self, obj):
        return True
