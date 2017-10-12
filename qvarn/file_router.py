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
        self._store = None
        self._parent_coll = None
        self._subpath = None

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
        obj_id = kwargs['id']
        try:
            obj = self._parent_coll.get(obj_id)
            sub_obj = self._parent_coll.get_subresource(obj_id, self._subpath)
            blob = self._store.get_blob(obj_id=obj_id, subpath=self._subpath)
        except (qvarn.NoSuchResource, qvarn.NoSuchObject) as e:
            return qvarn.no_such_resource_response(str(e))
        headers = {
            'Content-Type': sub_obj['content_type'],
            'Revision': obj['revision'],
        }
        return qvarn.ok_response(blob, headers)

    def _put_file(self, content_type, body, *args, **kwargs):
        obj_id = kwargs['id']

        # FIXME: add header getting to apifw
        import bottle
        revision = bottle.request.get_header('Revision')

        obj = self._parent_coll.get(obj_id)
        if obj['revision'] != revision:
            qvarn.log.log(
                'error',
                msg_text='Client gave wrong revision',
                revision_from_client=revision,
                current_revision=obj['revision'])
            return qvarn.conflict_response(
                'Bad revision {}'.format(revision))

        sub_obj = self._parent_coll.get_subresource(obj_id, self._subpath)
        sub_obj['content_type'] = content_type
        new_sub = self._parent_coll.put_subresource(
            sub_obj, subpath=self._subpath, obj_id=obj_id, revision=revision)

        try:
            self._store.remove_blob(obj_id=obj_id, subpath=self._subpath)
            self._store.create_blob(body, obj_id=obj_id, subpath=self._subpath)
        except qvarn.NoSuchObject as e:
            return qvarn.no_such_resource_response(str(e))

        headers = {
            'Revision': new_sub['revision'],
        }
        return qvarn.ok_response('', headers)
