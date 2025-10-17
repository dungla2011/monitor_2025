#!/usr/bin/env python3
"""
Raw SQL Helper Functions - No SQLAlchemy ORM overhead
Sử dụng psycopg2 trực tiếp để có performance tốt nhất
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def get_database_config():
    """Get database configuration from environment"""
    db_type = os.getenv('DB_TYPE', 'postgresql')
    
    if db_type == 'postgresql':
        return {
            'type': 'postgresql',
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_NAME', 'monitor_v2'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
    elif db_type == 'mysql':
        return {
            'type': 'mysql',
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'database': os.getenv('MYSQL_NAME', 'monitor_v2'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', '')
        }
    else:
        # Fallback to legacy settings
        return {
            'type': 'legacy',
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'monitor_v2'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }

def get_raw_connection():
    """Tạo raw connection - support cả MySQL và PostgreSQL"""
    config = get_database_config()
    
    if config['type'] == 'mysql':
        import pymysql
        return pymysql.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            charset='utf8mb4'
        )
    else:
        # PostgreSQL hoặc legacy
        import psycopg2
        return psycopg2.connect(
            host=config['host'],
            port=config['port'], 
            database=config['database'],
            user=config['user'],
            password=config['password']
        )

# ===== MONITOR ITEMS QUERIES =====

def get_enabled_items_raw():
    """
    Raw SQL: Lấy tất cả monitor items đã enable
    Thay thế cho SQLAlchemy ORM query
    
    Returns:
        list: Danh sách dict objects giống ORM
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, url_check, enable, type, check_interval_seconds,
                   user_id, last_check_status, count_online, count_offline,
                   last_check_time, result_valid, result_error, "maxAlertCount",
                   "stopTo", "forceRestart"
            FROM monitor_items 
            WHERE url_check IS NOT NULL 
            AND url_check != '' 
            AND enable = 1 
            AND deleted_at IS NULL
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        
        # Convert to dict objects (giống ORM objects)
        items = []
        for row in rows:
            items.append({
                'id': row[0],
                'name': row[1], 
                'url_check': row[2],
                'enable': row[3],
                'type': row[4],
                'check_interval_seconds': row[5],
                'user_id': row[6],
                'last_check_status': row[7],
                'count_online': row[8],
                'count_offline': row[9],
                'last_check_time': row[10],
                'result_valid': row[11],
                'result_error': row[12],
                'maxAlertCount': row[13],
                'stopTo': row[14],
                'forceRestart': row[15]
            })
            
        cursor.close()
        conn.close()
        return items
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def get_all_items_raw(limit=None):
    """
    Raw SQL: Lấy TẤT CẢ monitor items (enabled + disabled) cho complete cache
    
    Args:
        limit (int, optional): Giới hạn số lượng items tối đa
    
    Returns:
        list: Danh sách dict objects giống ORM (bao gồm cả disabled items)
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        # Build SQL query with optional LIMIT
        sql = """
            SELECT id, name, url_check, enable, type, check_interval_seconds,
                   user_id, last_check_status, count_online, count_offline,
                   last_check_time, result_valid, result_error, "maxAlertCount",
                   "stopTo", "forceRestart"
            FROM monitor_items 
            WHERE url_check IS NOT NULL 
            AND url_check != '' 
            AND deleted_at IS NULL
            ORDER BY id
        """
        
        if limit is not None:
            sql += f" LIMIT {limit}"
        
        cursor.execute(sql)
        
        rows = cursor.fetchall()
        
        # Convert to dict objects (giống ORM objects)
        items = []
        for row in rows:
            items.append({
                'id': row[0],
                'name': row[1], 
                'url_check': row[2],
                'enable': row[3],
                'type': row[4],
                'check_interval_seconds': row[5],
                'user_id': row[6],
                'last_check_status': row[7],
                'count_online': row[8],
                'count_offline': row[9],
                'last_check_time': row[10],
                'result_valid': row[11],
                'result_error': row[12],
                'maxAlertCount': row[13],
                'stopTo': row[14],
                'forceRestart': row[15]
            })
            
        cursor.close()
        conn.close()
        return items
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def get_monitor_item_by_id_raw(monitor_id):
    """
    Raw SQL: Lấy một monitor item theo ID
    
    Args:
        monitor_id (int): ID của monitor item
        
    Returns:
        dict: Monitor item object hoặc None
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, url_check, enable, type, check_interval_seconds,
                   user_id, last_check_status, count_online, count_offline,
                   last_check_time, result_valid, result_error, "maxAlertCount",
                   "stopTo", "forceRestart"
            FROM monitor_items 
            WHERE id = %s AND deleted_at IS NULL
        """, (monitor_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
            
        return {
            'id': row[0],
            'name': row[1], 
            'url_check': row[2],
            'enable': row[3],
            'type': row[4],
            'check_interval_seconds': row[5],
            'user_id': row[6],
            'last_check_status': row[7],
            'count_online': row[8],
            'count_offline': row[9],
            'last_check_time': row[10],
            'result_valid': row[11],
            'result_error': row[12],
            'maxAlertCount': row[13],
            'stopTo': row[14],
            'forceRestart': row[15]
        }
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def update_monitor_result_raw(monitor_id, status):
    """
    Raw SQL: Update monitor result và tăng counter
    
    Args:
        monitor_id (int): ID của monitor
        status (int): 1=success, -1=error
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        if status == 1:  # Success
            cursor.execute("""
                UPDATE monitor_items 
                SET last_check_status = %s,
                    last_check_time = NOW(),
                    count_online = count_online + 1
                WHERE id = %s
            """, (status, monitor_id))
        else:  # Error
            cursor.execute("""
                UPDATE monitor_items 
                SET last_check_status = %s,
                    last_check_time = NOW(),
                    count_offline = count_offline + 1  
                WHERE id = %s
            """, (status, monitor_id))
            
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def reset_monitor_counters_raw(monitor_id):
    """
    Raw SQL: Reset count_online và count_offline về 0
    
    Args:
        monitor_id (int): ID của monitor
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE monitor_items 
            SET count_online = 0, count_offline = 0
            WHERE id = %s
        """, (monitor_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

# ===== ALERT CONFIG QUERIES =====

def get_telegram_config_for_monitor_raw(monitor_id):
    """
    Raw SQL: Lấy cấu hình Telegram cho monitor item
    
    Args:
        monitor_id (int): ID của monitor item
        
    Returns:
        dict: {'bot_token': str, 'chat_id': str} hoặc None
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        # Set search_path for schema (PostgreSQL only)
        from dotenv import load_dotenv
        import os
        load_dotenv()
        db_type = os.getenv('DB_TYPE', 'mysql')
        if db_type == 'postgresql':
            schema_name = os.getenv('TIMESCALEDB_SCHEMA', 'public')
            cursor.execute(f"SET search_path TO {schema_name}, public")
        
        # Join 3 bảng để lấy telegram config
        cursor.execute("""
            SELECT mc.alert_config, mc.name
            FROM monitor_configs mc
            JOIN monitor_and_configs mac ON mc.id = mac.config_id
            WHERE mac.monitor_item_id = %s 
            AND mc.alert_type = 'telegram'
            AND mc.deleted_at IS NULL
            LIMIT 1
        """, (monitor_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or not row[0]:
            return None
            
        # Parse alert_config: <bot_token>,<chat_id>
        alert_config = row[0].strip()
        
        if ',' not in alert_config:
            return None
            
        parts = alert_config.split(',', 1)
        if len(parts) != 2:
            return None
            
        bot_token = parts[1].strip()
        chat_id = parts[0].strip()
        
        # Validate format
        if not bot_token or not chat_id:
            return None
            
        if ':' not in bot_token:
            return None
            
        if not (chat_id.lstrip('-').isdigit() or chat_id.startswith('@')):
            return None
            
        return {
            'bot_token': bot_token,
            'chat_id': chat_id
        }
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def get_webhook_config_for_monitor_raw(monitor_id):
    """
    Raw SQL: Lấy cấu hình webhook cho monitor item
    
    Args:
        monitor_id (int): ID của monitor item
        
    Returns:
        dict: {'webhook_url': str, 'webhook_name': str} hoặc None
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        # Set search_path for schema
        from dotenv import load_dotenv
        import os
        load_dotenv()
        db_type = os.getenv('DB_TYPE', 'mysql')
        schema_name = os.getenv('TIMESCALEDB_SCHEMA', 'public')
        if db_type == 'postgresql':
            cursor.execute(f"SET search_path TO {schema_name}, public")
        
        cursor.execute("""
            SELECT mc.alert_config, mc.name
            FROM monitor_configs mc
            JOIN monitor_and_configs mac ON mc.id = mac.config_id
            WHERE mac.monitor_item_id = %s 
            AND mc.alert_type = 'webhook'
            AND mc.deleted_at IS NULL
            LIMIT 1
        """, (monitor_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row or not row[0]:
            return None
            
        webhook_url = row[0].strip()
        webhook_name = row[1] or f"Webhook for Monitor {monitor_id}"
        
        if not webhook_url.startswith(('http://', 'https://')):
            return None
            
        return {
            'webhook_url': webhook_url,
            'webhook_name': webhook_name
        }
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

def get_all_alert_configs_for_monitor_raw(monitor_id):
    """
    Raw SQL: Lấy tất cả cấu hình alert cho monitor item
    
    Args:
        monitor_id (int): ID của monitor item
        
    Returns:
        list: Danh sách config dicts
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        # Set search_path for schema (PostgreSQL only)
        from dotenv import load_dotenv
        import os
        load_dotenv()
        db_type = os.getenv('DB_TYPE', 'mysql')
        if db_type == 'postgresql':
            schema_name = os.getenv('TIMESCALEDB_SCHEMA', 'public')
            cursor.execute(f"SET search_path TO {schema_name}, public")
        
        cursor.execute("""
            SELECT mc.id, mc.name, mc.alert_type, mc.alert_config
            FROM monitor_configs mc
            JOIN monitor_and_configs mac ON mc.id = mac.config_id
            WHERE mac.monitor_item_id = %s 
            AND mc.deleted_at IS NULL
            ORDER BY mc.id
        """, (monitor_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        configs = []
        for row in rows:
            configs.append({
                'id': row[0],
                'name': row[1],
                'alert_type': row[2],
                'alert_config': row[3]
            })
            
        return configs
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

# ===== MONITOR SETTINGS QUERIES =====

def get_monitor_settings_for_user_raw(user_id):
    """
    Raw SQL: Lấy monitor settings cho user
    
    Args:
        user_id (int): ID của user
        
    Returns:
        dict: Settings object hoặc None
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, status, alert_time_ranges, timezone, 
                   global_stop_alert_to, created_at, updated_at
            FROM monitor_settings 
            WHERE user_id = %s 
            AND deleted_at IS NULL
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
            
        return {
            'id': row[0],
            'user_id': row[1],
            'status': row[2],
            'alert_time_ranges': row[3],
            'timezone': row[4],
            'global_stop_alert_to': row[5],
            'created_at': row[6],
            'updated_at': row[7]
        }
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

# ===== STATISTICS QUERIES =====

def get_monitor_stats_raw():
    """
    Raw SQL: Lấy thống kê tổng quan
    
    Returns:
        dict: Statistics
    """
    conn = None
    cursor = None
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(CASE WHEN enable = 1 THEN 1 END) as enabled_items,
                COUNT(CASE WHEN last_check_status = 1 THEN 1 END) as online_items,
                COUNT(CASE WHEN last_check_status = -1 THEN 1 END) as offline_items,
                SUM(count_online) as total_online_checks,
                SUM(count_offline) as total_offline_checks
            FROM monitor_items 
            WHERE deleted_at IS NULL
        """)
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            'total_items': row[0] or 0,
            'enabled_items': row[1] or 0,
            'online_items': row[2] or 0,
            'offline_items': row[3] or 0,
            'total_online_checks': row[4] or 0,
            'total_offline_checks': row[5] or 0
        }
        
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise e

# ===== TESTING FUNCTION =====

def test_raw_sql_functions():
    """Test tất cả raw SQL functions"""
    try:
        print("🔍 Testing Raw SQL Functions...")
        
        # Test 1: Get enabled items
        print("\n1. Testing get_enabled_items_raw():")
        items = get_enabled_items_raw()
        print(f"   Found {len(items)} enabled items")
        for item in items[:3]:  # Show first 3
            print(f"   - ID: {item['id']}, Name: {item['name']}, Type: {item['type']}")
        
        # Test 2: Get stats
        print("\n2. Testing get_monitor_stats_raw():")
        stats = get_monitor_stats_raw()
        print(f"   Stats: {stats}")
        
        # Test 3: Get telegram config (if exists)
        if items:
            first_id = items[0]['id']
            print(f"\n3. Testing get_telegram_config_for_monitor_raw({first_id}):")
            telegram_config = get_telegram_config_for_monitor_raw(first_id)
            print(f"   Telegram config: {telegram_config}")
        
        print("\n✅ All raw SQL functions working!")
        return True
        
    except Exception as e:
        print(f"\n❌ Raw SQL test failed: {e}")
        return False

if __name__ == "__main__":
    test_raw_sql_functions()
