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


import qvarn


class CollectionAPI:

    object_keys = {
        'obj_id': str,
        'subpath': str,
    }

    def __init__(self):
        self._store = None
        self._type = None
        self._proto = None
        self._idgen = qvarn.ResourceIdGenerator()

    def set_object_store(self, store):
        self._store = store
        store.create_store(**self.object_keys)

    def set_resource_type(self, rt):
        assert isinstance(rt, qvarn.ResourceType)
        self._type = rt
        self._proto = self._type.get_latest_prototype()

    def get_type(self):
        return self._type

    def get_type_name(self):
        return self._type.get_type()

    def post(self, obj):
        v = qvarn.Validator()
        v.validate_new_resource(obj, self.get_type())

        new_obj = self._new_object(self._proto, obj)
        new_obj['id'] = self._invent_id(obj['type'])
        new_obj['revision'] = self._invent_id('revision')
        self._create_object(new_obj, obj_id=new_obj['id'], subpath='')

        rt = self.get_type()
        subprotos = rt.get_subpaths()
        for subpath, subproto in subprotos.items():
            empty = self._new_object(subproto, {})
            self._create_object(empty, obj_id=new_obj['id'], subpath=subpath)

        return new_obj

    def _create_object(self, obj, **keys):
        assert set(keys.keys()) == set(self.object_keys.keys())
        qvarn.log.log(
            'debug', msg_text='Collection._create_object', obj=obj, keys=keys)
        self._store.create_object(obj, **keys)

    def _new_object(self, proto, obj):
        return qvarn.add_missing_fields(proto, obj)

    def _invent_id(self, resource_type):
        return self._idgen.new_id(resource_type)

    def get(self, obj_id):
        return self._get_object(obj_id, '')

    def get_subresource(self, obj_id, subpath):
        return self._get_object(obj_id, subpath)

    def _get_object(self, obj_id, subpath):
        keys = {
            'obj_id': obj_id,
            'subpath': subpath,
        }
        qvarn.log.log(
            'debug', msg_text='CollectionAPI._get_object', keys=keys)
        objs = self._store.get_objects(**keys)
        assert len(objs) <= 1
        if objs:
            return objs[0]
        raise NoSuchResource(**keys)

    def delete(self, obj_id):
        self.get(obj_id)
        self._store.remove_objects(obj_id=obj_id)

    def list(self):
        oftype = qvarn.Equal('type', self._type.get_type())
        matches = self._store.find_objects(oftype)
        return {
            'resources': [
                {'id': keys['obj_id']} for keys, _ in matches
            ]
        }

    def put(self, obj):
        v = qvarn.Validator()
        v.validate_resource_update(obj, self.get_type())

        old = self.get(obj['id'])
        if old['revision'] != obj['revision']:
            raise WrongRevision(obj['revision'], old['revision'])

        new_obj = dict(obj)
        new_obj['revision'] = self._invent_id('revision')
        self._store.remove_objects(obj_id=new_obj['id'], subpath='')
        self._create_object(new_obj, obj_id=new_obj['id'], subpath='')

        return new_obj

    def put_subresource(self, sub_obj, subpath=None, **keys):
        assert subpath is not None
        obj_id = keys.pop('obj_id')
        revision = keys.pop('revision')
        parent = self.get(obj_id)
        if parent['revision'] != revision:
            raise WrongRevision(revision, parent['revision'])
        keys = {
            'obj_id': obj_id,
            'subpath': subpath,
        }
        self._store.remove_objects(**keys)
        self._create_object(sub_obj, **keys)

        parent = self._update_revision(obj_id)
        new_sub = dict(sub_obj)
        new_sub['revision'] = parent['revision']
        return new_sub

    def _update_revision(self, obj_id):
        obj = self.get(obj_id)
        obj['revision'] = self._invent_id('revision')
        self._store.remove_objects(obj_id=obj_id, subpath='')
        self._create_object(obj, obj_id=obj_id, subpath='')
        return obj

    def search(self, search_criteria):
        if not search_criteria:
            raise NoSearchCriteria()

        p = qvarn.SearchParser()
        sp = p.parse(search_criteria)
        correct_type = qvarn.ResourceTypeIs(self.get_type_name())
        sp.add_cond(correct_type)

        def pick_all(obj):
            return obj

        def pick_id(obj):
            return {
                'id': obj['id'],
            }

        def pick_some_from_object(obj, fields):
            return {
                key: obj[key]
                for key in obj
                if key in fields
            }

        def pick_some(fields):
            return lambda obj: pick_some_from_object(obj, fields)

        if sp.show_all:
            pick_fields = pick_all
        elif sp.show_fields:
            show_what = sp.show_fields + ['id']
            pick_fields = pick_some(show_what)
        else:
            pick_fields = pick_id

        unsorted = self._find_matches(sp.cond)
        if sp.sort_keys:
            result = self._sort_objects(unsorted, sp.sort_keys)
        else:
            result = unsorted

        if sp.offset is None and sp.limit is None:
            chosen = result
        elif sp.offset is None and sp.limit is not None:
            chosen = result[:sp.limit]
        elif sp.offset is not None and sp.limit is None:
            chosen = result[sp.offset:]
        elif sp.offset is not None and sp.limit is not None:
            chosen = result[sp.offset:sp.offset+sp.limit]

        picked = [pick_fields(o) for o in chosen]

        qvarn.log.log(
            'trace', msg_text='Collection.search, sorted',
            result=picked)

        return picked

    def _find_matches(self, cond):
        return [o for _, o in self._store.find_objects(cond)]

    def _sort_objects(self, objects, sort_keys):
        def object_sort_key(obj, fields):
            return [
                (key, value)
                for key, value in qvarn.flatten_object(obj)
                if key in fields
            ]

        return sorted(objects, key=lambda o: object_sort_key(o, sort_keys))


class WrongRevision(Exception):

    def __init__(self, actual, expected):
        super().__init__(
            'PUTted objects must have correct revision set: '
            'got {}, expected {}'.format(actual, expected))


class NoSuchResource(Exception):

    def __init__(self, **keys):
        keys_str = ', '.join(
            '{}={!r}'.format(key, keys[key]) for key in sorted(keys))
        super().__init__("There is no resource with keys {}".format(keys_str))


class NoSearchCriteria(Exception):

    def __init__(self):
        super().__init__('No search criteria was given')
