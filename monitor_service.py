import time
import requests
import subprocess
import platform
import threading
import os
import sys
from urllib.parse import urlparse
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from db_connection import engine
from models import MonitorItem, get_telegram_config_for_monitor_item, is_alert_time_allowed
from telegram_helper import send_telegram_alert, send_telegram_recovery

# Load environment variables
load_dotenv()


# Global dictionary để track running threads
running_threads = {} 
thread_lock = threading.Lock()
shutdown_event = threading.Event()  # Event để signal shutdown
stop_flags = {}  # Dictionary để signal stop cho từng thread riêng biệt

# Telegram notification throttling
telegram_last_sent = {}  # Dictionary để track thời gian gửi Telegram cuối cùng
TELEGRAM_THROTTLE_SECONDS = 30  # 30 giây giữa các notification giống nhau

# Error tracking cho từng thread
thread_consecutive_errors = {}  # Dictionary để track số lần lỗi liên tiếp của từng thread
CONSECUTIVE_ERROR_THRESHOLD = 10  # Số lần lỗi liên tiếp trước khi giãn alert
EXTENDED_ALERT_INTERVAL_MINUTES = 5  # Số phút giãn alert sau khi quá ngưỡng (0 = không giãn)
thread_last_alert_time = {}  # Dictionary để track thời gian gửi alert cuối cùng của từng thread

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def ol1(msg):
    print(msg)
    # Ghi log ra file với utf-8 encoding:
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

def send_telegram_notification(monitor_item, is_error=True, error_message="", response_time=None):
    """
    Gửi thông báo Telegram với logic lỗi liên tiếp và giãn alert
    
    Args:
        monitor_item: MonitorItem object
        is_error (bool): True nếu là lỗi, False nếu là phục hồi
        error_message (str): Thông báo lỗi
        response_time (float): Thời gian phản hồi (ms) cho trường hợp phục hồi
    """
    try:
        # Kiểm tra TELEGRAM_ENABLED từ .env (global setting)
        telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
        if not telegram_enabled:
            return
        
        thread_id = monitor_item.id
        current_time = time.time()
        
        # Xử lý logic lỗi liên tiếp
        if is_error:
            # Tăng counter lỗi liên tiếp
            thread_consecutive_errors[thread_id] = thread_consecutive_errors.get(thread_id, 0) + 1
            consecutive_errors = thread_consecutive_errors[thread_id]
            
            ol1(f"📊 [Thread {thread_id}] Consecutive errors: {consecutive_errors}")
            
            # Kiểm tra check interval
            check_interval_seconds = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
            check_interval_minutes = check_interval_seconds / 60
            
            # Logic giãn alert nếu:
            # 1. Check interval < 5 phút
            # 2. Lỗi liên tiếp >= 10 lần
            # 3. EXTENDED_ALERT_INTERVAL_MINUTES > 0
            should_throttle_extended = (
                check_interval_minutes < 5 and
                consecutive_errors > CONSECUTIVE_ERROR_THRESHOLD and
                EXTENDED_ALERT_INTERVAL_MINUTES > 0
            )
            
            if should_throttle_extended:
                # Kiểm tra thời gian gửi alert cuối cùng
                last_alert_time = thread_last_alert_time.get(thread_id, 0)
                time_since_last_alert = current_time - last_alert_time
                extended_throttle_seconds = EXTENDED_ALERT_INTERVAL_MINUTES * 60
                
                if time_since_last_alert < extended_throttle_seconds:
                    remaining_minutes = (extended_throttle_seconds - time_since_last_alert) / 60
                    ol1(f"🔕 [Thread {thread_id}] Extended alert throttle active ({remaining_minutes:.1f}m remaining)")
                    return
                
                ol1(f"⚠️ [Thread {thread_id}] Sending extended throttled alert (every {EXTENDED_ALERT_INTERVAL_MINUTES}m after {CONSECUTIVE_ERROR_THRESHOLD} consecutive errors)")
            
        else:
            # Phục hồi - reset counter lỗi liên tiếp
            if thread_id in thread_consecutive_errors:
                consecutive_errors = thread_consecutive_errors[thread_id]
                thread_consecutive_errors[thread_id] = 0
                ol1(f"✅ [Thread {thread_id}] Service recovered! Reset consecutive error count (was: {consecutive_errors})")
        
        # Kiểm tra user alert time settings trước khi gửi
        user_id = monitor_item.user_id if monitor_item.user_id else 0
        is_allowed, reason = is_alert_time_allowed(user_id)
        
        if not is_allowed:
            ol1(f"🔕 [Thread {thread_id}] Alert blocked for user {user_id}: {reason}")
            return
        else:
            ol1(f"✅ [Thread {thread_id}] Alert allowed for user {user_id}: {reason}")
        
        # Lấy config Telegram
        telegram_config = get_telegram_config_for_monitor_item(monitor_item.id)
        
        if not telegram_config:
            # Fallback to .env config
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                ol1(f"⚠️ [Thread {thread_id}] No Telegram config found (database or .env)")
                return
        else:
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config['chat_id']
            ol1(f"📱 [Thread {thread_id}] Using database Telegram config")
        
        # Basic throttling (30 giây giữa các notification giống nhau)
        notification_key = f"{monitor_item.name}_{thread_id}_{is_error}"
        
        if notification_key in telegram_last_sent:
            time_since_last = current_time - telegram_last_sent[notification_key]
            if time_since_last < TELEGRAM_THROTTLE_SECONDS:
                remaining = TELEGRAM_THROTTLE_SECONDS - time_since_last
                ol1(f"🔇 [Thread {thread_id}] Basic throttle active ({remaining:.0f}s remaining)")
                return
        
        # Cập nhật thời gian gửi
        telegram_last_sent[notification_key] = current_time
        if is_error:
            thread_last_alert_time[thread_id] = current_time
        
        # Gửi notification
        if is_error:
            consecutive_errors = thread_consecutive_errors.get(thread_id, 0)
            enhanced_error_message = f"{error_message} (Lỗi liên tiếp: {consecutive_errors})"
            
            result = send_telegram_alert(
                bot_token=bot_token,
                chat_id=chat_id,
                url_admin=f"https://monitor.mytree.vn/member/monitor-item/edit/{monitor_item.id}",
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                error_message=enhanced_error_message
            )
            if result['success']:
                ol1(f"📱 [Thread {thread_id}] Telegram alert sent successfully")
            else:
                ol1(f"❌ [Thread {thread_id}] Telegram alert failed: {result['message']}")
        else:
            result = send_telegram_recovery(
                bot_token=bot_token,
                chat_id=chat_id,
                service_name=monitor_item.name,
                url_admin=f"https://monitor.mytree.vn/member/monitor-item/edit/{monitor_item.id}",
                service_url=monitor_item.url_check,
                response_time=response_time or 0
            )
            if result['success']:
                ol1(f"📱 [Thread {thread_id}] Telegram recovery notification sent successfully")
            else:
                ol1(f"❌ [Thread {thread_id}] Telegram recovery notification failed: {result['message']}")
                
    except Exception as e:
        ol1(f"❌ [Thread {monitor_item.id}] Telegram notification error: {e}")


def extract_domain_from_url(url):
    """
    Trích xuất domain từ URL
    Ví dụ: https://glx.com.vn/path -> glx.com.vn
    """
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception as e:
        ol1(f"❌ Error parsing URL {url}: {e}")
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
            stderr_output = result.stderr.strip() if result.stderr else "No error details"
            stdout_output = result.stdout.strip() if result.stdout else ""
            
            # Log chi tiết để debug
            ol1(f"❌ Ping command failed:")
            # ol1(f"   Command: {' '.join(cmd)}")
            # ol1(f"   Return code: {result.returncode}")
            # ol1(f"   STDOUT: {stdout_output}")
            # ol1(f"   STDERR: {stderr_output}")
            
            return False, None, f"Ping failed (code {result.returncode}): {stderr_output}"
            
    except subprocess.TimeoutExpired:
        return False, None, f"Ping timeout after {timeout} seconds"
    except KeyboardInterrupt:
        return False, None, "Ping interrupted by user (Ctrl+C)"
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

def check_ping_web(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra HTTP/HTTPS service với retry logic
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    ol1(f"   🌐 HTTP/HTTPS check (attempt {attempt}/{max_attempts})...")
    
    success, status_code, response_time, message = ping_web(monitor_item.url_check)
    
    result = {
        'success': success,
        'response_time': response_time,
        'message': message,
        'details': {
            'status_code': status_code,
            'method': 'HTTP GET',
            'attempt': attempt
        }
    }
    
    if success:
        ol1(f"   ✅ {message} (Status: {status_code}, Time: {response_time:.2f}ms)")
        return result
    else:
        ol1(f"   ❌ Attempt {attempt}: {message}")
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"   ⏳ Waiting 3 seconds before retry...")
            time.sleep(3)
            return check_ping_web(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"   💥 Failed after {max_attempts} attempts")
            return result

def check_ping_icmp(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra ICMP ping service với retry logic
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    # Trích xuất domain từ URL
    host = extract_domain_from_url(monitor_item.url_check)
    if not host:
        return {
            'success': False,
            'response_time': None,
            'message': "❌ Cannot extract domain from URL",
            'details': {'host': None, 'method': 'ICMP ping', 'attempt': attempt}
        }
    
    ol1(f"   � ICMP ping to {host} (attempt {attempt}/{max_attempts})...")
    
    success, response_time, message = ping_icmp(host)
    
    result = {
        'success': success,
        'response_time': response_time,
        'message': message,
        'details': {
            'host': host,
            'method': 'ICMP ping',
            'attempt': attempt
        }
    }
    
    if success:
        ol1(f"   ✅ {message} (Time: {response_time:.2f}ms)")
        return result
    else:
        ol1(f"   ❌ Attempt {attempt}: {message}")
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"   ⏳ Waiting 3 seconds before retry...")
            time.sleep(3)
            return check_ping_icmp(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"   💥 Failed after {max_attempts} attempts")
            return result

def check_service(monitor_item):
    """
    Kiểm tra một dịch vụ dựa trên thông tin trong database với retry logic
    
    Args:
        monitor_item: MonitorItem object from database
        
    Returns:
        dict: Kết quả kiểm tra với các key: success, response_time, message, details
    """
    # Đặt giá trị mặc định cho timeRangeSeconds nếu None hoặc 0
    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    
    ol1(f"\n🔍 Checking service: {monitor_item.name} (ID: {monitor_item.id})")
    ol1(f"   Type: {monitor_item.type}")
    ol1(f"   URL: {monitor_item.url_check}")
    ol1(f"   Check interval: {check_interval}s")
    ol1(f"   Retry policy: 3 attempts, 3s interval")
    
    base_result = {
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
        base_result['message'] = "❌ No URL to check"
        return base_result
    
    # Gọi hàm kiểm tra phù hợp
    if monitor_item.type == 'ping_web':
        check_result = check_ping_web(monitor_item)
    elif monitor_item.type == 'ping_icmp':
        check_result = check_ping_icmp(monitor_item)
    else:
        base_result['message'] = f"❌ Unknown service type: {monitor_item.type}"
        ol1(f"   {base_result['message']}")
        return base_result
    
    # Merge kết quả
    base_result.update({
        'success': check_result['success'],
        'response_time': check_result['response_time'],
        'message': check_result['message'],
        'details': check_result['details']
    })
    
    # Note: Telegram notification sẽ được xử lý ở thread level để có context đầy đủ
    
    return base_result

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
        ol1(f"❌ Error getting monitor item {item_id}: {e}")
        return None

def update_monitor_item(monitor_item):
    """
    Cập nhật monitor item vào database
    
    Args:
        monitor_item: MonitorItem object đã được modify
    """
    try:
        session = SessionLocal()
        # Lấy item từ DB và cập nhật
        db_item = session.query(MonitorItem).filter(MonitorItem.id == monitor_item.id).first()
        if db_item:
            db_item.last_ok_or_error = monitor_item.last_ok_or_error
            db_item.last_check_time = datetime.now()
            session.commit()
        session.close()
    except Exception as e:
        ol1(f"❌ Error updating monitor item {monitor_item.id}: {e}")
        raise

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
    original_item.last_ok_or_error = monitor_item.last_ok_or_error
    
    check_interval_org = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300

    check_interval = monitor_item.timeRangeSeconds if monitor_item.timeRangeSeconds else 300
    check_count = 0
    
    # Reset counter lỗi liên tiếp khi start thread
    thread_consecutive_errors[monitor_item.id] = 0
    if monitor_item.id in thread_last_alert_time:
        del thread_last_alert_time[monitor_item.id]
    
    ol1(f"🚀 [Thread {monitor_item.id}] Starting monitoring for: {monitor_item.name}")
    ol1(f"   [Thread {monitor_item.id}] Check interval: {check_interval} seconds")
    ol1(f"   [Thread {monitor_item.id}] Type: {monitor_item.type}")
    ol1(f"   [Thread {monitor_item.id}] Reset consecutive error counter")
    ol1(f"   [Thread {monitor_item.id}] Monitoring config changes...")
    
    try:
        last_check_time = 0
        
        while not shutdown_event.is_set():  # Check shutdown event
            current_time = time.time()
            
            # Kiểm tra nếu đã đủ thời gian để check service
            if current_time - last_check_time >= check_interval:
                check_count += 1
                timestamp = datetime.now().strftime('%H:%M:%S')
                ol1(f"\n📊 [Thread {monitor_item.id}] Check #{check_count} at {timestamp}")
               
            #    Nếu có monitor_item.stopTo, và nếu stopTo > now thì không chạy check
                if monitor_item.stopTo and monitor_item.stopTo > datetime.now():
                    ol1(f"   ⏸️ [Thread {monitor_item.id}] Monitor is paused until {monitor_item.stopTo}. Skipping check.")
                else:
                    # Kiểm tra dịch vụ với log đầy đủ
                    result = check_service(monitor_item)

                    # Lưu trạng thái cũ để so sánh cho Telegram notification
                    old_status = monitor_item.last_ok_or_error
                    
                    # Cập nhật trạng thái mới
                    new_status = 1 if result['success'] else -1
                    monitor_item.last_ok_or_error = new_status
                    monitor_item.lastCheck = datetime.now()
                    
                    # Gửi Telegram notification dựa trên thay đổi trạng thái
                    if result['success'] and old_status == -1:
                        # Service phục hồi từ lỗi -> OK
                        send_telegram_notification(
                            monitor_item=monitor_item,
                            is_error=False,
                            response_time=result['response_time']
                        )

                    if not result['success']:
                        # Service chuyển từ OK/Unknown -> lỗi
                        send_telegram_notification(
                            monitor_item=monitor_item,
                            is_error=True,
                            error_message=result['message']
                        )

                    # Cập nhật database
                    try:
                        update_monitor_item(monitor_item) 
                    except Exception as e:
                        ol1(f"   ❌ [Thread {monitor_item.id}] Error updating database: {e}")

                    # Hiển thị kết quả ngắn gọn
                    status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                    response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                    ol1(f"   [Thread {monitor_item.id}] {status} | {response_time_str} | {monitor_item.name} ({monitor_item.type})")
                
                last_check_time = current_time
            
            # Sleep 3 giây hoặc cho đến khi shutdown
            if shutdown_event.wait(timeout=3):
                break
                
            # Kiểm tra stop flag riêng cho thread này
            if stop_flags.get(monitor_item.id, False):
                ol1(f"\n🛑 [Thread {monitor_item.id}] Received stop signal from MainThread")
                break
            
            # Lấy item hiện tại từ database để so sánh
            current_item = get_monitor_item_by_id(monitor_item.id)
            
            if not current_item:
                ol1(f"\n🛑 [Thread {monitor_item.id}] Item not found in database. Stopping {monitor_item.name} after {check_count} checks.")
                break
            
            # So sánh các trường quan trọng
            has_changes, changes = compare_monitor_item_fields(original_item, current_item)
            
            if has_changes:
                ol1(f"\n🔄 [Thread {monitor_item.id}] Configuration changes detected for {monitor_item.name}:")
                for change in changes:
                    ol1(f"   - {change}")
                ol1(f"🛑 [Thread {monitor_item.id}] Stopping thread due to config changes after {check_count} checks.")
                break
            
            # Kiểm tra enable status riêng (để có log rõ ràng)
            if not current_item.enable:
                ol1(f"\n🛑 [Thread {monitor_item.id}] Monitor disabled (enable=0). Stopping {monitor_item.name} after {check_count} checks.")
                break
                
    except KeyboardInterrupt:
        ol1(f"\n🛑 [Thread {monitor_item.id}] Monitor stopped by user after {check_count} checks.")
    except Exception as e:
        ol1(f"\n❌ [Thread {monitor_item.id}] Monitor error for {monitor_item.name}: {e}")
    finally:
        # Remove thread from tracking và clear stop flag
        with thread_lock:
            if monitor_item.id in running_threads:
                del running_threads[monitor_item.id]
            if monitor_item.id in stop_flags:
                del stop_flags[monitor_item.id]
            # Cleanup error tracking khi thread dừng
            if monitor_item.id in thread_consecutive_errors:
                del thread_consecutive_errors[monitor_item.id]
            if monitor_item.id in thread_last_alert_time:
                del thread_last_alert_time[monitor_item.id]
            ol1(f"🧹 [Thread {monitor_item.id}] Thread cleanup completed for {monitor_item.name}")

def show_thread_status():
    """
    Hiển thị trạng thái của tất cả threads đang chạy
    """
    with thread_lock:
        if not running_threads:
            ol1("❌ No monitor threads are currently running")
            return
        
        ol1(f"📊 Monitor Thread Status ({len(running_threads)} threads)")
        ol1("-" * 80)
        
        for item_id, thread_info in running_threads.items():
            status = "🟢 Running" if thread_info['thread'].is_alive() else "🔴 Stopped"
            runtime = datetime.now() - thread_info['start_time']
            ol1(f"ID: {item_id:2d} | {thread_info['item'].name:20s} | {status} | Runtime: {runtime}")
        
        active_count = len([t for t in running_threads.values() if t['thread'].is_alive()])
        ol1(f"\nActive: {active_count}/{len(running_threads)} threads")

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
        ol1(f"❌ Error getting enabled items: {e}")
        return []

def get_running_item_ids():
    """
    Lấy danh sách ID của các items đang chạy
    """
    with thread_lock:
        return [item_id for item_id, thread_info in running_threads.items() 
                if thread_info['thread'].is_alive()]

def get_running_item_ids_and_start_time():
    """
    Lấy danh sách ID và thời gian bắt đầu của các items đang chạy
    """
    with thread_lock:
        return {item_id: thread_info['start_time'] for item_id, thread_info in running_threads.items() 
                if thread_info['thread'].is_alive()}

def start_monitor_thread(monitor_item):
    """
    Bắt đầu một monitor thread cho item
    """
    with thread_lock:
        # Kiểm tra xem đã có thread cho item này chưa
        if monitor_item.id in running_threads:
            existing_thread = running_threads[monitor_item.id]['thread']
            if existing_thread.is_alive():
                ol1(f"⚠️ [Main] Thread for {monitor_item.name} (ID: {monitor_item.id}) is already running. Skipping.")
                return existing_thread
            else:
                # Thread cũ đã chết, xóa khỏi tracking
                ol1(f"🧹 [Main] Removing dead thread for {monitor_item.name} (ID: {monitor_item.id})")
                del running_threads[monitor_item.id]
    
    ol1(f"🔧 [Main] Starting thread for: {monitor_item.name} (ID: {monitor_item.id})")
    
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
            ol1(f"💀 [Main] Force stopping thread: {item_name} (ID: {item_id})")
            
            # Set stop flag cho thread đó
            stop_flags[item_id] = True
            
            # Chờ thread stop (timeout 10 giây)
            if thread_info['thread'].is_alive():
                thread_info['thread'].join(timeout=10)
                if thread_info['thread'].is_alive():
                    ol1(f"⚠️ [Main] Thread {item_id} did not stop within timeout (may need process restart)")
                else:
                    ol1(f"✅ [Main] Thread {item_id} stopped successfully")
            
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
            ol1(f"🛑 [Main] Requesting stop for: {item_name} (ID: {item_id})")
            
            # Thread sẽ tự dừng khi kiểm tra enable status
            # Chờ thread tự cleanup
            if thread_info['thread'].is_alive():
                # Set timeout để tránh wait vô hạn
                thread_info['thread'].join(timeout=10)
                if thread_info['thread'].is_alive():
                    ol1(f"⚠️ [Main] Thread {item_id} did not stop gracefully within timeout")
            
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
            ol1(f"🧹 [Main] Cleaned up dead thread: {thread_info['item'].name} (ID: {item_id})")

def main_manager_loop():
    """
    Main thread quản lý tự động các monitor threads
    Chạy vòng lặp 5 giây một lần để:
    1. Kiểm tra items enabled trong DB
    2. So sánh với running threads
    3. Start threads cho items mới enabled
    4. Stop threads cho items bị disabled
    """
    ol1("🚀 Starting Main Thread Manager...")
    ol1("   ⏰ Check interval: 5 seconds")
    ol1("   🔄 Auto-manage monitor threads based on database")
    ol1("="*80)
    
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

            running_ids_and_start_time = get_running_item_ids_and_start_time()

            # Cleanup dead threads trước
            cleanup_dead_threads()
            
            # Tìm items cần start (enabled trong DB nhưng chưa running)
            items_to_start = enabled_ids - running_ids
            
            # Tìm items cần stop (running nhưng không enabled trong DB)  
            items_to_stop = running_ids - enabled_ids
            
            if cycle_count % 12 == 1:  # Print status every 60 seconds (12 * 5s)
                ol1(f"\n📊 [Main Manager] Cycle #{cycle_count} at {timestamp}")
                ol1(f"   💾 DB Enabled: {len(enabled_ids)} items {list(enabled_ids)}")
                ol1(f"   🏃 Running: {len(running_ids)} threads {list(running_ids)}")
                
                # In thời gian bắt đầu của các running threads (chỉ trong status report)
                for item_id, start_time in running_ids_and_start_time.items():
                    ol1(f"      🕒 Thread {item_id} started at {start_time}")
                    
                if items_to_start:
                    ol1(f"   ➕ Need to start: {list(items_to_start)}")
                if items_to_stop:
                    ol1(f"   ➖ Need to stop: {list(items_to_stop)}")
            
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
        ol1(f"\n🛑 [Main Manager] Shutting down after {cycle_count} cycles...")
    except Exception as e:
        ol1(f"\n❌ [Main Manager] Error: {e}")
    finally:
        # Signal shutdown to all threads
        shutdown_event.set()
        
        # Set stop flags for all threads
        with thread_lock:
            for item_id in running_threads.keys():
                stop_flags[item_id] = True
        
        ol1("🛑 [Main Manager] Stopping all monitor threads...")
        with thread_lock:
            for item_id, thread_info in running_threads.items():
                if thread_info['thread'].is_alive():
                    ol1(f"   ⏳ Waiting for {thread_info['item'].name} (ID: {item_id}) to stop...")
                    thread_info['thread'].join(timeout=10)
        
        ol1("✅ [Main Manager] All threads stopped. Manager shutdown complete.")

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
        ol1(f"❌ Error getting enabled monitor items: {e}")
        return []


def main():
    """
    Main function với các options khác nhau
    """
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
            
        if command == 'manager' or command == 'auto':
            # Main thread manager - tự động quản lý threads
            main_manager_loop()
            
        elif command == 'test':
            # Test first enabled service once with retry logic
            enabled_items = get_enabled_items_from_db()
            if enabled_items:
                first_item = enabled_items[0]
                ol1(f"✅ Testing enabled monitor item: {first_item.name} (ID: {first_item.id})")
                ol1(f"   URL: {first_item.url_check}")
                ol1(f"   Type: {first_item.type}")
                ol1("="*80)
                result = check_service(first_item)
                ol1("="*80)
                ol1(f"🏁 Test completed for: {first_item.name}")
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                response_time = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                ol1(f"   Final result: {status} | {response_time} | {result['message']}")
            else:
                ol1("❌ No enabled monitor items found in database")
            
        elif command == 'status':
            # Hiển thị trạng thái threads
            show_thread_status()           
        else:
            ol1("Usage:")
            ol1("  python monitor_service.py test       - Test first service once")            
            ol1("  python monitor_service.py manager    - Auto-manage all monitor threads (recommended)")
            

if __name__ == "__main__":
    main()
