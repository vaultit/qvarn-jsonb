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


import bottle
import jwt

import qvarn


class Router:

    def __init__(self):
        pass

    def get_routes(self):
        raise NotImplementedError()

    def get_access_params(self, type_name, claims):
        user_id = claims.get('sub')
        if not user_id and self.is_trusted_client(claims):
            user_id = self.get_user_id_from_headers()
            qvarn.log.log(
                'trace', msg_text='user_id from headers', user_id=user_id)

        params = {
            'method': bottle.request.method,
            'client_id': claims['aud'],
            'user_id': user_id,
            'resource_type': type_name,
        }
        qvarn.log.log(
            'trace', msg_text='get_access_params', params=params,
            claims=claims, user_id=user_id)
        return params

    def is_trusted_client(self, claims):
        scopes = claims.get('scope', '').split()
        is_trusted = 'uapi_trusted_client' in scopes
        qvarn.log.log(
            'trace', msg_text='is trusted?', scopes=scopes,
            is_trusted=is_trusted)
        return is_trusted

    def get_user_id_from_headers(self):
        headers = bottle.request.headers
        qvarn.log.log(
            'trace', msg_text='access params headers',
            headers=dict(headers))
        token = headers.get('Qvarn-Access-By')
        qvarn.log.log(
            'trace', msg_text='Qvarn-Access-By token',
            token=token)
        if token:
            c = self.parse_token(token)
            return c.get('sub', '')
        return ''

    def parse_token(self, token):
        return jwt.decode(
            token,
            verify=False,
            audience=None, options={'verify_aud': False}
        )
