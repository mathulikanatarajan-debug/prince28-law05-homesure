# Day 4 verification evidence

## Docker and Compose

- `docker compose up --build -d` completed successfully and built `homesure-api`
  and `homesure-migrate`.
- `docker image inspect homesure-api:latest` returned image ID
  `sha256:c370d24e856cf711485d9ae58cc5e5a49426d8a2f697351caa308ce8dfd90a40`.
- `docker compose exec -T api id` reported `uid=999(app) gid=999(app)`.
- `docker compose ps --all` reported API healthy on `localhost:8001`, PostgreSQL
  healthy on `localhost:5433`, Redis healthy on `localhost:6379`, and the
  migration job exited with status 0.
- `docker compose config --quiet` completed successfully.

## Database and endpoints

- The Compose database reports Alembic revision `59888dbfdaf5` and contains
  20 document records.
- The Compose migration/seed job exited successfully and reported
  `records=20 inserted=0 updated=0 unchanged=20`.
- Integration tests create a unique PostgreSQL database for each run, apply
  migrations, test loading records twice, and drop the database afterward.
  The latest run left zero `homesure_test_*` databases behind.
- `GET http://localhost:8001/health` returned `{"status":"ok"}`.
- `GET http://localhost:8001/ready` returned
  `{"status":"ready","checks":{"database":true}}`.

## Quality checks

- `uv run poe lint`: Ruff checks passed; 35 Python files were formatted.
- `uv run poe test`: 27 passed.
- `uv run poe test-integration`: 8 passed.
- `uv run poe cov`: 35 passed; 100% statement and branch coverage for
  `homesure` (230 statements, 26 branches, zero missing statements or partial
  branches).

## Remaining limitations

- Integration tests and `poe cov` require a reachable PostgreSQL server and a
  role allowed to create and drop databases. By default they use the Compose
  PostgreSQL service; `TEST_DATABASE_URL` can select another server.
- Redis is running as a Compose service, but the current API health/readiness
  endpoints do not probe Redis; readiness checks PostgreSQL.
