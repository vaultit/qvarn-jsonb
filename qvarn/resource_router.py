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


class ResourceRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._coll = None
        self._baseurl = None
        self._notify = None

    def set_baseurl(self, baseurl):
        self._baseurl = baseurl

    def set_collection(self, coll):
        self._coll = coll

    def set_notifier(self, notify):
        self._notify = notify

    def get_routes(self):
        assert self._baseurl is not None

        rt = self._coll.get_type()
        path = rt.get_path()
        id_path = '{}/<id>'.format(path)

        return [
            {
                'method': 'POST',
                'path': path,
                'callback': self._create,
            },
            {
                'method': 'PUT',
                'path': id_path,
                'callback': self._update,
            },
            {
                'method': 'GET',
                'path': path,
                'callback': self._list,
            },
            {
                'method': 'GET',
                'path': id_path,
                'callback': self._get,
            },
            {
                'method': 'GET',
                'path': path + '/search/<search_criteria:path>',
                'callback': self._search,
            },
            {
                'method': 'DELETE',
                'path': id_path,
                'callback': self._delete,
            },
        ]

    def _create(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        if 'type' not in body:
            body['type'] = self._coll.get_type_name()

        validator = qvarn.Validator()
        try:
            validator.validate_new_resource(body, self._coll.get_type())
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        result_body = self._coll.post(body)
        qvarn.log.log(
            'debug', msg_text='POST a new resource, result',
            body=result_body)
        location = '{}{}/{}'.format(
            self._baseurl, self._coll.get_type().get_path(), result_body['id'])
        self._notify(result_body['id'], result_body['revision'], 'created')
        return qvarn.created_response(result_body, location)

    def _update(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        if 'type' not in body:
            body['type'] = self._coll.get_type_name()

        if 'id' not in body:
            body['id'] = kwargs['id']

        validator = qvarn.Validator()
        try:
            validator.validate_resource_update(body, self._coll.get_type())
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        obj_id = kwargs['id']
        # FIXME: the following test should be enabled once we
        # no longer need test-api.
        if False and body['id'] != obj_id:
            raise qvarn.IdMismatch(body['id'], obj_id)

        try:
            result_body = self._coll.put(body)
        except qvarn.WrongRevision as e:
            return qvarn.conflict_response(str(e))
        except qvarn.NoSuchResource as e:
            # We intentionally say bad request, instead of not found.
            # This is to be compatible with old Qvarn. This may get
            # changed later.
            return qvarn.bad_request_response(str(e))

        self._notify(result_body['id'], result_body['revision'], 'updated')
        return qvarn.ok_response(result_body)

    def _list(self, *args, **kwargs):
        body = self._coll.list()
        return qvarn.ok_response(body)

    def _get(self, *args, **kwargs):
        try:
            obj = self._coll.get(kwargs['id'])
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))
        return qvarn.ok_response(obj)

    def _search(self, *args, **kwargs):
        path = kwargs['raw_uri_path']
        search_criteria = path.split('/search/', 1)[1]
        try:
            result = self._coll.search(search_criteria)
        except qvarn.UnknownSearchField as e:
            return qvarn.unknown_search_field_response(e)
        except qvarn.NeedSortOperator:
            return qvarn.need_sort_response()
        except qvarn.SearchParserError as e:
            return qvarn.search_parser_error_response(e)
        body = {
            'resources': result,
        }
        return qvarn.ok_response(body)

    def _delete(self, *args, **kwargs):
        obj_id = kwargs['id']
        self._coll.delete(obj_id)
        self._notify(obj_id, None, 'deleted')
        return qvarn.ok_response({})
