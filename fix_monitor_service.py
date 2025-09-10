"""
Script to directly fix the set_monitor_refs call in monitor_service.py
"""

def fix_monitor_service():
    """Fix the monitor_service.py file"""
    print("🔧 Fixing monitor_service.py...")
    
    # Read the file
    try:
        with open('monitor_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📏 Original file: {len(content.splitlines())} lines")
        
        # Replace the set_monitor_refs call
        old_call = """api.set_monitor_refs(
            running_threads=running_threads,
            thread_consecutive_errors=thread_consecutive_errors,
            thread_last_alert_time=thread_last_alert_time,
            get_all_monitor_items=get_all_monitor_items,
            shutdown_event=shutdown_event
        )"""
        
        new_call = """api.set_monitor_refs(
            running_threads=running_threads,
            thread_alert_managers=thread_alert_managers,
            get_all_monitor_items=get_all_monitor_items,
            shutdown_event=shutdown_event
        )"""
        
        if old_call in content:
            content = content.replace(old_call, new_call)
            print("✅ Replaced set_monitor_refs call")
        else:
            print("❌ Could not find old set_monitor_refs call")
            # Try a more flexible approach
            import re
            pattern = r'api\.set_monitor_refs\(\s*running_threads=running_threads,\s*thread_consecutive_errors=thread_consecutive_errors,\s*thread_last_alert_time=thread_last_alert_time,\s*get_all_monitor_items=get_all_monitor_items,\s*shutdown_event=shutdown_event\s*\)'
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                content = re.sub(pattern, """api.set_monitor_refs(
            running_threads=running_threads,
            thread_alert_managers=thread_alert_managers,
            get_all_monitor_items=get_all_monitor_items,
            shutdown_event=shutdown_event
        )""", content, flags=re.MULTILINE | re.DOTALL)
                print("✅ Used regex to replace set_monitor_refs call")
            else:
                print("❌ Could not find call with regex either")
        
        # Add import if missing
        if 'class_send_alert_of_thread' not in content:
            content = content.replace('from utils import ol1', 'from utils import ol1, class_send_alert_of_thread')
            print("✅ Added class_send_alert_of_thread import")
        
        # Add thread_alert_managers if missing
        if 'thread_alert_managers = {}' not in content:
            # Find where to add it (after shutdown_event)
            if 'shutdown_event = threading.Event()' in content:
                insertion_point = 'shutdown_event = threading.Event()  # Event để signal shutdown'
                new_section = """shutdown_event = threading.Event()  # Event để signal shutdown
stop_flags = {}  # Dictionary để signal stop cho từng thread riêng biệt

# Alert management - Dictionary chứa alert object cho mỗi thread
thread_alert_managers = {}  # {thread_id: class_send_alert_of_thread_instance}
thread_alert_lock = threading.Lock()  # Lock để thread-safe khi truy cập alert managers"""
                content = content.replace(insertion_point, new_section)
                print("✅ Added thread_alert_managers declaration")
        
        # Add helper functions if missing
        if 'def get_alert_manager(' not in content:
            helper_functions = '''

def get_alert_manager(thread_id):
    """
    Lấy alert manager cho thread ID, tạo mới nếu chưa có
    """
    with thread_alert_lock:
        if thread_id not in thread_alert_managers:
            thread_alert_managers[thread_id] = class_send_alert_of_thread(thread_id)
        return thread_alert_managers[thread_id]


def cleanup_alert_manager(thread_id):
    """
    Cleanup alert manager khi thread kết thúc
    """
    with thread_alert_lock:
        if thread_id in thread_alert_managers:
            del thread_alert_managers[thread_id]

'''
            # Insert after the constants
            if 'EXTENDED_ALERT_INTERVAL_MINUTES = 5' in content:
                content = content.replace('EXTENDED_ALERT_INTERVAL_MINUTES = 5', 'EXTENDED_ALERT_INTERVAL_MINUTES = 5' + helper_functions)
                print("✅ Added helper functions")
        
        # Write the fixed content
        with open('monitor_service.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📏 Fixed file: {len(content.splitlines())} lines")
        print("✅ monitor_service.py has been fixed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_monitor_service()
