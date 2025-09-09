#!/usr/bin/env python3
"""
Script tổng hợp cho performance testing với 1000 và 3000 domains
Hướng dẫn đầy đủ cách chạy test performance
"""

import sys
import subprocess
import os

def print_banner():
    """In banner"""
    print("=" * 80)
    print("🚀 ADVANCED PERFORMANCE TESTING TOOLKIT")
    print("=" * 80)
    print("Thư mục: test-1000/")
    print("Các script có sẵn:")
    print("  1. create_1000_test_domains.py - Tạo 1000 test domains (6 loại khác nhau)")  
    print("  2. create_3000_test_domains.py - Tạo 3000 test records (1000 domains x 3 loại)")
    print("  3. cleanup_test_domains.py    - Xóa 1000 test domains")
    print("  4. cleanup_3000_test_domains.py - Xóa 3000 test records")
    print("  5. performance_monitor.py     - Monitor hiệu suất realtime")
    print("  6. ../monitor_service.py      - Main monitoring service (thư mục gốc)")
    print("=" * 80)

def show_menu():
    """Hiển thị menu"""
    print("\n📋 MENU:")
    print("  1. 🏗️  Tạo 1000 test domains (6 loại monitor) - ~16.7 checks/sec")
    print("  2. 🔥 Tạo 3000 test records (1000 domains x 3 loại) - ~50 checks/sec")
    print("  3. 📊 Chạy performance monitor")
    print("  4. 🚀 Bắt đầu monitor service (test mode)")
    print("  5. 🛑 Dừng monitor service")
    print("  6. 🧹 Xóa 1000 test domains")
    print("  7. 🧹 Xóa 3000 test records") 
    print("  8. 📖 Hướng dẫn manual testing")
    print("  9. 📊 Hiển thị database statistics")
    print("  0. 👋 Thoát")

def run_script(script_name):
    """Chạy script Python"""
    try:
        print(f"🚀 Running {script_name}...")
        result = subprocess.run([sys.executable, script_name], 
                              cwd=os.getcwd(),
                              capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def run_script_args(args):
    """Chạy script với arguments"""
    try:
        result = subprocess.run([sys.executable] + args, 
                              cwd=os.getcwd(),
                              capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_database_stats():
    """Hiển thị database statistics"""
    try:
        print("\n📊 DATABASE STATISTICS")
        print("=" * 50)
        result = subprocess.run([
            sys.executable, "-c", 
            """
import sys, os
sys.path.insert(0, '..')
from dotenv import load_dotenv
load_dotenv('../.env.test')
from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

session = sessionmaker(bind=engine)()
try:
    total = session.query(MonitorItem).count()
    enabled = session.query(MonitorItem).filter(MonitorItem.enable == True).count()
    test_1k = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).filter(~MonitorItem.name.like('TEST_3K_%')).count()
    test_3k = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_3K_%')).count()
    online = session.query(MonitorItem).filter(MonitorItem.last_check_status == 1).count()
    offline = session.query(MonitorItem).filter(MonitorItem.last_check_status == -1).count()
    pending = session.query(MonitorItem).filter(MonitorItem.last_check_status.is_(None)).count()
    
    print(f"Total items: {total}")
    print(f"Enabled items: {enabled}")
    print(f"1K Test domains: {test_1k}")
    print(f"3K Test records: {test_3k}")
    print(f"Status - Online: {online} | Offline: {offline} | Pending: {pending}")
    
    if test_1k > 0:
        print(f"1K Test load: ~{test_1k/60:.1f} checks/second")
    if test_3k > 0:
        print(f"3K Test load: ~{test_3k/60:.1f} checks/second")
    
    total_test_load = (test_1k + test_3k) / 60
    if total_test_load > 0:
        print(f"Total test load: ~{total_test_load:.1f} checks/second")
        
finally:
    session.close()
            """
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ Error getting stats: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def show_manual_guide():
    """Hiển thị hướng dẫn manual"""
    print("\n" + "="*70)
    print("📖 HƯỚNG DẪN MANUAL TESTING")
    print("="*70)
    
    print("\n🔄 1. LIGHTWEIGHT TEST (1000 domains):")
    print("   Load: ~16.7 checks/second")
    print("   1. python create_1000_test_domains.py")
    print("   2. python performance_monitor.py  # Terminal mới")
    print("   3. cd .. && python monitor_service.py start --test  # Terminal thứ 3")
    print("   4. python cleanup_test_domains.py  # Sau khi test xong")
    
    print("\n🔥 2. INTENSIVE TEST (3000 records):")
    print("   Load: ~50 checks/second - HIGH PERFORMANCE TEST!")
    print("   1. python create_3000_test_domains.py")
    print("   2. python performance_monitor.py  # Terminal mới")
    print("   3. cd .. && python monitor_service.py start --test  # Terminal thứ 3")
    print("   4. python cleanup_3000_test_domains.py  # Sau khi test xong")
    
    print("\n📊 3. PERFORMANCE METRICS TO MONITOR:")
    print("   - CPU usage (should stay under 80%)")
    print("   - Memory usage (watch for leaks)")
    print("   - Thread count (should be stable)")
    print("   - Database response time")
    print("   - Network I/O")
    print("   - Error rate")
    
    print("\n⚠️ 4. PERFORMANCE WARNINGS:")
    print("   - 1K test: Suitable for development testing")
    print("   - 3K test: HIGH LOAD - production-like stress test")
    print("   - Monitor system resources closely during 3K test")
    print("   - Stop test immediately if system becomes unstable")
    
    print("\n🎯 5. EXPECTED RESULTS:")
    print("   - Service should handle load without crashes")
    print("   - Memory usage should stabilize (no leaks)")
    print("   - Response times should remain reasonable")
    print("   - Error rates should be low (<5%)")
    
    print("\n📁 6. TEST DATA:")
    print("   - 1000 real domains from major websites")
    print("   - 3 test types: web_content, ping_icmp, ssl_expired_check")
    print("   - 60 second intervals for all tests")
    print("   - Uses test database (.env.test)")

def main():
    """Main function"""
    print_banner()
    
    # Check if we're in the correct directory
    current_dir = os.path.basename(os.getcwd())
    if current_dir != "test-1000":
        print("⚠️  Warning: Nên chạy script này từ thư mục test-1000")
        print(f"   Current directory: {os.getcwd()}")
    
    while True:
        show_menu()
        
        try:
            choice = input("\n❓ Chọn option (0-9): ").strip()
            
            if choice == '0':
                print("👋 Tạm biệt!")
                break
                
            elif choice == '1':
                print("\n🏗️ Tạo 1000 test domains (6 loại monitor)...")
                print("💡 Load: ~16.7 checks/second")
                run_script("create_1000_test_domains.py")
                
            elif choice == '2':
                print("\n🔥 Tạo 3000 test records (1000 domains x 3 loại)...")
                print("⚠️  CẢNH BÁO: Load cao ~50 checks/second!")
                print("   Điều này có thể gây tải nặng cho hệ thống!")
                confirm = input("❓ Bạn có chắc chắn muốn tiếp tục? (y/N): ").lower().strip()
                if confirm in ['y', 'yes']:
                    run_script("create_3000_test_domains.py")
                else:
                    print("❌ Đã hủy tạo 3000 test records")
                
            elif choice == '3':
                print("\n📊 Khởi động performance monitor...")
                print("💡 Tip: Monitor sẽ hiển thị stats realtime cho cả 1K và 3K tests")
                run_script("performance_monitor.py")
                
            elif choice == '4':
                print("\n🚀 Bắt đầu monitor service (test mode)...")
                print("💡 Service sẽ chạy với tất cả test domains/records")
                try:
                    subprocess.run([sys.executable, "../monitor_service.py", "start", "--test"])
                except KeyboardInterrupt:
                    print("\n🛑 Service stopped by user")
                    
            elif choice == '5':
                print("\n🛑 Dừng monitor service...")
                run_script_args(["../monitor_service.py", "stop"])
                
            elif choice == '6':
                print("\n🧹 Xóa 1000 test domains...")
                run_script("cleanup_test_domains.py")
                
            elif choice == '7':
                print("\n🧹 Xóa 3000 test records...")
                run_script("cleanup_3000_test_domains.py")
                
            elif choice == '8':
                show_manual_guide()
                input("\n⏎ Press Enter to continue...")
                
            elif choice == '9':
                show_database_stats()
                input("\n⏎ Press Enter to continue...")
                
            else:
                print("❌ Option không hợp lệ! Chọn từ 0-9")
                
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Tạm biệt!")
        sys.exit(0)
