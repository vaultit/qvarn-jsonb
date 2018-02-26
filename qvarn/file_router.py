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


class FileRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._api = None
        self._store = None
        self._parent_coll = None
        self._subpath = None

    def set_api(self, api):
        self._api = api

    def set_subpath(self, subpath):
        self._subpath = subpath

    def set_parent_collection(self, parent_coll):
        self._parent_coll = parent_coll

    def set_object_store(self, store):
        self._store = store

    def get_routes(self):
        rt = self._parent_coll.get_type()
        file_path = '{}/<id>/{}'.format(rt.get_path(), self._subpath)
        return [
            {
                'method': 'GET',
                'path': file_path,
                'callback': self._get_file,
            },
            {
                'method': 'PUT',
                'path': file_path,
                'callback': self._put_file,
            },
        ]

    def _get_file(self, *args, **kwargs):
        qvarn.log.log('trace', msg_text='_get_file', kwargs=kwargs)
        claims = kwargs.get('claims')
        assert claims is not None
        params = self.get_access_params(
            self._parent_coll.get_type_name(), claims)

        obj_id = kwargs['id']
        try:
            obj = self._parent_coll.get(
                obj_id, claims=claims, access_params=params)
            sub_obj = self._parent_coll.get_subresource(
                obj_id, self._subpath, claims=claims, access_params=params)
            blob = self._store.get_blob(obj_id=obj_id, subpath=self._subpath)
        except (qvarn.NoSuchResource, qvarn.NoSuchObject) as e:
            return qvarn.no_such_resource_response(str(e))
        headers = {
            'Content-Type': sub_obj['content_type'],
            'Revision': obj['revision'],
        }
        return qvarn.ok_response(blob, headers)

    def _put_file(self, content_type, body, *args, **kwargs):
        claims = kwargs.get('claims')
        params = self.get_access_params(
            self._parent_coll.get_type_name(), claims)

        obj_id = kwargs['id']

        # FIXME: add header getting to apifw
        import bottle
        revision = bottle.request.get_header('Revision')

        id_allowed = self._api.is_id_allowed(kwargs.get('claims', {}))

        obj = self._parent_coll.get(obj_id, allow_cond=qvarn.Yes())
        if not id_allowed and obj['revision'] != revision:
            qvarn.log.log(
                'error',
                msg_text='Client gave wrong revision',
                revision_from_client=revision,
                current_revision=obj['revision'])
            return qvarn.conflict_response(
                'Bad revision {}'.format(revision))

        sub_obj = self._parent_coll.get_subresource(
            obj_id, self._subpath, allow_cond=qvarn.Yes())
        sub_obj['content_type'] = content_type
        qvarn.log.log(
            'trace', msg_text='_put_file', claims=claims,
            access_params=params)
        if id_allowed:
            new_sub = self._parent_coll.put_subresource_no_revision(
                sub_obj, subpath=self._subpath, obj_id=obj_id,
                revision=revision, claims=claims, access_params=params)
        else:
            new_sub = self._parent_coll.put_subresource(
                sub_obj, subpath=self._subpath, obj_id=obj_id,
                revision=revision, claims=claims, access_params=params)

        try:
            self._store.remove_blob(obj_id=obj_id, subpath=self._subpath)
            self._store.create_blob(body, obj_id=obj_id, subpath=self._subpath)
        except qvarn.NoSuchObject as e:
            return qvarn.no_such_resource_response(str(e))

        headers = {
            'Revision': new_sub['revision'],
        }
        return qvarn.ok_response('', headers)
