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


def schema(r):
    return list(generate([], r))


def generate(name, r):
    funcs = {
        dict: dict_schema,
        list: list_schema,
        str: simple_schema,
    }
    for x in funcs[type(r)](name, r):
        yield x


def dict_schema(name, r):
    for key in sorted(r.keys()):
        for x in generate(name + [key], r[key]):
            yield x


def list_schema(name, r):
    yield name, list, type(r[0])


def simple_schema(name, r):
    yield name, type(r)
