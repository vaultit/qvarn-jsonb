# idgen_tests.py - unit tests for ResourceIdGenerator
#
# Copyright 2015, 2016 Suomen Tilaajavastuu Oy
# Copyright 2017 Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import unittest

import qvarn


class ResourceIdGeneratorTests(unittest.TestCase):

    def test_returns_a_unicode_string(self):
        rig = qvarn.ResourceIdGenerator()
        resource_id = rig.new_id('person')
        self.assertTrue(isinstance(resource_id, str))

    def test_returns_new_values_each_time(self):
        rig = qvarn.ResourceIdGenerator()
        id_1 = rig.new_id('person')
        id_2 = rig.new_id('person')
        self.assertNotEqual(id_1, id_2)
