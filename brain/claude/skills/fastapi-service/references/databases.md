# Databases (PostgreSQL / MongoDB)
- Read the real schema before writing models or queries: MCP server `databases` - `db_list`, then
  `pg_schema` (tables; one table's columns, constraints, indexes) or `mongo_schema` (collections; fields and
  types from a sample, indexes). Check a query with `pg_query` / `pg_explain` or `mongo_find` / `mongo_aggregate`.
- Writing: `pg_execute` (any SQL, committed) / `mongo_write` (insert / update / delete / indexes) work only on
  connections marked `"write": true`, and the user confirms each call. Say what you will change first; seed and
  test data are fine; lasting schema changes belong in the app's migrations (Alembic for SQLAlchemy) - write the
  migration, run it on the dev database, check with pg_schema. Never write to a connection the user calls production.
  Connections: `~/.claude/brain/databases.json` (passwords in ~/.pgpass or an env variable).
- Postgres from FastAPI: SQLAlchemy 2 (async engine + asyncpg, or psycopg 3); Mongo: pymongo / motor; one
  client per app in the lifespan, never per request.
