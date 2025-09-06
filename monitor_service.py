import time
import requests
import subprocess
import platform
import threading
from urllib.parse import urlparse
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Global dictionary để track running threads
running_threads = {}
thread_lock = threading.Lock()
shutdown_event = threading.Event()  # Event để signal shutdown
stop_flags = {}  # Dictionary để signal stop cho từng thread riêng biệt

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def extract_domain_from_url(url):
    """
    Trích xuất domain từ URL
    Ví dụ: https://glx.com.vn/path -> glx.com.vn
    """
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception as e:
        print(f"❌ Error parsing URL {url}: {e}")
        return None

def ping_icmp(host, timeout=5):
    """
    Ping ICMP đến host
    Returns: (success: bool, response_time: float or None, error_message: str)
    """
    try:
        # Xác định command ping dựa trên OS
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), host]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if result.returncode == 0:
            return True, response_time, "Ping successful"
        else:
            return False, None, f"Ping failed: {result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return False, None, f"Ping timeout after {timeout} seconds"
    except Exception as e:
        return False, None, f"Ping error: {str(e)}"

def ping_web(url, timeout=10):
    """
    Kiểm tra HTTP/HTTPS URL
    Returns: (success: bool, status_code: int or None, response_time: float, error_message: str)
    """
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            return True, response.status_code, response_time, "HTTP request successful"
        else:
            return False, response.status_code, response_time, f"HTTP {response.status_code}: {response.reason}"
            
    except requests.exceptions.Timeout:
        return False, None, None, f"HTTP timeout after {timeout} seconds"
    except requests.exceptions.ConnectionError:
        return False, None, None, "Connection error - cannot reach server"
    except requests.exceptions.RequestException as e:
        return False, None, None, f"HTTP request error: {str(e)}"
    except Exception as e:
        return False, None, None, f"Unexpected error: {str(e)}"

def check_service(monitor_item):
    """
    Kiểm tra một dịch vụ dựa trên thông tin trong database
    
    Args:
        monitor_item: MonitorItem object from database
        
    Returns:
        dict: Kết quả kiểm tra với các key: success, response_time, message, details
    """
    # Đặt giá trị mặc định cho timeRangeSeconds nếu None hoặc 0
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    
    print(f"\n🔍 Checking service: {monitor_item.name} (ID: {monitor_item.id})")
    print(f"   Type: {monitor_item.type}")
    print(f"   URL: {monitor_item.url_check}")
    print(f"   Check interval: {check_interval}s")
    
    result = {
        'monitor_item_id': monitor_item.id,
        'name': monitor_item.name,
        'type': monitor_item.type,
        'url_check': monitor_item.url_check,
        'check_interval': check_interval,
        'check_time': datetime.now(),
        'success': False,
        'response_time': None,
        'message': '',
        'details': {}
    }
    
    if not monitor_item.url_check:
        result['message'] = "❌ No URL to check"
        return result
    
    if monitor_item.type == 'ping_web':
        print("   🌐 Performing HTTP/HTTPS check...")
        success, status_code, response_time, message = ping_web(monitor_item.url_check)
        
        result['success'] = success
        result['response_time'] = response_time
        result['message'] = message
        result['details'] = {
            'status_code': status_code,
            'method': 'HTTP GET'
        }
        
        if success:
            print(f"   ✅ {message} (Status: {status_code}, Time: {response_time:.2f}ms)")
        else:
            print(f"   ❌ {message}")
            
    elif monitor_item.type == 'ping_icmp':
        # Trích xuất domain từ URL
        host = extract_domain_from_url(monitor_item.url_check)
        if not host:
            result['message'] = "❌ Cannot extract domain from URL"
            return result
            
        print(f"   🏓 Performing ICMP ping to: {host}")
        success, response_time, message = ping_icmp(host)
        
        result['success'] = success
        result['response_time'] = response_time
        result['message'] = message
        result['details'] = {
            'host': host,
            'method': 'ICMP ping'
        }
        
        if success:
            print(f"   ✅ {message} (Time: {response_time:.2f}ms)")
        else:
            print(f"   ❌ {message}")
            
    else:
        result['message'] = f"❌ Unknown service type: {monitor_item.type}"
        print(f"   {result['message']}")
    
    return result

def get_monitor_item_by_id(item_id):
    """
    Lấy monitor item từ database theo ID
    
    Args:
        item_id: ID của monitor item
        
    Returns:
        MonitorItem object hoặc None nếu không tìm thấy
    """
    try:
        session = SessionLocal()
        item = session.query(MonitorItem).filter(MonitorItem.id == item_id).first()
        session.close()
        return item
    except Exception as e:
        print(f"❌ Error getting monitor item {item_id}: {e}")
        return None

def compare_monitor_item_fields(original_item, current_item):
    """
    So sánh các trường quan trọng của monitor item
    
    Args:
        original_item: MonitorItem ban đầu
        current_item: MonitorItem hiện tại từ DB
        
    Returns:
        tuple: (has_changes: bool, changes: list)
    """
    if not current_item:
        return True, ["Item not found in database"]
    
    # Các trường cần theo dõi thay đổi
    fields_to_check = [
        ('enable', 'enable'),
        ('name', 'name'),
        ('user_id', 'user_id'),
        ('url_check', 'url_check'),
        ('type', 'type'),
        ('maxAlertCount', 'maxAlertCount'),
        ('timeRangeSeconds', 'timeRangeSeconds'),
        ('result_check', 'result_check'),
        ('result_error', 'result_error'),
        ('stopTo', 'stopTo'),
        ('forceRestart', 'forceRestart')
    ]
    
    changes = []
    
    for field_name, attr_name in fields_to_check:
        original_value = getattr(original_item, attr_name)
        current_value = getattr(current_item, attr_name)
        
        if original_value != current_value:
            changes.append(f"{field_name}: {original_value} -> {current_value}")
    
    return len(changes) > 0, changes

def check_monitor_enable_status(monitor_item_id):
    """
    Kiểm tra trạng thái enable của monitor item từ database
    
    Args:
        monitor_item_id: ID của monitor item
        
    Returns:
        bool: True nếu enable=1, False nếu enable=0/NULL/empty
    """
    try:
        session = SessionLocal()
        item = session.query(MonitorItem).filter(MonitorItem.id == monitor_item_id).first()
        session.close()
        
        if item and item.enable:
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Error checking enable status: {e}")
        return False
    """
    Kiểm tra trạng thái enable của monitor item từ database
    
    Args:
        monitor_item_id: ID của monitor item
        
    Returns:
        bool: True nếu enable=1, False nếu enable=0/NULL/empty
    """
    try:
        session = SessionLocal()
        item = session.query(MonitorItem).filter(MonitorItem.id == monitor_item_id).first()
        session.close()
        
        if item and item.enable:
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Error checking enable status: {e}")
        return False

def monitor_service_thread(monitor_item):
    """
    Monitor một dịch vụ trong thread riêng biệt
    
    Args:
        monitor_item: MonitorItem object from database
    """
    thread_name = f"Monitor-{monitor_item.id}-{monitor_item.name}"
    threading.current_thread().name = thread_name
    
    # Lưu trữ giá trị ban đầu để so sánh
    original_item = MonitorItem()
    original_item.enable = monitor_item.enable
    original_item.name = monitor_item.name
    original_item.user_id = monitor_item.user_id
    original_item.url_check = monitor_item.url_check
    original_item.type = monitor_item.type
    original_item.maxAlertCount = monitor_item.maxAlertCount
    original_item.timeRangeSeconds = monitor_item.timeRangeSeconds
    original_item.result_check = monitor_item.result_check
    original_item.result_error = monitor_item.result_error
    original_item.stopTo = monitor_item.stopTo
    original_item.forceRestart = monitor_item.forceRestart
    
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    check_count = 0
    
    print(f"🚀 [Thread {monitor_item.id}] Starting monitoring for: {monitor_item.name}")
    print(f"   [Thread {monitor_item.id}] Check interval: {check_interval} seconds")
    print(f"   [Thread {monitor_item.id}] Type: {monitor_item.type}")
    print(f"   [Thread {monitor_item.id}] Monitoring config changes...")
    
    try:
        last_check_time = 0
        
        while not shutdown_event.is_set():  # Check shutdown event
            current_time = time.time()
            
            # Kiểm tra nếu đã đủ thời gian để check service
            if current_time - last_check_time >= check_interval:
                check_count += 1
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n📊 [Thread {monitor_item.id}] Check #{check_count} at {timestamp}")
                
                # Kiểm tra dịch vụ (không in chi tiết để tránh spam log)
                result = check_service_silent(monitor_item)
                
                # Hiển thị kết quả ngắn gọn
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                print(f"   [Thread {monitor_item.id}] {status} | {response_time_str} | {monitor_item.name} ({monitor_item.type})")
                
                last_check_time = current_time
            
            # Sleep 3 giây hoặc cho đến khi shutdown
            if shutdown_event.wait(timeout=3):
                break
                
            # Kiểm tra stop flag riêng cho thread này
            if stop_flags.get(monitor_item.id, False):
                print(f"\n🛑 [Thread {monitor_item.id}] Received stop signal from MainThread")
                break
            
            # Lấy item hiện tại từ database để so sánh
            current_item = get_monitor_item_by_id(monitor_item.id)
            
            if not current_item:
                print(f"\n🛑 [Thread {monitor_item.id}] Item not found in database. Stopping {monitor_item.name} after {check_count} checks.")
                break
            
            # So sánh các trường quan trọng
            has_changes, changes = compare_monitor_item_fields(original_item, current_item)
            
            if has_changes:
                print(f"\n🔄 [Thread {monitor_item.id}] Configuration changes detected for {monitor_item.name}:")
                for change in changes:
                    print(f"   - {change}")
                print(f"🛑 [Thread {monitor_item.id}] Stopping thread due to config changes after {check_count} checks.")
                break
            
            # Kiểm tra enable status riêng (để có log rõ ràng)
            if not current_item.enable:
                print(f"\n🛑 [Thread {monitor_item.id}] Monitor disabled (enable=0). Stopping {monitor_item.name} after {check_count} checks.")
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 [Thread {monitor_item.id}] Monitor stopped by user after {check_count} checks.")
    except Exception as e:
        print(f"\n❌ [Thread {monitor_item.id}] Monitor error for {monitor_item.name}: {e}")
    finally:
        # Remove thread from tracking và clear stop flag
        with thread_lock:
            if monitor_item.id in running_threads:
                del running_threads[monitor_item.id]
            if monitor_item.id in stop_flags:
                del stop_flags[monitor_item.id]
            print(f"🧹 [Thread {monitor_item.id}] Thread cleanup completed for {monitor_item.name}")

def check_service_silent(monitor_item):
    """
    Kiểm tra service nhưng không print ra log chi tiết (dành cho multi-thread)
    
    Args:
        monitor_item: MonitorItem object from database
        
    Returns:
        dict: Kết quả kiểm tra
    """
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    
    result = {
        'monitor_item_id': monitor_item.id,
        'name': monitor_item.name,
        'type': monitor_item.type,
        'url_check': monitor_item.url_check,
        'check_interval': check_interval,
        'check_time': datetime.now(),
        'success': False,
        'response_time': None,
        'message': '',
        'details': {}
    }
    
    if not monitor_item.url_check:
        result['message'] = "No URL to check"
        return result
    
    if monitor_item.type == 'ping_web':
        success, status_code, response_time, message = ping_web(monitor_item.url_check)
        result['success'] = success
        result['response_time'] = response_time
        result['message'] = message
        result['details'] = {'status_code': status_code, 'method': 'HTTP GET'}
        
    elif monitor_item.type == 'ping_icmp':
        host = extract_domain_from_url(monitor_item.url_check)
        if not host:
            result['message'] = "Cannot extract domain from URL"
            return result
            
        success, response_time, message = ping_icmp(host)
        result['success'] = success
        result['response_time'] = response_time
        result['message'] = message
        result['details'] = {'host': host, 'method': 'ICMP ping'}
        
    else:
        result['message'] = f"Unknown service type: {monitor_item.type}"
    
    return result

def monitor_service_loop(monitor_item):
    """
    Monitor một dịch vụ liên tục vô tận với sleep 3 giây và check enable status
    (Single thread version - để tương thích với code cũ)
    
    Args:
        monitor_item: MonitorItem object from database
    """
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    check_count = 0
    
    print(f"🚀 Starting continuous monitoring for: {monitor_item.name}")
    print(f"   Check interval: {check_interval} seconds")
    print(f"   Sleep interval: 3 seconds (checking enable status)")
    print("   Duration: Unlimited (until enable=0 or stopped)")
    print("="*80)
    
    try:
        last_check_time = 0
        
        while True:
            current_time = time.time()
            
            # Kiểm tra nếu đã đủ thời gian để check service
            if current_time - last_check_time >= check_interval:
                check_count += 1
                print(f"\n📊 Check #{check_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Kiểm tra dịch vụ
                result = check_service(monitor_item)
                
                # Hiển thị kết quả ngắn gọn
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                print(f"   Result: {status} | Time: {response_time_str} | {result['message']}")
                
                last_check_time = current_time
            
            # Sleep 3 giây
            print(f"   ⏰ Sleeping 3 seconds... (Next check in {max(0, check_interval - (current_time - last_check_time)):.0f}s)")
            time.sleep(3)
            
            # Kiểm tra enable status từ database
            if not check_monitor_enable_status(monitor_item.id):
                print(f"\n🛑 Monitor item disabled (enable=0). Stopping monitor after {check_count} checks.")
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 Monitor stopped by user after {check_count} checks.")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")

def start_all_monitors():
    """
    Bắt đầu monitor tất cả enabled items, mỗi item trong một thread riêng biệt
    """
    print("🚀 Starting multi-threaded monitoring for all enabled services...")
    print("="*80)
    
    # Lấy tất cả enabled items
    items = get_all_enabled_monitor_items()
    
    if not items:
        print("❌ No enabled monitor items found in database")
        print("💡 Please enable at least one monitor item (set enable=1) to start monitoring")
        return
    
    print(f"✅ Found {len(items)} enabled monitor items")
    
    # Khởi tạo threads cho mỗi item
    threads = []
    with thread_lock:
        running_threads.clear()
    
    for item in items:
        print(f"   🔧 Setting up thread for: {item.name} (ID: {item.id})")
        thread = threading.Thread(
            target=monitor_service_thread,
            args=(item,),
            name=f"Monitor-{item.id}-{item.name}",
            daemon=True
        )
        threads.append(thread)
        
        with thread_lock:
            running_threads[item.id] = {
                'thread': thread,
                'item': item,
                'start_time': datetime.now()
            }
    
    # Start all threads
    print(f"\n🚀 Starting {len(threads)} monitor threads...")
    for thread in threads:
        thread.start()
        time.sleep(0.1)  # Small delay to avoid overwhelming
    
    print(f"✅ All {len(threads)} monitor threads started successfully!")
    print("="*80)
    
    try:
        # Monitor thread status
        while True:
            time.sleep(10)  # Check thread status every 10 seconds
            
            with thread_lock:
                active_count = len([t for t in running_threads.values() if t['thread'].is_alive()])
                total_count = len(running_threads)
            
            if active_count == 0:
                print("🏁 All monitor threads have stopped.")
                break
            else:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n📊 [{timestamp}] Active threads: {active_count}/{total_count}")
                
                # Show thread status
                with thread_lock:
                    for item_id, thread_info in running_threads.items():
                        if thread_info['thread'].is_alive():
                            runtime = datetime.now() - thread_info['start_time']
                            print(f"   🟢 {thread_info['item'].name} (ID: {item_id}) - Running for {runtime}")
                        else:
                            print(f"   🔴 {thread_info['item'].name} (ID: {item_id}) - Stopped")
    
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down all monitor threads...")
        
        # Wait for all threads to finish
        for thread_info in running_threads.values():
            if thread_info['thread'].is_alive():
                print(f"   ⏳ Waiting for {thread_info['item'].name} to stop...")
                thread_info['thread'].join(timeout=5)
        
        print("✅ All monitor threads stopped.")

def show_thread_status():
    """
    Hiển thị trạng thái của tất cả threads đang chạy
    """
    with thread_lock:
        if not running_threads:
            print("❌ No monitor threads are currently running")
            return
        
        print(f"📊 Monitor Thread Status ({len(running_threads)} threads)")
        print("-" * 80)
        
        for item_id, thread_info in running_threads.items():
            status = "🟢 Running" if thread_info['thread'].is_alive() else "🔴 Stopped"
            runtime = datetime.now() - thread_info['start_time']
            print(f"ID: {item_id:2d} | {thread_info['item'].name:20s} | {status} | Runtime: {runtime}")
        
        active_count = len([t for t in running_threads.values() if t['thread'].is_alive()])
        print(f"\nActive: {active_count}/{len(running_threads)} threads")

def get_enabled_items_from_db():
    """
    Lấy tất cả enabled monitor items từ database
    """
    try:
        session = SessionLocal()
        items = session.query(MonitorItem).filter(
            MonitorItem.url_check.isnot(None),
            MonitorItem.url_check != '',
            MonitorItem.enable == True
        ).all()
        session.close()
        return items
    except Exception as e:
        print(f"❌ Error getting enabled items: {e}")
        return []

def get_running_item_ids():
    """
    Lấy danh sách ID của các items đang chạy
    """
    with thread_lock:
        return [item_id for item_id, thread_info in running_threads.items() 
                if thread_info['thread'].is_alive()]

def start_monitor_thread(monitor_item):
    """
    Bắt đầu một monitor thread cho item
    """
    print(f"🔧 [Main] Starting thread for: {monitor_item.name} (ID: {monitor_item.id})")
    
    thread = threading.Thread(
        target=monitor_service_thread,
        args=(monitor_item,),
        name=f"Monitor-{monitor_item.id}-{monitor_item.name}",
        daemon=True
    )
    
    with thread_lock:
        running_threads[monitor_item.id] = {
            'thread': thread,
            'item': monitor_item,
            'start_time': datetime.now()
        }
    
    thread.start()
    return thread

def force_stop_monitor_thread(item_id):
    """
    Force stop một monitor thread bằng cách set stop flag
    (MainThread có thể "kill" thread này)
    """
    with thread_lock:
        if item_id in running_threads:
            thread_info = running_threads[item_id]
            item_name = thread_info['item'].name
            print(f"💀 [Main] Force stopping thread: {item_name} (ID: {item_id})")
            
            # Set stop flag cho thread đó
            stop_flags[item_id] = True
            
            # Chờ thread stop (timeout 10 giây)
            if thread_info['thread'].is_alive():
                thread_info['thread'].join(timeout=10)
                if thread_info['thread'].is_alive():
                    print(f"⚠️ [Main] Thread {item_id} did not stop within timeout (may need process restart)")
                else:
                    print(f"✅ [Main] Thread {item_id} stopped successfully")
            
            return True
    return False

def stop_monitor_thread(item_id):
    """
    Dừng một monitor thread (bằng cách đánh dấu để nó tự dừng)
    """
    with thread_lock:
        if item_id in running_threads:
            thread_info = running_threads[item_id]
            item_name = thread_info['item'].name
            print(f"🛑 [Main] Requesting stop for: {item_name} (ID: {item_id})")
            
            # Thread sẽ tự dừng khi kiểm tra enable status
            # Chờ thread tự cleanup
            if thread_info['thread'].is_alive():
                # Set timeout để tránh wait vô hạn
                thread_info['thread'].join(timeout=10)
                if thread_info['thread'].is_alive():
                    print(f"⚠️ [Main] Thread {item_id} did not stop gracefully within timeout")
            
            return True
    return False

def cleanup_dead_threads():
    """
    Dọn dẹp các threads đã chết
    """
    with thread_lock:
        dead_threads = []
        for item_id, thread_info in running_threads.items():
            if not thread_info['thread'].is_alive():
                dead_threads.append(item_id)
        
        for item_id in dead_threads:
            thread_info = running_threads.pop(item_id)
            print(f"🧹 [Main] Cleaned up dead thread: {thread_info['item'].name} (ID: {item_id})")

def main_manager_loop():
    """
    Main thread quản lý tự động các monitor threads
    Chạy vòng lặp 5 giây một lần để:
    1. Kiểm tra items enabled trong DB
    2. So sánh với running threads
    3. Start threads cho items mới enabled
    4. Stop threads cho items bị disabled
    """
    print("🚀 Starting Main Thread Manager...")
    print("   ⏰ Check interval: 5 seconds")
    print("   🔄 Auto-manage monitor threads based on database")
    print("="*80)
    
    cycle_count = 0
    
    try:
        while not shutdown_event.is_set():
            cycle_count += 1
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Lấy enabled items từ DB
            enabled_items = get_enabled_items_from_db()
            enabled_ids = {item.id for item in enabled_items}
            
            # Lấy running items
            running_ids = set(get_running_item_ids())
            
            # Cleanup dead threads trước
            cleanup_dead_threads()
            
            # Tìm items cần start (enabled trong DB nhưng chưa running)
            items_to_start = enabled_ids - running_ids
            
            # Tìm items cần stop (running nhưng không enabled trong DB)  
            items_to_stop = running_ids - enabled_ids
            
            if cycle_count % 12 == 1:  # Print status every 60 seconds (12 * 5s)
                print(f"\n📊 [Main Manager] Cycle #{cycle_count} at {timestamp}")
                print(f"   💾 DB Enabled: {len(enabled_ids)} items {list(enabled_ids)}")
                print(f"   🏃 Running: {len(running_ids)} threads {list(running_ids)}")
                if items_to_start:
                    print(f"   ➕ Need to start: {list(items_to_start)}")
                if items_to_stop:
                    print(f"   ➖ Need to stop: {list(items_to_stop)}")
            
            # Start new threads
            for item_id in items_to_start:
                item = next((item for item in enabled_items if item.id == item_id), None)
                if item:
                    start_monitor_thread(item)
                    time.sleep(0.1)  # Small delay between starts
            
            # Stop threads for disabled items với force stop
            for item_id in items_to_stop:
                force_stop_monitor_thread(item_id)
            
            # Wait 5 seconds or until shutdown
            if shutdown_event.wait(timeout=5):
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 [Main Manager] Shutting down after {cycle_count} cycles...")
    except Exception as e:
        print(f"\n❌ [Main Manager] Error: {e}")
    finally:
        # Signal shutdown to all threads
        shutdown_event.set()
        
        # Set stop flags for all threads
        with thread_lock:
            for item_id in running_threads.keys():
                stop_flags[item_id] = True
        
        print("🛑 [Main Manager] Stopping all monitor threads...")
        with thread_lock:
            for item_id, thread_info in running_threads.items():
                if thread_info['thread'].is_alive():
                    print(f"   ⏳ Waiting for {thread_info['item'].name} (ID: {item_id}) to stop...")
                    thread_info['thread'].join(timeout=10)
        
        print("✅ [Main Manager] All threads stopped. Manager shutdown complete.")

def monitor_service_loop(monitor_item):
    """
    Monitor một dịch vụ liên tục vô tận với sleep 3 giây và check enable status
    
    Args:
        monitor_item: MonitorItem object from database
    """
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    check_count = 0
    
    print(f"🚀 Starting continuous monitoring for: {monitor_item.name}")
    print(f"   Check interval: {check_interval} seconds")
    print(f"   Sleep interval: 3 seconds (checking enable status)")
    print("   Duration: Unlimited (until enable=0 or stopped)")
    print("="*80)
    
    try:
        last_check_time = 0
        
        while True:
            current_time = time.time()
            
            # Kiểm tra nếu đã đủ thời gian để check service
            if current_time - last_check_time >= check_interval:
                check_count += 1
                print(f"\n📊 Check #{check_count} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Kiểm tra dịch vụ
                result = check_service(monitor_item)
                
                # Hiển thị kết quả ngắn gọn
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                print(f"   Result: {status} | Time: {response_time_str} | {result['message']}")
                
                last_check_time = current_time
            
            # Sleep 3 giây
            print(f"   ⏰ Sleeping 3 seconds... (Next check in {max(0, check_interval - (current_time - last_check_time)):.0f}s)")
            time.sleep(3)
            
            # Kiểm tra enable status từ database
            if not check_monitor_enable_status(monitor_item.id):
                print(f"\n🛑 Monitor item disabled (enable=0). Stopping monitor after {check_count} checks.")
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 Monitor stopped by user after {check_count} checks.")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")

def get_all_enabled_monitor_items():
    """
    Lấy tất cả monitor items đang enabled
    """
    try:
        session = SessionLocal()
        items = session.query(MonitorItem).filter(
            MonitorItem.url_check.isnot(None),
            MonitorItem.url_check != '',
            MonitorItem.enable == True
        ).all()
        session.close()
        return items
    except Exception as e:
        print(f"❌ Error getting enabled monitor items: {e}")
        return []

def monitor_all_services_once():
    """
    Kiểm tra tất cả dịch vụ enabled một lần
    """
    print("🚀 Checking all enabled services...")
    print("="*80)
    
    items = get_all_enabled_monitor_items()
    
    if not items:
        print("❌ No enabled monitor items found")
        return
    
    results = []
    for item in items:
        result = check_service(item)
        results.append(result)
    
    # Tóm tắt kết quả
    print(f"\n📊 Summary of {len(results)} services:")
    print("-" * 60)
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        response_time_str = f"{result['response_time']:.1f}ms" if result['response_time'] else "N/A"
        print(f"   {status} {result['name']} ({result['type']}) - {response_time_str}")
    
    return results

def get_first_monitor_item():
    """
    Lấy hàng đầu tiên từ bảng monitor_items có enable = 1
    """
    try:
        session = SessionLocal()
        first_item = session.query(MonitorItem).filter(
            MonitorItem.url_check.isnot(None),
            MonitorItem.url_check != '',
            MonitorItem.enable == True  # Chỉ lấy những item đã enabled
        ).first()
        session.close()
        return first_item
    except Exception as e:
        print(f"❌ Error getting first monitor item: {e}")
        return None

def test_first_service():
    """
    Test kiểm tra dịch vụ đầu tiên (chỉ những item đã enabled)
    """
    print("🚀 Testing monitor service checker...")
    print("="*80)
    
    # Lấy hàng đầu tiên có enable=1
    first_item = get_first_monitor_item()
    
    if not first_item:
        print("❌ No enabled monitor items found in database")
        print("💡 Please enable at least one monitor item (set enable=1) to start testing")
        return
    
    print(f"✅ Found enabled monitor item: {first_item.name} (ID: {first_item.id})")
    print(f"   Enable status: {'✅ Enabled' if first_item.enable else '❌ Disabled'}")
    
    # Kiểm tra dịch vụ
    result = check_service(first_item)
    
    # Hiển thị kết quả chi tiết
    print("\n📊 Check Result Summary:")
    print("-" * 50)
    print(f"Service Name: {result['name']}")
    print(f"Service Type: {result['type']}")
    print(f"URL/Target: {result['url_check']}")
    print(f"Check Interval: {result['check_interval']}s")
    print(f"Check Time: {result['check_time']}")
    print(f"Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"Response Time: {result['response_time']:.2f}ms" if result['response_time'] else "N/A")
    print(f"Message: {result['message']}")
    
    if result['details']:
        print("Details:")
        for key, value in result['details'].items():
            print(f"  - {key}: {value}")
    
    return result

def main():
    """
    Main function với các options khác nhau
    """
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'loop':
            # Monitor dịch vụ đầu tiên liên tục vô tận
            first_item = get_first_monitor_item()
            if first_item:
                print(f"✅ Found enabled monitor item: {first_item.name} (ID: {first_item.id})")
                monitor_service_loop(first_item)
            else:
                print("❌ No enabled monitor items found in database")
                print("💡 Please enable at least one monitor item (set enable=1) to start monitoring")
                
        elif command == 'all':
            # Kiểm tra tất cả dịch vụ enabled một lần
            monitor_all_services_once()
            
        elif command == 'multi' or command == 'multithread':
            # Monitor tất cả enabled services với multi-threading (legacy)
            start_all_monitors()
            
        elif command == 'manager' or command == 'auto':
            # Main thread manager - tự động quản lý threads
            main_manager_loop()
            
        elif command == 'status':
            # Hiển thị trạng thái threads
            show_thread_status()
            
        elif command == 'test':
            # Test dịch vụ đầu tiên
            test_first_service()
            
        else:
            print("Usage:")
            print("  python monitor_service.py test       - Test first service once")
            print("  python monitor_service.py loop       - Monitor first service continuously (single thread)")
            print("  python monitor_service.py manager    - Auto-manage all monitor threads (recommended)")
            print("  python monitor_service.py multi      - Monitor all enabled services (multi-threaded, legacy)")
            print("  python monitor_service.py status     - Show thread status")
            print("  python monitor_service.py all        - Check all enabled services once")
    else:
        # Mặc định: test dịch vụ đầu tiên
        test_first_service()

if __name__ == "__main__":
    main()
