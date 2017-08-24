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


def schema(r):
    stack = []
    push(stack, [], r)
    result = []
    for x in generate(stack):
        result.append(x)
    return result


def push(stack, name, r):
    stack.append((name, r))


def pop(stack):
    return stack.pop()


def generate(stack):
    funcs = {
        dict: dict_schema,
        list: list_schema,
        str: simple_schema,
        int: simple_schema,
        bool: simple_schema,
        type(None): simple_schema,
    }

    while stack:
        name, r = pop(stack)
        for x in funcs[type(r)](stack, name, r):
            yield x


def dict_schema(stack, name, r):
    for key in reversed(sorted(r.keys())):
        push(stack, name + [key], r[key])
    return []  # must return an iterable


def list_schema(stack, name, r):
    qvarn.log.log(
        'trace', msg_text='list_schema', stack=stack, name=name, len_r=len(r))
    if len(r) > 0:
        yield name, list, type(r[0])
        if isinstance(r[0], dict):
            push(stack, name, r[0])
    else:
        yield name, list, None


def simple_schema(stack, name, r):
    yield name, type(r)
