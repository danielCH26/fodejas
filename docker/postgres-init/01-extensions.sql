-- GAP #3 — Enable pg_stat_statements extension.
-- NOTE: This script runs ONLY on first initialization of an empty data directory.
-- The PostgreSQL official image executes .sql files in /docker-entrypoint-initdb.d/
-- only when the data directory is empty (fresh cluster creation).
--
-- For EXISTING volumes:
--   docker compose exec db psql -U fodejas_user -d fodejas_db -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
--
-- After enabling, restart the db service to load shared_preload_libraries:
--   docker compose up -d db

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
