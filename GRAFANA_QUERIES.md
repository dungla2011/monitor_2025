# Grafana Query Improvements cho Monitor Dashboard

## 1. Query cải thiện - Response Time by Monitor
```sql
SELECT 
  time_bucket('5 minutes', time) AS time,
  monitor_id,
  AVG(response_time) as "Response Time (ms)",
  COUNT(*) as "Check Count"
FROM glx_monitor_v2.monitor_checks 
WHERE $__timeFilter(time)
  AND status = 1
  AND response_time IS NOT NULL
  AND response_time < 10000  -- Lọc bỏ response time quá lớn
GROUP BY time_bucket('5 minutes', time), monitor_id
ORDER BY time
```

## 2. Query - Success/Failure Status
```sql
SELECT 
  time_bucket('5 minutes', time) AS time,
  monitor_id,
  SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as "Success",
  SUM(CASE WHEN status = -1 THEN 1 ELSE 0 END) as "Failures"
FROM glx_monitor_v2.monitor_checks 
WHERE $__timeFilter(time)
GROUP BY time_bucket('5 minutes', time), monitor_id
ORDER BY time
```

## 3. Query - Uptime Percentage
```sql
SELECT 
  time_bucket('1 hour', time) AS time,
  monitor_id,
  (COUNT(*) FILTER (WHERE status = 1)::decimal / COUNT(*) * 100) as "Uptime %"
FROM glx_monitor_v2.monitor_checks 
WHERE $__timeFilter(time)
GROUP BY time_bucket('1 hour', time), monitor_id
HAVING COUNT(*) > 0
ORDER BY time
```

## 4. Query - Monitor Details Table
```sql
SELECT 
  monitor_id as "Monitor ID",
  MAX(time) as "Last Check",
  COUNT(*) as "Total Checks",
  AVG(response_time) as "Avg Response (ms)",
  (COUNT(*) FILTER (WHERE status = 1)::decimal / COUNT(*) * 100) as "Success Rate %"
FROM glx_monitor_v2.monitor_checks 
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY monitor_id
ORDER BY monitor_id
```

## 5. Cài đặt Panel tốt hơn:

### Panel Type: Time Series
- **Unit**: milliseconds (ms)
- **Y-Axis Min**: 0
- **Y-Axis Max**: 5000 (để thấy rõ response time bình thường)

### Panel Type: Stat
- **Unit**: percent (%)
- **Thresholds**: 
  - Red: < 95%
  - Yellow: 95-99%
  - Green: > 99%

### Panel Type: Table  
- Format: Table
- Show: Latest values