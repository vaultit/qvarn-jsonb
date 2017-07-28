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


import os


import apifw
import qvarn


class QvarnAPI:

    def __init__(self):
        self._store = None

    def set_object_store(self, store):
        self._store = store
        self._store.create_store(obj_id=str)

    def find_missing_route(self, path):
        if path == '/version':
            return [
                {
                    'method': 'GET',
                    'path': '/version',
                    'callback': self.version,
                },
            ]

        try:
            rt = self.get_resource_type(path)
        except NoSuchResourceType:
            return []

        coll = qvarn.CollectionAPI()
        coll.set_object_store(self._store)
        coll.set_resource_type(rt)

        id_path = os.path.join(path, '<id>')
        return [
            {
                'method': 'POST',
                'path': path,
                'callback': self.get_post_callback(coll),
            },
            {
                'method': 'PUT',
                'path': id_path,
                'callback': self.get_put_callback(coll),
            },
            {
                'method': 'GET',
                'path': path,
                'callback': self.get_resource_list_callback(coll),
            },
            {
                'method': 'GET',
                'path': id_path,
                'callback': self.get_resource_callback(coll),
            },
            {
                'method': 'DELETE',
                'path': id_path,
                'callback': self.delete_resource_callback(coll),
            },
        ]

    def version(self, content_type, body):
        return apifw.Response({
            'status': apifw.HTTP_OK,
            'body': {
                'api': {
                    'version': qvarn.__version__,
                },
                'implementation': {
                    'name': 'Qvarn',
                    'version': qvarn.__version__,
                },
            },
            'headers': {
                'Content-Type': 'application/json',
            },
        })

    def add_resource_type(self, rt):
        path = rt.get_path()
        objs = self._store.get_objects(obj_id=path)
        if objs:
            raise ResourceTypeAlreadyExists(path)
        obj = {
            'type': 'resource_type',
            'id': path,
            'spec': rt.as_dict(),
        }
        self._store.create_object(obj, obj_id=path)

    def get_resource_type(self, path):
        objs = self._store.get_objects(obj_id=path)
        assert 0 <= len(objs) <= 1
        if len(objs) == 0:
            raise NoSuchResourceType(path)
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def get_post_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body):
            if content_type != 'application/json':
                raise NotJson(content_type)
            if 'type' not in body:
                body['type'] = coll.get_type()
            try:
                self.validate_json(body)
            except ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return apifw.Response({
                    'status': apifw.HTTP_BAD_REQUEST,
                    'body': str(e),
                })
            return apifw.Response({
                'status': apifw.HTTP_CREATED,
                'body': coll.post(body),
                'headers': {
                    'Content-Type': 'application/json',
                },
            })
        return wrapper

    def get_put_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            if content_type != 'application/json':
                raise NotJson(content_type)
            self.validate_json(body)
            obj_id = kwargs['id']
            if body['id'] != obj_id:
                raise IdMismatch(body['id'], obj_id)
            return apifw.Response({
                'status': apifw.HTTP_OK,
                'body': coll.put(body),
                'headers': {
                    'Content-Type': 'application/json',
                },
            })
        return wrapper

    def get_resource_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            try:
                obj = coll.get(kwargs['id'])
            except qvarn.NoSuchResource:
                return {
                    'status': apifw.HTTP_NOT_FOUND,
                    'body': '',
                    'headers': {},
                }
            return apifw.Response({
                'status': apifw.HTTP_OK,
                'body': obj,
                'headers': {
                    'Content-Type': 'application/json',
                },
            })
        return wrapper

    def get_resource_list_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            return apifw.Response({
                'status': apifw.HTTP_OK,
                'body': coll.list(),
                'headers': {
                    'Content-Type': 'application/json',
                },
            })
        return wrapper

    def validate_json(self, obj):  # pragma: no cover
        if not isinstance(obj, dict):
            raise NotDict()
        if 'type' not in obj:
            raise NoType()

    def delete_resource_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            return apifw.Response({
                'status': apifw.HTTP_OK,
                'body': coll.delete(kwargs['id']),
                'headers': {
                    'Content-Type': 'application/json',
                },
            })
        return wrapper


class NoSuchResourceType(Exception):

    def __init__(self, path):
        super().__init__('No resource type for path {}'.format(path))


class ResourceTypeAlreadyExists(Exception):

    def __init__(self, type_name):
        super().__init__('Resource type {} already exits'.format(type_name))


class NotJson(Exception):  # pragma: no cover

    def __init__(self, ct):
        super().__init__('Was expecting application/json, not {}'.format(ct))


class ValidationError(Exception):

    pass


class NotDict(ValidationError):  # pragma: no cover

    def __init__(self):
        super().__init__('Was expecting a JSON object (dict)')


class NoType(ValidationError):  # pragma: no cover

    def __init__(self):
        super().__init__('Was expecting a "type" field in resource')


class IdMismatch(Exception):  # pragma: no cover

    def __init__(self, obj_id, id_from_path):
        super().__init__(
            'Resource has id {} but path says {}'.format(obj_id, id_from_path))
