"""Postgres implementation of TaskRepository.

Same interface as InMemoryTaskRepository, so service.py and app.py are
UNCHANGED. The only difference: rows live in Postgres, which persists them on
disk (a Docker named volume), so they survive an app + container restart.
"""

from __future__ import annotations

import psycopg2
import psycopg2.extras

from .repository import Task, TaskRepository


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self):
        # New connection per call keeps this simple and restart-safe; a real
        # service would use a pool. autocommit so each write is durable.
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = True
        return conn

    @staticmethod
    def _row_to_task(row) -> Task:
        return Task(id=row["id"], title=row["title"], done=row["done"])

    def add(self, title: str) -> Task:
        with self._connect() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, FALSE) "
                "RETURNING id, title, done",
                (title,),
            )
            return self._row_to_task(cur.fetchone())

    def list(self) -> list[Task]:
        with self._connect() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
            return [self._row_to_task(r) for r in cur.fetchall()]

    def get(self, task_id: int) -> Task | None:
        with self._connect() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            )
            row = cur.fetchone()
            return self._row_to_task(row) if row else None

    def set_done(self, task_id: int, done: bool) -> Task | None:
        with self._connect() as conn, conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                "UPDATE tasks SET done = %s WHERE id = %s "
                "RETURNING id, title, done",
                (done, task_id),
            )
            row = cur.fetchone()
            return self._row_to_task(row) if row else None

    def delete(self, task_id: int) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0
