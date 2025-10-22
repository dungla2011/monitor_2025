-- Migration: Add email_notification column to monitor_settings table
-- Date: 2025-10-22
-- Description: Store user email addresses for email notifications

-- Add email_notification column
ALTER TABLE monitor_settings 
ADD COLUMN email_notification VARCHAR(255) NULL 
COMMENT 'Email address for notifications';

-- Create index for faster lookups
CREATE INDEX idx_monitor_settings_email ON monitor_settings(email_notification);

-- Show result
SELECT 'Migration completed successfully' AS status;
