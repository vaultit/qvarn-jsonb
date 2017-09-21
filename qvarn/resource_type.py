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


import os

import yaml


class ResourceType:

    def __init__(self):
        self._type = None
        self._path = None
        self._versions = []
        self._version = None
        self._prototype = None

    def from_spec(self, spec):
        self.set_type(spec['type'])
        self.set_path(spec['path'])
        self._versions = spec['versions']
        self.set_version_spec(self._versions[-1])

    def as_dict(self):
        return {
            'type': self.get_type(),
            'path': self.get_path(),
            'versions': [
                version_spec
                for version_spec in self._versions
            ]
        }

    def set_type(self, type_name):
        self._type = type_name

    def get_type(self):
        return self._type

    def set_path(self, path):
        self._path = path

    def get_path(self):
        return self._path

    def set_version_spec(self, version_spec):
        self._version = version_spec['version']
        self._prototype = version_spec['prototype']

    def get_all_versions(self):
        return [v['version'] for v in self._versions]

    def get_version(self, version):
        for v in self._versions:
            if v['version'] == version:
                return v
        raise KeyError('Version %r not found' % version)

    def get_latest_version(self):
        return self._version

    def get_latest_prototype(self):
        return self._prototype

    def get_subpaths(self):
        v = self._versions[-1]
        return v.get('subpaths', {})


def load_resource_types(dirname):  # pragma: no cover
    assert dirname is not None
    resource_types = []
    basenames = [x for x in os.listdir(dirname) if x.endswith('.yaml')]
    for basename in basenames:
        pathname = os.path.join(dirname, basename)
        with open(pathname) as f:
            spec = yaml.safe_load(f)
        rt = ResourceType()
        rt.from_spec(spec)
        resource_types.append(rt)
    return resource_types


def add_missing_fields(proto, obj):
    # Assume obj is validated.

    return _fill_in_dict(proto, obj)


def _fill_in_dict(proto, obj):
    new = {}
    defaults = {
        str: '',
        int: 0,
        bool: False,
    }

    for field in proto:
        if type(proto[field]) in defaults:
            if field not in obj:
                new[field] = defaults[type(proto[field])]
        elif isinstance(proto[field], list):
            if field not in obj:
                new[field] = []
            elif isinstance(proto[field][0], dict):
                new[field] = [
                    _fill_in_dict(proto[field][0], x)
                    for x in obj[field]
                ]
            elif type(proto[field][0]) in defaults:
                new[field] = list(obj[field])
        else:  # pragma: no cover
            assert 0

    if isinstance(obj, dict):  # pragma: no cover
        for field in obj:
            if field not in new:
                if isinstance(obj[field], list):
                    new[field] = list(obj[field])
                else:
                    new[field] = obj[field]

    return new
