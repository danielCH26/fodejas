-- PostgreSQL Monitoring Setup
-- Enable required extensions and create views for monitoring

-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create view for slow queries analysis
CREATE OR REPLACE VIEW slow_queries AS
SELECT
    left(query, 100) as query_preview,
    calls,
    total_exec_time as total_time_ms,
    mean_exec_time as mean_time_ms,
    stddev_exec_time as stddev_time_ms,
    rows
FROM pg_stat_statements
WHERE calls > 10
ORDER BY total_exec_time DESC
LIMIT 20;

-- Create view for connection stats
CREATE OR REPLACE VIEW connection_stats AS
SELECT
    datname,
    numbackends as total_connections,
    xact_commit as transactions_committed,
    xact_rollback as transactions_rolled_back,
    blks_read,
    blks_hit,
    round(100 * blks_hit / nullif(blks_hit + blks_read, 0), 2) as cache_hit_ratio
FROM pg_stat_database
WHERE datname IS NOT NULL;

-- Create view for cache hit ratio
CREATE OR REPLACE VIEW cache_hit_ratio AS
SELECT
    'buffer cache' as metric,
    round(100 * blks_hit / nullif(blks_hit + blks_read, 0), 2) as hit_ratio
FROM pg_stat_database
WHERE datname = current_database();

-- Create view for table bloat estimation
CREATE OR REPLACE VIEW table_bloat AS
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fodejas_user;
