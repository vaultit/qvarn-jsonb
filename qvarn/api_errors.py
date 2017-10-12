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


class NoSuchResourceType(Exception):  # pragma: no cover

    def __init__(self, path):
        super().__init__('No resource type for path {}'.format(path))


class TooManyResourceTypes(Exception):  # pragma: no cover

    def __init__(self, path):
        super().__init__('Too many resource types for path {}'.format(path))


class TooManyResources(Exception):  # pragma: no cover

    def __init__(self, resource_id):
        super().__init__('Too many resources with id {}'.format(resource_id))


class NotJson(Exception):  # pragma: no cover

    def __init__(self, ct):
        super().__init__('Was expecting application/json, not {}'.format(ct))


class IdMismatch(Exception):  # pragma: no cover

    def __init__(self, obj_id, id_from_path):
        super().__init__(
            'Resource has id {} but path says {}'.format(obj_id, id_from_path))
