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


import logging


def get_rt(api, name):
    token = api.get_token('resource_types')
    r = api.GET(token, '/resource_types/{}'.format(name))
    obj = r.json()
    spec = obj['spec']
    rt = {
        'type': spec['type'],
        'plural': spec['path'].split('/')[1],
        'path': spec['path'],
        'subpaths': list(spec['versions'][-1]['subpaths'].keys()),
    }
    logging.debug('get_rt: %r', rt)
    return rt
