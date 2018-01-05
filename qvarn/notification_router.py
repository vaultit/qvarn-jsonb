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


class NotificationRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._api = None
        self._baseurl = None
        self._store = None
        self._parent_coll = None
        self._listener_coll = None

    def set_api(self, api):
        self._api = api

    def set_baseurl(self, baseurl):
        self._baseurl = baseurl

    def set_parent_collection(self, parent_coll):
        self._parent_coll = parent_coll

    def set_object_store(self, store, listener_rt):
        self._store = store
        listeners = qvarn.CollectionAPI()
        listeners.set_object_store(self._store)
        listeners.set_resource_type(listener_rt)
        self._listener_coll = listeners

    def get_routes(self):
        rt = self._parent_coll.get_type()
        listeners_path = '{}/listeners'.format(rt.get_path())
        listener_id_path = '{}/<listener_id>'.format(listeners_path)
        notifications_path = '{}/notifications'.format(listener_id_path)
        notification_id_path = '{}/<notification_id>'.format(
            notifications_path)

        return [
            {
                'method': 'POST',
                'path': listeners_path,
                'callback': self._create_listener,
            },
            {
                'method': 'GET',
                'path': listeners_path,
                'callback': self._get_listener_list,
            },
            {
                'method': 'GET',
                'path': listener_id_path,
                'callback': self._get_a_listener,
            },
            {
                'method': 'PUT',
                'path': listener_id_path,
                'callback': self._update_listener,
            },
            {
                'method': 'DELETE',
                'path': listener_id_path,
                'callback': self._delete_listener,
            },
            {
                'method': 'POST',
                'path': notifications_path,
                'callback': self._create_a_notification,
            },
            {
                'method': 'GET',
                'path': notifications_path,
                'callback': self._get_notifications_list,
            },
            {
                'method': 'GET',
                'path': notification_id_path,
                'callback': self._get_a_notification,
            },
            {
                'method': 'DELETE',
                'path': notification_id_path,
                'callback': self._delete_notification,
            },
        ]

    def _create_listener(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        rt = self._listener_coll.get_type()
        validator = qvarn.Validator()
        try:
            validator.validate_against_prototype(
                rt.get_type(), body, rt.get_latest_prototype())
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        if 'type' not in body:
            body['type'] = 'listener'

        rtype = self._parent_coll.get_type_name()
        if body.get('listen_on_type', rtype) != rtype:
            return qvarn.bad_request_response(
                'listen_on_type does not have value {}'.format(rtype))
        body['listen_on_type'] = rtype

        id_allowed = self._api.is_id_allowed(kwargs.get('claims', {}))
        if id_allowed:
            result_body = self._listener_coll.post_with_id(body)
        else:
            result_body = self._listener_coll.post(body)
        location = self._get_new_resource_location(result_body)
        qvarn.log.log(
            'debug', msg_text='POST a new listener, result',
            body=result_body, location=location)
        return qvarn.created_response(result_body, location)

    def _get_new_resource_location(self, resource):
        return '{}{}/listeners/{}'.format(
            self._baseurl, self._parent_coll.get_type().get_path(),
            resource['id'])

    def _get_listener_list(self, content_type, body, *args, **kwargs):
        rtype = self._parent_coll.get_type_name()
        listener_list = self._listener_coll.list()['resources']
        listener_ids = [listener['id'] for listener in listener_list]
        listeners = [self._listener_coll.get(lid) for lid in listener_ids]
        qvarn.log.log('trace', msg_text='xxx', listeners=listeners)
        correct_ids = [
            {"id": listener['id']}
            for listener in listeners
            if listener['listen_on_type'] == rtype
        ]
        body = {
            'resources': correct_ids,
        }
        return qvarn.ok_response(body)

    def _get_a_listener(self, *args, **kwargs):
        try:
            obj = self._listener_coll.get(kwargs['listener_id'])
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))
        return qvarn.ok_response(obj)

    def _update_listener(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        if 'type' not in body:
            body['type'] = 'listener'

        listener_id = kwargs['listener_id']
        if 'id' not in body:
            body['id'] = listener_id

        validator = qvarn.Validator()
        try:
            validator.validate_resource_update(
                body, self._listener_coll.get_type())
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        try:
            result_body = self._listener_coll.put(body)
        except qvarn.WrongRevision as e:
            return qvarn.conflict_response(str(e))
        except qvarn.NoSuchResource as e:
            # We intentionally say bad request, instead of not found.
            # This is to be compatible with old Qvarn. This may get
            # changed later.
            return qvarn.bad_request_response(str(e))

        return qvarn.ok_response(result_body)

    def _delete_listener(self, *args, **kwargs):
        listener_id = kwargs['listener_id']
        self._listener_coll.delete(listener_id)
        for obj_id in self._find_notifications(listener_id):
            self._store.remove_objects(obj_id=obj_id)
        return qvarn.ok_response({})

    def _find_notifications(self, listener_id):
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

    def _get_notifications_list(self, *args, **kwargs):
        def timestamp(pair):
            _, obj = pair
            return obj['timestamp']

        listener_id = kwargs['listener_id']
        cond = qvarn.All(
            qvarn.Equal('type', 'notification'),
            qvarn.Equal('listener_id', listener_id)
        )
        pairs = self._store.find_objects(cond)
        ordered = sorted(pairs, key=timestamp)
        body = {
            'resources': [
                {
                    'id': keys['obj_id']
                }
                for keys, _ in ordered
            ]
        }
        return qvarn.ok_response(body)

    def _get_a_notification(self, *args, **kwargs):
        listener_id = kwargs['listener_id']
        notification_id = kwargs['notification_id']
        cond = qvarn.All(
            qvarn.Equal('type', 'notification'),
            qvarn.Equal('listener_id', listener_id),
            qvarn.Equal('id', notification_id),
        )
        pairs = self._store.find_objects(cond)
        if not pairs:
            return qvarn.no_such_resource_response(notification_id)
        if len(pairs) > 1:
            raise qvarn.TooManyResources(notification_id)
        return qvarn.ok_response(pairs[0][1])

    def _create_a_notification(self, content_type, body, *args, **kwargs):
        claims = kwargs['claims']
        is_allowed = self._api.is_id_allowed(claims)

        if not is_allowed:
            return qvarn.forbidden_request_resonse('Not for you')

        notif = dict(body)
        assert 'id' in notif
        assert 'listener_id' in notif
        assert 'revision' in notif
        self._api.create_notification(notif)

        return qvarn.created_response(notif, '')

    def _delete_notification(self, *args, **kwargs):
        listener_id = kwargs['listener_id']
        notification_id = kwargs['notification_id']
        cond = qvarn.All(
            qvarn.Equal('type', 'notification'),
            qvarn.Equal('listener_id', listener_id),
            qvarn.Equal('id', notification_id),
        )
        for keys, _ in self._store.find_objects(cond):
            values = {
                key: keys[key]
                for key in keys
                if isinstance(keys[key], str)
            }
            self._store.remove_objects(**values)
        return qvarn.ok_response({})
