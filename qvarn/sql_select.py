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
    conds = list(flatten(cond))
    if len(conds) == 1:
        query, params = _select_on_simple_cond(counter, cond)
    else:
        query, params = _select_on_multiple_conds(counter, conds)

    qvarn.log.log(
        'trace',
        msg_text='sql_select',
        query=query,
        params=params)
    return query, params


def _select_on_simple_cond(counter, cond):
    name = qvarn.get_unique_name('name', counter=counter)
    value = qvarn.get_unique_name('value', counter=counter)
    params = {
        name: cond.name,
        value: cond.pattern,
    }
    template = (
        "SELECT obj_id FROM _aux WHERE "
        "_field->>'name' = %({})s "
        "AND _field->>'value' {}"
    )
    query = template.format(name, cond.cmp_sql(value))
    return query, params


def _select_on_multiple_conds(counter, conds):
    params = {
        'count': len(conds),
    }

    template = (
        "SELECT _temp.obj_id FROM ("
        "SELECT obj_id, count(obj_id) AS _hits FROM _aux WHERE "
        "{} "
        "GROUP BY obj_id) AS _temp WHERE _hits >= %(count)s"
    )

    part_template = "(_field->>'name' = %({})s AND _field->>'value' {})"
    parts = []
    for subcond in conds:
        name = qvarn.get_unique_name('name', counter=counter)
        value = qvarn.get_unique_name('value', counter=counter)
        params[name] = subcond.name
        params[value] = subcond.pattern
        part = part_template.format(name, subcond.cmp_sql(value))
        parts.append(part)

    query = template.format(' OR '.join(parts))

    return query, params


def flatten(cond):
    subs = cond.get_subconditions()
    if subs:
        for sub in subs:
            for c in flatten(sub):
                yield c
    else:
        yield cond
