"""Persistence proof WITHOUT Docker (sandbox has no daemon).

pgserver ships real PostgreSQL binaries and runs a server against a fixed data
directory. That data dir plays the exact role a Docker named volume plays. So:

  ROUND 1: start Postgres on data dir -> app writes rows -> stop BOTH app and
           the Postgres server (full shutdown, like `docker compose down`).
  ROUND 2: start a FRESH Postgres server on the SAME data dir -> start a FRESH
           app -> the rows are still there.

If Round 2 sees Round 1's rows, persistence across an app + database restart is
proven. This is the same guarantee `pgdata:/var/lib/postgresql/data` gives in
docker-compose.yml.
"""

import os
import sys

import pgserver

DATA_DIR = "/tmp/be04_pgdata"  # the "volume"


def run_app_round(dsn, label, writes=None):
    # Import inside so each round builds a fresh app/service/repo, like a
    # restarted container.
    os.environ["DATABASE_URL"] = dsn
    for mod in list(sys.modules):
        if mod.startswith("app"):
            del sys.modules[mod]
    from app.main import create_app

    client = create_app().test_client()

    if writes:
        for title in writes:
            r = client.post("/tasks", json={"title": title})
            assert r.status_code == 201, r.data
    rows = client.get("/tasks").get_json()
    print(f"[{label}] app sees {len(rows)} task(s): {[t['title'] for t in rows]}")
    return rows


def ensure_schema(dsn):
    import psycopg2
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur, open(
            os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
        ) as f:
            cur.execute(f.read())


def main():
    print("=== ROUND 1: fresh server on data dir, app writes rows ===")
    db = pgserver.get_server(DATA_DIR)
    dsn = db.get_uri()
    ensure_schema(dsn)
    run_app_round(dsn, "round1-before", writes=["buy milk", "ship BE-04"])
    db.cleanup()  # full server shutdown == `docker compose down`
    print("Postgres server stopped (data dir left on disk).\n")

    print("=== ROUND 2: BRAND NEW server on the SAME data dir, fresh app ===")
    db2 = pgserver.get_server(DATA_DIR)
    dsn2 = db2.get_uri()
    rows = run_app_round(dsn2, "round2-after")
    db2.cleanup()

    titles = {t["title"] for t in rows}
    ok = {"buy milk", "ship BE-04"} <= titles
    print()
    if ok:
        print("PERSISTENCE PROVEN: rows written before the restart survived it.")
        sys.exit(0)
    print("FAIL: rows did not persist.")
    sys.exit(1)


if __name__ == "__main__":
    main()
