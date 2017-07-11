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


import time
import unittest

import Crypto.PublicKey.RSA

import apifw


# We generate keys here, once, so we only need to do it once.

token_signing_key = Crypto.PublicKey.RSA.generate(1024)
wrong_signing_key = Crypto.PublicKey.RSA.generate(1024)

class TokenTests(unittest.TestCase):

    def make_claimes(self, now):
        return {
            'iss': 'https://idp.example.com',
            'sub': 'subject-uuid',
            'aud': 'audience-uuid',
            'exp': now + 3600,
            'scope': 'openid person_resource_id uapi_orgs_get uapi_orgs_post'
        }

    def test_valid_token_is_valid(self):
        now = int(time.time())
        claims = self.make_claimes(now)
        encoded = apifw.create_token(claims, token_signing_key)
        self.assertTrue(isinstance(encoded, bytes))
        self.assertEqual(len(encoded.split(b'.')), 3)

        decoded = apifw.decode_token(
            encoded,
            token_signing_key,
            claims['aud'])
        self.assertEqual(decoded, claims)

    def test_expired_token_is_invalid(self):
        now = int(time.time())
        claims = self.make_claimes(now - 86400)
        encoded = apifw.create_token(claims, token_signing_key)
        with self.assertRaises(Exception):
            apifw.decode_token(
                encoded,
                token_signing_key,
                claims['aud'])
