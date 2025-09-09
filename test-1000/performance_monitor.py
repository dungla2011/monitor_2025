#!/usr/bin/env python3
"""
Script monitor performance trong lúc chạy 1000 thread test
Hiển thị real-time stats về CPU, Memory, Thread count, Database stats
"""

import time
import psutil
import threading
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load test environment
print("🧪 Loading test environment (.env.test)")
load_dotenv(os.path.join('..', '.env.test'))

from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Create session factory
SessionLocal = sessionmaker(bind=engine)

class PerformanceMonitor:
    """Monitor system performance during test"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.start_time = None
        
    def get_database_stats(self):
        """Lấy thống kê database"""
        session = SessionLocal()
        try:
            total_items = session.query(MonitorItem).count()
            enabled_items = session.query(MonitorItem).filter(MonitorItem.enable == True).count()
            test_1k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).filter(~MonitorItem.name.like('TEST_3K_%')).count()
            test_3k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_3K_%')).count()
            
            # Thống kê status
            online_items = session.query(MonitorItem).filter(MonitorItem.last_check_status == 1).count()
            offline_items = session.query(MonitorItem).filter(MonitorItem.last_check_status == -1).count()
            pending_items = session.query(MonitorItem).filter(MonitorItem.last_check_status.is_(None)).count()
            
            return {
                'total': total_items,
                'enabled': enabled_items,
                'test_1k': test_1k_items,
                'test_3k': test_3k_items,
                'online': online_items,
                'offline': offline_items,
                'pending': pending_items
            }
        except Exception as e:
            return {'error': str(e)}
        finally:
            session.close()
    
    def get_system_stats(self):
        """Lấy thống kê hệ thống"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Process info
            current_process = psutil.Process()
            process_memory = current_process.memory_info().rss / (1024**2)  # MB
            process_cpu = current_process.cpu_percent()
            
            # Thread count
            thread_count = current_process.num_threads()
            
            # Network
            net_io = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_percent': memory_percent,
                'memory_used_gb': memory_used_gb,
                'memory_total_gb': memory_total_gb,
                'process_memory_mb': process_memory,
                'process_cpu_percent': process_cpu,
                'thread_count': thread_count,
                'net_bytes_sent': net_io.bytes_sent,
                'net_bytes_recv': net_io.bytes_recv
            }
        except Exception as e:
            return {'error': str(e)}
    
    def display_stats(self):
        """Hiển thị stats"""
        while self.running:
            try:
                # Clear screen (Windows)
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                
                current_time = datetime.now()
                uptime = current_time - self.start_time if self.start_time else "N/A"
                
                print("=" * 80)
                print(f"🔥 PERFORMANCE MONITOR - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⏱️  Uptime: {uptime}")
                print("=" * 80)
                
                # System stats
                sys_stats = self.get_system_stats()
                if 'error' not in sys_stats:
                    print("🖥️  SYSTEM PERFORMANCE:")
                    print(f"   CPU Usage: {sys_stats['cpu_percent']:.1f}% ({sys_stats['cpu_count']} cores)")
                    print(f"   Memory: {sys_stats['memory_used_gb']:.2f}GB / {sys_stats['memory_total_gb']:.2f}GB ({sys_stats['memory_percent']:.1f}%)")
                    print(f"   Process CPU: {sys_stats['process_cpu_percent']:.1f}%")
                    print(f"   Process Memory: {sys_stats['process_memory_mb']:.1f}MB")
                    print(f"   Thread Count: {sys_stats['thread_count']}")
                    print(f"   Network: ↑{sys_stats['net_bytes_sent']/(1024**2):.1f}MB ↓{sys_stats['net_bytes_recv']/(1024**2):.1f}MB")
                else:
                    print(f"🖥️  SYSTEM ERROR: {sys_stats['error']}")
                
                print()
                
                # Database stats
                db_stats = self.get_database_stats()
                if 'error' not in db_stats:
                    print("💾 DATABASE STATS:")
                    print(f"   Total Items: {db_stats['total']}")
                    print(f"   Enabled Items: {db_stats['enabled']}")
                    print(f"   Test 1K Items: {db_stats['test_1k']} (1000 domains test)")
                    print(f"   Test 3K Items: {db_stats['test_3k']} (3000 records test)")
                    print(f"   Status - Online: {db_stats['online']} | Offline: {db_stats['offline']} | Pending: {db_stats['pending']}")
                    
                    # Progress calculation for both test types
                    if db_stats['test_1k'] > 0:
                        completed_1k = db_stats['online'] + db_stats['offline']
                        progress_1k = min(100, (completed_1k / db_stats['test_1k']) * 100) if db_stats['test_1k'] > 0 else 0
                        print(f"   1K Test Progress: {completed_1k}/{db_stats['test_1k']} ({progress_1k:.1f}%)")
                    
                    if db_stats['test_3k'] > 0:
                        completed_3k = db_stats['online'] + db_stats['offline'] 
                        progress_3k = min(100, (completed_3k / db_stats['test_3k']) * 100) if db_stats['test_3k'] > 0 else 0
                        expected_load = db_stats['test_3k'] / 60
                        print(f"   3K Test Progress: {completed_3k}/{db_stats['test_3k']} ({progress_3k:.1f}%)")
                        print(f"   3K Expected Load: ~{expected_load:.1f} checks/second")
                else:
                    print(f"💾 DATABASE ERROR: {db_stats['error']}")
                
                print()
                print("💡 Press Ctrl+C to stop monitoring")
                print("=" * 80)
                
                # Sleep for 5 seconds
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopping performance monitor...")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(5)
    
    def start(self):
        """Bắt đầu monitor"""
        if self.running:
            print("⚠️ Monitor is already running")
            return
        
        self.running = True
        self.start_time = datetime.now()
        print("🚀 Starting performance monitor...")
        
        # Start monitor in separate thread
        self.monitor_thread = threading.Thread(target=self.display_stats)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        try:
            self.monitor_thread.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Dừng monitor"""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        print("✅ Performance monitor stopped")

def main():
    """Main function"""
    print("=" * 60)
    print("📊 PERFORMANCE MONITOR FOR 1000 THREAD TEST")
    print("=" * 60)
    
    monitor = PerformanceMonitor()
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        monitor.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
