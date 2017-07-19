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


class ResourceType:

    def __init__(self):
        self._type = None
        self._path = None
        self._version = None

    def from_spec(self, spec):
        self.set_type(spec['type'])
        self.set_path(spec['path'])
        versions = spec['versions']
        self.set_latest_version(versions[-1]['version'])

    def set_type(self, type_name):
        self._type = type_name

    def get_type(self):
        return self._type

    def set_path(self, path):
        self._path = path

    def get_path(self):
        return self._path

    def set_latest_version(self, version):
        self._version = version

    def get_latest_version(self):
        return self._version
