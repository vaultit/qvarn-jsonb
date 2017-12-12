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


resource_types = {
    'person': {
        'type': 'persons',
        'path': '/persons',
        'subpaths': ['private', 'photo', 'sync'],
    },
    'org': {
        'type': 'orgs',
        'path': '/orgs',
        'subpaths': ['sync'],
    },
    'card': {
        'type': 'cards',
        'path': '/cards',
        'subpaths': ['sync', 'holder_photo', 'issuer_logo'],
    },
    'contract': {
        'type': 'contracts',
        'path': '/contracts',
        'subpaths': ['sync', 'document'],
    },
}


def get_rt(name):
    if name in resource_types:
        return resource_types[name]
    for rt in resource_types.values():
        if rt['type'] == name:
            return rt
    assert 0
