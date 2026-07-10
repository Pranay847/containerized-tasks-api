"""Service layer: business rules, unaware of WHERE data is stored.

This file does not change when we swap InMemory -> Postgres. It only ever
talks to the TaskRepository interface.
"""

from __future__ import annotations

from .repository import Task, TaskRepository


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self._repo = repo

    def create_task(self, title: str) -> Task:
        title = (title or "").strip()
        if not title:
            raise ValueError("title is required")
        return self._repo.add(title)

    def list_tasks(self) -> list[Task]:
        return self._repo.list()

    def get_task(self, task_id: int) -> Task | None:
        return self._repo.get(task_id)

    def complete_task(self, task_id: int) -> Task | None:
        return self._repo.set_done(task_id, True)

    def delete_task(self, task_id: int) -> bool:
        return self._repo.delete(task_id)
