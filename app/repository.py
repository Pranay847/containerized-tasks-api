"""Repository interface + in-memory implementation.

The service layer (service.py) and routes (app.py) depend ONLY on this
interface, so swapping the in-memory store for Postgres changes exactly one
wiring line and nothing else. That is the whole point of BE-04.
"""

from __future__ import annotations

import abc
from dataclasses import asdict, dataclass


@dataclass
class Task:
    id: int
    title: str
    done: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class TaskRepository(abc.ABC):
    """The storage contract. Both InMemory and Postgres implement this."""

    @abc.abstractmethod
    def add(self, title: str) -> Task: ...

    @abc.abstractmethod
    def list(self) -> list[Task]: ...

    @abc.abstractmethod
    def get(self, task_id: int) -> Task | None: ...

    @abc.abstractmethod
    def set_done(self, task_id: int, done: bool) -> Task | None: ...

    @abc.abstractmethod
    def delete(self, task_id: int) -> bool: ...


class InMemoryTaskRepository(TaskRepository):
    """The A2 store: a dict. Data lives only as long as the process."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def add(self, title: str) -> Task:
        task = Task(id=self._next_id, title=title, done=False)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def list(self) -> list[Task]:
        return [self._tasks[k] for k in sorted(self._tasks)]

    def get(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

    def set_done(self, task_id: int, done: bool) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.done = done
        return task

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None
