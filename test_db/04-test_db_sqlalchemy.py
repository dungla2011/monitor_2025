#!/usr/bin/env python3
"""
Database Performance Test with UPDATE using SQLAlchemy (copy of file 02 + SQLAlchemy)
- Kết nối database từ .env
- Đếm số hàng trong monitor_items
- Tạo N threads cho N hàng
- Mỗi thread: SELECT + UPDATE count_online + 1
- Lặp cứ 1 phút/lần
- Log errors vào error_db.log
- Dừng khi Ctrl+C
- GIỮ NGUYÊN CONNECTION LEAK như file 01/02
- SỬ DỤNG SQLAlchemy thay vì psycopg2
"""

import os
import sys
import threading
import time
import signal
import logging
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
    print(f"🔗 Using PostgreSQL with SQLAlchemy: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Fallback to legacy DB_* variables
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'monitor_v2')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    print(f"🔗 Using Legacy DB config with SQLAlchemy: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    pool_size=10000,
    max_overflow=10000,
    pool_timeout=10,
    pool_recycle=3600,
    echo=False  # Set True for SQL debug
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define model (simple table definition)
Base = declarative_base()

class MonitorItem(Base):
    __tablename__ = "monitor_items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url_check = Column(String)
    enable = Column(Integer)
    last_check_time = Column(DateTime)
    count_online = Column(Integer)

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

def get_db_session():
    """Tạo SQLAlchemy session"""
    try:
        session = SessionLocal()
        return session
    except Exception as e:
        error_logger.error(f"Failed to create SQLAlchemy session: {e}")
        raise

def count_monitor_items():
    """Đếm số hàng trong bảng monitor_items"""
    try:
        session = get_db_session()
        count = session.query(MonitorItem).count()
        session.close()
        return count
    except Exception as e:
        error_logger.error(f"Failed to count monitor_items: {e}")
        raise

def get_monitor_item_ids():
    """Lấy danh sách tất cả IDs từ monitor_items"""
    try:
        session = get_db_session()
        result = session.query(MonitorItem.id).order_by(MonitorItem.id).all()
        ids = [row[0] for row in result]
        session.close()
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
    SELECT + UPDATE count_online + 1 cứ 1 phút 1 lần using SQLAlchemy
    """
    with stats_lock:
        stats['threads_running'] += 1
    
    # Thread started silently - only log errors
    
    cycle = 0
    
    try:
        while not shutdown_event.is_set():
            cycle += 1
            
            try:
                # Tạo SQLAlchemy session
                session = get_db_session()
                
                start_time = time.time()
                
                # 1. SELECT current record using SQLAlchemy ORM
                monitor_item = session.query(MonitorItem).filter(MonitorItem.id == item_id).first()
                
                if monitor_item:
                    current_count = monitor_item.count_online or 0
                    new_count = current_count + 1
                    
                    # 2. UPDATE count_online + 1 using SQLAlchemy ORM
                    monitor_item.count_online = new_count

                    #thêm last_check_time = time hiện tại
                    monitor_item.last_check_time = datetime.now()
                    
                    # 🚨 COMMIT ĐỂ LƯU THAY ĐỔI!
                    session.commit()
                    
                    query_time = time.time() - start_time
                    
                    # 🚨 ĐÓNG SESSION TRONG TRY - NẾU CÓ EXCEPTION SAU ĐÂY THÌ LEAK!
                    session.close()
                    
                    update_stats(success=True)
                    # Chỉ log nếu cần debug - bình thường không log
                    
                else:
                    session.close()
                    update_stats(success=False)
                    error_logger.error(f"Thread {thread_num} - Item {item_id} not found in cycle {cycle}")
                    
            except Exception as e:
                update_stats(success=False)
                error_logger.error(f"Thread {thread_num} - Item {item_id} - Cycle {cycle}: {e}")
                # 🚨 SESSION KHÔNG ĐƯỢC ĐÓNG KHI CÓ EXCEPTION - LEAK!
            # Chờ 5 giây hoặc cho đến khi shutdown
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
    
    console_logger.info("🚀 Starting Database Performance Test with UPDATE (SQLAlchemy)")
    console_logger.info(f"🔗 Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    console_logger.info("🎯 Using SQLAlchemy ORM instead of raw psycopg2")
    console_logger.info("=" * 80)
    
    try:
        # Test connection
        console_logger.info("🔍 Testing SQLAlchemy connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            console_logger.info(f"✅ SQLAlchemy connection successful: {result[0]}")
        
        # Đếm số hàng
        console_logger.info("📊 Counting monitor_items...")
        total_count = count_monitor_items()
        console_logger.info(f"📊 Found {total_count} monitor items")
        
        # Lấy danh sách IDs
        console_logger.info("📋 Getting monitor item IDs...")
        item_ids = get_monitor_item_ids()
        console_logger.info(f"📋 Got {len(item_ids)} item IDs")
        
        # Tạo threads
        console_logger.info(f"🔧 Creating {len(item_ids)} threads...")
        
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
        print("📈 Stats will be printed every 30 seconds")
        print("❌ Errors (if any) will be logged to error_db.log")
        print("🎯 Using SQLAlchemy ORM for database operations")
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
            
        # Close engine
        engine.dispose()
        console_logger.info("🎯 SQLAlchemy engine disposed")
        console_logger.info("✅ Database Performance Test with SQLAlchemy completed")

if __name__ == "__main__":
    main()
