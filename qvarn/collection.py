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

    def __init__(self):
        self._store = None
        self._type = None
        self._idgen = qvarn.ResourceIdGenerator()

    def set_object_store(self, store):
        self._store = store
        store.create_store(obj_id=str)

    def set_resource_type(self, rt):
        assert isinstance(rt, qvarn.ResourceType)
        self._type = rt

    def get_type(self):
        return self._type

    def get_type_name(self):
        return self._type.get_type()

    def post(self, obj):
        v = qvarn.Validator()
        v.validate_new_resource(obj, self.get_type())

        new_obj = self._new_object(obj)
        new_obj['id'] = self._invent_id(obj['type'])
        new_obj['revision'] = self._invent_id('revision')
        self._store.create_object(new_obj, obj_id=new_obj['id'])
        return new_obj

    def _new_object(self, obj):
        return qvarn.add_missing_fields(self.get_type(), obj)

    def _invent_id(self, resource_type):
        return self._idgen.new_id(resource_type)

    def get(self, obj_id):
        qvarn.log.log('debug', msg_text='CollectionAPI.get', obj_id=obj_id)
        objs = self._store.get_objects(obj_id=obj_id)
        qvarn.log.log('debug', msg_text='CollectionAPI.get', objs=objs)
        assert len(objs) <= 1
        if objs:
            return objs[0]
        raise NoSuchResource(obj_id)

    def delete(self, obj_id):
        self.get(obj_id)
        self._store.remove_objects(obj_id=obj_id)

    def list(self):
        oftype = qvarn.Equal('type', self._type.get_type())
        obj_ids = self._store.find_object_ids(oftype)
        return {
            'resources': [
                {'id': x['obj_id']} for x in obj_ids
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
        self._store.remove_objects(obj_id=new_obj['id'])
        self._store.create_object(new_obj, obj_id=new_obj['id'])

        return new_obj

    def search(self, search_criteria):
        if not search_criteria:
            raise NoSearchCriteria()
        p = qvarn.SearchParser()
        cond, show_what = p.parse(search_criteria)
        cond2 = self._make_cond_type_specific(cond)
        qvarn.log.log(
            'trace', msg_text='Collection.search', show_what=show_what,
            type=self.get_type_name())
        if show_what == 'show_all':
            result = self._store.find_objects(cond2)
        elif show_what:
            result = [
                self._strip_obj(obj, show_what + ['id'])
                for obj in self._store.find_objects(cond2)
            ]
        else:
            ids = self._store.find_object_ids(cond2)
            result = [
                {
                    'id': keys['obj_id'],
                }
                for keys in ids
            ]
            for keys in ids:
                obj = self._store.get_objects(**keys)
                qvarn.log.log(
                    'trace', msg_text='search hit', keys=keys, obj=obj)
        qvarn.log.log(
            'trace', msg_text='Collection.search', show_what=show_what,
            result=result)
        return result

    def _make_cond_type_specific(self, cond):
        correct_type = qvarn.ResourceTypeIs(self.get_type_name())
        return qvarn.All(correct_type, cond)

    def _strip_obj(self, obj, fields):
        return {
            key: obj[key]
            for key in obj
            if key in fields
        }


class WrongRevision(Exception):

    def __init__(self, actual, expected):
        super().__init__(
            'PUTted objects must have correct revision set: '
            'got {}, expected {}'.format(actual, expected))


class NoSuchResource(Exception):

    def __init__(self, obj_id):
        super().__init__("There is no resource with id {}".format(obj_id))


class NoSearchCriteria(Exception):

    def __init__(self):
        super().__init__('No search criteria was given')
