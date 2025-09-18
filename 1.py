#!/usr/bin/env python3
"""
Script to insert 3000 test monitor items into database
"""

import sys
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import database helpers
from sql_helpers import get_database_config
import pymysql
import psycopg2

def insert_test_monitors():
    """Insert 3000 test monitor items"""
    
    # Get database config
    db_config = get_database_config()
    
    print(f"[INFO] Connecting to {db_config['type']} database...")
    print(f"[INFO] Host: {db_config['host']}:{db_config['port']}")
    print(f"[INFO] Database: {db_config['database']}")
    
    start_time = time.time()
    
    try:
        if db_config['type'] == 'mysql':
            # MySQL connection
            connection = pymysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                charset='utf8mb4',
                autocommit=True
            )
            cursor = connection.cursor()
            
            # MySQL INSERT query
            insert_query = """
                INSERT INTO monitor_items (
                    name, enable, url_check, type, check_interval_seconds,
                    user_id, last_check_status, result_valid, result_error,
                    count_online, count_offline, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
            """
            
        else:
            # PostgreSQL connection
            connection = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database']
            )
            connection.autocommit = True
            cursor = connection.cursor()
            
            # PostgreSQL INSERT query
            insert_query = """
                INSERT INTO monitor_items (
                    name, enable, url_check, type, check_interval_seconds,
                    user_id, last_check_status, result_valid, result_error,
                    count_online, count_offline, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                ) RETURNING id
            """
        
        print(f"[START] Inserting 3000 test monitor items...")
        
        # Batch insert for better performance
        batch_size = 100
        total_inserted = 0
        
        for batch_start in range(0, 3000, batch_size):
            batch_end = min(batch_start + batch_size, 3000)
            batch_data = []
            
            for i in range(batch_start, batch_end):
                monitor_name = f"TEST_3K_{i+1:04d}_web_content_check"
                enable = 1  # Enabled by default
                url_check = f"http://10.0.0.66/1.php?check_x={{ID}}"  # Placeholder for ID
                monitor_type = "web_content"
                check_interval_seconds = 60  # 1 minute
                user_id = 1
                last_check_status = 0  # Not checked yet
                result_valid = ""  # Empty - no specific text required
                result_error = ""  # Empty - no error text to avoid
                count_online = 0
                count_offline = 0
                
                batch_data.append((
                    monitor_name, enable, url_check, monitor_type, check_interval_seconds,
                    user_id, last_check_status, result_valid, result_error,
                    count_online, count_offline
                ))
            
            # Insert batch
            if db_config['type'] == 'mysql':
                cursor.executemany(insert_query, batch_data)
                # Get last inserted ID range for MySQL
                cursor.execute("SELECT LAST_INSERT_ID()")
                last_id = cursor.fetchone()[0]
                first_id = last_id - len(batch_data) + 1
                
                # Update URLs with actual IDs
                for i, data in enumerate(batch_data):
                    actual_id = first_id + i
                    actual_url = f"http://10.0.0.66/1.php?check_x={actual_id}"
                    cursor.execute(
                        "UPDATE monitor_items SET url_check = %s WHERE id = %s",
                        (actual_url, actual_id)
                    )
                    
            else:
                # PostgreSQL - insert one by one to get IDs
                for data in batch_data:
                    cursor.execute(insert_query, data)
                    new_id = cursor.fetchone()[0]
                    actual_url = f"http://10.0.0.66/1.php?check_x={new_id}"
                    cursor.execute(
                        "UPDATE monitor_items SET url_check = %s WHERE id = %s",
                        (actual_url, new_id)
                    )
            
            total_inserted += len(batch_data)
            
            # Progress report
            progress = (total_inserted / 3000) * 100
            print(f"[PROGRESS] Inserted {total_inserted}/3000 monitors ({progress:.1f}%)")
        
        elapsed_time = time.time() - start_time
        print(f"\n[SUCCESS] Successfully inserted 3000 monitor items!")
        print(f"[STATS] Total time: {elapsed_time:.2f} seconds")
        print(f"[STATS] Average: {3000/elapsed_time:.1f} inserts/second")
        
        # Show sample of inserted data
        print(f"\n[SAMPLE] Sample inserted monitors:")
        cursor.execute("SELECT id, name, url_check FROM monitor_items WHERE type = 'web_content' ORDER BY id DESC LIMIT 5")
        samples = cursor.fetchall()
        
        for sample in samples:
            if db_config['type'] == 'mysql':
                monitor_id, name, url = sample
            else:
                monitor_id, name, url = sample
            print(f"  ID: {monitor_id} | Name: {name} | URL: {url}")
        
        # Show total count
        cursor.execute("SELECT COUNT(*) FROM monitor_items WHERE type = 'web_content'")
        total_web_content = cursor.fetchone()[0]
        print(f"\n[INFO] Total web_content monitors in database: {total_web_content}")
        
    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
        print(f"[CLEANUP] Database connection closed")
    
    return True

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        print("=" * 80)
        print("TEST MONITOR INSERTION SCRIPT")
        print("=" * 80)
        print("This script will insert 3000 test monitor items with:")
        print("  - Type: web_content")
        print("  - URL: http://10.0.0.66/1.php?check_x=<id>")
        print("  - Interval: 60 seconds")
        print("  - Enable: 1 (enabled)")
        print("=" * 80)
        
        confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
        if confirm == 'yes':
            success = insert_test_monitors()
            if success:
                print(f"\n🎉 SUCCESS! You can now test with:")
                print(f"   python monitor_service_asyncio.py start --limit=100")
                print(f"   python monitor_service_asyncio.py start --chunk=1-500")
            else:
                print(f"\n❌ FAILED! Check the error messages above.")
        else:
            print("[CANCELLED] Operation cancelled by user")
    else:
        print("Test Monitor Insertion Script")
        print("=" * 40)
        print("This script will insert 3000 test web_content monitors")
        print("into the monitor_items table for testing AsyncIO performance.")
        print("")
        print("Usage:")
        print("  python insert_test_monitors.py --confirm")
        print("")
        print("What will be inserted:")
        print("  - 3000 monitors with type='web_content'")
        print("  - URLs: http://10.0.0.66/1.php?check_x=<id>")
        print("  - All monitors enabled (enable=1)")
        print("  - Check interval: 60 seconds")
        print("  - Names: TEST_3K_0001_web_content_check, etc.")
        print("")
        print("⚠️  WARNING: This will add 3000 rows to your database!")
        print("   Make sure you have enough space and this is a test environment.")

if __name__ == "__main__":
    main()