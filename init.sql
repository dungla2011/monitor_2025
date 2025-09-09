-- Initialize database for Monitor Service
USE monitor_db;

-- Create tables will be handled by SQLAlchemy
-- This file is for any initial data or custom setup

-- You can add initial monitor items here if needed
-- INSERT INTO monitor_items (name, url, type, interval_seconds, enabled) VALUES
-- ('Example Website', 'https://example.com', 'ping_web', 60, 1);

-- Grant additional permissions if needed
GRANT ALL PRIVILEGES ON monitor_db.* TO 'monitor_user'@'%';
FLUSH PRIVILEGES;
