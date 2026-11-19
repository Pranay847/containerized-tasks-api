"""Every PostgresTaskRepository call must close its connection.

psycopg2's `with conn:` only commits/rolls back; it does not close. Without
an explicit close each request leaks a server connection until GC.
"""

import pytest

from app import postgres_repository
from app.postgres_repository import PostgresTaskRepository


class FakeCursor:
    rowcount = 1

    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return self._row

    def fetchall(self):
        return [self._row]


class FakeConn:
    def __init__(self):
        self.closed = False
        self.autocommit = False

    def cursor(self, cursor_factory=None):
        return FakeCursor({"id": 1, "title": "t", "done": False})

    def close(self):
        self.closed = True


@pytest.fixture
def conns(monkeypatch):
    made = []

    def fake_connect(dsn):
        conn = FakeConn()
        made.append(conn)
        return conn

    monkeypatch.setattr(postgres_repository.psycopg2, "connect", fake_connect)
    return made


@pytest.mark.parametrize(
    "call",
    [
        lambda r: r.add("t"),
        lambda r: r.list(),
        lambda r: r.get(1),
        lambda r: r.set_done(1, True),
        lambda r: r.delete(1),
    ],
    ids=["add", "list", "get", "set_done", "delete"],
)
def test_each_call_closes_its_connection(conns, call):
    call(PostgresTaskRepository("postgresql://fake"))
    assert len(conns) == 1
    assert conns[0].autocommit is True
    assert conns[0].closed is True
