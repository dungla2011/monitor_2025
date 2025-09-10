"""
Script kiểm tra tính nhất quán của code sau khi chuyển sang alert manager class
"""

import os
import sys

def check_monitor_service():
    """Kiểm tra monitor_service.py"""
    print("🔍 Checking monitor_service.py...")
    
    with open('monitor_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kiểm tra import
    if 'class_send_alert_of_thread' in content:
        print("✅ class_send_alert_of_thread được import")
    else:
        print("❌ class_send_alert_of_thread KHÔNG được import")
    
    # Kiểm tra thread_alert_managers
    if 'thread_alert_managers = {}' in content:
        print("✅ thread_alert_managers được khai báo")
    else:
        print("❌ thread_alert_managers KHÔNG được khai báo")
    
    # Kiểm tra old dictionaries
    old_vars = ['telegram_last_sent_of_each_thread', 'thread_consecutive_errors', 'thread_last_alert_time']
    for var in old_vars:
        if f'{var} = {{}}' in content:
            print(f"❌ Old dictionary {var} vẫn còn được khai báo")
        else:
            print(f"✅ Old dictionary {var} đã được loại bỏ")
    
    # Kiểm tra set_monitor_refs call
    if 'thread_alert_managers=thread_alert_managers' in content:
        print("✅ set_monitor_refs gọi với tham số mới")
    else:
        print("❌ set_monitor_refs gọi với tham số cũ")

def check_single_instance_api():
    """Kiểm tra single_instance_api.py"""
    print("\n🔍 Checking single_instance_api.py...")
    
    with open('single_instance_api.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kiểm tra signature của set_monitor_refs
    if 'def set_monitor_refs(self, running_threads, thread_alert_managers' in content:
        print("✅ set_monitor_refs có signature mới")
    else:
        print("❌ set_monitor_refs vẫn có signature cũ")
    
    # Kiểm tra __init__
    if 'self.thread_alert_managers = None' in content:
        print("✅ __init__ có thread_alert_managers")
    else:
        print("❌ __init__ thiếu thread_alert_managers")

def check_utils():
    """Kiểm tra utils.py"""
    print("\n🔍 Checking utils.py...")
    
    if os.path.exists('utils.py'):
        with open('utils.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'class class_send_alert_of_thread:' in content:
            print("✅ class_send_alert_of_thread được định nghĩa trong utils.py")
        else:
            print("❌ class_send_alert_of_thread KHÔNG được định nghĩa trong utils.py")
    else:
        print("❌ utils.py không tồn tại")

if __name__ == "__main__":
    print("🔧 Checking code consistency after alert manager migration...\n")
    
    check_monitor_service()
    check_single_instance_api()
    check_utils()
    
    print("\n✅ Check completed!")
