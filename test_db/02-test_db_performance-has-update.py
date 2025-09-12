#!/usr/bin/env python3
"""
Database Performance Test with UPDATE (copy of file 01 + UPDATE)
- Kết nối database từ .env
- Đếm số hàng trong monitor_items
- Tạo N threads cho N hàng
- Mỗi thread: SELECT + UPDATE count_online + 1
- Lặp cứ 1 phút/lần
- Log errors vào error_db.log
- Dừng khi Ctrl+C
- GIỮ NGUYÊN CONNECTION LEAK như file 01
"""

import os
import sys
import threading
import time
import signal
import logging
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Database connection settings from .env
DB_TYPE = os.getenv('DB_TYPE', 'postgresql')

if DB_TYPE == 'postgresql':
    # Use PostgreSQL configuration
    DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    DB_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    DB_NAME = os.getenv('POSTGRES_NAME', 'monitor_v2')
    DB_USER = os.getenv('POSTGRES_USER', 'postgres')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    print(f"🔗 Using PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")
else:
    # Fallback to legacy DB_* variables
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'monitor_v2')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    print(f"🔗 Using Legacy DB config: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Global variables
shutdown_event = threading.Event()
active_threads = []
stats_lock = threading.Lock()
stats = {
    'total_queries': 0,
    'successful_queries': 0,
    'failed_queries': 0,
    'threads_running': 0
}

# Setup error logging - vừa ghi file VÀ in màn hình
error_logger = logging.getLogger('db_error')
error_logger.setLevel(logging.ERROR)

# File handler - ghi vào error_db.log
file_handler = logging.FileHandler('error_db.log')
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter('%(asctime)s - Thread-%(thread)d - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)

# Console handler - in ra màn hình
console_error_handler = logging.StreamHandler()
console_error_handler.setLevel(logging.ERROR)
console_error_formatter = logging.Formatter('❌ %(asctime)s - %(message)s', '%H:%M:%S')
console_error_handler.setFormatter(console_error_formatter)

# Add both handlers to error logger
error_logger.addHandler(file_handler)
error_logger.addHandler(console_error_handler)

# Setup console logging for stats only
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S')
console_handler.setFormatter(console_formatter)

console_logger = logging.getLogger('console')
console_logger.setLevel(logging.INFO)
console_logger.addHandler(console_handler)

def get_db_connection():
    """Tạo kết nối database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        error_logger.error(f"Failed to connect to database: {e}")
        raise

def count_monitor_items():
    """Đếm số hàng trong bảng monitor_items"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM monitor_items")
        result = cursor.fetchone()
        count = result['count']
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        error_logger.error(f"Failed to count monitor_items: {e}")
        raise

def get_monitor_item_ids():
    """Lấy danh sách tất cả IDs từ monitor_items"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM monitor_items ORDER BY id")
        results = cursor.fetchall()
        ids = [row['id'] for row in results]
        cursor.close()
        conn.close()
        return ids
    except Exception as e:
        error_logger.error(f"Failed to get monitor_item ids: {e}")
        raise

def update_stats(success=True):
    """Cập nhật thống kê"""
    with stats_lock:
        stats['total_queries'] += 1
        if success:
            stats['successful_queries'] += 1
        else:
            stats['failed_queries'] += 1

def monitor_thread(item_id, thread_num):
    """
    Thread monitor cho 1 hàng
    SELECT + UPDATE count_online + 1 cứ 1 phút 1 lần
    """
    with stats_lock:
        stats['threads_running'] += 1
    
    # Thread started silently - only log errors
    
    cycle = 0
    
    try:
        while not shutdown_event.is_set():
            cycle += 1
            
            try:
                # Kết nối và query
                conn = get_db_connection()
                cursor = conn.cursor()
                
                start_time = time.time()
                
                # 1. SELECT current count_online
                cursor.execute(
                    "SELECT id, name, url_check, enable, count_online FROM monitor_items WHERE id = %s",
                    (item_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    current_count = result['count_online'] or 0
                    new_count = current_count + 1
                    
                    # 2. UPDATE count_online + 1
                    cursor.execute(
                        # UUpdate   thêm last_time_check = time hiện tại
                        "UPDATE monitor_items SET count_online = %s, last_check_time = %s WHERE id = %s",
                        (new_count, datetime.now(), item_id) 
                    )
                    
                    # 🚨 THIẾU COMMIT - PHẢI COMMIT ĐỂ LƯU THAY ĐỔI!
                    conn.commit()
                    
                query_time = time.time() - start_time
                
                # 🚨 ĐÓNG CONNECTION TRONG TRY - NẾU CÓ EXCEPTION SAU ĐÂY THÌ LEAK!
                cursor.close()
                conn.close()
                
                if result:
                    update_stats(success=True)
                    # Chỉ log nếu cần debug - bình thường không log
                else:
                    update_stats(success=False)
                    error_logger.error(f"Thread {thread_num} - Item {item_id} not found in cycle {cycle}")
                    
            except Exception as e:
                update_stats(success=False)
                error_logger.error(f"Thread {thread_num} - Item {item_id} - Cycle {cycle}: {e}")
                # 🚨 CONNECTION KHÔNG ĐƯỢC ĐÓNG KHI CÓ EXCEPTION - LEAK!
                
            # Chờ 60 giây hoặc cho đến khi shutdown
            shutdown_event.wait(5)
            
    except Exception as e:
        error_logger.error(f"Thread {thread_num} fatal error: {e}")
        
    finally:
        with stats_lock:
            stats['threads_running'] -= 1
        # Thread stopped silently - only errors are logged

def print_stats():
    """In thống kê định kỳ"""
    while not shutdown_event.is_set():
        time.sleep(30)  # Mỗi 30 giây
        
        with stats_lock:
            current_stats = stats.copy()
            
        success_rate = 0
        if current_stats['total_queries'] > 0:
            success_rate = (current_stats['successful_queries'] / current_stats['total_queries']) * 100
            
        console_logger.info(
            f"📊 STATS - Threads: {current_stats['threads_running']}, "
            f"Queries: {current_stats['total_queries']}, "
            f"Success: {current_stats['successful_queries']}, "
            f"Failed: {current_stats['failed_queries']}, "
            f"Rate: {success_rate:.1f}%"
        )

def signal_handler(signum, frame):
    """Xử lý Ctrl+C"""
    console_logger.info(f"\n🛑 Received signal {signum}, shutting down...")
    shutdown_event.set()

def main():
    """Main function"""
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    console_logger.info("🚀 Starting Database Performance Test with UPDATE")
    console_logger.info(f"🔗 Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    console_logger.info("=" * 80)
    
    try:
        # Đếm số hàng
        console_logger.info("📊 Counting monitor_items...")
        total_count = count_monitor_items()
        console_logger.info(f"� Found {total_count} monitor items")
        
        # Lấy danh sách IDs
        console_logger.info("📋 Getting monitor item IDs...")
        item_ids = get_monitor_item_ids()
        console_logger.info(f"📋 Got {len(item_ids)} item IDs")
        
        # Tạo threads
        console_logger.info(f"� Creating {len(item_ids)} threads...")
        
        for i, item_id in enumerate(item_ids, 1):
            thread = threading.Thread(
                target=monitor_thread,
                args=(item_id, i),
                name=f"Monitor-{i}"
            )
            thread.daemon = True
            active_threads.append(thread)
            thread.start()
            
            # Small delay để không overwhelm database
            time.sleep(0.01)
            
        print(f"✅ Started {len(active_threads)} monitor threads")
        
        # Start stats thread
        stats_thread = threading.Thread(target=print_stats, name="Stats")
        stats_thread.daemon = True
        stats_thread.start()
        
        # Main loop - chờ cho đến khi shutdown
        print("🔄 Monitoring started - Press Ctrl+C to stop")
        print("� Stats will be printed every 30 seconds")
        print("❌ Errors (if any) will be logged to error_db.log")
        print("-" * 80)
        
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except Exception as e:
        console_logger.error(f"❌ Main error: {e}")
        error_logger.error(f"Main function error: {e}")
        
    finally:
        # Cleanup
        print("\n🔄 Shutting down threads...")
        shutdown_event.set()
        
        # Chờ threads kết thúc (tối đa 10 giây)
        for thread in active_threads:
            thread.join(timeout=10)
            
        # Final stats
        with stats_lock:
            final_stats = stats.copy()
            
        print("=" * 80)
        console_logger.info("📊 FINAL STATISTICS:")
        console_logger.info(f"   Total Queries: {final_stats['total_queries']}")
        console_logger.info(f"   Successful: {final_stats['successful_queries']}")
        console_logger.info(f"   Failed: {final_stats['failed_queries']}")
        
        if final_stats['total_queries'] > 0:
            success_rate = (final_stats['successful_queries'] / final_stats['total_queries']) * 100
            console_logger.info(f"   Success Rate: {success_rate:.2f}%")
            
        console_logger.info("✅ Database Performance Test with UPDATE completed")

if __name__ == "__main__":
    main()
