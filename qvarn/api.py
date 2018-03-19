# Copyright (C) 2017  Lars Wirzenius
# Copyright (C) 2018  Ivan Dolgov
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


import re
import jwt

import qvarn


class QvarnAPI:

    def __init__(self):
        self._store = None
        self._validator = qvarn.Validator()
        self._baseurl = None
        self._rt_coll = None
        self._notifs = None
        self._alog = None

    def set_base_url(self, baseurl):  # pragma: no cover
        self._baseurl = baseurl

    def set_object_store(self, store):
        self._store = store
        self._store.create_store(obj_id=str, subpath=str)

    def add_resource_type(self, rt):
        path = rt.get_path()
        keys = {
            'obj_id': rt.get_type(),
            'subpath': '',
        }
        self._store.remove_objects(**keys)

        obj = {
            'id': rt.get_type(),
            'type': 'resource_type',
            'path': path,
            'spec': rt.as_dict(),
        }
        self._store.create_object(obj, **keys, auxtable=True)

    def get_resource_type(self, path):
        path = self._canonical_path(path)
        objs = self._get_resource_type_given_path(path)
        if not objs:
            qvarn.log.log(
                'error',
                msg_text='There is no resource type for path',
                path=path)
            raise qvarn.NoSuchResourceType(path)
        # This is disabled until we solve the problem of having multiple
        # Qvarn instances creating the same resource types at startup
        # (or, later, via the API).
        # elif len(objs) > 1:  # pragma: no cover
        #     qvarn.log.log(
        #         'error',
        #         msg_text='There are more than one resource types for path',
        #         path=path,
        #         objs=objs)
        #     raise qvarn.TooManyResourceTypes(path)
        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def _canonical_path(self, path):  # pragma: no cover
        parts = path.split('/')
        if not path.startswith('/') or not parts:
            return path
        return '/{}'.format(parts[1])

    def _get_resource_type_given_path(self, path):
        cond = qvarn.All(
            qvarn.Equal('path', path),
            qvarn.Equal('type', 'resource_type'),
        )
        results = self._store.get_matches(cond=cond)
        qvarn.log.log(
            'trace', msg_text='_get_resource_type_given_path',
            results=results, path=path)
        return [obj for _, obj in results]

    def get_listener_resource_type(self):
        return self._get_resource_type_given_type('listener')

    def get_notification_resource_type(self):  # pragma: no cover
        return self._get_resource_type_given_type('notification')

    def get_access_log_resource_type(self):  # pragma: no cover
        return self._get_resource_type_given_type('access')

    def _get_resource_type_given_type(self, type_name):
        cond = qvarn.All(
            qvarn.Equal('id', type_name),
            qvarn.Equal('type', 'resource_type'),
        )
        results = self._store.get_matches(cond=cond)
        qvarn.log.log(
            'trace', msg_text='_get_resource_type_given_type',
            results=results, type_name=type_name)
        objs = [obj for _, obj in results]

        if not objs:  # pragma: no cover
            raise qvarn.NoSuchResourceType(type_name)
        elif len(objs) > 1:  # pragma: no cover
            raise qvarn.TooManyResourceTypes(type_name)

        rt = qvarn.ResourceType()
        rt.from_spec(objs[0]['spec'])
        return rt

    def find_missing_route(self, path):
        qvarn.log.log('info', msg_text='find_missing_route', path=path)

        if path == '/version':
            qvarn.log.log('info', msg_text='Add /version route')
            v = qvarn.VersionRouter()
            return v.get_routes()

        if path == '/allow':
            qvarn.log.log('info', msg_text='Add /allow route')
            a = qvarn.AllowRouter()
            a.set_store(self._store)
            return a.get_routes()

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
        router.set_api(self)
        router.set_baseurl(self._baseurl)
        router.set_collection(coll)
        router.set_notifier(self.notify)
        router.set_access_logger(self.log_access)
        routes = router.get_routes()

        files = rt.get_files()
        for subpath in rt.get_subpaths():
            if subpath not in files:
                sub_router = qvarn.SubresourceRouter()
                sub_router.set_api(self)
                sub_router.set_subpath(subpath)
                sub_router.set_parent_collection(coll)
                more = sub_router.get_routes()
            else:
                file_router = qvarn.FileRouter()
                file_router.set_api(self)
                file_router.set_subpath(subpath)
                file_router.set_object_store(self._store)
                file_router.set_parent_collection(coll)
                more = file_router.get_routes()
            routes.extend(more)

        listener_rt = self.get_listener_resource_type()
        notif_router = qvarn.NotificationRouter()
        notif_router.set_api(self)
        notif_router.set_baseurl(self._baseurl)
        notif_router.set_parent_collection(coll)
        notif_router.set_object_store(self._store, listener_rt)
        routes.extend(notif_router.get_routes())

        return routes

    def is_id_allowed(self, claims):
        scopes = claims.get('scope', '').split()
        return 'uapi_set_meta_fields' in scopes

    def notify(self, rid, rrev, change):  # pragma: no cover
        obj = {
            'type': 'notification',
            'resource_id': rid,
            'resource_revision': rrev,
            'resource_change': change,
            'timestamp': qvarn.get_current_timestamp(),
        }
        for listener in self.find_listeners(rid, change):
            obj['listener_id'] = listener['id']
            self.create_notification(obj)

    def create_notification(self, notif):  # pragma: no cover
        qvarn.log.log(
            'info', msg_text='Create notification',
            notification=notif)
        notifs = self._create_notifs_collection()
        notifs.post_with_id(notif)

    def _create_notifs_collection(self):  # pragma: no cover
        if self._notifs is None:
            rt = self.get_notification_resource_type()
            self._notifs = qvarn.CollectionAPI()
            self._notifs.set_object_store(self._store)
            self._notifs.set_resource_type(rt)
        return self._notifs

    def find_listeners(self, rid, change):  # pragma: no cover
        cond = qvarn.Equal('type', 'listener')
        pairs = self._store.get_matches(cond)
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

    def log_access(self, res, rtype, op,
                   ahead, qhead, ohead, whead):  # pragma: no cover
        if rtype in [
                'access', 'notification', 'listener', 'resource_type']:
            return

        token_headers = ahead
        if qhead:
            token_headers = ', '.join([ahead, qhead])
        encoded_tokens = re.split(r'(?:\A|,\s*)Bearer ', token_headers)[1:]
        tokens = [jwt.decode(t, verify=False) for t in encoded_tokens]
        persons = [
            {
                'accessor_id': t['sub'],
                'accessor_type': 'person',
            }
            for t in tokens]
        clients = [
            {
                'accessor_id': t['aud'],
                'accessor_type': 'client',
            }
            for t in tokens]
        orgs = [
            {
                'accessor_id': t,
                'accessor_type': 'org',
            }
            for t in re.findall(r',?\s*Org (.+?)(?:,|\Z)', ohead) if t]
        others = [
            {
                'accessor_id': t,
                'accessor_type': 'other',
            }
            for t in re.findall(r',?\s*Other (.+?)(?:,|\Z)', ohead) if t]

        self.create_access_entry(
            {
                'type': 'access',
                'resource_type': rtype,
                'resource_id': res.get('id'),
                'resource_revision': res.get('revision'),
                'operation': op,
                'accessors': [*persons, *clients, *orgs, *others],
                'why': whead,
                'timestamp': qvarn.get_current_timestamp(),
            })

    def create_access_entry(self, entry):  # pragma: no cover
        qvarn.log.log('info', msg_text='Log access', access_entry=entry)
        alog = self._create_alog_collection()
        alog.post_with_id(entry)

    def _create_alog_collection(self):  # pragma: no cover
        if self._alog is None:
            rt = self.get_access_log_resource_type()
            self._alog = qvarn.CollectionAPI()
            self._alog.set_object_store(self._store)
            self._alog.set_resource_type(rt)
        return self._alog
