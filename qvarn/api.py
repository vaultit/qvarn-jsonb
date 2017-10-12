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

import yaml

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
            raise qvarn.NoSuchResourceType(path)
        elif len(objs) > 1:  # pragma: no cover
            qvarn.log.log(
                'error',
                msg_text='There are more than one resource types for path',
                path=path,
                objs=objs)
            raise qvarn.TooManyResourceTypes(path)
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
            raise qvarn.NoSuchResourceType('listener')
        elif len(objs) > 1:  # pragma: no cover
            raise qvarn.TooManyResourceTypes('listener')
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
            raise qvarn.NoSuchResourceType('listener')
        elif len(objs) > 1:  # pragma: no cover
            raise qvarn.TooManyResourceTypes('listener')
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def find_missing_route(self, path):
        qvarn.log.log('info', msg_text='find_missing_route', path=path)

        if path == '/version':
            qvarn.log.log('info', msg_text='Add /version route')
            v = qvarn.VersionRouter()
            return v.get_routes()

        try:
            rt = self.get_resource_type(path)
        except qvarn.NoSuchResourceType:
            qvarn.log.log('warning', msg_text='No such route', path=path)
            return []

        routes = self.resource_routes(path, rt)
        qvarn.log.log('info', msg_text='Found missing routes', routes=routes)
        return routes

    def resource_routes(self, path, rt):  # pragma: no cover
        coll = qvarn.CollectionAPI()
        coll.set_object_store(self._store)
        coll.set_resource_type(rt)

        router = qvarn.ResourceRouter()
        router.set_collection(coll)
        router.set_notifier(self.notify)
        routes = router.get_routes()

        files = rt.get_files()
        for subpath in rt.get_subpaths():
            if subpath not in files:
                sub_router = qvarn.SubresourceRouter()
                sub_router.set_subpath(subpath)
                sub_router.set_parent_collection(coll)
                more = sub_router.get_routes()
            else:
                file_router = qvarn.FileRouter()
                file_router.set_subpath(subpath)
                file_router.set_object_store(self._store)
                file_router.set_parent_collection(coll)
                more = file_router.get_routes()
            routes.extend(more)

        listener_rt = self.get_listener_resource_type()
        notif_router = qvarn.NotificationRouter()
        notif_router.set_baseurl(self._baseurl)
        notif_router.set_parent_collection(coll)
        notif_router.set_object_store(self._store, listener_rt)
        routes.extend(notif_router.get_routes())

        return routes

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
            'timestamp': qvarn.get_current_timestamp(),
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
