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


class Validator:

    def validate(self, resource, resource_type):
        if not isinstance(resource, dict):
            raise NotADict(resource)
        if 'type' not in resource:
            raise NoType()

    def validate_has_id(self, resource, resource_type):
        self.validate(resource, resource_type)
        if 'id' not in resource:
            raise NoId()

    def validate_lacks_id(self, resource, resource_type):
        self.validate(resource, resource_type)
        if 'id' in resource:
            raise HasId(resource)


class ValidationError(Exception):

    pass


class NotADict(ValidationError):  # pragma: no cover

    def __init__(self, resource):
        super().__init__('Was expecting a dict, got %r' % type(resource))


class NoType(ValidationError):  # pragma: no cover

    def __init__(self):
        super().__init__('Was expecting a "type" field in resource')


class NoId(ValidationError):  # pragma: no cover

    def __init__(self):
        super().__init__(
            'Resource does not have and "id" field, but one expected')


class HasId(ValidationError):  # pragma: no cover

    def __init__(self, resource):
        super().__init__(
            'Resource has id %s, but it must not have one' % resource['id'])
