"""Route tests: exercise the HTTP layer against the in-memory repository.

These need no database, so they always run (unlike the Postgres half of the
contract test).
"""

import pytest

from app.main import create_app
from app.repository import InMemoryTaskRepository
from app.service import TaskService


@pytest.fixture
def client():
    app = create_app(TaskService(InMemoryTaskRepository()))
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_trims_title_and_returns_201(client):
    resp = client.post("/tasks", json={"title": "  ship it  "})
    assert resp.status_code == 201
    assert resp.get_json() == {"id": 1, "title": "ship it", "done": False}


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": "   "}])
def test_create_rejects_missing_or_blank_title(client, body):
    resp = client.post("/tasks", json=body)
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "title is required"}
    assert client.get("/tasks").get_json() == []


def test_create_with_non_json_body_is_400(client):
    resp = client.post("/tasks", data="not json", content_type="text/plain")
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "title is required"}


def test_list_get_complete_delete_flow(client):
    client.post("/tasks", json={"title": "a"})
    client.post("/tasks", json={"title": "b"})
    assert [t["title"] for t in client.get("/tasks").get_json()] == ["a", "b"]

    assert client.get("/tasks/2").get_json()["title"] == "b"

    done = client.post("/tasks/1/complete")
    assert done.status_code == 200
    assert done.get_json()["done"] is True

    resp = client.delete("/tasks/1")
    assert resp.status_code == 204
    assert resp.data == b""
    assert [t["id"] for t in client.get("/tasks").get_json()] == [2]


@pytest.mark.parametrize(
    "method,path",
    [("get", "/tasks/42"), ("post", "/tasks/42/complete"), ("delete", "/tasks/42")],
)
def test_unknown_id_returns_404(client, method, path):
    resp = getattr(client, method)(path)
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}
