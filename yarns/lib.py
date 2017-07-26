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


import os
import re
import tempfile


import cliapp
import Crypto.PublicKey.RSA
import requests


from yarnutils import *


srcdir = os.environ['SRCDIR']
datadir = os.environ['DATADIR']


vars = Variables(datadir)


def get(url, headers=None):
    r = requests.get(url, headers=headers)
    return r.status_code, r.text


def post(url, headers=None, body=None):
    r = requests.post(url, headers=headers, data=body)
    return r.status_code, r.text


def put(url, headers=None, body=None):
    r = requests.put(url, headers=headers, data=body)
    return r.status_code, r.text


def delete(url, headers=None):
    r = requests.delete(url, headers=headers)
    return r.status_code, r.text


def create_token_signing_key_pair():
    RSA_KEY_BITS = 4096  # A nice, currently safe length
    key = Crypto.PublicKey.RSA.generate(RSA_KEY_BITS)
    return key.exportKey('PEM'), key.exportKey('OpenSSH')


def create_token(privkey, iss, aud, scopes):
    filename = write_temp(privkey)
    argv = [
        os.path.join(srcdir, 'create-token'),
        filename,
        iss,
        aud,
        scopes,
    ]
    return cliapp.runcmd(argv)


def cat(filename):
    return open(filename).read()


def write_temp(data):
    fd, filename = tempfile.mkstemp(dir=datadir)
    os.write(fd, data)
    os.close(fd)
    return filename


def expand_vars(text, vars):
    result = ''
    while text:
        m = re.search(r'\${(?P<name>[^}]+)}', text)
        if not m:
            result += text
            break
        name = m.group('name')
        result += text[:m.start()] + vars[name]
        text = text[m.end():]
    return result


def dict_matches(wanted, actual):
    assert isinstance(wanted, dict)
    assert isinstance(actual, dict)
    for key in wanted:
        assert key in actual
        assert wanted[key] == actual[key]
    return True
