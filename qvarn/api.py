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
        self._validator = qvarn.Validator()
        self._baseurl = None

    def set_base_url(self, baseurl):  # pragma: no cover
        self._baseurl = baseurl

    def set_object_store(self, store):
        self._store = store
        self._store.create_store(obj_id=str)

    def find_missing_route(self, path):
        qvarn.log.log('info', msg_text='find_missing_route', path=path)

        if path == '/version':
            return [
                {
                    'method': 'GET',
                    'path': '/version',
                    'callback': self.version,
                    'needs-authorization': False,
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
                'method': 'GET',
                'path': path + '/search/<search_criteria:path>',
                'callback': self.get_search_callback(coll),
            },
            {
                'method': 'DELETE',
                'path': id_path,
                'callback': self.delete_resource_callback(coll),
            },
        ]

    def version(self, content_type, body):
        version = {
            'api': {
                'version': qvarn.__version__,
            },
            'implementation': {
                'name': 'Qvarn',
                'version': qvarn.__version__,
            },
        }
        return ok_response(version)

    def add_resource_type(self, rt):
        path = rt.get_path()
        objs = self._store.get_objects(obj_id=path)
        if not objs:
            obj = {
                'type': 'resource_type',
                'id': path,
                'spec': rt.as_dict(),
            }
            self._store.create_object(obj, obj_id=path, auxtable=False)

    def get_resource_type(self, path):
        objs = self._store.get_objects(obj_id=path)
        if len(objs) == 0:
            raise NoSuchResourceType(path)
        elif len(objs) > 1:  # pragma: no cover
            raise TooManyResourceTypes(path)
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def get_post_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body):
            if content_type != 'application/json':
                raise NotJson(content_type)
            if 'type' not in body:
                body['type'] = coll.get_type_name()
            try:
                self._validator.validate_new_resource(body, coll.get_type())
            except qvarn.ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return bad_request_response(str(e))
            result_body = coll.post(body)
            qvarn.log.log(
                'debug', msg_text='POST a new resource, result',
                body=result_body)
            location = '{}{}/{}'.format(
                self._baseurl, coll.get_type().get_path(), result_body['id'])
            return created_response(result_body, location)
        return wrapper

    def get_put_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            if content_type != 'application/json':
                raise NotJson(content_type)

            if 'type' not in body:
                body['type'] = coll.get_type_name()

            if 'id' not in body:
                body['id'] = kwargs['id']

            try:
                self._validator.validate_resource_update(
                    body, coll.get_type())
            except qvarn.ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return bad_request_response(str(e))

            obj_id = kwargs['id']
            # FIXME: the following test should be enabled once we
            # no longer need test-api.
            if False and body['id'] != obj_id:
                raise IdMismatch(body['id'], obj_id)

            try:
                result_body = coll.put(body)
            except qvarn.WrongRevision as e:
                return conflict_response(str(e))
            except qvarn.NoSuchResource as e:
                return bad_request_response(str(e))

            return ok_response(result_body)
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
            return ok_response(obj)
        return wrapper

    def get_resource_list_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            body = coll.list()
            return ok_response(body)
        return wrapper

    def get_search_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, search_criteria='', **kwargs):
            try:
                result = coll.search(search_criteria)
            except qvarn.SearchParserError as e:
                return bad_request_response(str(e))
            body = {
                'resources': result,
            }
            return ok_response(body)
        return wrapper

    def delete_resource_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            body = coll.delete(kwargs['id'])
            return ok_response(body)
        return wrapper


def response(status, body, headers):  # pragma: no cover
    return apifw.Response(
        {
            'status': status,
            'body': body,
            'headers': headers,
        }
    )


def ok_response(body):  # pragma: no cover
    headers = {
        'Content-Type': 'application/json',
    }
    return response(apifw.HTTP_OK, body, headers)


def created_response(body, location):  # pragma: no cover
    headers = {
        'Content-Type': 'application/json',
        'Location': location,
    }
    return response(apifw.HTTP_CREATED, body, headers)


def bad_request_response(body):  # pragma: no cover
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def conflict_response(body):  # pragma: no cover
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_CONFLICT, body, headers)


class NoSuchResourceType(Exception):

    def __init__(self, path):
        super().__init__('No resource type for path {}'.format(path))


class TooManyResourceTypes(Exception):  # pragma: no cover

    def __init__(self, path):
        super().__init__('Too many resource types for path {}'.format(path))


class NotJson(Exception):  # pragma: no cover

    def __init__(self, ct):
        super().__init__('Was expecting application/json, not {}'.format(ct))


class IdMismatch(Exception):  # pragma: no cover

    def __init__(self, obj_id, id_from_path):
        super().__init__(
            'Resource has id {} but path says {}'.format(obj_id, id_from_path))
