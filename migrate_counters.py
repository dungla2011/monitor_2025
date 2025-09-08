#!/usr/bin/env python3
"""
Migration script để thêm count_online và count_offline vào bảng monitor_items
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from db_connection import engine

def migrate_database():
    """Add count_online and count_offline columns to monitor_items table"""
    print("🔄 Starting database migration...")
    
    with engine.connect() as connection:
        # Kiểm tra xem column đã tồn tại chưa
        try:
            # Try to describe the table to check existing columns
            result = connection.execute(text("PRAGMA table_info(monitor_items)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"📋 Current columns in monitor_items: {columns}")
            
            # Add count_online column if not exists
            if 'count_online' not in columns:
                print("➕ Adding count_online column...")
                connection.execute(text("ALTER TABLE monitor_items ADD COLUMN count_online INTEGER DEFAULT 0"))
                print("✅ count_online column added successfully")
            else:
                print("✅ count_online column already exists")
            
            # Add count_offline column if not exists
            if 'count_offline' not in columns:
                print("➕ Adding count_offline column...")
                connection.execute(text("ALTER TABLE monitor_items ADD COLUMN count_offline INTEGER DEFAULT 0"))
                print("✅ count_offline column added successfully")
            else:
                print("✅ count_offline column already exists")
            
            # Commit changes
            connection.commit()
            print("💾 Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            connection.rollback()
            raise

if __name__ == "__main__":
    migrate_database()
