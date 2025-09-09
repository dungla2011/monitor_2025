#!/usr/bin/env python3
"""
Script tổng hợp cho performance testing với 1000 domains
Hướng dẫn đầy đủ cách chạy test performance
"""

import sys
import subprocess
import os

def print_banner():
    """In banner"""
    print("=" * 80)
    print("🚀 PERFORMANCE TESTING TOOLKIT")
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
    print("  1. Tạo 1000 test domains (6 loại monitor)")
    print("  2. Tạo 3000 test records (1000 domains x 3 loại)")
    print("  3. Chạy performance monitor")
    print("  4. Bắt đầu monitor service (test mode)")
    print("  5. Dừng monitor service")
    print("  6. Xóa 1000 test domains")
    print("  7. Xóa 3000 test records") 
    print("  8. Hướng dẫn manual testing")
    print("  0. Thoát")
    print("  5. Xóa tất cả test domains")
    print("  6. Hướng dẫn manual testing")
    print("  0. Thoát")

def run_script(script_name):
    """Chạy script Python trong thư mục hiện tại"""
    try:
        print(f"🚀 Running {script_name}...")
        result = subprocess.run([sys.executable, script_name], 
                              cwd=os.getcwd(),
                              capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def run_script_parent(script_name, args=None):
    """Chạy script Python trong thư mục cha"""
    try:
        parent_dir = os.path.dirname(os.getcwd())
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        print(f"🚀 Running {script_name} in parent directory...")
        result = subprocess.run(cmd, 
                              cwd=parent_dir,
                              capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def show_manual_guide():
    """Hiển thị hướng dẫn manual"""
    print("\n" + "="*60)
    print("📖 HƯỚNG DẪN MANUAL TESTING")
    print("="*60)
    
    print("\n🔄 CÁCH CHẠY TEST PERFORMANCE:")
    print("Từ thư mục test-1000:")
    
    print("\n1. Activate virtual environment (từ thư mục gốc):")
    print("   cd ..")
    print("   .\\venv\\Scripts\\Activate.ps1")
    print("   cd test-1000")
    
    print("\n2. Tạo 1000 test domains:")
    print("   python create_1000_test_domains.py")
    
    print("\n3. Mở terminal mới và chạy performance monitor:")
    print("   cd test-1000")
    print("   python performance_monitor.py")
    
    print("\n4. Mở terminal thứ 3 và start monitor service (từ thư mục gốc):")
    print("   cd ..")
    print("   python monitor_service.py start --test")
    
    print("\n5. Quan sát performance trong monitor:")
    print("   - CPU usage")
    print("   - Memory usage") 
    print("   - Thread count")
    print("   - Database stats")
    print("   - Test progress")
    
    print("\n6. Sau khi test xong, cleanup:")
    print("   python monitor_service.py stop  # Từ thư mục gốc")
    print("   python cleanup_test_domains.py  # Từ thư mục test-1000")
    
    print("\n📁 CẤU TRÚC THỨ MỤC:")
    print("   monitor_2025/")
    print("   ├── monitor_service.py          # Main service")
    print("   ├── .env.test                   # Test config")
    print("   ├── models.py, db_connection.py # Database modules")
    print("   └── test-1000/")
    print("       ├── create_1000_test_domains.py")
    print("       ├── cleanup_test_domains.py")
    print("       ├── performance_monitor.py")
    print("       └── performance_test_toolkit.py")
    
    print("\n⚠️  LƯU Ý:")
    print("   - Script trong test-1000 đã được cập nhật để import từ thư mục cha")
    print("   - 1000 domains với interval 60s = ~16.7 checks/second")
    print("   - Monitor CPU và Memory usage")
    print("   - Kiểm tra database connection pool")
    print("   - Test trong môi trường test (.env.test)")
    
    print("\n📊 METRICS CẦN QUAN SÁT:")
    print("   - CPU usage không vượt quá 80%")
    print("   - Memory usage ổn định")  
    print("   - Thread count không tăng liên tục")
    print("   - Database response time")
    print("   - Network I/O")
    
    print("\n🎯 KẾT QUẢ MONG MUỐN:")
    print("   - Service ổn định với 1000 concurrent checks")
    print("   - Không memory leak")
    print("   - Response time hợp lý")
    print("   - Error rate thấp")

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
            choice = input("\n❓ Chọn option (0-6): ").strip()
            
            if choice == '0':
                print("👋 Tạm biệt!")
                break
                
            elif choice == '1':
                print("\n🏗️ Tạo 1000 test domains...")
                run_script("create_1000_test_domains.py")
                
            elif choice == '2':
                print("\n📊 Khởi động performance monitor...")
                print("💡 Tip: Mở terminal mới để chạy monitor service từ thư mục gốc")
                run_script("performance_monitor.py")
                
            elif choice == '3':
                print("\n🚀 Bắt đầu monitor service (test mode)...")
                print("💡 Service sẽ chạy với 1000 domains, interval 60s")
                try:
                    run_script_parent("monitor_service.py", ["start", "--test"])
                except KeyboardInterrupt:
                    print("\n🛑 Service stopped by user")
                    
            elif choice == '4':
                print("\n🛑 Dừng monitor service...")
                run_script_parent("monitor_service.py", ["stop"])
                
            elif choice == '5':
                print("\n🧹 Xóa tất cả test domains...")
                run_script("cleanup_test_domains.py")
                
            elif choice == '6':
                show_manual_guide()
                input("\n⏎ Press Enter to continue...")
                
            else:
                print("❌ Option không hợp lệ!")
                
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
