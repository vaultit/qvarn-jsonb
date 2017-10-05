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


import io
import os
import time

import yaml

import apifw
import qvarn


resource_type_spec_yaml = '''
type: resource_type
path: /resource_types
versions:

- version: v0
  prototype:
    type: ""
    id: ""
    revision: ""
    name: ""
    yaml: ""
'''

listener_spec = {
    'type': 'listener',
    'path': '/listeners',
    'versions': [
        {
            'version': 'v0',
            'prototype': {
                'id': '',
                'type': '',
                'revision': '',
                'notify_of_new': False,
                'listen_on_all': False,
                'listen_on': [''],
            },
            'subpaths': {},
        },
    ],
}

notification_spec = {
    'type': 'notification',
    'path': '/notifications',
    'versions': [
        {
            'version': 'v0',
            'prototype': {
                'id': '',
                'type': '',
                'revision': '',
                'listener_id': '',
                'resource_id': '',
                'resource_revision': '',
                'resource_change': '',
                'timestamp': '',
            },
            'subpaths': {},
        },
    ],
}


class QvarnAPI:

    def __init__(self):
        self._store = None
        self._validator = qvarn.Validator()
        self._baseurl = None
        self._rt_coll = None

    def set_base_url(self, baseurl):  # pragma: no cover
        self._baseurl = baseurl

    def set_object_store(self, store):
        self._store = store
        self._store.create_store(obj_id=str, subpath=str)
        self.set_up_resource_types()

    def set_up_resource_types(self):
        f = io.StringIO(resource_type_spec_yaml)
        spec = yaml.safe_load(f)
        rt = qvarn.ResourceType()
        rt.from_spec(spec)
        self._rt_coll = qvarn.CollectionAPI()
        self._rt_coll.set_object_store(self._store)
        self._rt_coll.set_resource_type(rt)

        for spec in [listener_spec, notification_spec]:
            rt2 = qvarn.ResourceType()
            rt2.from_spec(spec)
            self.add_resource_type(rt2)

    def add_resource_type(self, rt):
        path = rt.get_path()
        cond1 = qvarn.Equal('path', path)
        cond2 = qvarn.Equal('type', 'resource_type')
        cond = qvarn.All(cond1, cond2)
        results = self._store.find_objects(cond)
        objs = [obj for _, obj in results]
        if not objs:
            obj = {
                'id': rt.get_type(),
                'type': 'resource_type',
                'path': path,
                'spec': rt.as_dict(),
            }
            self._store.create_object(
                obj, obj_id=obj['id'], subpath='', auxtable=True)

    def get_resource_type(self, path):
        cond1 = qvarn.Equal('path', path)
        cond2 = qvarn.Equal('type', 'resource_type')
        cond = qvarn.All(cond1, cond2)
        results = self._store.find_objects(cond)
        objs = [obj for _, obj in results]
        qvarn.log.log('debug', objs=objs)
        if len(objs) == 0:
            qvarn.log.log(
                'error',
                msg_text='There is no resource type for path',
                path=path)
            raise NoSuchResourceType(path)
        elif len(objs) > 1:  # pragma: no cover
            qvarn.log.log(
                'error',
                msg_text='There are more than one resource types for path',
                path=path,
                objs=objs)
            raise TooManyResourceTypes(path)
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def get_listener_resource_type(self):
        cond1 = qvarn.Equal('id', 'listener')
        cond2 = qvarn.Equal('type', 'resource_type')
        cond = qvarn.All(cond1, cond2)
        results = self._store.find_objects(cond)
        objs = [obj for _, obj in results]
        qvarn.log.log('debug', objs=objs)
        if len(objs) == 0:  # pragma: no cover
            raise NoSuchResourceType('listener')
        elif len(objs) > 1:  # pragma: no cover
            raise TooManyResourceTypes('listener')
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def get_notification_resource_type(self):  # pragma: no cover
        cond1 = qvarn.Equal('id', 'notification')
        cond2 = qvarn.Equal('type', 'resource_type')
        cond = qvarn.All(cond1, cond2)
        results = self._store.find_objects(cond)
        objs = [obj for _, obj in results]
        qvarn.log.log('debug', objs=objs)
        if len(objs) == 0:  # pragma: no cover
            raise NoSuchResourceType('listener')
        elif len(objs) > 1:  # pragma: no cover
            raise TooManyResourceTypes('listener')
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def find_missing_route(self, path):
        qvarn.log.log('info', msg_text='find_missing_route', path=path)

        if path == '/version':
            qvarn.log.log('info', msg_text='Add /version route')
            return self.version_route()

        try:
            rt = self.get_resource_type(path)
        except NoSuchResourceType:
            qvarn.log.log('warning', msg_text='No such route', path=path)
            return []

        routes = self.resource_routes(path, rt)
        loggable_routes = [
            {
                key: repr(r[key])
                for key in r
            }
            for r in routes
        ]
        qvarn.log.log('info', msg_text='Add routes', routes=loggable_routes)
        return routes

    def version_route(self):
        return [
            {
                'method': 'GET',
                'path': '/version',
                'callback': self.version,
                'needs-authorization': False,
            },
        ]

    def version(self, content_type, body, **kwargs):
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

    def resource_routes(self, path, rt):
        coll = qvarn.CollectionAPI()
        coll.set_object_store(self._store)
        coll.set_resource_type(rt)

        id_path = os.path.join(path, '<id>')
        routes = [
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

        for subpath in rt.get_subpaths():
            routes.extend([
                {
                    'method': 'GET',
                    'path': '{}/{}'.format(id_path, subpath),
                    'callback': self.get_subpath_callback(coll, subpath),
                },
                {
                    'method': 'PUT',
                    'path': '{}/{}'.format(id_path, subpath),
                    'callback': self.put_subpath_callback(coll, subpath),
                },
            ])

        return routes + self._get_notification_routes(coll, path, id_path)

    def _get_notification_routes(self, coll, path, id_path):
        rt = self.get_listener_resource_type()
        listeners = qvarn.CollectionAPI()
        listeners.set_object_store(self._store)
        listeners.set_resource_type(rt)

        return [
            {
                'method': 'POST',
                'path': path + '/listeners',
                'callback': self.get_post_listener_callback(coll, listeners),
            },
            {
                'method': 'GET',
                'path': path + '/listeners',
                'callback': self.get_listener_list_callback(listeners),
            },
            {
                'method': 'GET',
                'path': path + '/listeners/<id>',
                'callback': self.get_listener_callback(coll, listeners),
            },
            {
                'method': 'PUT',
                'path': path + '/listeners/<id>',
                'callback': self.put_listener_callback(listeners),
            },
            {
                'method': 'DELETE',
                'path': path + '/listeners/<id>',
                'callback': self.delete_listener_callback(listeners),
            },
            {
                'method': 'GET',
                'path': path + '/listeners/<id>/notifications',
                'callback': self.get_notifications_list_callback(),
            },
            {
                'method': 'GET',
                'path': path + '/listeners/<listener_id>/notifications/<id>',
                'callback': self.get_notification_callback(),
            },
            {
                'method': 'DELETE',
                'path': path + '/listeners/<listener_id>/notifications/<id>',
                'callback': self.delete_notification_callback(),
            },
        ]

    def get_post_listener_callback(self, coll, listeners):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            if content_type != 'application/json':
                raise NotJson(content_type)

            rt = listeners.get_type()
            try:
                self._validator.validate_against_prototype(
                    rt.get_type(), body, rt.get_latest_prototype())
            except qvarn.ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return bad_request_response(str(e))

            if 'type' not in body:
                body['type'] = 'listener'

            result_body = listeners.post(body)
            qvarn.log.log(
                'debug', msg_text='POST a new listener, result',
                body=result_body)
            location = '{}{}/listeners/{}'.format(
                self._baseurl, coll.get_type().get_path(),
                result_body['id'])
            return created_response(result_body, location)
        return wrapper

    def get_listener_list_callback(self, listeners):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            body = listeners.list()
            return ok_response(body)
        return wrapper

    def get_listener_callback(self, coll, listeners):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            try:
                obj = listeners.get(kwargs['id'])
            except qvarn.NoSuchResource as e:
                return no_such_resource_response(str(e))
            return ok_response(obj)
        return wrapper

    def put_listener_callback(self, listeners):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            if content_type != 'application/json':
                raise NotJson(content_type)

            if 'type' not in body:
                body['type'] = 'listener'

            listener_id = kwargs['id']

            if 'id' not in body:
                body['id'] = listener_id

            try:
                self._validator.validate_resource_update(
                    body, listeners.get_type())
            except qvarn.ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return bad_request_response(str(e))

            try:
                result_body = listeners.put(body)
            except qvarn.WrongRevision as e:
                return conflict_response(str(e))
            except qvarn.NoSuchResource as e:
                # We intentionally say bad request, instead of not found.
                # This is to be compatible with old Qvarn. This may get
                # changed later.
                return bad_request_response(str(e))

            return ok_response(result_body)
        return wrapper

    def get_notifications_list_callback(self):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            rid = kwargs['id']
            cond = qvarn.All(
                qvarn.Equal('type', 'notification'),
                qvarn.Equal('listener_id', rid)
            )
            pairs = self._store.find_objects(cond)
            qvarn.log.log(
                'trace', msg_text='Found notifications',
                notifications=pairs)
            body = {
                'resources': [
                    {
                        'id': keys['obj_id']
                    }
                    for keys, _ in pairs
                ]
            }
            return ok_response(body)
        return wrapper

    def get_notification_callback(self):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            listener_id = kwargs['listener_id']
            notification_id = kwargs['id']
            cond = qvarn.All(
                qvarn.Equal('type', 'notification'),
                qvarn.Equal('listener_id', listener_id),
                qvarn.Equal('id', notification_id),
            )
            pairs = self._store.find_objects(cond)
            qvarn.log.log(
                'trace', msg_text='Found notifications',
                notifications=pairs)
            if len(pairs) == 0:
                return no_such_resource_response(notification_id)
            if len(pairs) > 1:
                raise TooManyResources(notification_id)
            return ok_response(pairs[0][1])
        return wrapper

    def delete_listener_callback(self, listeners):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            listener_id = kwargs['id']
            listeners.delete(listener_id)
            for obj_id in self.find_notifications(listener_id):
                self._store.remove_objects(obj_id=obj_id)
            return ok_response({})
        return wrapper

    def delete_notification_callback(self):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            listener_id = kwargs['listener_id']
            notification_id = kwargs['id']
            cond = qvarn.All(
                qvarn.Equal('type', 'notification'),
                qvarn.Equal('listener_id', listener_id),
                qvarn.Equal('id', notification_id),
            )
            for keys, _ in self._store.find_objects(cond):
                self._store.remove_objects(**keys)
            return ok_response({})
        return wrapper

    def find_notifications(self, listener_id):  # pragma: no cover
        cond = qvarn.All(
            qvarn.Equal('type', 'notification'),
            qvarn.Equal('listener_id', listener_id),
        )
        obj_ids = [
            keys['obj_id']
            for keys, _ in self._store.find_objects(cond)
        ]
        qvarn.log.log(
            'trace', msg_text='Found notifications',
            notifications=obj_ids)
        return obj_ids

    def notify(self, rid, rrev, change):  # pragma: no cover
        rt = self.get_notification_resource_type()
        notifs = qvarn.CollectionAPI()
        notifs.set_object_store(self._store)
        notifs.set_resource_type(rt)
        obj = {
            'type': 'notification',
            'resource_id': rid,
            'resource_revision': rrev,
            'resource_change': change,
            'timestamp': self.get_current_timestamp(),
        }
        for listener in self.find_listeners(rid, change):
            obj['listener_id'] = listener['id']
            qvarn.log.log(
                'info', msg_text='Notify listener of change',
                notification=obj)
            notifs.post(obj)

    def find_listeners(self, rid, change):  # pragma: no cover
        cond = qvarn.Equal('type', 'listener')
        pairs = self._store.find_objects(cond)
        for _, obj in pairs:
            if self.listener_matches(obj, rid, change):
                yield obj

    def listener_matches(self, obj, rid, change):  # pragma: no cover
        if change == 'created' and obj.get('notify_of_new'):
            return True
        if change != 'created' and obj.get('listen_on_all'):
            return True
        if rid in obj.get('listen_on', []):
            return True
        return False

    def get_current_timestamp(self):  # pragma: no cover
        return time.strftime('%Y-%m-%dT%H:%M:%S')

    def get_post_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
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
            self.notify(result_body['id'], result_body['revision'], 'created')
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
                # We intentionally say bad request, instead of not found.
                # This is to be compatible with old Qvarn. This may get
                # changed later.
                return bad_request_response(str(e))

            self.notify(
                result_body['id'], result_body['revision'], 'updated')
            return ok_response(result_body)
        return wrapper

    def put_subpath_callback(self, coll, subpath):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            if content_type != 'application/json':
                raise NotJson(content_type)

            obj_id = kwargs['id']
            if 'revision' not in body:
                return bad_request_response('must have revision')
            revision = body.pop('revision')

            rt = coll.get_type()
            try:
                self._validator.validate_subresource(subpath, rt, body)
            except qvarn.ValidationError as e:
                qvarn.log.log('error', msg_text=str(e), body=body)
                return bad_request_response(str(e))

            try:
                result_body = coll.put_subresource(
                    body, subpath=subpath, obj_id=obj_id, revision=revision)
            except qvarn.WrongRevision as e:
                return conflict_response(str(e))
            except qvarn.NoSuchResource as e:
                return no_such_resource_response(str(e))

            return ok_response(result_body)
        return wrapper

    def get_resource_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            try:
                obj = coll.get(kwargs['id'])
            except qvarn.NoSuchResource as e:
                return no_such_resource_response(str(e))
            return ok_response(obj)
        return wrapper

    def get_subpath_callback(self, coll, subpath):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            try:
                obj = coll.get_subresource(kwargs['id'], subpath)
            except qvarn.NoSuchResource as e:
                return no_such_resource_response(str(e))
            return ok_response(obj)
        return wrapper

    def get_resource_list_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            body = coll.list()
            return ok_response(body)
        return wrapper

    def get_search_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            path = kwargs['raw_uri_path']
            search_criteria = path.split('/search/', 1)[1]
            try:
                result = coll.search(search_criteria)
            except qvarn.UnknownSearchField as e:
                return unknown_search_field_response(e)
            except qvarn.NeedSortOperator:
                return need_sort_response()
            except qvarn.SearchParserError as e:
                return search_parser_error_response(e)
            body = {
                'resources': result,
            }
            return ok_response(body)
        return wrapper

    def delete_resource_callback(self, coll):  # pragma: no cover
        def wrapper(content_type, body, **kwargs):
            obj_id = kwargs['id']
            coll.delete(obj_id)
            self.notify(obj_id, None, 'deleted')
            return ok_response({})
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


def no_such_resource_response(msg):  # pragma: no cover
    return response(apifw.HTTP_NOT_FOUND, msg, {})


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


def need_sort_response():  # pragma: no cover
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'message': 'LIMIT and OFFSET can only be used with together SORT.',
        'error_code': 'LimitWithoutSortError',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def search_parser_error_response(e):  # pragma: no cover
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'message': 'Could not parse search condition',
        'error_code': 'BadSearchCondition',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def unknown_search_field_response(e):  # pragma: no cover
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'field': e.field,
        'message': 'Resource does not contain given field',
        'error_code': 'FieldNotInResource',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def conflict_response(body):  # pragma: no cover
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_CONFLICT, body, headers)


class NoSuchResourceType(Exception):  # pragma: no cover

    def __init__(self, path):
        super().__init__('No resource type for path {}'.format(path))


class TooManyResourceTypes(Exception):  # pragma: no cover

    def __init__(self, path):
        super().__init__('Too many resource types for path {}'.format(path))


class TooManyResources(Exception):  # pragma: no cover

    def __init__(self, resource_id):
        super().__init__('Too many resources with id {}'.format(resource_id))


class NotJson(Exception):  # pragma: no cover

    def __init__(self, ct):
        super().__init__('Was expecting application/json, not {}'.format(ct))


class IdMismatch(Exception):  # pragma: no cover

    def __init__(self, obj_id, id_from_path):
        super().__init__(
            'Resource has id {} but path says {}'.format(obj_id, id_from_path))
