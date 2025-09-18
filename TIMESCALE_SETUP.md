# TimescaleDB Setup Guide for Monitor Service

## 1. Installation

### Docker (Recommended):
```bash
# Pull TimescaleDB image
docker pull timescale/timescaledb:latest-pg14

# Run TimescaleDB container
docker run -d --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=monitor_db \
  -v timescaledb_data:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg14
```

### Manual Installation:
```bash
# Ubuntu/Debian
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
curl -L https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install timescaledb-2-postgresql-14

# Enable extension
sudo timescaledb-tune
sudo systemctl restart postgresql
```

## 2. Database Setup

```sql
-- Connect to PostgreSQL and create database
CREATE DATABASE monitor_db;
\c monitor_db;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Run the schema from timescaledb_schema.sql
\i /path/to/timescaledb_schema.sql
```

## 3. Configuration

Update your `.env` file:
```env
# Database Configuration
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=monitor_db

# TimescaleDB specific
TIMESCALE_ENABLED=true
TIMESCALE_RETENTION_DAYS=30
TIMESCALE_COMPRESSION_DAYS=7
```

## 4. Benefits for Monitor Service

### Storage Efficiency:
- **Raw data**: ~100MB/day for 1000 monitors (1-minute intervals)
- **With compression**: ~5-10MB/day (90%+ savings)
- **Auto cleanup**: Old data automatically deleted

### Query Performance:
- **Time-based queries**: 10-100x faster than regular PostgreSQL
- **Aggregations**: Pre-computed continuous aggregates
- **Analytics**: Built-in time-series functions

### Example Queries:

```sql
-- Monitor uptime last 24 hours
SELECT monitor_id, 
       (COUNT(*) FILTER (WHERE status = 1)::decimal / COUNT(*) * 100) as uptime
FROM monitor_checks 
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY monitor_id;

-- Response time trends (5-minute buckets)
SELECT time_bucket('5 minutes', time) as bucket,
       AVG(response_time) as avg_response
FROM monitor_checks 
WHERE monitor_id = 1 AND time >= NOW() - INTERVAL '2 hours'
GROUP BY bucket ORDER BY bucket;

-- Top slowest monitors
SELECT monitor_id, AVG(response_time) as avg_response
FROM monitor_checks 
WHERE status = 1 AND time >= NOW() - INTERVAL '1 hour'
GROUP BY monitor_id 
ORDER BY avg_response DESC LIMIT 10;
```

## 5. Migration from Current System

```python
# Migration script example
async def migrate_to_timescale():
    # 1. Create TimescaleDB tables
    # 2. Copy existing data from monitor_items updates
    # 3. Setup continuous monitoring
    pass
```

## 6. Monitoring Dashboard

With TimescaleDB, you can easily integrate with:
- **Grafana**: Beautiful time-series dashboards
- **Prometheus**: Metrics collection and alerting  
- **Tableau**: Business intelligence and reporting
- **Custom APIs**: Real-time monitor status APIs

## 7. Production Considerations

- **Backup**: Use pg_dump with TimescaleDB support
- **Scaling**: TimescaleDB handles millions of data points
- **High Availability**: Multi-node setup available
- **Security**: Standard PostgreSQL security practices