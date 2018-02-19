# Copyright (C) 2017-2018  Lars Wirzenius
# Copyright (C) 2018  Ivan Dolgov
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


import json  # pylint: disable=unused-import
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


V = Variables(datadir)
V['qvarns'] = {}
V['users'] = {}


def srcpath(path):
    return os.path.join(srcdir, path)


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


def strfy(v):
    if isinstance(v, unicode):
        return v.encode('utf-8')
    if isinstance(v, dict):
        return {
            strfy(key): strfy(value)
            for key, value in v.items()
        }
    if isinstance(v, list):
        return [strfy(item) for item in v]
    return v


def add_postgres_config(config):
    pg = os.environ.get('QVARN_POSTGRES')
    if pg:
        with open(pg) as f:
            config['database'] = yaml.safe_load(f)
            config['memory-database'] = False
    return config


def qvarn_var_name(name):
    return 'qvarn_{}'.format(name)


def get_qvarn(name):
    var_name = qvarn_var_name(name)
    return V[var_name]


def save_qvarn(name, qvarn_vars):
    var_name = qvarn_var_name(name)
    V[var_name] = qvarn_vars


def add_authz_header(headers, token):
    if token is not None:
        if headers is None:
            headers = {}
        headers['Authorization'] = 'Bearer {}'.format(token)
    assert headers is None or isinstance(headers, dict)
    return headers


def request(func, name, path, **kwargs):
    status, resp_headers, content = func(name, path, **kwargs)
    as_json = None
    if content and resp_headers.get('Content-Type') == 'application/json':
        as_json = json.loads(content)
    V['response'] = {
        'status_code': status,
        'headers': resp_headers,
        'body': content,
        'json': as_json,
    }


def request_resource(qvarn_name, path, token):
    request(get_from_qvarn, qvarn_name, path, token=token)
    return {
        'status': get_status(),
        'headers': get_headers(),
        'body': get_json(),
    }


def get_status():
    return V['response']['status_code']


def get_headers():
    return V['response']['headers']


def get_body():
    return V['response']['body']


def get_json():
    return V['response']['json']


def get_from_qvarn(name, path, headers=None, token=None, body=None):
    assert headers is None or isinstance(headers, dict)
    assert token is None or isinstance(token, str)
    qvarn_vars = get_qvarn(name)
    url = '{}/{}'.format(qvarn_vars['url'], path)
    headers = add_authz_header(headers, token)
    return GET(url, headers=headers, body=body)


def post_to_qvarn(name, path, headers=None, body=None, token=None):
    assert headers is None or isinstance(headers, dict)
    assert body is None or isinstance(body, dict)
    assert token is None or isinstance(token, str)
    qvarn_vars = get_qvarn(name)
    url = '{}/{}'.format(qvarn_vars['url'], path)
    headers = add_authz_header(headers, token)
    return POST(url, headers=headers, body=body)


def put_to_qvarn(name, path, headers=None, body=None, token=None):
    assert headers is None or isinstance(headers, dict)
    assert body is None or isinstance(body, (dict, str))
    assert token is None or isinstance(token, str)
    qvarn_vars = get_qvarn(name)
    url = '{}/{}'.format(qvarn_vars['url'], path)
    headers = add_authz_header(headers, token)
    return PUT(url, headers=headers, body=body)


def delete_from_qvarn(name, path, headers=None, token=None, body=None):
    assert headers is None or isinstance(headers, dict)
    assert token is None or isinstance(token, str)
    qvarn_vars = get_qvarn(name)
    url = '{}/{}'.format(qvarn_vars['url'], path)
    headers = add_authz_header(headers, token)
    return DELETE(url, headers=headers, body=body)


def GET(url, headers=None, body=None):
    headers = add_content_type(headers, body)
    if isinstance(body, dict):
        body = json.dumps(body)
    print 'get: url={} headers={}'.format(url, headers)
    r = requests.get(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.content


def add_content_type(headers, body):
    if headers is None:
        headers = {}
    if isinstance(body, dict):
        ct = 'application/json'
    else:
        ct = 'application/octent-type'
    if 'Content-Type' not in headers:
        headers['Content-Type'] = ct
    return headers


def POST(url, headers=None, body=None):
    headers = add_content_type(headers, body)
    if isinstance(body, dict):
        body = json.dumps(body)
    r = requests.post(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.text


def PUT(url, headers=None, body=None):
    headers = add_content_type(headers, body)
    if isinstance(body, dict):
        body = json.dumps(body)
    r = requests.put(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.text


def DELETE(url, headers=None, body=None):
    headers = add_content_type(headers, body)
    if isinstance(body, dict):
        body = json.dumps(body)
    r = requests.delete(url, headers=headers, data=body)
    return r.status_code, dict(r.headers), r.text


def create_token_signing_key_pair():
    RSA_KEY_BITS = 4096  # A nice, currently safe length
    key = Crypto.PublicKey.RSA.generate(RSA_KEY_BITS)
    return key.exportKey('PEM'), key.exportKey('OpenSSH')


def create_token(privkey, iss, sub, aud, scopes):
    filename = write_temp(privkey)
    argv = [
        os.path.join(srcdir, 'create-token'),
        filename,
        iss,
        sub,
        aud,
        scopes,
    ]
    return cliapp.runcmd(argv)


def token_var_name(qvarn, user):
    return 'token_{}_{}'.format(qvarn, user)


def has_token(qvarn, user):
    return get_token(qvarn, user) is not None


def get_token(qvarn, user):
    var_name = token_var_name(qvarn, user)
    return V[var_name]


def save_token(qvarn, user, token):
    var_name = token_var_name(qvarn, user)
    V[var_name] = token
    V['tokens'] = (V['tokens'] or []) + [var_name]


def forget_all_tokens():
    print('tokens', V['tokens'])
    token_names = V['tokens'] or []
    print('token_names', token_names)
    for name in token_names:
        V[name] = None


def create_token_for_user(qvarn_name, user_name, scopes, force=False):
    if force or not has_token(qvarn_name, user_name):
        qvarn_vars = get_qvarn(qvarn_name)
        token = create_token(
            qvarn_vars['privkey'], qvarn_name, user_name,
            qvarn_vars['audience'], scopes)
        save_token(qvarn_name, user_name, token)
    return get_token(qvarn_name, user_name)


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


def expand_vars(text, variables):
    result = ''
    while text:
        m = re.search(r'\${(?P<name>[^}]+)}', text)
        if not m:
            result += text
            break
        name = m.group('name')
        print('expanding ', name, repr(variables[name]))
        result += text[:m.start()] + variables[name]
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


def start_qvarn(name, audience='audience', fine_grained=False):
    privkey, pubkey = create_token_signing_key_pair()
    port = cliapp.runcmd([os.path.join(srcdir, 'randport')]).strip()

    qvarn_vars = {
        'issuer': name,
        'audience': audience,
        'api.log': 'qvarn-{}.log'.format(name),
        'gunicorn3.log': 'gunicorn3-{}.log'.format(name),
        'pid-file': '{}.pid'.format(name),
        'port': port,
        'url': 'http://127.0.0.1:{}'.format(port),
        'privkey': privkey,
        'pubkey': pubkey,
        'fine-grained': fine_grained,
    }
    save_qvarn(name, qvarn_vars)

    start_qvarn_with_vars(name)


def start_qvarn_with_vars(name):
    qvarn_vars = get_qvarn(name)

    config = {
        'log': [
            {
                'filename': qvarn_vars['api.log'],
            },
        ],
        'baseurl': qvarn_vars['url'],
        'token-issuer': qvarn_vars['issuer'],
        'token-audience': qvarn_vars['audience'],
        'token-public-key': qvarn_vars['pubkey'],
        'resource-type-dir': os.path.join(srcdir, 'resource_type'),
        'enable-fine-grained-access-control': qvarn_vars['fine-grained'],
    }
    config = add_postgres_config(config)
    config_filename = os.path.join(datadir, 'qvarn-{}.yaml'.format(name))
    write(config_filename, yaml.safe_dump(config))

    env = dict(os.environ)
    env['QVARN_CONFIG'] = config_filename

    argv = [
        'gunicorn3',
        '--daemon',
        '--bind', '127.0.0.1:{}'.format(qvarn_vars['port']),
        '-p', qvarn_vars['pid-file'],
        'qvarn.backend:app',
    ]
    cliapp.runcmd(argv, env=env, stdout=None, stderr=None)

    wait_for_file(qvarn_vars['pid-file'], 2.0)


def wait_for_file(filename, timeout):
    until = time.time() + timeout
    while time.time() < until and not os.path.exists(filename):
        time.sleep(0.01)
    assert os.path.exists(filename)


def stop_qvarn(name):
    qvarn_vars = get_qvarn(name)
    if qvarn_vars:
        filename = qvarn_vars['pid-file']
        pid_text = cat(filename)
        pid = int(pid_text)
        os.kill(pid, signal.SIGTERM)


def dump_qvarn(qvarn_name, filename, names):
    qvarn_vars = get_qvarn(qvarn_name)
    token = create_token_for_user(qvarn_name, '', V['scopes'])
    argv = [
        srcpath('qvarn-dump'),
        '--token', token,
        '--api', qvarn_vars['url'],
        '--output', filename,
        '--log', filename + '.log',
    ] + names
    cliapp.runcmd(argv)


def qvarn_copy(source_name, target_name, names):
    source = get_qvarn(source_name)
    assert source is not None
    target = get_qvarn(target_name)
    assert source is not None
    source_token = create_token_for_user(
        source_name, '', V['scopes'], force=True)
    target_token = create_token_for_user(
        target_name, '', V['scopes'], force=True)
    argv = [
        srcpath('qvarn-copy'),
        '--source-token', source_token,
        '--target-token', target_token,
        '--source', source['url'],
        '--target', target['url'],
        '--log', 'copy.log',
    ] + names
    cliapp.runcmd(argv)


def delete_access(qvarn_vars, min_seconds):
    argv = [
        srcpath('qvarn-access'),
        '--token', qvarn_vars['token'],
        '--api', qvarn_vars['url'],
        '--log', 'access_delete.log',
        '--delete',
        '--min-seconds', str(min_seconds),
    ]
    cliapp.runcmd(argv)
