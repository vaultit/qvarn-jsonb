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


import json
import os
import re
import signal
import tempfile
import time


import cliapp
import Crypto.PublicKey.RSA
import requests
import yaml


from yarnutils import *


srcdir = os.environ['SRCDIR']
datadir = os.environ['DATADIR']


vars = Variables(datadir)


def hexdigit(c):
    return ord(c) - ord('0')


def unescape(s):
    t = ''
    while s:
        if s.startswith('\\x') and len(s) >= 4:
            a = hexdigit(s[2])
            b = hexdigit(s[3])
            t += chr(a * 16 + b)
            s = s[4:]
        else:
            t += s[0]
            s = s[1:]
    return t


def add_postgres_config(config):
    pg = os.environ.get('QVARN_POSTGRES')
    if pg:
        with open(pg) as f:
            config['database'] = yaml.safe_load(f)
            config['memory-database'] = False
    return config


def get(url, headers=None):
    print('get: url={} headers={}'.format(url, headers))
    r = requests.get(url, headers=headers)
    return r.status_code, dict(r.headers), r.content


def post(url, headers=None, body=None):
    r = requests.post(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.text


def put(url, headers=None, body=None):
    r = requests.put(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.text


def delete(url, headers=None):
    r = requests.delete(url, headers=headers)
    return r.status_code, dict(r.headers), r.text


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


def write(filename, data):
    with open(filename, 'w') as f:
        f.write(data)


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
        print('expanding ', name)
        result += text[:m.start()] + vars[name]
        text = text[m.end():]
    return result


def values_match(wanted, actual):
    print
    print 'wanted:', repr(wanted)
    print 'actual:', repr(actual)

    if type(wanted) != type(actual):
        print 'wanted and actual types differ', type(wanted), type(actual)
        return False

    if isinstance(wanted, dict):
        for key in wanted:
            if key not in actual:
                print 'key {!r} not in actual'.format(key)
                return False
            if not values_match(wanted[key], actual[key]):
                return False
    elif isinstance(wanted, list):
        if len(wanted) != len(actual):
            print 'wanted and actual are of different lengths'
        for witem, aitem in zip(wanted, actual):
            if not values_match(witem, aitem):
                return False
    else:
        if wanted != actual:
            print 'wanted and actual differ'
            return False

    return True


def start_qvarn(name):
    privkey, pubkey = create_token_signing_key_pair()
    write('key', privkey)

    port = cliapp.runcmd([os.path.join(srcdir, 'randport' )]).strip()

    vars[name] = {
        'issuer': 'issuer',
        'audience': 'audience',
        'api.log': 'qvarn-{}.log'.format(name),
        'gunicorn3.log': 'gunicorn3-{}.log'.format(name),
        'pid-file': '{}.pid'.format(name),
        'port': port,
        'url': 'http://127.0.0.1:{}'.format(port),
        'privkey': privkey,
        'pubkey': pubkey,
    }

    config = {
        'log': [
            {
                'filename': vars[name]['api.log'],
            },
        ],
        'baseurl': vars[name]['url'],
        'token-issuer': vars[name]['issuer'],
        'token-audience': vars[name]['audience'],
        'token-public-key': pubkey,
        'resource-type-dir': os.path.join(srcdir, 'resource_type'),
    }
    config = add_postgres_config(config)
    config_filename = os.path.join(datadir, 'qvarn-{}.yaml'.format(name))

    env = dict(os.environ)
    env['QVARN_CONFIG'] = config_filename
    write(config_filename, yaml.safe_dump(config))

    argv = [
        'gunicorn3',
        '--daemon',
        '--bind', '127.0.0.1:{}'.format(vars[name]['port']),
        '-p', vars[name]['pid-file'],
        'qvarn.backend:app',
    ]
    cliapp.runcmd(argv, env=env, stdout=None, stderr=None)

    wait_for_file(vars[name]['pid-file'], 2.0)


def wait_for_file(filename, timeout):
    until = time.time() + timeout
    while time.time() < until and not os.path.exists(filename):
        time.sleep(0.01)
    assert os.path.exists(filename)


def stop_qvarn(name):
    if vars[name]:
        filename = vars[name]['pid-file']
        pid_text = cat(filename)
        pid = int(pid_text)
        os.kill(pid, signal.SIGTERM)
