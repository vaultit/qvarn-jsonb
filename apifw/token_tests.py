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


# This is the a pre-generated token signing key. Actually, it is a key
# pair, with both the public and private keys. It was generated with
# this call: Crypto.PublicKey.RSA.generate(1024). We use pre-generated
# version because the key generation takes time, and we'd like tests
# to execute quickly. The key length is short, because there's no need
# for a secure key in these tests.

token_signing_key = b'''\
-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQDwX379dN0PxFXPw0Exh+yTIzZ2oZ9zfwnyW34E3bNbpfDLlgev
bOmECp71Xp0XsAexc2XxbPwgx0focDD2LGDepbCeVK9DprBc7J7Nno5DKmV8Z9eT
bJ5uK/gbqulcmeaX6lznNbS+nL7DtBBCumHv5+GUxm0R5A2E1Z6ob241ewIDAQAB
AoGBANTZq0jjIBGjKN2WJ/elRi8wojzAd8K9PuCWdev3KajBM44Dp4CG7+0VvpbG
llLwdI+FAUOc31JjROCl4CVNPOST9oSUIrWuoXdBXSmFozPvnGqUiX7ifu8uIzB9
gXoy/x8EiTl3c/GtFRvrdQdyc4pDMskD70PF1dLkBfYR8oKBAkEA9S9fIubRr0/N
TIldF5KzYdcwOQq6KqyObBlHFqdYYlkEnRSXdWO7HeFcUECVfL/yYp+URf/rvtbE
6gskOb6EuwJBAPr5yYVGKcPtgIWXly8p/yfpurrSo4l6nu4GKJtKI5IAJSq5MRyk
jvHnO3EzIAdvkPJgB1PAhyhp8H5YPdrEZkECQQCmrx/UUGs47d26LKB3CCqfV3XX
Ma3CmTDx2HV1tyrlIXN7fqZBDh4FgFIL1PxLpQqZdbeNpyCTytpv6kckYptFAkEA
9M1y0KmokXD3fNdpY1rOhGsKdbKCS9YscbXWI+rEGWRE3JB5JBwrRi+rHnak1jvv
oUsjuoDAFR6Is2R1KQ+LQQJBAIfQquABIx9Kq+wi6dEXtATMlQwa+Gxl9sp4hUrD
4D29pbc1CsTQZVeZDtf6Js9ppUWhUUI6GmrwGCSzX/LC0WI=
-----END RSA PRIVATE KEY-----
'''


# This is another key, used to test invalid signatures.

other_key = b'''\
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDJyeup0HGCOyeaxC3/MDAgjRpKNF7227gHV/PlNm/LXm2bS0w0
Fd7jYnHIm4sgKfWhgV9wlC9dUEkdhLfUsMFogPDo7s1oBPkKKdPjMTkBHnpD/E/2
UcX8oe+/qa2rFMdmZMeWUPlzqjpNU/6vqOX5lL9qNlIaNw8Uoj69YoU86QIDAQAB
AoGAH2fl3dArWnGKgHP4FLeTRf2wEcyE2zbnNX1i4FHQpH5V4M2fVpvwzMMNooNS
6/ab3D8ec48csBFGz+lQEzJPZ4VR6sYV5+XbHHsHxwHZwEdaPhSNaIWYCkI9Yngd
cpB4Ejz3HISsWbzf9D7CoPK5QrOIZUZ9YRidOeUUbepv0uECQQDN6X/CCa2FwFxP
c8b/e4GD0kFNditNnrgbs2q/bPF9+oGxlhfeyJXblCfqOSAzRquePjyEDtSbQTPt
1UyU7EwnAkEA+t+nN5cBFCC6JcNyfZ4fZpcCHGQ09HplZVDk8K4VzSWSc+mTbvTf
LpTZv++7f2fAfY4CJ3RGD3+CRzouXzkIbwJBAKWhKO7/seBgduBCFNP0mJ1cRsL0
RqjM/vLpQvhvvWDEXAZo4RKG7mQNrH2vLcORGQLUtQDUnRe1PvwUEuHHoQkCQQD2
iGDYJSGfOQYU5DuXrJLpCw68/dB4S+tmpBdHWZv9DKYeGHSU/jhwm0Bc+OaFrlyg
RbRiN0Y+JqzM+CTn2LErAkAMYJlhsX/TgSlhlVpmDNHK+f9decLOetzlMg7LatqO
ux3VzoZr+a4ryiEpWqOHOk0OX97VIZn3VYr4Q24qg3zz
-----END RSA PRIVATE KEY-----
'''

token_signing_key = Crypto.PublicKey.RSA.generate(1024)
wrong_signing_key = Crypto.PublicKey.RSA.generate(1024)

class TokenTests(unittest.TestCase):

    def test_valid_token_is_valid(self):
        now = int(time.time())
        claims = {
            'iss': 'https://idp.example.com',
            'sub': 'subject-uuid',
            'aud': 'audience-uuid',
            'exp': now + 3600,
            'scope': 'openid person_resource_id uapi_orgs_get uapi_orgs_post'
        }
        encoded = apifw.create_token(claims, token_signing_key.exportKey('PEM'))
        self.assertTrue(isinstance(encoded, bytes))
        self.assertEqual(len(encoded.split(b'.')), 3)

        decoded = apifw.decode_token(
            encoded,
            token_signing_key.exportKey('OpenSSH'),
            claims['aud'])
        self.assertEqual(decoded, claims)
