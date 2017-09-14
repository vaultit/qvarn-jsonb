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


def sql_select(counter, cond):
    subconds = cond.get_subconditions()
    if not subconds:
        name = qvarn.get_unique_name('name', counter=counter)
        value = qvarn.get_unique_name('value', counter=counter)
        params = {
            name: cond.name,
            value: cond.pattern,
        }
        template = (
            "SELECT obj_id FROM _aux WHERE "
            "_field->>'name' = %({})s AND _field->>'value' {}"
        )
        query = template.format(name, cond.cmp_sql(value))
    else:
        params = {
            'count': len(subconds),
        }

        template = (
            "SELECT _temp.obj_id, _obj FROM _objects, ("
            "SELECT obj_id, count(obj_id) AS _hits FROM _aux WHERE "
            "{} "
            "GROUP BY obj_id) WHERE _hits = %(count)s"
        )

        part_template = "(_field->>'name' = %({})s AND _field->>'value' {})"
        parts = []
        for subcond in subconds:
            name = qvarn.get_unique_name('name', counter=counter)
            value = qvarn.get_unique_name('value', counter=counter)
            params[name] = subcond.name
            params[value] = subcond.pattern
            part = part_template.format(name, subcond.cmp_sql(value))
            parts.append(part)

        query = template.format(' OR '.join(parts))

    return query, params
