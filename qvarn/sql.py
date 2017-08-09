# sql.py - SQL dialect adaptation
#
# Copyright (C) 2017  Lars Wirzenius


'''Communicate with a PostgreSQL server.'''


import psycopg2
import psycopg2.pool
import psycopg2.extras
import psycopg2.extensions


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

    def __enter__(self):
        self._conn = self._sql.get_conn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:  # pragma: no cover
                self._conn.rollback()
        except BaseException:  # pragma: no cover
            self._sql.put_conn(self._conn)
            self._conn = None
            raise
        self._sql.put_conn(self._conn)
        self._conn = None

    def execute(self, query, values):
        c = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute(query, values)
        return c

    def get_rows(self, cursor):
        for row in cursor:
            yield dict(row)

    def create_jsonb_table(self, table_name, **keys):
        columns = ', '.join(
            '{} {}'.format(self._q(key_name), self._sqltype(col_type))
            for key_name, col_type in keys.items()
        )
        return 'CREATE TABLE IF NOT EXISTS {} ({})'.format(
            self._q(table_name),
            columns)

    def _sqltype(self, col_type):
        types = [
            (str, 'TEXT'),
            (dict, 'JSONB'),
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
        qvarn.log.log(
            'debug', msg_text='PostgresAdapater.select_objects',
            query=query, keys=keys, conditions=conditions)
        return query

    def select_objects_on_cond(self, table_name, cond, *keys):
        sql_cond, values = cond.as_sql()
        col_names = [self._q(key) for key in keys]
        query = 'SELECT {} FROM {} WHERE {}'.format(
            ', '.join(col_names),
            self._q(table_name),
            sql_cond,
        )
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


class Condition:

    def matches(self, obj):  # pragma: no cover
        raise NotImplementedError()

    def as_sql(self):  # pragma: no cover
        raise NotImplementedError()


class Equal(Condition):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def matches(self, obj):
        return obj.get(self.name) == self.value

    def as_sql(self):  # pragma: no cover
        values = {
            self.name: self.value,
        }
        template = "( _obj ->> '{}' = {} )"
        query = template.format(
            qvarn.quote(self.name), qvarn.placeholder(self.name))
        return query, values


class All(Condition):

    def matches(self, obj):
        return True

    def as_sql(self):  # pragma: no cover
        return 'TRUE', {}
