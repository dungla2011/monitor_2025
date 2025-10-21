-- ============================================
-- Migration: Add firebase_token to monitor_settings table
-- Date: 2025-10-21
-- ============================================

-- Add firebase_token column to monitor_settings table
ALTER TABLE monitor_settings 
ADD COLUMN firebase_token VARCHAR(255) NULL 
COMMENT 'Firebase Cloud Messaging token for push notifications';

-- Create index for faster lookups (optional but recommended)
CREATE INDEX idx_monitor_settings_firebase_token 
ON monitor_settings(firebase_token);

-- Verify the column was added
SHOW COLUMNS FROM monitor_settings LIKE 'firebase_token';

-- Example: Update a user's Firebase token
-- UPDATE monitor_settings 
-- SET firebase_token = 'your_firebase_token_here' 
-- WHERE user_id = 1;
