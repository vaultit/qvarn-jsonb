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


def sql_select(counter, cond, allow_cond, keys_check):
    assert cond is not None
    conds = list(flatten(cond))
    query, params = select_on_multiple_conds(
        counter, conds, allow_cond, keys_check)
    return query, params


def select_on_multiple_conds(counter, conds, allow_cond, keys_check):
    params = {
        'count': len(conds),
    }

    part_template = "(_field->>'name' = %({name})s AND {valuecmp})"
    parts = []
    for subcond in conds:
        if isinstance(subcond, qvarn.Cmp):
            name = qvarn.get_unique_name('name', counter=counter)
            value = qvarn.get_unique_name('value', counter=counter)
            params[name] = subcond.name
            params[value] = subcond.pattern
            part = part_template.format(
                name=name,
                valuecmp=subcond.cmp_sql(value),
            )
        else:  # pragma: no cover
            part, values = subcond.as_sql()
            params.update(values)
        parts.append(part)

    template = ' '.join('''
        SELECT DISTINCT _objects.obj_id, _objects.subpath, _objects._obj
            FROM _objects, {allow_table} (
            SELECT obj_id, count(obj_id) AS _hits FROM _aux WHERE
            {parts}
            GROUP BY obj_id
        ) AS _temp WHERE
            _hits >= %(count)s AND
            _temp.obj_id = _objects.obj_id AND
            {keys_check} AND {allow_check}
    '''.split())

    allow_table = ''
    allow_check = 'TRUE'
    if allow_cond is not None:
        allow_table = '_allow, '
        allow_check, allow_params = allow_cond.as_sql()
        params.update(allow_params)

    query = template.format(
        parts=' OR '.join(parts),
        keys_check=keys_check,
        allow_table=allow_table,
        allow_check=allow_check,
    )
    return query, params


def flatten(cond):
    subs = cond.get_subconditions()
    if subs:
        for sub in subs:
            for c in flatten(sub):
                yield c
    else:
        yield cond
