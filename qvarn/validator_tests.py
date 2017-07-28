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


import unittest


import qvarn


class ValidatorTests(unittest.TestCase):

    def setUp(self):
        self.spec = {
            'type': 'foo',
            'path': '/foos',
            'versions': [
                {
                    'version': 'v0',
                    'prototype': {
                        'type': '',
                        'id': '',
                        'revision': '',
                        'foo': '',
                    },
                },
            ]
        }

        self.resource_type = qvarn.ResourceType()
        self.resource_type.from_spec(self.spec)

        self.validator = qvarn.Validator()

        self.resource = {
            'type': 'foo',
            'id': 'resource-1',
            'revision': 'revision-1',
            'foo': 'this is foo',
        }

    def test_accepts_valid_resource(self):
        self.validator.validate(self.resource, self.resource_type)

    def test_rejects_resource_that_is_not_a_dict(self):
        with self.assertRaises(qvarn.ValidationError):
            self.validator.validate(None, self.resource_type)

    def test_rejects_resource_without_type(self):
        del self.resource['type']
        with self.assertRaises(qvarn.ValidationError):
            self.validator.validate(self.resource, self.resource_type)

    def test_rejects_resource_without_id(self):
        del self.resource['id']
        with self.assertRaises(qvarn.ValidationError):
            self.validator.validate_has_id(self.resource, self.resource_type)

    def test_rejects_resource_with_id(self):
        with self.assertRaises(qvarn.ValidationError):
            self.validator.validate_lacks_id(self.resource, self.resource_type)
