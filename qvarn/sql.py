# sql.py - SQL dialect adaptation
#
# Copyright (C) 2017  Lars Wirzenius


'''Communicate with a PostgreSQL server.'''


import time

import psycopg2
import psycopg2.pool
import psycopg2.extras
import psycopg2.extensions
import slog

import qvarn


class PostgresAdapter:  # pragma: no cover

    def __init__(self):
        self._pool = None

    def connect(self, **kwargs):
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=kwargs['min_conn'],
            maxconn=kwargs['max_conn'],
            database=kwargs['database'],
            user=kwargs['user'],
            password=kwargs['password'],
            host=kwargs['host'],
            port=kwargs['port'],
        )

    def transaction(self):
        return Transaction(self)

    def get_conn(self):
        return self._pool.getconn()

    def put_conn(self, conn, close=False):
        self._pool.putconn(conn)


class Transaction:  # pragma: no cover

    def __init__(self, sql):
        self._sql = sql
        self._conn = None
        self._started = None
        self._queries = None

    def __enter__(self):
        self._started = time.time()
        self._queries = []
        self._conn = self._sql.get_conn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        commit_ms = None
        try:
            if exc_type is None:
                t = time.time()
                self._conn.commit()
                commit_ms = time.time() - t
            else:  # pragma: no cover
                self._conn.rollback()
        except BaseException:
            # If an exception was raised inside the transaction the
            # connection may be in an invalid state and should not be
            # reused, hence close=True.
            self._sql.put_conn(self._conn, close=True)
            self._conn = None
            raise
        self._sql.put_conn(self._conn)
        self._conn = None

        ended = time.time()
        duration = 1000.0 * (ended - self._started)
        qvarn.log.log(
            'sql', msg_text='SQL transaction', ms=duration,
            commit_ms=commit_ms, queries=self._queries)
        self._started = None
        self._queries = []

    def execute(self, query, values):
        started = time.time()
        c = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute(query, values)
        duration = 1000.0 * (time.time() - started)
        self._queries.append({
            'query': query,
            'values': values,
            'ms': duration,
        })
        return c

    def get_rows(self, cursor):
        for row in cursor:
            yield dict(row)

    def create_table(self, table_name, **keys):
        columns = ', '.join(
            '{} {}'.format(self._q(key_name), self._sqltype(col_type))
            for key_name, col_type in keys.items()
        )
        return 'CREATE TABLE IF NOT EXISTS {} ({})'.format(
            self._q(table_name),
            columns)

    def index_exists(self, table_name, index_name):
        query = """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = %(table_name)s AND
                  indexname = %(index_name)s
        """
        cursor = self.execute(query, {
            'table_name': table_name,
            'index_name': index_name,
        })
        with cursor:
            return cursor.fetchone()['count'] > 0

    def create_index(self, table_name, index_name, column_name):
        query = 'CREATE INDEX {} ON {} ({})'.format(
            self._q(index_name), self._q(table_name), self._q(column_name))
        if not self.index_exists(table_name, index_name):
            self.execute(query, {})

    def create_jsonb_index(
            self, table_name, index_name, column_name, field_name):
        sql = "CREATE INDEX {} ON {} (lower({} ->> '{}'))"
        query = sql.format(
            self._q(index_name), self._q(table_name), self._q(column_name),
            self._q(field_name))
        if not self.index_exists(table_name, index_name):
            self.execute(query, {})

    def _sqltype(self, col_type):
        types = [
            (str, 'TEXT'),
            (int, 'BIGINT'),
            (bool, 'BOOL'),
            (dict, 'JSONB'),
            (bytes, 'BYTEA'),
        ]
        for t, n in types:
            if col_type == t:
                return n
        assert False

    def insert_object(self, table_name, *keys):
        columns = [self._q(k) for k in keys]
        placeholders = [self._placeholder(k) for k in keys]
        return 'INSERT INTO {} ({}) VALUES ({})'.format(
            self._q(table_name),
            ', '.join(columns),
            ', '.join(placeholders),
        )

    def remove_objects(self, table_name, *keys):
        conditions = [
            '{} = {}'.format(self._q(key), self._placeholder(key))
            for key in keys
        ]
        return 'DELETE FROM {} WHERE {}'.format(
            self._q(table_name),
            ' AND '.join(conditions),
        )

    def select_objects_with_keys_and_cond(
            self, table_name, cond, allow_cond, **keys):
        keys_check = self.keys_checks(keys)
        query, values = qvarn.sql_select(
            _counter, cond, allow_cond, keys_check)
        values.update(self.keys_values(keys))
        return query, values

    def keys_checks(self, keys):
        if not keys:
            checks = ['TRUE']
        else:
            checks = [
                '_objects.{} = {}'.format(quote(key), placeholder(key))
                for key in keys
            ]
        sql_snippet = ' AND '.join(checks)
        return sql_snippet

    def keys_values(self, keys):
        return {
            quote(key): keys[key]
            for key in keys
        }

    def select_objects(self, table_name, col_name, *keys):
        conditions = [
            '{} = {}'.format(self._q(key), self._placeholder(key))
            for key in keys
        ]
        query = 'SELECT {} FROM {}'.format(
            self._q(col_name),
            self._q(table_name),
        )
        if conditions:
            query += ' WHERE {}'.format(' AND '.join(conditions))
        return query

    def has_allow_rule(self, table_name, rule):
        conditions = [
            '{} = {}'.format(self._q(key), self._placeholder(key))
            for key in rule if rule[key] is not None
        ] + [
            '{} IS NULL'.format(self._q(key))
            for key in rule if rule[key] is None
        ]
        query = 'SELECT * FROM {} WHERE {}'.format(
            self._q(table_name),
            ' AND '.join(conditions),
        )
        return query

    def remove_allow_rule(self, table_name, rule):
        conditions = [
            '{} = {}'.format(self._q(key), self._placeholder(key))
            for key in rule if rule[key] is not None
        ] + [
            '{} IS NULL'.format(self._q(key))
            for key in rule if rule[key] is None
        ]
        query = 'DELETE FROM {} WHERE {}'.format(
            self._q(table_name),
            ' AND '.join(conditions),
        )
        return query

    def _condition(self, cond):
        return cond.as_sql()

    def _q(self, name):
        return quote(name)

    def _placeholder(self, name):
        return placeholder(name)


def quote(name):  # pragma: no cover
    ascii_lower = 'abcdefghijklmnopqrstuvwxyz'
    ascii_digits = '0123456789'
    ascii_chars = ascii_lower + ascii_lower.upper() + ascii_digits
    ok = ascii_chars + '_'
    assert name.strip(ok) == '', 'must have only allowed chars: %r' % name
    return '_'.join(name.split('-'))


def placeholder(name):  # pragma: no cover
    return '%({})s'.format(quote(name))


_counter = slog.Counter()


def get_unique_name(base, counter=None):  # pragma: no cover
    if counter is None:
        counter = _counter
    return '{}{}'.format(base, counter.increment())


class Condition:  # pragma: no cover

    def get_subconditions(self):
        return []

    def matches(self, obj, keys):  # pragma: no cover
        raise NotImplementedError()

    def as_sql(self):  # pragma: no cover
        raise NotImplementedError()


class All(Condition):

    def __init__(self, *conds):
        self.conds = list(conds)

    def append_subcondition(self, cond):
        self.conds.append(cond)

    def get_subconditions(self):
        return self.conds

    def matches(self, obj, keys):
        for cond in self.conds:
            if not cond.matches(obj, keys):
                return False
        return True

    def as_sql(self):  # pragma: no cover
        pairs = [cond.as_sql() for cond in self.conds]
        conds = ' AND '.join(query for query, _ in pairs)
        values = {}
        for _, value in pairs:
            values.update(value)
        return '( {} )'.format(conds), values


class Cmp(Condition):  # pragma: no cover

    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def compare(self, a, b):
        raise NotImplementedError()

    def cmp_py(self, actual):
        if isinstance(actual, str):
            return self.compare(actual.lower(), self.pattern.lower())
        return self.compare(actual, self.pattern)

    def cmp_sql(self, pattern_name):
        return "lower(_field->>'value') {} lower(%({})s)".format(
            self.get_operator(), pattern_name)

    def get_operator(self):
        raise NotImplementedError()

    def matches(self, obj, keys):
        for key, actual in qvarn.flatten_object(obj):
            if key == self.name and self.cmp_py(actual):
                return True
        return False

    def as_sql(self):  # pragma: no cover
        name_name = get_unique_name('name')
        pattern_name = get_unique_name('pattern')
        values = {
            name_name: self.name,
            pattern_name: self.pattern,
        }
        query = ("_field ->> 'name' = %%(%s)s AND "
                 "_field ->> 'value' %s") % (
                     name_name, self.cmp_sql(pattern_name))
        return query, values


class Equal(Cmp):

    def compare(self, a, b):
        return a == b

    def get_operator(self):  # pragma: no cover
        return '='


class ResourceTypeIs(Equal):

    def __init__(self, type_name):
        super().__init__('type', type_name)

    def matches(self, obj, keys):
        return obj.get('type') == self.pattern


class NotEqual(Cmp):

    def compare(self, a, b):
        return a != b

    def get_operator(self):  # pragma: no cover
        return '!='


class GreaterThan(Cmp):

    def compare(self, a, b):
        return a > b

    def get_operator(self):  # pragma: no cover
        return '>'


class GreaterOrEqual(Cmp):

    def compare(self, a, b):
        return a >= b

    def get_operator(self):  # pragma: no cover
        return '>='


class LessThan(Cmp):

    def compare(self, a, b):
        return a < b

    def get_operator(self):  # pragma: no cover
        return '<'


class LessOrEqual(Cmp):

    def compare(self, a, b):
        return a <= b

    def get_operator(self):  # pragma: no cover
        return '<='


class Contains(Cmp):

    def compare(self, a, b):
        return b in a

    def cmp_sql(self, pattern_name):  # pragma: no cover
        t = "lower(_field->>'value') LIKE '%%' || lower(%({})s) || '%%'"
        return t.format(pattern_name)

    def get_operator(self):  # pragma: no cover
        pass


class Startswith(Cmp):

    def compare(self, a, b):
        return a.startswith(b)

    def cmp_sql(self, pattern_name):  # pragma: no cover
        t = "lower(_field->>'value') LIKE lower(%({})s) || '%%'"
        return t.format(pattern_name)

    def get_operator(self):  # pragma: no cover
        pass


class Yes(Condition):

    def compare(self, a, b):  # pragma: no cover
        assert False

    def matches(self, obj, keys):
        return True

    def as_sql(self):  # pragma: no cover
        return 'TRUE', {}


class No(Condition):

    def compare(self, a, b):  # pragma: no cover
        assert False

    def matches(self, obj, keys):
        return False

    def as_sql(self):  # pragma: no cover
        return 'FALSE', {}


class AccessIsAllowed(Condition):  # pragma: no cover

    def __init__(self, req_params, allow):
        self._params = req_params
        self._allow = allow or []

    def matches(self, obj, keys):  # pragma: no cover

        def rule_allows(r):
            qvarn.log.log('zzz', obj=obj, r=r, params=self._params)
            p = self._params
            return (
                r['method'] == p['method'] and
                r['client_id'] in ('*', p['client_id']) and
                r['user_id'] in ('*', p['user_id']) and
                r['resource_id'] in ('*', keys['obj_id']) and
                ('type' not in obj or
                 r['resource_type'] in (None, obj['type'])) and
                (r['resource_field'] is None or r['resource_field'] in obj) and
                (r['resource_value'] in ('*', obj.get(r['resource_field'])))
            )

        qvarn.log.log('yyy', allow=self._allow)
        return any(rule_allows(r) for r in self._allow)

    def as_sql(self):  # pragma: no cover
        placeholders = {
            key: placeholder(key)
            for key in self._params
        }
        values = {
            quote(key): self._params[key]
            for key in self._params
        }
        query = ' AND '.join([
            "_allow.method = {method}",
            "_allow.subpath = _objects.subpath",
            "(_allow.client_id = '*' OR _allow.client_id = {client_id})",
            "(_allow.user_id = '*' OR _allow.user_id = {user_id})",
            ("(_allow.resource_id = '*' OR _"
             "allow.resource_id = _objects.obj_id)"),
        ]).format(**placeholders)
        return query, values
