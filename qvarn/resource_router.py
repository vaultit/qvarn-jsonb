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


# FIXME: remove when redundant
import bottle

import qvarn


class ResourceRouter(qvarn.Router):

    def __init__(self):
        super().__init__()
        self._api = None
        self._coll = None
        self._baseurl = None
        self._notify = None
        self._log_access = None

    def set_api(self, api):
        self._api = api

    def set_baseurl(self, baseurl):
        self._baseurl = baseurl

    def set_collection(self, coll):
        self._coll = coll

    def set_notifier(self, notify):
        self._notify = notify

    def set_access_logger(self, log_access):
        self._log_access = log_access

    def get_routes(self):
        assert self._baseurl is not None

        rt = self._coll.get_type()
        path = rt.get_path()
        id_path = '{}/<id>'.format(path)

        def S(callback, msg, **kwargs):
            return qvarn.stopwatch(callback, msg, **kwargs)

        routes = [
            {
                'method': 'GET',
                'path': path,
                'callback': S(self._list, 'LIST'),
            },
            {
                'method': 'GET',
                'path': id_path,
                'callback': S(self._get, 'GET'),
            },
            {
                'method': 'GET',
                'path': path + '/search/<search_criteria:path>',
                'callback': S(self._search, 'SEARCH'),
            },
            {
                'method': 'DELETE',
                'path': id_path,
                'callback': S(self._delete, 'DELETE'),
            },
        ]

        if self._coll.get_type_name() not in ['access']:
            routes += [
                {
                    'method': 'POST',
                    'path': path,
                    'callback': S(self._create, 'POST'),
                },
                {
                    'method': 'PUT',
                    'path': id_path,
                    'callback': S(self._update, 'PUT'),
                },
            ]

        return routes

    def _get_access_params(self, claims):
        return {
            'method': bottle.request.method,
            'client_id': claims['aud'],
            'user_id': claims['sub'],
            'resource_type': self._coll.get_type_name(),
        }

    def _create(self, content_type, body, *args, **kwargs):
        if content_type != 'application/json':
            raise qvarn.NotJson(content_type)

        if 'type' not in body:
            body['type'] = self._coll.get_type_name()

        id_allowed = self._api.is_id_allowed(kwargs.get('claims', {}))

        validator = qvarn.Validator()
        try:
            if id_allowed:
                validator.validate_new_resource_with_id(
                    body, self._coll.get_type())
            else:
                validator.validate_new_resource(
                    body, self._coll.get_type())
        except (qvarn.HasId, qvarn.HasRevision) as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))
        except qvarn.ValidationError as e:
            qvarn.log.log('error', msg_text=str(e), body=body)
            return qvarn.bad_request_response(str(e))

        result_body = self._coll.post_with_id(body)
        location = '{}{}/{}'.format(
            self._baseurl, self._coll.get_type().get_path(),
            result_body['id'])

        self._notify(result_body['id'], result_body['revision'], 'created')
        self._log_access(
            result_body,
            result_body.get('type'),
            'POST',
            # FIXME: add header getting to apifw
            bottle.request.get_header('Authorization', ''),
            bottle.request.get_header('Qvarn-Token', ''),
            bottle.request.get_header('Qvarn-Access-By', ''),
            bottle.request.get_header('Qvarn-Why', None))

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
        self._log_access(
            result_body,
            result_body.get('type'),
            'PUT',
            # FIXME: add header getting to apifw
            bottle.request.get_header('Authorization', ''),
            bottle.request.get_header('Qvarn-Token', ''),
            bottle.request.get_header('Qvarn-Access-By', ''),
            bottle.request.get_header('Qvarn-Why', None))

        return qvarn.ok_response(result_body)

    def _list(self, *args, **kwargs):
        claims = kwargs.get('claims')
        params = self._get_access_params(claims)
        body = self._coll.list(claims=claims, access_params=params)

        for obj in body.get('resources', []):
            self._log_access(
                obj,
                self._coll.get_type_name(),
                'GET',
                # FIXME: add header getting to apifw
                bottle.request.get_header('Authorization', ''),
                bottle.request.get_header('Qvarn-Token', ''),
                bottle.request.get_header('Qvarn-Access-By', ''),
                bottle.request.get_header('Qvarn-Why', None))

        return qvarn.ok_response(body)

    def _get(self, *args, **kwargs):
        claims = kwargs.get('claims')
        params = self._get_access_params(claims)

        try:
            obj = self._coll.get(
                kwargs['id'], claims=claims, access_params=params)
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))

        self._log_access(
            obj,
            obj.get('type'),
            'GET',
            # FIXME: add header getting to apifw
            bottle.request.get_header('Authorization', ''),
            bottle.request.get_header('Qvarn-Token', ''),
            bottle.request.get_header('Qvarn-Access-By', ''),
            bottle.request.get_header('Qvarn-Why', None))

        return qvarn.ok_response(obj)

    def _search(self, *args, **kwargs):
        claims = kwargs.get('claims')
        params = self._get_access_params(claims)

        path = kwargs['raw_uri_path']
        search_criteria = path.split('/search/', 1)[1]
        try:
            result = self._coll.search(
                search_criteria, claims=claims, access_params=params)
        except qvarn.UnknownSearchField as e:
            return qvarn.unknown_search_field_response(e)
        except qvarn.NeedSortOperator:
            return qvarn.need_sort_response()
        except qvarn.SearchParserError as e:
            return qvarn.search_parser_error_response(e)

        for obj in result:
            self._log_access(
                obj,
                self._coll.get_type_name(),
                'SEARCH',
                # FIXME: add header getting to apifw
                bottle.request.get_header('Authorization', ''),
                bottle.request.get_header('Qvarn-Token', ''),
                bottle.request.get_header('Qvarn-Access-By', ''),
                bottle.request.get_header('Qvarn-Why', None))

        return qvarn.ok_response({'resources': result})

    def _delete(self, *args, **kwargs):
        claims = kwargs.get('claims')
        params = self._get_access_params(claims)
        qvarn.log.log(
            'trace', msg_text='_delete callback', claims=claims, params=params)

        obj_id = kwargs['id']
        try:
            self._coll.delete(obj_id, claims=claims, access_params=params)
        except qvarn.NoSuchResource as e:
            return qvarn.no_such_resource_response(str(e))

        self._notify(obj_id, None, 'deleted')
        self._log_access(
            {'id': obj_id},
            self._coll.get_type_name(),
            'DELETE',
            # FIXME: add header getting to apifw
            bottle.request.get_header('Authorization', ''),
            bottle.request.get_header('Qvarn-Token', ''),
            bottle.request.get_header('Qvarn-Access-By', ''),
            bottle.request.get_header('Qvarn-Why', None))

        return qvarn.ok_response({})
