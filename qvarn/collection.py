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
        self._type = rt

    def get_routes(self):
        raise NotSetUp()

    def post(self, obj):
        if not obj.get('type'):
            raise NoType()
        if obj.get('id'):
            raise HasId()
        if obj.get('revision'):
            raise HasRevision()

        new_obj = dict(obj)
        new_obj['id'] = self._invent_id(obj['type'])
        new_obj['revision'] = self._invent_id('revision')
        self._store.create_object(new_obj, obj_id=new_obj['id'])
        return new_obj

    def _invent_id(self, resource_type):
        return self._idgen.new_id(resource_type)

    def get(self, obj_id):
        objs = self._store.get_objects(obj_id=obj_id)
        assert len(objs) <= 1
        if objs:
            return objs[0]
        raise NoSuchResource(obj_id)

    def delete(self, obj_id):
        self.get(obj_id)
        self._store.remove_objects(obj_id=obj_id)

    def list(self):
        obj_ids = self._store.find_object_ids(qvarn.All())
        return {
            'resources': [
                {'id': x['obj_id']} for x in obj_ids
            ]
        }

    def put(self, obj):
        if not obj.get('type'):
            raise NoType()
        if not obj.get('id'):
            raise NoId()
        if not obj.get('revision'):
            raise NoRevision()

        old = self.get(obj['id'])
        if old['revision'] != obj['revision']:
            raise WrongRevision()

        new_obj = dict(obj)
        new_obj['revision'] = self._invent_id('revision')
        self._store.remove_objects(obj_id=new_obj['id'])
        self._store.create_object(new_obj, obj_id=new_obj['id'])

        return new_obj


class NotSetUp(Exception):

    def __init__(self):
        super().__init__('CollectionAPI object is not set up')


class NoType(Exception):

    def __init__(self):
        super().__init__("Objects must have a type set")


class HasId(Exception):

    def __init__(self):
        super().__init__("POSTed objects mustn't have an id set")


class HasRevision(Exception):

    def __init__(self):
        super().__init__("POSTed objects mustn't have a revision set")


class NoId(Exception):

    def __init__(self):
        super().__init__("PUTted objects must have an id set")


class NoRevision(Exception):

    def __init__(self):
        super().__init__("PUTted objects must have a revision set")


class WrongRevision(Exception):

    def __init__(self):
        super().__init__("PUTted objects must have correct revision set")


class NoSuchResource(Exception):

    def __init__(self, obj_id):
        super().__init__("There is no resource with id {}".format(obj_id))
