"""Contract test: run the SAME assertions against both repositories.

If InMemory and Postgres both pass this identical test, they honour the same
interface - which is exactly why the service and routes never change.
"""

import os

import pytest

from app.repository import InMemoryTaskRepository
from app.postgres_repository import PostgresTaskRepository


def _make_inmemory():
    return InMemoryTaskRepository()


def _make_postgres():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not set")
    repo = PostgresTaskRepository(dsn)
    # clean slate
    with repo._connect() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE tasks RESTART IDENTITY")
    return repo


@pytest.fixture(params=[_make_inmemory, _make_postgres])
def repo(request):
    return request.param()


def test_add_and_get(repo):
    t = repo.add("write BE-04")
    assert t.title == "write BE-04"
    assert t.done is False
    assert repo.get(t.id).title == "write BE-04"


def test_list_is_ordered(repo):
    a = repo.add("a")
    b = repo.add("b")
    ids = [t.id for t in repo.list()]
    assert ids == sorted(ids)
    assert {a.title, b.title} <= {t.title for t in repo.list()}


def test_set_done(repo):
    t = repo.add("finish")
    updated = repo.set_done(t.id, True)
    assert updated.done is True
    assert repo.get(t.id).done is True


def test_delete(repo):
    t = repo.add("temp")
    assert repo.delete(t.id) is True
    assert repo.get(t.id) is None
    assert repo.delete(9999) is False
