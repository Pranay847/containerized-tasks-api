-- Runs automatically on first container start via the Postgres image's
-- /docker-entrypoint-initdb.d hook. Idempotent so re-runs are safe.
CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);
