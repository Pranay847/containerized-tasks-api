"""Flask app + routes. This is the wiring layer.

The ONLY BE-04 change from the A2 version is build_repository(): if DATABASE_URL
is set we use Postgres, otherwise we fall back to the original in-memory store.
The routes below are byte-for-byte the A2 routes - unchanged.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, request

from .postgres_repository import PostgresTaskRepository
from .repository import InMemoryTaskRepository, TaskRepository
from .service import TaskService


def build_repository() -> TaskRepository:
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return PostgresTaskRepository(dsn)
    return InMemoryTaskRepository()


def create_app(service: TaskService | None = None) -> Flask:
    app = Flask(__name__)
    svc = service or TaskService(build_repository())

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/tasks")
    def list_tasks():
        return jsonify([t.to_dict() for t in svc.list_tasks()])

    @app.post("/tasks")
    def create_task():
        data = request.get_json(silent=True) or {}
        try:
            task = svc.create_task(data.get("title", ""))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        return jsonify(task.to_dict()), 201

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id: int):
        task = svc.get_task(task_id)
        if task is None:
            return jsonify(error="not found"), 404
        return jsonify(task.to_dict())

    @app.post("/tasks/<int:task_id>/complete")
    def complete_task(task_id: int):
        task = svc.complete_task(task_id)
        if task is None:
            return jsonify(error="not found"), 404
        return jsonify(task.to_dict())

    @app.delete("/tasks/<int:task_id>")
    def delete_task(task_id: int):
        if not svc.delete_task(task_id):
            return jsonify(error="not found"), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
