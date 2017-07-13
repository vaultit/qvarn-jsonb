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


import logging
import re
import time


import bottle
import Crypto.PublicKey.RSA
import jwt


import apifw


class BottleLoggingPlugin(apifw.HttpTransaction):

    # This a binding between Bottle and apifw.HttpTransaction, as a
    # Bottle plugin. We arrange the perform_transaction method to be
    # called with the right arguments, in particular the callback
    # function to call. We also provide Bottle specific methods to log
    # the HTTP request and response, and to amend the response by
    # adding a Date header.

    def apply(self, callback, route):

        def wrapper(*args, **kwargs):
            return self.perform_transaction(callback, *args, **kwargs)

        return wrapper

    def amend_response(self):
        rfc822 = time.strftime('%a, %d %b %Y %H:%M:%S %z')
        bottle.response.set_header('Date', rfc822)

    def construct_request_log(self):
        r = bottle.request
        return {
            'method': r.method,
            'path': r.path,
        }

    def construct_response_log(self):
        r = bottle.response
        return {
            'status': r.status_code,
            'text': r.body,
        }


class BottleAuthorizationPlugin(object):

    route_pat = re.compile(r'<[^>]*>')

    def __init__(self):
        self.pubkey = None
        self.iss = None
        self.aud = None

    def set_token_signing_public_key(self, pubkey):
        self.pubkey = Crypto.PublicKey.RSA.importKey(pubkey)

    def set_expected_issuer(self, iss):
        self.iss = iss

    def set_expected_audience(self, aud):
        self.aud = aud

    def apply(self, callback, route):

        def wrapper(*args, **kwargs):
            if self.is_authorized(route):
                return callback(*args, **kwargs)

            headers = {
                'WWW-Authenticate': 'Bearer',
            }
            raise bottle.HTTPError(401, headers=headers)

        return wrapper

    def is_authorized(self, route):
        value = bottle.request.get_header('Authorization', '')
        if not value:
            raise bottle.HTTPError(400, body='No Authorization header')
        words = value.split()
        if len(words) != 2:
            raise bottle.HTTPError(
                400, body='Authorization should be "Bearer TOKEN"')
        if words[0].lower() != 'bearer':
            raise bottle.HTTPError(
                400, body='Authorization should be "Bearer TOKEN"')

        try:
            claims = apifw.decode_token(
                words[1], self.pubkey, audience=self.aud)
        except jwt.InvalidTokenError as e:
            raise bottle.HTTPError(400, body=str(e))

        if claims['iss'] != self.iss:
            raise bottle.HTTPError(
                400,
                body='Expected issuer %s, got %s' % (self.iss, claims['iss']))

        return self.scope_allows_route(claims['scope'], route)

    def scope_allows_route(self, claim_scopes, route):
        scopes = claim_scopes.split(' ')
        route_scope = self.get_scope_for_route(route['method'], route['rule'])
        return route_scope in scopes

    def get_scope_for_route(self, method, rule):
        scope = re.sub(self.route_pat, 'id', rule)
        scope = scope.replace('/', '_')
        scope = 'uapi%s_%s' % (scope, method)
        return scope.lower()


class BottleApplication(object):

    # Provide the interface to bottle.Bottle that we need.
    # Specifically, we set up a hook to call the
    # Api.find_missing_route method when a request would otherwise
    # return 404, and we add the routes it returns to Bottle so that
    # they are there for this and future requests.

    def __init__(self, bottleapp, api):
        self._bottleapp = bottleapp
        self._bottleapp.add_hook('before_request', self._add_missing_route)
        self._api = api

    def add_plugin(self, plugin):
        self._bottleapp.install(plugin)

    def _add_missing_route(self):
        try:
            self._bottleapp.match(bottle.request.environ)
        except bottle.HTTPError:
            routes = self._api.find_missing_route(bottle.request.path)
            if routes:
                for route in routes:
                    route_dict = {
                        'method': route.get('method', 'GET'),
                        'path': route['path'],
                        'callback': route['callback'],
                    }
                    logging.info('adding route: %r', route_dict)
                    self._bottleapp.route(**route_dict)
            else:
                raise


def create_bottle_application(api, logger, config):
    # Create a new bottle.Bottle application, set it up, and return it
    # so that gunicorn can execute it from the main program.

    bottleapp = bottle.Bottle()
    app = BottleApplication(bottleapp, api)

    plugin = BottleLoggingPlugin()
    if logger:
        plugin.set_dict_logger(logger)
    app.add_plugin(plugin)

    authz = BottleAuthorizationPlugin()
    authz.set_token_signing_public_key(config['token-public-key'])
    authz.set_expected_issuer(config['token-issuer'])
    authz.set_expected_audience(config['token-audience'])
    app.add_plugin(authz)

    return bottleapp
