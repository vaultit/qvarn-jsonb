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


class SubresourceRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._parent_coll = None
        self._subpath = None

    def set_subpath(self, subpath):
        self._subpath = subpath

    def set_parent_collection(self, parent_coll):
        self._parent_coll = parent_coll

    def get_routes(self):
        rt = self._parent_coll.get_type()
        path = '{}/<id>/{}'.format(rt.get_path(), self._subpath)
        return [
            {
                'method': 'GET',
                'path': path,
                'callback': self._get_subresource,
            },
            {
                'method': 'PUT',
                'path': path,
                'callback': self._put_subresource,
            },
        ]

    def _get_subresource(self, *args, **kwargs):
        obj_id = kwargs['id']
        try:
            obj = self._parent_coll.get_subresource(obj_id, self._subpath)
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))
        return qvarn.ok_response(obj)

    def _put_subresource(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        obj_id = kwargs['id']
        if 'revision' not in body:
            return qvarn.bad_request_response('must have revision')
        revision = body.pop('revision')

        rt = self._parent_coll.get_type()
        validator = qvarn.Validator()
        try:
            validator.validate_subresource(self._subpath, rt, body)
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        try:
            result_body = self._parent_coll.put_subresource(
                body, subpath=self._subpath, obj_id=obj_id, revision=revision)
        except qvarn.WrongRevision as e:
            return qvarn.conflict_response(str(e))
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))

        return qvarn.ok_response(result_body)
