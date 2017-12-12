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


class PostgresAdapter:

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

    def put_conn(self, conn):
        self._pool.putconn(conn)


class Transaction:

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
        try:
            if exc_type is None:
                t = time.time()
                self._conn.commit()
                commit_ms = time.time() - t
            else:  # pragma: no cover
                self._conn.rollback()
        except BaseException:  # pragma: no cover
            self._sql.put_conn(self._conn)
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

    def create_index(self, table_name, index_name, column_name):
        return 'CREATE INDEX IF NOT EXISTS {} ON {} ({})'.format(
            self._q(index_name), self._q(table_name), self._q(column_name))

    def create_jsonb_index(
            self, table_name, index_name, column_name, field_name):
        sql = "CREATE INDEX IF NOT EXISTS {} ON {} (lower({} ->> '{}'))"
        return sql.format(
            self._q(index_name), self._q(table_name), self._q(column_name),
            self._q(field_name))

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

    def select_objects_on_cond(self, table_name, cond, *keys):
        query, values = qvarn.sql_select(_counter, cond)
        return query, values

    def _condition(self, cond):
        return cond.as_sql()

    def _q(self, name):
        return quote(name)

    def _placeholder(self, name):
        return placeholder(name)


def quote(name):
    ascii_lower = 'abcdefghijklmnopqrstuvwxyz'
    ascii_digits = '0123456789'
    ascii_chars = ascii_lower + ascii_lower.upper() + ascii_digits
    ok = ascii_chars + '_'
    assert name.strip(ok) == '', 'must have only allowed chars: %r' % name
    return '_'.join(name.split('-'))


def placeholder(name):
    return '%({})s'.format(quote(name))


_counter = slog.Counter()


def get_unique_name(base, counter=None):
    if counter is None:
        counter = _counter
    return '{}{}'.format(base, counter.increment())


class Condition:

    def get_subconditions(self):
        return []

    def matches(self, obj):  # pragma: no cover
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

    def matches(self, obj):
        for cond in self.conds:
            if not cond.matches(obj):
                return False
        return True

    def as_sql(self):  # pragma: no cover
        pairs = [cond.as_sql() for cond in self.conds]
        conds = ' AND '.join(query for query, _ in pairs)
        values = {}
        for _, value in pairs:
            values.update(value)
        return '( {} )'.format(conds), values


class Cmp(Condition):

    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern

    def cmp_py(self, actual):
        raise NotImplementedError()

    def cmp_sql(self, pattern_name):
        return "lower(_field->>'value') {} lower(%({})s)".format(
            self.get_operator(), pattern_name)

    def get_operator(self):
        raise NotImplementedError()

    def matches(self, obj):
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

    def cmp_py(self, actual):
        return self.pattern.lower() == actual.lower()

    def get_operator(self):
        return '='


class ResourceTypeIs(Equal):

    def __init__(self, type_name):
        super().__init__('type', type_name)

    def matches(self, obj):
        return obj.get('type') == self.pattern


class NotEqual(Cmp):

    def cmp_py(self, actual):
        return self.pattern.lower() != actual.lower()

    def get_operator(self):
        return '!='


class GreaterThan(Cmp):

    def cmp_py(self, actual):
        return actual.lower() > self.pattern.lower()

    def get_operator(self):
        return '>'


class GreaterOrEqual(Cmp):

    def cmp_py(self, actual):
        return actual.lower() >= self.pattern.lower()

    def get_operator(self):
        return '>='


class LessThan(Cmp):

    def cmp_py(self, actual):
        return actual.lower() < self.pattern.lower()

    def get_operator(self):
        return '<'


class LessOrEqual(Cmp):

    def cmp_py(self, actual):
        return actual.lower() <= self.pattern.lower()

    def get_operator(self):
        return '<='


class Contains(Cmp):

    def cmp_py(self, actual):
        return self.pattern.lower() in actual.lower()

    def cmp_sql(self, pattern_name):
        t = "lower(_field->>'value') LIKE '%%' || lower(%({})s) || '%%'"
        return t.format(pattern_name)

    def get_operator(self):
        pass


class Startswith(Cmp):

    def cmp_py(self, actual):
        return actual.lower().startswith(self.pattern.lower())

    def cmp_sql(self, pattern_name):
        t = "lower(_field->>'value') LIKE lower(%({})s) || '%%'"
        return t.format(pattern_name)

    def get_operator(self):
        pass


class Yes(Condition):

    def matches(self, obj):
        return True

    def as_sql(self):  # pragma: no cover
        return 'TRUE', {}
