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


def scopes_for_type(name, subpaths):
    scopes = []

    scopes.append('uapi_{}_post'.format(name))
    scopes.append('uapi_{}_get'.format(name))
    scopes.append('uapi_{}_id_get'.format(name))
    scopes.append('uapi_{}_id_put'.format(name))
    scopes.append('uapi_{}_id_delete'.format(name))

    scopes.append('uapi_{}_listeners_get'.format(name))
    scopes.append('uapi_{}_listeners_post'.format(name))
    scopes.append('uapi_{}_listeners_id_get'.format(name))
    scopes.append('uapi_{}_listeners_id_put'.format(name))
    scopes.append('uapi_{}_listeners_id_delete'.format(name))

    scopes.append('uapi_{}_listeners_id_notifications_get'.format(name))
    scopes.append('uapi_{}_listeners_id_notifications_post'.format(name))
    scopes.append('uapi_{}_listeners_id_notifications_id_get'.format(name))
    scopes.append('uapi_{}_listeners_id_notifications_id_delete'.format(name))

    for subtype in subpaths:
        scopes.append('uapi_{}_id_{}_get'.format(name, subtype))
        scopes.append('uapi_{}_id_{}_put'.format(name, subtype))

    scopes.append('uapi_set_meta_fields')

    return ' '.join(scopes)
