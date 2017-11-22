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


import apifw


def response(status, body, headers):
    return apifw.Response(
        {
            'status': status,
            'body': body,
            'headers': headers,
        }
    )


def ok_response(body, headers=None):
    if headers is None:
        headers = {}
    if 'Content-Type' not in headers:
        headers.update({
            'Content-Type': 'application/json',
        })
    return response(apifw.HTTP_OK, body, headers)


def no_such_resource_response(msg):
    return response(apifw.HTTP_NOT_FOUND, msg, {})


def created_response(body, location):
    headers = {
        'Content-Type': 'application/json',
        'Location': location,
    }
    return response(apifw.HTTP_CREATED, body, headers)


def bad_request_response(body):
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def forbidden_request_response(body):
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_FORBIDDEN, body, headers)


def need_sort_response():
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'message': 'LIMIT and OFFSET can only be used with together SORT.',
        'error_code': 'LimitWithoutSortError',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def search_parser_error_response(e):
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'message': 'Could not parse search condition',
        'error_code': 'BadSearchCondition',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def unknown_search_field_response(e):
    headers = {
        'Content-Type': 'application/json',
    }
    body = {
        'field': e.field,
        'message': 'Resource does not contain given field',
        'error_code': 'FieldNotInResource',
    }
    return response(apifw.HTTP_BAD_REQUEST, body, headers)


def conflict_response(body):
    headers = {
        'Content-Type': 'text/plain',
    }
    return response(apifw.HTTP_CONFLICT, body, headers)
