# Copyright 2017  Lars Wirzenius
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


import configparser
import logging
import time


import cliapp
import requests


import qvarnutils


def create_api(url, secrets_filename, token):
    api = QvarnAPI()
    api.set_api_url(url)
    if token:
        api.set_token(token, None)
    else:
        api.lookup_credentials(secrets_filename)
    return api


class QvarnAPI:

    def __init__(self):
        self._api_url = None
        self._client_id = None
        self._client_secret = None
        self._token = None
        self._token_created = None
        self._token_rt = None
        self._session = requests.Session()

    def set_api_url(self, api_url):
        self._api_url = api_url

    def set_token(self, token, rt):
        self._token = token
        self._token_created = time.time()
        self._token_rt = rt

    def lookup_credentials(self, filename):
        cp = configparser.ConfigParser()
        cp.read(filename)
        self._client_id = cp[self._api_url]['client_id']
        self._client_secret = cp[self._api_url]['client_secret']

    def fresh_token(self, rt):
        self.set_token(self._get_new_token(rt), rt)

    def get_token(self):
        max_age = 1800
        if self._token_created is not None:
            age = time.time() - self._token_created
        if not self._token or age > max_age:
            self.set_token(self._get_new_token(self._token_rt), self._token_rt)
        return self._token

    def _get_new_token(self, rt):
        auth = (self._client_id, self._client_secret)

        data = {
            u'grant_type': u'client_credentials',
            u'scope': qvarnutils.scopes_for_type(rt['type'], rt['subpaths']),
        }

        r = self.request('POST', '/auth/token', auth=auth, data=data)
        obj = r.json()
        return obj[u'access_token']

    def get_resource_paths(self, rt):
        path = rt['path']
        rpaths = self.sort_resources(self.get_resource_list(path, rt))
        listeners = self.sort_resources(self.get_listeners(path, rt))
        notifs = self.sort_resources(
            self.get_notifications(path, rt, listeners))
        return rpaths + listeners + notifs

    def sort_resources(self, resources):
        return list(sorted(resources, key=lambda r: r.get('src_path', '_')))

    def get_listeners(self, path, rt):
        listener_path = '{}/listeners'.format(path)
        listener_ids = self.get_list(listener_path)
        listeners = [
            {
                'type': rt['type'],
                'src_path': '{}/{}'.format(listener_path, rid),
                'tgt_path': listener_path,
                'subpaths': [],
            }
            for rid in listener_ids
        ]
        return listeners

    def get_notifications(self, path, rt, listeners):
        notifs = []
        for listener in listeners:
            notifs_path = '{}/notifications'.format(listener['src_path'])
            notif_ids = self.get_list(notifs_path)
            notifs.extend(
                {
                    'type': rt['type'],
                    'src_path': '{}/{}'.format(notifs_path, nid),
                    'tgt_path': notifs_path,
                    'subpaths': [],
                }
                for nid in notif_ids
            )
        return notifs

    def get_resource_list(self, path, rt):
        resources = self.get_list(path)
        rpaths = []
        for rid in resources:
            rpath = {
                'type': rt['type'],
                'src_path': '{}/{}'.format(path, rid),
                'tgt_path': path,
                'subpaths': [
                    '{}/{}/{}'.format(path, rid, subpath)
                    for subpath in rt['subpaths']
                ]
            }
            rpaths.append(rpath)
        return rpaths

    def get_list(self, path):
        resp = self.GET(self.get_token(), path)
        if not resp.ok:
            logging.error('GET %s failed', path)
            return []

        obj = resp.json()
        return [r['id'] for r in obj['resources']]

    def GET(self, token, path):
        return self.request('GET', path, token=token)

    def POST(self, token, path, resource, content_type, revision):
        headers = self.prepare_usual_headers(content_type, revision)
        return self.request(
            'POST', path, token=token, headers=headers, data=resource)

    def PUT(self, token, path, resource, content_type, revision):
        headers = self.prepare_usual_headers(content_type, revision)
        return self.request(
            'PUT', path, token=token, headers=headers, data=resource)

    def DELETE(self, token, path):
        return self.request('DELETE', path, token=token)

    def prepare_usual_headers(self, content_type, revision):
        headers = {
            'Content-Type': content_type,
        }
        if revision:
            headers['Revision'] = revision
        return headers

    def request(self, method, path, token=None, headers=None,
                auth=None, data=None):

        funcs = {
            'POST': self._session.post,
            'PUT': self._session.put,
            'GET': self._session.get,
            'DELETE': self._session.delete,
        }

        url = '{}{}'.format(self._api_url, path)

        if token:
            headers = dict(headers or {})
            headers['Authorization'] = 'Bearer {}'.format(token)

        response = funcs[method](
            url,
            headers=headers,
            auth=auth,
            data=data,
            verify=False)

        if not response.ok:
            raise Error(
                method, self._api_url, path, response.status_code,
                response.text)

        return response


class Error(cliapp.AppException):

    def __init__(self, method, api_url, path, status, body):
        super().__init__(
            'Error {status}: {method} {url}{path}\n\n{body}'.format(
                status=status, method=method, url=api_url, path=path,
                body=body))
