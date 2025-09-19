-- Complete TimescaleDB Setup for Monitor Service
-- Single file setup - run once to create everything

-- 1. Create dedicated schema for monitor system
CREATE SCHEMA IF NOT EXISTS glx_monitor_v2;

-- 2. Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Verify extension is loaded
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        RAISE EXCEPTION 'TimescaleDB extension failed to load! Please install TimescaleDB first.';
    ELSE
        RAISE NOTICE 'TimescaleDB extension loaded successfully (version: %)!', 
            (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb');
    END IF;
END $$;

-- 3. Create base tables in monitor schema
CREATE TABLE IF NOT EXISTS glx_monitor_v2.monitor_checks (
    time TIMESTAMPTZ NOT NULL,
    monitor_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    check_type TEXT NOT NULL,
    status BIGINT NOT NULL, -- 1=success, -1=failure
    response_time DECIMAL(10,3), -- milliseconds
    message TEXT,
    details JSONB,
    PRIMARY KEY (time, monitor_id)
);

CREATE TABLE IF NOT EXISTS glx_monitor_v2.monitor_stats_hourly (
    time TIMESTAMPTZ NOT NULL,
    monitor_id BIGINT NOT NULL,
    total_checks BIGINT DEFAULT 0,
    successful_checks BIGINT DEFAULT 0,
    failed_checks BIGINT DEFAULT 0,
    avg_response_time DECIMAL(10,3),
    min_response_time DECIMAL(10,3),
    max_response_time DECIMAL(10,3),
    uptime_percentage DECIMAL(5,2),
    PRIMARY KEY (time, monitor_id)
);

CREATE TABLE IF NOT EXISTS glx_monitor_v2.monitor_system_metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_type TEXT NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    tags JSONB,
    PRIMARY KEY (time, metric_type)
);

-- 4. Convert to hypertables
SELECT create_hypertable('glx_monitor_v2.monitor_checks', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
SELECT create_hypertable('glx_monitor_v2.monitor_stats_hourly', 'time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
SELECT create_hypertable('glx_monitor_v2.monitor_system_metrics', 'time', chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- 5. Create indexes
CREATE INDEX IF NOT EXISTS idx_monitor_checks_monitor_time ON glx_monitor_v2.monitor_checks (monitor_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_checks_status ON glx_monitor_v2.monitor_checks (status, time DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_system_metrics_type ON glx_monitor_v2.monitor_system_metrics (metric_type, time DESC);

-- 6. Enable compression
ALTER TABLE glx_monitor_v2.monitor_checks SET (timescaledb.compress = true);
ALTER TABLE glx_monitor_v2.monitor_stats_hourly SET (timescaledb.compress = true);

-- 7. Create policies
SELECT add_retention_policy('glx_monitor_v2.monitor_checks', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('glx_monitor_v2.monitor_stats_hourly', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('glx_monitor_v2.monitor_system_metrics', INTERVAL '7 days', if_not_exists => TRUE);

SELECT add_compression_policy('glx_monitor_v2.monitor_checks', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('glx_monitor_v2.monitor_stats_hourly', INTERVAL '30 days', if_not_exists => TRUE);

-- 8. Show final status
SELECT 
    'TimescaleDB Setup Complete!' as status,
    (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb') as version,
    (SELECT COUNT(*) FROM timescaledb_information.hypertables) as hypertables_created;

-- Show created hypertables
SELECT hypertable_name, num_chunks, hypertable_schema FROM timescaledb_information.hypertables;