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


import qvarn


class Validator:

    def _validate(self, resource, resource_type):
        if not isinstance(resource, dict):
            raise NotADict(resource)
        if 'type' not in resource:
            raise NoType()
        if resource['type'] != resource_type.get_type():
            raise WrongType(resource['type'], resource_type.get_type())

        actual_schema = qvarn.schema(resource)
        wanted_schema = qvarn.schema(resource_type.get_latest_prototype())

        allowed_names = [x[0] for x in wanted_schema]
        for actual in actual_schema:
            if actual[0] not in allowed_names:
                dotted = '.'.join(actual[0])
                raise UnknownField(resource['type'], dotted)

    def validate_new_resource(self, resource, resource_type):
        self._validate(resource, resource_type)
        if 'id' in resource:
            raise HasId()
        if 'revision' in resource:
            raise HasRevision()

    def validate_resource_update(self, resource, resource_type):
        self._validate(resource, resource_type)
        if 'id' not in resource:
            raise NoId()
        if 'revision' not in resource:
            raise NoRevision()


class ValidationError(Exception):

    pass


class NotADict(ValidationError):  # pragma: no cover

    def __init__(self, resource):
        super().__init__('Was expecting a dict, got %r' % type(resource))


class NoType(ValidationError):

    def __init__(self):
        super().__init__("Resources MUST have a type field")


class WrongType(ValidationError):

    def __init__(self, actual, expected):
        super().__init__(
            'Resource has type %s, but %s was expected' % (actual, expected))


class NoId(ValidationError):

    def __init__(self):
        super().__init__("PUTted resources MUST have an id set")


class HasId(ValidationError):

    def __init__(self):
        super().__init__("POSTed resources MUST NOT have an id set")


class NoRevision(ValidationError):

    def __init__(self):
        super().__init__("PUTted resources MUST have a revision set")


class HasRevision(ValidationError):

    def __init__(self):
        super().__init__("POSTed resources MUST NOT have a revision set")


class UnknownField(ValidationError):  # pragma: no cover

    def __init__(self, type_name, name):
        super().__init__(
            'Resource type {} has unknown field {}'.format(
                type_name, name))


class UnknownSubpath(ValidationError):  # pragma: no cover

    def __init__(self, type_name, subpath):
        super().__init__(
            'Resource type {} has not sub-resource {}'.format(
                type_name, subpath))
