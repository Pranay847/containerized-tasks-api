# Containerize your stack (FlyRank BE-04)

A small tasks API whose in-memory store was swapped for **Postgres running in
Docker**, with the whole stack starting from one command and data that survives
a restart. Week 2, Backend AI Engineering track.

## What this is

The A2 service was a Flask tasks API with a `TaskRepository` interface and an
**in-memory** implementation. BE-04 adds a **Postgres** implementation of the
same interface. Because the service layer and routes only ever talk to the
interface, **they did not change** — the swap is one line in `build_repository()`.

```
app/
  repository.py           # TaskRepository interface + InMemoryTaskRepository (A2)
  postgres_repository.py  # PostgresTaskRepository — same interface, new backend
  service.py              # business rules — UNCHANGED from A2
  main.py                 # Flask routes — UNCHANGED except build_repository()
db/schema.sql             # tasks table, run once on first DB init
docker-compose.yml        # app + postgres, one command, named volume
Dockerfile                # app image
.env.example              # committed; real .env is gitignored
tests/                    # contract test + persistence proof
```

## Run the whole stack (one command)

```bash
cp .env.example .env      # edit the password if you like
docker compose up         # builds the app, starts Postgres, wires them together
```

The app is on http://localhost:8000. Postgres data lives in the named volume
`pgdata`, so it outlives `docker compose down`.

## API

| Method | Path                     | Does                          |
|--------|--------------------------|-------------------------------|
| GET    | `/health`                | liveness                      |
| GET    | `/tasks`                 | list tasks                    |
| POST   | `/tasks`                 | create `{ "title": "..." }`   |
| GET    | `/tasks/{id}`            | one task                      |
| POST   | `/tasks/{id}/complete`   | mark done                     |
| DELETE | `/tasks/{id}`            | delete                        |

## How the swap stays clean

`service.py` and the routes depend on the `TaskRepository` **interface**, not on
any storage. `tests/test_repository_contract.py` runs the *same* assertions
against both `InMemoryTaskRepository` and `PostgresTaskRepository`; both pass, so
they honour one contract. That is why switching storage touched only the wiring.

## Persistence — how I actually checked it (honest note)

The requirement is that data survives an **app + database restart**. Here is
exactly what I ran, and the one caveat.

**Caveat, stated plainly:** I do not have a Docker daemon in my dev environment,
so I did **not** run `docker compose up` myself. Instead I proved the same
guarantee at the layer that matters — a real PostgreSQL server writing to a
fixed data directory, which is precisely the role the `pgdata` Docker volume
plays.

`tests/prove_persistence.py` does this (using `pgserver`, which ships real
Postgres binaries):

1. **Round 1** — start Postgres on a data dir, start a fresh app, `POST` two
   tasks, then **fully shut down both the app and the Postgres server** (the
   equivalent of `docker compose down`).
2. **Round 2** — start a **brand-new** Postgres server on the **same data dir**
   and a **fresh** app. Query `/tasks`.

Result (reproducible with `PYTHONPATH=. python3 tests/prove_persistence.py`):

```
=== ROUND 1: fresh server on data dir, app writes rows ===
[round1-before] app sees 2 task(s): ['buy milk', 'ship BE-04']
Postgres server stopped (data dir left on disk).

=== ROUND 2: BRAND NEW server on the SAME data dir, fresh app ===
[round2-after] app sees 2 task(s): ['buy milk', 'ship BE-04']

PERSISTENCE PROVEN: rows written before the restart survived it.
```

The rows written before the restart were still there after it. With
`docker compose`, the named volume `pgdata:/var/lib/postgresql/data` gives this
same durability across `docker compose down && docker compose up`. To reproduce
it the container way on a machine with Docker:

```bash
docker compose up -d
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"title":"buy milk"}'
docker compose down          # stops app AND db containers
docker compose up -d         # volume re-mounts
curl localhost:8000/tasks    # buy milk is still there
```

## Config & secrets

The connection string comes from `DATABASE_URL` in `.env`, which is
**gitignored**; `.env.example` is committed so anyone can copy it. If
`DATABASE_URL` is unset the app falls back to the original in-memory store,
which keeps local prototyping and the contract test trivial.

## Tests

```bash
# contract test needs a Postgres; run both repos through one server:
PYTHONPATH=. python3 - <<'PY'
import pgserver, os, pytest, psycopg2
db = pgserver.get_server("/tmp/be04_test_pg"); dsn = db.get_uri()
with psycopg2.connect(dsn) as c:
    c.autocommit = True
    with c.cursor() as cur, open("db/schema.sql") as f: cur.execute(f.read())
os.environ["TEST_DATABASE_URL"] = dsn
raise SystemExit(pytest.main(["tests/test_repository_contract.py", "-v"]))
PY
```

`8 passed` — four assertions, each run against both repositories.
