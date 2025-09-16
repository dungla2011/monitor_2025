import time
import threading
import os
import sys
import atexit
import signal
from datetime import datetime
from dotenv import load_dotenv

# Import monitor check functions from separate module
from monitor_checks import (
    extract_domain_from_url,
    ping_icmp,
    check_ssl_certificate,
    check_tcp_port,
    ping_web,
    fetch_web_content,
    check_open_port_tcp_then_error,
    check_ssl_expired_check,
    check_open_port_tcp_then_valid,
    check_ping_web,
    check_ping_icmp,
    check_web_content
)

# Parse command line arguments
def parse_chunk_argument():
    """Parse --chunk argument từ command line"""
    chunk_info = None
    
    for arg in sys.argv:
        if arg.startswith('--chunk='):
            chunk_str = arg.split('=')[1]  # Get "1-300" part
            try:
                parts = chunk_str.split('-')
                if len(parts) == 2:
                    chunk_number = int(parts[0])  # 1, 2, 3...
                    chunk_size = int(parts[1])    # 300
                    chunk_info = {
                        'number': chunk_number,
                        'size': chunk_size,
                        'offset': (chunk_number - 1) * chunk_size,  # 0, 300, 600...
                        'limit': chunk_size
                    }
                    print(f"📦 Chunk mode: #{chunk_number} (offset: {chunk_info['offset']}, limit: {chunk_size})")
                    break
            except ValueError:
                print(f"❌ Invalid chunk format: {chunk_str}. Use format: --chunk=1-300")
    
    return chunk_info

def parse_limit_argument():
    """Parse --limit argument từ command line"""
    limit = None
    
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit_str = arg.split('=')[1]
            try:
                limit = int(limit_str)
                print(f"🔢 Limit mode: Processing maximum {limit} monitor items")
                break
            except ValueError:
                print(f"❌ Invalid limit format: {limit_str}. Use format: --limit=500")
    
    return limit

# Global chunk info
CHUNK_INFO = parse_chunk_argument()

def get_api_port():
    """Get API port, adjusted for chunk mode"""
    base_port = int(os.getenv('HTTP_PORT', 5005))
    
    if CHUNK_INFO:
        # Offset port by chunk number to avoid conflicts
        # Chunk 1 -> port 5005, Chunk 2 -> port 5006, etc.
        chunk_port = base_port + (CHUNK_INFO['number'] - 1)
        ol1(f"🌐 Chunk mode: API port adjusted to {chunk_port} for chunk #{CHUNK_INFO['number']}")
        return chunk_port
    
    return base_port

# Load environment variables FIRST - check for --test argument  
if '--test' in sys.argv or 'test' in sys.argv:
    try:
        print("[TEST MODE] Loading test environment (.env.test)")
    except UnicodeEncodeError:
        print("TEST MODE - Loading test environment (.env.test)")
    load_dotenv('.env.test', override=True)  # Force override existing variables
else:
    load_dotenv()

# Now import modules that depend on environment variables
# NO SQLAlchemy imports needed for raw SQL approach
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy import text
# from db_connection import engine
# Raw SQL helpers - NO SQLAlchemy ORM overhead
from sql_helpers import (
    get_enabled_items_raw,
    get_all_items_raw,
    get_monitor_item_by_id_raw, 
    update_monitor_result_raw,
    get_telegram_config_for_monitor_raw,
    get_webhook_config_for_monitor_raw,
    get_monitor_settings_for_user_raw,
    get_monitor_stats_raw
)

# Keep models for schema definition only (không dùng cho queries)
from models import MonitorItem, is_alert_time_allowed

class MonitorItemDict:
    """Convert dict to object-like access for backward compatibility"""
    def __init__(self, data_dict):
        self._data = data_dict
        for key, value in data_dict.items():
            setattr(self, key, value)
    
    def get(self, key, default=None):
        return self._data.get(key, default)
from telegram_helper import send_telegram_alert, send_telegram_recovery
from webhook_helper import send_webhook_alert, send_webhook_recovery, get_webhook_config_for_monitor_item
from single_instance_api import SingleInstanceManager, MonitorAPI, check_instance_and_get_status
from utils import ol1, class_send_alert_of_thread, class_send_alert_of_thread, format_response_time, olerror, safe_get_env_int, safe_get_env_bool, validate_url, generate_thread_name, format_counter_display

# Single Instance Manager - MUST be initialized after loading environment
instance_manager = SingleInstanceManager()

# Global dictionary để track running threads
running_threads = {} 
thread_lock = threading.Lock()
shutdown_event = threading.Event()  # Event để signal shutdown
stop_flags = {}  # Dictionary để signal stop cho từng thread riêng biệt

# Telegram notification throttling
# Alert management - Dictionary chứa alert object cho mỗi thread
thread_alert_managers = {}  # {thread_id: class_send_alert_of_thread_instance}
thread_alert_lock = threading.Lock()  # Lock để thread-safe khi truy cập alert managers

# Throttle settings - Read from environment variables
TELEGRAM_THROTTLE_SECONDS = safe_get_env_int('TELEGRAM_THROTTLE_SECONDS', 30)  # Giây throttle cho Telegram
CONSECUTIVE_ERROR_THRESHOLD = safe_get_env_int('CONSECUTIVE_ERROR_THRESHOLD', 10)  # Ngưỡng lỗi liên tiếp để giãn alert
EXTENDED_ALERT_INTERVAL_MINUTES = safe_get_env_int('EXTENDED_ALERT_INTERVAL_MINUTES', 5)  # Số phút giãn alert sau khi quá ngưỡng (0 = không giãn)

# ===== CACHE SYSTEM FOR MONITOR ITEMS =====
# Global cache for monitor items to reduce DB queries from 1000/sec to 1/sec
all_monitor_items = {}  # {item_id: MonitorItemDict}
all_monitor_items_index = {}  # {item_id: MonitorItemDict} - same as above for fast lookup

# ===== DELTA TIME TRACKING =====
# Global dictionary để track thời gian check cuối cùng của mỗi monitor
monitor_last_check_times = {}  # {monitor_id: unix_timestamp}
monitor_check_times_lock = threading.Lock()  # Lock để thread-safe
last_get_all_monitor_items = 0  # Unix timestamp
cache_thread = None
cache_lock = threading.Lock()
CACHE_REFRESH_INTERVAL = 1  # seconds - cache refresh every 1 second
CACHE_EXPIRY_SECONDS = 5  # seconds - cache considered fresh for 5 seconds


# ===== CACHE SYSTEM FUNCTIONS =====

def cache_refresh_thread():
    """
    Background thread để refresh cache monitor items mỗi 1 giây
    Giảm DB queries từ 3000 threads × 1 query/3s = 1000 queries/sec xuống 1 query/sec
    """
    global all_monitor_items, all_monitor_items_index, last_get_all_monitor_items
    
    thread_name = "CacheRefresh"
    threading.current_thread().name = thread_name
    
    # Parse limit argument
    limit = parse_limit_argument()
    limit_msg = f" (limit: {limit})" if limit else ""
    
    ol1(f"🗄️ [Cache] Starting cache refresh thread (interval: {CACHE_REFRESH_INTERVAL}s){limit_msg}")
    
    while not shutdown_event.is_set():
        try:
            # Load monitor items from DB using raw SQL with optional limit
            from sql_helpers import get_all_items_raw
            all_items_raw = get_all_items_raw(limit=limit)
            
            # Convert to indexed dictionary for O(1) lookup
            new_cache = {}
            for item_dict in all_items_raw:
                item_obj = MonitorItemDict(item_dict)
                new_cache[item_obj.id] = item_obj
            
            # Update cache atomically
            with cache_lock:
                all_monitor_items = new_cache
                all_monitor_items_index = new_cache  # Same reference for fast lookup
                last_get_all_monitor_items = time.time()
            
            # Log cache stats periodically (every 10 refreshes = 10 seconds)
            if int(time.time()) % 10 == 0:
                enabled_count = len([item for item in new_cache.values() if item.enable])
                disabled_count = len(new_cache) - enabled_count
                limit_info = f" (limit: {limit})" if limit else ""
                ol1(f"🗄️ [Cache] Refreshed: {len(new_cache)} total items ({enabled_count} enabled, {disabled_count} disabled){limit_info}")
            
        except Exception as e:
            ol1(f"❌ [Cache] Error refreshing cache: {e}")
            # Don't break the loop - keep trying
        
        # Wait 1 second or until shutdown
        if shutdown_event.wait(timeout=CACHE_REFRESH_INTERVAL):
            break
    
    ol1(f"🗄️ [Cache] Cache refresh thread stopped")

def start_cache_thread():
    """
    Start cache refresh thread
    """
    global cache_thread
    
    if cache_thread and cache_thread.is_alive():
        ol1("⚠️ [Cache] Cache thread already running")
        return
    
    cache_thread = threading.Thread(
        target=cache_refresh_thread,
        name="CacheRefresh",
        daemon=True
    )
    cache_thread.start()
    
    # Wait a moment for initial cache load
    time.sleep(1.5)  # Give time for first cache load
    ol1(f"✅ [Cache] Cache refresh thread started")

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

# Raw SQL approach - no need for SessionLocal

# Flag để track cleanup đã chạy chưa
cleanup_running = False

def cleanup_on_exit():
    """Cleanup function khi thoát"""
    global instance_manager, cleanup_running, cache_thread
    
    if cleanup_running:
        return  # Tránh cleanup nhiều lần
    
    cleanup_running = True
    ol1("🔄 Cleaning up before exit...")
    
    # Signal all threads to stop
    shutdown_event.set()
    
    # Wait for cache thread to stop
    if cache_thread and cache_thread.is_alive():
        ol1("⏳ Waiting for cache thread to stop...")
        cache_thread.join(timeout=2)
        if cache_thread.is_alive():
            ol1("⚠️ Cache thread still running after timeout")
    
    # Wait for monitor threads to finish (with timeout)
    with thread_lock:
        for thread_id, thread_info in list(running_threads.items()):
            try:
                thread = thread_info['thread'] if isinstance(thread_info, dict) else thread_info
                if thread.is_alive():
                    ol1(f"⏳ Waiting for thread {thread_id} to finish...")
                    thread.join(timeout=2)  # 2 second timeout
                    if thread.is_alive():
                        ol1(f"⚠️ Thread {thread_id} still running after timeout")
            except Exception as e:
                ol1(f"⚠️ Error cleaning up thread {thread_id}: {e}")
                
    # Cleanup instance manager
    if instance_manager:
        instance_manager.cleanup()
    
    ol1("✅ Cleanup completed")

# Register cleanup handlers
atexit.register(cleanup_on_exit)

# Counter để track số lần nhấn Ctrl+C
ctrl_c_count = 0

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global ctrl_c_count
    ctrl_c_count += 1
    
    ol1(f"🛑 Received signal {signum}, shutting down... (press Ctrl+C again for force exit)")
    
    if ctrl_c_count >= 2:
        ol1("⚡ Force exit - killing process immediately!")
        os._exit(1)  # Force exit không đợi cleanup
    
    cleanup_on_exit()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# === DATABASE OPERATIONS ===

def test_db_connection_main_thread(retry_delay=10):
    """
    Raw SQL: Test DB connection cho MAIN THREAD - retry vô hạn
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            from sql_helpers import get_raw_connection
            conn = get_raw_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            if attempt > 1:
                ol1(f"✅ DATABASE RECOVERED after {attempt-1} failed attempts (main thread)")
            return True
        except Exception as e:
            ol1(f"⚠️ Main thread DB connection failed (attempt {attempt}): {e}")
            ol1(f"🔄 Main thread retrying in {retry_delay} seconds... (will retry forever)")
            time.sleep(retry_delay)

def test_db_connection_worker_thread():
    """
    Raw SQL: Test DB connection cho WORKER THREAD - fail fast
    """
    try:
        from sql_helpers import get_raw_connection
        conn = get_raw_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        ol1(f"💥 Worker thread DB connection failed: {e}")
        ol1(f"🔥 Worker thread will DIE - main thread will restart it")
        raise e  # Let worker thread die

# Raw SQL approach - no need for execute_db_operation_main_thread

def execute_db_operation_worker_thread(operation_func, operation_name="DB operation"):
    """
    DB operation cho WORKER THREAD - fail fast, không retry
    Raw SQL approach - không cần session management
    """
    try:
        result = operation_func()
        return result
    except Exception as e:
        ol1(f"💥 Worker thread {operation_name} failed: {e}")
        raise e  # Let worker thread die

# === HELPER FUNCTIONS ===

def get_all_monitor_items_main_thread(chunk_info=None):
    """
    Raw SQL: Lấy tất cả monitor items - cho MAIN THREAD (retry vô hạn)
    """
    try:
        all_items_raw = get_enabled_items_raw()
        
        if chunk_info:
            offset = chunk_info['offset']
            limit = chunk_info['limit']
            items_raw = all_items_raw[offset:offset + limit]
            ol1(f"📊 Retrieved chunk #{chunk_info['number']}: {len(items_raw)} items (offset: {offset}, limit: {limit})")
        else:
            items_raw = all_items_raw
            ol1(f"📊 Retrieved {len(items_raw)} enabled items from DB")
        
        # Convert to object-like
        items = [MonitorItemDict(item_dict) for item_dict in items_raw]
        return items
    except Exception as e:
        ol1(f"❌ Error getting monitor items: {e}")
        return []

def safe_update_monitor_item_worker_thread(monitor_item):
    """
    Raw SQL: Update monitor item - cho WORKER THREAD (fail fast)
    Nếu DB lỗi thì worker thread sẽ die
    """
    try:
        # Determine status and messages
        status = monitor_item['last_check_status'] if isinstance(monitor_item, dict) else monitor_item.last_check_status
        error_msg = monitor_item.get('result_error') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_error', None)
        valid_msg = monitor_item.get('result_valid') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_valid', None)
        item_id = monitor_item['id'] if isinstance(monitor_item, dict) else monitor_item.id
        
        # Raw SQL update
        update_monitor_result_raw(item_id, status, error_msg, valid_msg)
        return True
        
    except Exception as e:
        ol1(f"💥 Worker thread failed to update monitor item {item_id}: {e}", monitorItem=monitor_item)
        ol1(f"🔥 This worker thread will die now!", monitorItem=monitor_item)
        raise e  # Let worker thread die

def start_api_server():
    """Khởi động API server trong thread riêng"""
    try:
        ol1("🔧 Initializing API server...")
        port = get_api_port()  # Use chunk-aware port
        host = os.getenv('HTTP_HOST', '127.0.0.1')

        print(f"🌐 Starting API server at http://{host}:{port}")
        

        api = MonitorAPI(host=host, port=port)
        
        # Pass references directly để tránh circular import
        api.set_monitor_refs(
            running_threads=running_threads,
            thread_alert_managers=thread_alert_managers,
            get_all_monitor_items=get_all_monitor_items,
            shutdown_event=shutdown_event
        )
        
        ol1("✅ API server initialized successfully")
        api.start_server()
    except Exception as e:
        ol1(f"❌ API Server error: {e}")
        import traceback
        ol1(f"❌ Traceback: {traceback.format_exc()}")
        # Print more detailed error info
        import traceback
        ol1(f"Error details: {traceback.format_exc()}")

def get_all_monitor_items():
    """
    Hàm helper để API có thể truy cập tất cả monitor items
    Sử dụng main thread logic (retry vô hạn)
    """
    return get_all_monitor_items_main_thread(CHUNK_INFO)

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
        # telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
        # if not telegram_enabled:
        #     return
        
        thread_id = monitor_item.id
        current_time = time.time()
        alert_manager = get_alert_manager(thread_id)
        
        # Xử lý logic lỗi liên tiếp
        if is_error:
            # Tăng counter lỗi liên tiếp
            alert_manager.increment_consecutive_error()
            consecutive_errors = alert_manager.get_consecutive_error_count()
            
            ol1(f"📊 [Thread {thread_id}] Consecutive errors: {consecutive_errors}")
            
            # Kiểm tra check interval
            check_interval_seconds = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
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
                if not alert_manager.should_send_extended_alert(EXTENDED_ALERT_INTERVAL_MINUTES):
                    time_since_last_alert = current_time - alert_manager.thread_last_alert_time
                    remaining_minutes = (EXTENDED_ALERT_INTERVAL_MINUTES * 60 - time_since_last_alert) / 60
                    ol1(f"🔕 [Thread {thread_id}] Extended alert throttle active ({remaining_minutes:.1f}m remaining)", monitor_item)
                    return
                
                ol1(f"⚠️ [Thread {thread_id}] Throttled alert (every {EXTENDED_ALERT_INTERVAL_MINUTES}m, {CONSECUTIVE_ERROR_THRESHOLD} consecutive errs)", monitor_item)
            
        else:
            # Phục hồi - reset counter lỗi liên tiếp
            consecutive_errors = alert_manager.get_consecutive_error_count()
            if consecutive_errors > 0:
                alert_manager.reset_consecutive_error()
                ol1(f"✅ [Thread {thread_id}] Service recovered! Reset consecutive error count (was: {consecutive_errors})", monitor_item)
        
        # Kiểm tra user alert time settings trước khi gửi
        user_id = monitor_item.user_id if monitor_item.user_id else 0
        is_allowed, reason = is_alert_time_allowed(user_id)
        
        if not is_allowed:
            ol1(f"🔕 [Thread {thread_id}] Alert blocked for user {user_id}: {reason}", monitor_item)
            return
        else:
            ol1(f"✅ [Thread {thread_id}] Alert allowed for user {user_id}: {reason}", monitor_item)

        # Lấy config Telegram
        telegram_config = get_telegram_config_for_monitor_raw(monitor_item.id)
        
        if not telegram_config:
            # Fallback to .env config
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                ol1(f"⚠️ [Thread {thread_id}] No Telegram config found (database or .env)", monitor_item)
                return
        else:
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config['chat_id']
            ol1(f"📱 [Thread {thread_id}] Using database Telegram config", monitor_item)
        
        # Basic throttling (30 giây giữa các notification giống nhau)
        alert_manager = get_alert_manager(thread_id)
        
        if not alert_manager.can_send_telegram_alert(TELEGRAM_THROTTLE_SECONDS):
            remaining = TELEGRAM_THROTTLE_SECONDS - (current_time - alert_manager.thread_telegram_last_sent_alert)
            ol1(f"🔇 [Thread {thread_id}] Basic throttle active {TELEGRAM_THROTTLE_SECONDS} ({remaining:.0f}s remaining)", monitor_item)
            return
        
        # Cập nhật thời gian gửi
        alert_manager.mark_telegram_sent()
        if is_error:
            alert_manager.update_last_alert_time()
        
        # Gửi notification
        if is_error:
            consecutive_errors = alert_manager.get_consecutive_error_count()
            enhanced_error_message = f"{error_message} (Lỗi liên tiếp: {consecutive_errors})"
            
            admin_domain = os.getenv('ADMIN_DOMAIN', 'monitor.mytree.vn')
            result = send_telegram_alert(
                bot_token=bot_token,
                chat_id=chat_id,
                url_admin=f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}",
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                error_message=enhanced_error_message
            )
            if result['success']:
                ol1(f"📱 [Thread {thread_id}] Telegram alert sent successfully", monitor_item)
            else:
                ol1(f"❌ [Thread {thread_id}] Telegram alert failed: {result['message']}", monitor_item)
        else:
            admin_domain = os.getenv('ADMIN_DOMAIN', 'monitor.mytree.vn')
            result = send_telegram_recovery(
                bot_token=bot_token,
                chat_id=chat_id,
                service_name=monitor_item.name,
                url_admin=f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}",
                service_url=monitor_item.url_check,
                response_time=response_time or 0
            )
            if result['success']:
                ol1(f"📱 [Thread {thread_id}] Telegram recovery notification sent successfully",monitor_item)
            else:
                ol1(f"❌ [Thread {thread_id}] Telegram recovery notification failed: {result['message']}", monitor_item)
                
    except Exception as e:
        ol1(f"❌ [Thread {monitor_item.id}] Telegram notification error: {e}", monitor_item)


def send_webhook_notification(monitor_item, is_error=True, error_message="", response_time=None):
    """
    Gửi webhook notification (chỉ 1 lần khi error và 1 lần khi recovery)
    
    Args:
        monitor_item: MonitorItem object
        is_error (bool): True nếu là lỗi, False nếu là phục hồi
        error_message (str): Thông báo lỗi
        response_time (float): Thời gian phản hồi (ms) cho trường hợp phục hồi
    """
    try:
        thread_id = monitor_item.id
        alert_manager = get_alert_manager(thread_id)
        
        # Lấy webhook config
        webhook_config = get_webhook_config_for_monitor_raw(monitor_item.id)
        if not webhook_config:
            return  # Không có webhook config
        
        webhook_url = webhook_config['webhook_url']
        webhook_name = webhook_config['webhook_name']
        
        if is_error:
            # Kiểm tra có nên gửi webhook error không (chỉ lần đầu lỗi)
            if not alert_manager.should_send_webhook_error():
                ol1(f"🔕 [Thread {thread_id}] Webhook error already sent, skipping", monitor_item)
                return
            
            # Gửi webhook error
            consecutive_errors = alert_manager.get_consecutive_error_count()
            enhanced_error_message = f"{error_message} (Lỗi liên tiếp: {consecutive_errors})"
            
            result = send_webhook_alert(
                webhook_url=webhook_url,
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                error_message=enhanced_error_message,
                alert_type="error",
                monitor_id=monitor_item.id,
                consecutive_errors=consecutive_errors,
                check_interval_seconds=monitor_item.check_interval_seconds,
                webhook_name=webhook_name
            )
            
            if result:
                alert_manager.mark_webhook_error_sent()
                ol1(f"🪝 [Thread {thread_id}] Webhook error sent successfully to {webhook_name}", monitor_item)
            else:
                ol1(f"❌ [Thread {thread_id}] Webhook error failed to {webhook_name}", monitor_item)
                
        else:
            # Phục hồi - kiểm tra có nên gửi webhook recovery không
            if not alert_manager.should_send_webhook_recovery():
                # Kiểm tra lý do cụ thể
                with alert_manager._lock:
                    if not alert_manager.thread_webhook_error_sent:
                        ol1(f"🔕 [Thread {thread_id}] Webhook recovery skipped: No previous error sent", monitor_item)
                    elif alert_manager.thread_webhook_recovery_sent:
                        ol1(f"🔕 [Thread {thread_id}] Webhook recovery skipped: Already sent", monitor_item)
                    else:
                        ol1(f"🔕 [Thread {thread_id}] Webhook recovery skipped: Unknown reason", monitor_item)
                return
            
            # Gửi webhook recovery
            recovery_message = f"Service '{monitor_item.name}' is back online"
            if response_time:
                recovery_message += f" (Response time: {response_time:.0f}ms)"
            
            result = send_webhook_recovery(
                webhook_url=webhook_url,
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                recovery_message=recovery_message,
                monitor_id=monitor_item.id,
                response_time=response_time or 0,
                webhook_name=webhook_name
            )
            
            if result:
                alert_manager.mark_webhook_recovery_sent()
                ol1(f"🪝 [Thread {thread_id}] Webhook recovery sent successfully to {webhook_name}", monitor_item)
            else:
                ol1(f"❌ [Thread {thread_id}] Webhook recovery failed to {webhook_name}", monitor_item)
                
    except Exception as e:
        ol1(f"❌ [Thread {monitor_item.id}] Webhook notification error: {e}", monitor_item)


def check_service(monitor_item):
    """
    Kiểm tra một dịch vụ dựa trên thông tin trong database với retry logic
    
    Args:
        monitor_item: MonitorItem object from database
        
    Returns:
        dict: Kết quả kiểm tra với các key: success, response_time, message, details
    """
    # Đặt giá trị mặc định cho check_interval_seconds nếu None hoặc 0
    check_interval = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
    
    ol1(f"=== Checking: (ID: {monitor_item.id})", monitor_item)
    ol1(f"Type: {monitor_item.type}", monitor_item)
    ol1(f"URL: {monitor_item.url_check}", monitor_item)
    ol1(f"Interval: {check_interval}s", monitor_item)
    ol1(f"Retry: 3 attempts, 3s interval", monitor_item)

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
    elif monitor_item.type == 'web_content':
        check_result = check_web_content(monitor_item)
    elif monitor_item.type == 'open_port_tcp_then_error':
        check_result = check_open_port_tcp_then_error(monitor_item)
    elif monitor_item.type == 'open_port_tcp_then_valid':
        check_result = check_open_port_tcp_then_valid(monitor_item)
    elif monitor_item.type == 'ssl_expired_check':
        check_result = check_ssl_expired_check(monitor_item)
    else:
        base_result['message'] = f"❌ Unknown service type: {monitor_item.type}"
        ol1(f"{base_result['message']}", monitor_item.id)
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
    Optimized: Get monitor item by ID from cache first, fallback to DB
    Giảm DB queries từ mỗi thread query DB → chỉ 1 cache lookup
    """
    global all_monitor_items, last_get_all_monitor_items
    
    current_time = time.time()
    
    # Try cache first if it's fresh (within 5 seconds)
    with cache_lock:
        cache_age = current_time - last_get_all_monitor_items
        
        if cache_age <= CACHE_EXPIRY_SECONDS and item_id in all_monitor_items:
            item = all_monitor_items[item_id]
            # ol1(f"✅ Cache hit for item {item_id}", item)
            # Cache hit - return cached item
            return item

    # Cache miss or expired - fallback to DB (fail fast for worker threads)
    try:
        ol1(f"✅ *** NOT Cache hit for {item_id}, so Get From DB ", item_id)
        olerror(f"✅ *** NOT Cache hit for {item_id}, so Get From DB ")

        item_dict = get_monitor_item_by_id_raw(item_id)
        if item_dict:
            item_obj = MonitorItemDict(item_dict)
            
            # Update cache with this item
            with cache_lock:
                all_monitor_items[item_id] = item_obj
            
            return item_obj
        return None
    except Exception as e:
        olerror(f"Worker thread failed to get monitor item {item_id}: {e}", item_id)
        ol1(f"💥 Worker thread failed to get monitor item {item_id}: {e}", item_id)
        ol1(f"🔥 This worker thread will die now!", item_id)
        raise e  # Let worker thread die

def update_monitor_item(monitor_item):
    """
    Raw SQL: Cập nhật monitor item vào database
    
    Args:
        monitor_item: MonitorItem dict hoặc object đã được modify
    """
    try:
        # Extract values
        status = monitor_item['last_check_status'] if isinstance(monitor_item, dict) else monitor_item.last_check_status
        error_msg = monitor_item.get('result_error') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_error', None)
        valid_msg = monitor_item.get('result_valid') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_valid', None)
        item_id = monitor_item['id'] if isinstance(monitor_item, dict) else monitor_item.id
        
        # Raw SQL update
        update_monitor_result_raw(item_id, status, error_msg, valid_msg)
        
    except Exception as e:
        ol1(f"❌ Error updating monitor item {item_id}: {e}")
        raise

def calculate_and_update_delta_time(monitor_id):
    """
    Tính delta time giữa lần check hiện tại và lần check trước đó
    
    Args:
        monitor_id (int): ID của monitor
        
    Returns:
        str: Formatted delta time string (e.g., "15.2s", "2m 30s", "1h 5m")
    """
    current_time = time.time()
    delta_str = "N/A"
    
    with monitor_check_times_lock:
        last_check_time = monitor_last_check_times.get(monitor_id)
        
        if last_check_time is not None:
            # Tính delta time
            delta_seconds = current_time - last_check_time
            
            # Format delta time
            if delta_seconds < 60:
                delta_str = f"{delta_seconds:.1f}s"
            elif delta_seconds < 3600:  # < 1 hour
                minutes = int(delta_seconds // 60)
                seconds = int(delta_seconds % 60)
                delta_str = f"{minutes}m {seconds}s"
            else:  # >= 1 hour
                hours = int(delta_seconds // 3600)
                minutes = int((delta_seconds % 3600) // 60)
                delta_str = f"{hours}h {minutes}m"
        
        # Cập nhật thời gian check hiện tại
        monitor_last_check_times[monitor_id] = current_time
    
    return delta_str


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
        ('check_interval_seconds', 'check_interval_seconds'),
        ('result_valid', 'result_valid'),
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
    original_item.check_interval_seconds = monitor_item.check_interval_seconds
    original_item.result_valid = monitor_item.result_valid
    original_item.result_error = monitor_item.result_error
    original_item.stopTo = monitor_item.stopTo
    original_item.forceRestart = monitor_item.forceRestart
    original_item.last_check_status = monitor_item.last_check_status
   
    check_interval = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
    check_count = 0
    
    # Reset counter lỗi liên tiếp khi start thread
    alert_manager = get_alert_manager(monitor_item.id)
    alert_manager.reset_consecutive_error()
    alert_manager.reset_webhook_flags()  # Reset webhook flags

    ol1(f"🚀[Thread {monitor_item.id}] Starting monitoring: {monitor_item.name}", monitorItem=monitor_item)
    ol1(f"[Thread {monitor_item.id}] Interval: {check_interval} seconds", monitorItem=monitor_item)
    ol1(f"[Thread {monitor_item.id}] Type: {monitor_item.type}", monitorItem=monitor_item)
    ol1(f"[Thread {monitor_item.id}] Reset consecutive error counter", monitorItem=monitor_item)

    try:
        last_check_time = 0
        
        while not shutdown_event.is_set():  # Check shutdown event
            current_time = time.time()
            
            # Kiểm tra nếu đã đủ thời gian để check service
            if current_time - last_check_time >= check_interval:
                check_count += 1
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Tính delta time với lần check trước
                delta_time = calculate_and_update_delta_time(monitor_item.id)

                ol1(f"📊 - [Thread {monitor_item.id}] Check #{check_count} at {timestamp}, DTime = {delta_time}", monitorItem=monitor_item, newLine=True)

            #    Nếu có monitor_item.stopTo, và nếu stopTo > now thì không chạy check
                # Handle stopTo - could be datetime, string, or invalid value
                should_pause = False
                if monitor_item.stopTo:
                    try:
                        # Skip if stopTo is just the column name (invalid data)
                        if isinstance(monitor_item.stopTo, str) and monitor_item.stopTo.lower() in ['stopto', 'null', '']:
                            # Invalid stopTo value, ignore pause
                            pass
                        elif isinstance(monitor_item.stopTo, str):
                            from dateutil import parser
                            stop_time = parser.parse(monitor_item.stopTo)
                            if stop_time > datetime.now():
                                should_pause = True
                        elif hasattr(monitor_item.stopTo, 'year'):  # datetime object
                            if monitor_item.stopTo > datetime.now():
                                should_pause = True
                    except Exception as e:
                        # Silently ignore parsing errors for invalid stopTo values
                        pass
                
                if should_pause:
                    ol1(f"⏸️ [Thread {monitor_item.id}] Monitor is paused until {monitor_item.stopTo}. Skipping check.")
                else:
                    # Kiểm tra dịch vụ với log đầy đủ
                    result = check_service(monitor_item)

                    # Lưu trạng thái cũ để so sánh cho Telegram notification
                    old_status = monitor_item.last_check_status
                    
                    # Cập nhật trạng thái mới và counter
                    new_status = 1 if result['success'] else -1
                    monitor_item.last_check_status = new_status
                    monitor_item.last_check_time = datetime.now()
                    
                    # Cập nhật counter: thành công -> count_online++, thất bại -> count_offline++
                    if result['success']:
                        if monitor_item.count_online is None:
                            monitor_item.count_online = 0
                        monitor_item.count_online += 1
                        ol1(f"📈 [Thread {monitor_item.id}] count_online: {monitor_item.count_online}")
                    else:
                        if monitor_item.count_offline is None:
                            monitor_item.count_offline = 0  
                        monitor_item.count_offline += 1
                        ol1(f"📉 [Thread {monitor_item.id}] count_offline: {monitor_item.count_offline}")
                    
                    # Gửi Telegram notification dựa trên thay đổi trạng thái
                    if result['success'] and old_status == -1:
                        # Service phục hồi từ lỗi -> OK
                        send_telegram_notification(
                            monitor_item=monitor_item,
                            is_error=False,
                            response_time=result['response_time']
                        )
                        # Gửi webhook recovery
                        send_webhook_notification(
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
                        # Gửi webhook error
                        send_webhook_notification(
                            monitor_item=monitor_item,
                            is_error=True,
                            error_message=result['message']
                        )

                    # Cập nhật database - sử dụng worker thread logic (fail fast)
                    safe_update_monitor_item_worker_thread(monitor_item)

                    # Hiển thị kết quả ngắn gọn
                    status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                    response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                    ol1(f"[Thread {monitor_item.id}] {status} | {response_time_str} | {monitor_item.name} ({monitor_item.type})", monitorItem=monitor_item)
                
                last_check_time = current_time
            
            # Sleep 3 giây hoặc cho đến khi shutdown
            if shutdown_event.wait(timeout=3):
                break
                
            # Kiểm tra stop flag riêng cho thread này
            if stop_flags.get(monitor_item.id, False):
                ol1(f"\n🛑 [Thread {monitor_item.id}] Received stop signal from MainThread", monitorItem=monitor_item)
                break
            
            # Lấy item hiện tại từ database để so sánh
            current_item = get_monitor_item_by_id(monitor_item.id)
            
            if not current_item:
                ol1(f"\n🛑 [Thread {monitor_item.id}] Item not found in database. Stopping {monitor_item.name} after {check_count} checks.", monitorItem=monitor_item)
                break
            
            # So sánh các trường quan trọng
            has_changes, changes = compare_monitor_item_fields(original_item, current_item)
            
            if has_changes:
                ol1(f"🔄 [Thread {monitor_item.id}] Configuration changes detected for {monitor_item.name}:", monitor_item)
                for change in changes:
                    ol1(f"- {change}")
                ol1(f"🛑 [Thread {monitor_item.id}] Stopping thread due to config changes after {check_count} checks.", monitor_item)
                break
            
            # Kiểm tra enable status riêng (để có log rõ ràng)
            if not current_item.enable:
                ol1(f"\n🛑 [Thread {monitor_item.id}] Monitor disabled (enable=0). Stopping {monitor_item.name} after {check_count} checks.", monitor_item)
                break
                
    except KeyboardInterrupt:
        ol1(f"\n🛑 [Thread {monitor_item.id}] Monitor stopped by user after {check_count} checks.", monitor_item)
    except Exception as e:
        ol1(f"\n❌ [Thread {monitor_item.id}] Monitor error for {monitor_item.name}: {e}",monitor_item)
    finally:
        # Remove thread from tracking và clear stop flag
        with thread_lock:
            if monitor_item.id in running_threads:
                del running_threads[monitor_item.id]
            if monitor_item.id in stop_flags:
                del stop_flags[monitor_item.id]
            # Cleanup alert manager khi thread dừng
            cleanup_alert_manager(monitor_item.id)
            ol1(f"🧹 [Thread {monitor_item.id}] Thread cleanup completed for {monitor_item.name}", monitor_item)

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
    Optimized: Get enabled items from cache first, fallback to DB
    Giảm DB queries từ mỗi 5s main loop query → chỉ memory access
    """
    global all_monitor_items, last_get_all_monitor_items
    
    current_time = time.time()
    
    # Try cache first if it's fresh
    with cache_lock:
        cache_age = current_time - last_get_all_monitor_items
        
        if cache_age <= CACHE_EXPIRY_SECONDS and all_monitor_items:
            # Cache hit - filter enabled items
            enabled_items = [item for item in all_monitor_items.values() if item.enable]
            
            # Apply chunking if needed
            if CHUNK_INFO:
                offset = CHUNK_INFO['offset']
                limit = CHUNK_INFO['limit']
                chunk_items = enabled_items[offset:offset + limit]
                return chunk_items
            
            return enabled_items
    
    # Cache miss or expired - fallback to original DB logic
    try:
        if CHUNK_INFO:
            all_items_raw = get_enabled_items_raw()
            
            offset = CHUNK_INFO['offset']
            limit = CHUNK_INFO['limit']
            
            ol1(f"📊 [DB Fallback] Total enabled items in DB: {len(all_items_raw)}")
            
            # Apply chunking
            items_raw = all_items_raw[offset:offset + limit]
            
            ol1(f"📦 [DB Fallback] Chunk #{CHUNK_INFO['number']}: Got {len(items_raw)} items "
                f"(offset: {offset}, limit: {limit})")
        else:
            # No chunk - get all enabled items
            items_raw = get_enabled_items_raw()
        
        # Convert to objects
        items = [MonitorItemDict(item_dict) for item_dict in items_raw]
        return items
        
    except Exception as e:
        ol1(f"❌ [DB Fallback] Error getting enabled items: {e}")
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

def force_stop_monitor_thread(monitor_item):
    """
    Force stop một monitor thread bằng cách set stop flag
    (MainThread có thể "kill" thread này)
    """
    item_id = monitor_item.id
    with thread_lock:
        if item_id in running_threads:
            thread_info = running_threads[item_id]
            item_name = thread_info['item'].name
            ol1(f"💀 [Main] Force stopping thread: {item_name} (ID: {item_id})", monitor_item)
            
            # Set stop flag cho thread đó
            stop_flags[item_id] = True

            # Khong cho, thread stop hay khong khong quan trọng

            
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
    Đặc biệt track những threads chết do DB error (để restart)
    """
    with thread_lock:
        dead_threads = []
        for item_id, thread_info in running_threads.items():
            if not thread_info['thread'].is_alive():
                dead_threads.append(item_id)
        
        for item_id in dead_threads:
            thread_info = running_threads.pop(item_id)
            thread_name = thread_info['item'].name
            
            # Check if thread died due to DB error (thread finished but process still running)
            if shutdown_event.is_set():
                ol1(f"🧹 [Main] Cleaned up thread during shutdown: {thread_name} (ID: {item_id})")
            else:
                ol1(f"💀 [Main] DEAD THREAD detected: {thread_name} (ID: {item_id})")
                ol1(f"🔄 [Main] This thread likely died due to DB error - will be restarted automatically")
                
            # Clear stop flag
            if item_id in stop_flags:
                del stop_flags[item_id]

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
    ol1("⏰ Interval: 5 seconds")
    ol1("🔄 Auto-manage monitor threads based on database")
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
            
            
            ol1(f"\n📊 [Main Manager] Cycle #{cycle_count} at {timestamp}")
            ol1(f"💾 DB Enabled: {len(enabled_ids)} items {list(enabled_ids)}")
            ol1(f"🏃 Running: {len(running_ids)} threads {list(running_ids)}")
            
            # In thời gian bắt đầu của các running threads (chỉ trong status report)
            for item_id, start_time in running_ids_and_start_time.items():
                ol1(f"   🕒 Thread {item_id} started at {start_time}")
                
            if items_to_start:
                ol1(f"➕ Need to start: {list(items_to_start)}")
            if items_to_stop:
                ol1(f"➖ Need to stop: {list(items_to_stop)}")
            
            # Start new threads
            for item_id in items_to_start:
                item = next((item for item in enabled_items if item.id == item_id), None)
                if item:
                    start_monitor_thread(item)
                    time.sleep(0.001)  # Small delay between starts
            
            # Stop threads for disabled items với force stop
            for item_id in items_to_stop:
                monitor_it = get_monitor_item_by_id(item_id)  # Just to log if item not found
                force_stop_monitor_thread(monitor_it)
            
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
       

def get_all_enabled_monitor_items():
    """
    Lấy tất cả monitor items đang enabled
    """
    try:
        items_raw = get_enabled_items_raw()
        return [MonitorItemDict(item_dict) for item_dict in items_raw]
    except Exception as e:
        ol1(f"❌ Error getting enabled monitor items: {e}")
        return []


def main():
    """Main function với single instance protection và HTTP API"""
    global instance_manager
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            # Chỉ kiểm tra status, không cần single instance
            if check_instance_and_get_status():
                return
            else:
                print("❌ No monitor service instance is running")
                return
                
        elif command == 'stop':
            # Dừng service qua API
            if check_instance_and_get_status():
                try:
                    import requests
                    port = get_api_port()
                    response = requests.post(f"http://127.0.0.1:{port}/api/shutdown", timeout=5)
                    if response.status_code == 200:
                        print("✅ Shutdown command sent successfully")
                    else:
                        print(f"⚠️ Shutdown API response: {response.status_code}")
                except requests.RequestException as e:
                    print(f"❌ Cannot send shutdown command: {e}")
            return
                
        elif command == 'manager' or command == 'start':
            # Kiểm tra single instance dựa trên port (chunk-aware)
            port = get_api_port()
            instance_manager_check = SingleInstanceManager(port=port)
            is_running, pid, current_port = instance_manager_check.is_already_running()
            if is_running:
                host = os.getenv('HTTP_HOST', '127.0.0.1')
                print(f"⚠️ Monitor service is already running on port {current_port}")
                if pid:
                    print(f"   PID: {pid}")
                else:
                    # Thử tìm process đang sử dụng port
                    process_info = instance_manager_check.get_process_using_port(current_port)
                    if process_info:
                        pid_found, name, cmdline = process_info
                        print(f"   Process using port {current_port}: PID {pid_found} - {name}")
                        print(f"   Command: {cmdline}")
                    else:
                        print(f"   Unknown process is using port {current_port}")
                        
                print(f"🌐 Dashboard: http://{host}:{current_port}")
                print("Use 'python monitor_service.py stop' to shutdown")
                return
            
            # Tạo lock file với chunk-specific name
            lock_file = "monitor_service.lock"
            if CHUNK_INFO:
                lock_file = f"monitor_service_chunk_{CHUNK_INFO['number']}.lock"
            
            instance_manager = SingleInstanceManager(lock_file=lock_file, port=port)
            if not instance_manager.create_lock_file():
                print("❌ Failed to create lock file. Exiting.")
                return
                
            ol1("🚀 Starting Monitor Service with Cache + HTTP API...")
            ol1(f"🔒 Instance locked (PID: {os.getpid()})")
            
            # Show chunk info if using chunk mode
            if CHUNK_INFO:
                ol1(f"📦 CHUNK MODE: Processing chunk #{CHUNK_INFO['number']} "
                    f"(size: {CHUNK_INFO['size']}, offset: {CHUNK_INFO['offset']})")
                ol1(f"📝 This instance will only process items {CHUNK_INFO['offset']+1} "
                    f"to {CHUNK_INFO['offset']+CHUNK_INFO['size']}")
            else:
                ol1("📊 FULL MODE: Processing all enabled monitor items")
            
            # Start cache refresh thread FIRST (reduces DB load from 1000 queries/sec to 1 query/sec)
            start_cache_thread()
            ol1("✅ Cache system initialized - DB queries reduced by 99.9%")
            
            # Start HTTP API server in background thread
            api_thread = threading.Thread(target=start_api_server, daemon=True)
            api_thread.start()
            
            # Wait a bit for API server to start
            time.sleep(2)
            port = int(os.getenv('HTTP_PORT', 5005))
            ol1(f"🌐 HTTP Dashboard: http://127.0.0.1:{port}")
            ol1(f"📊 API Status: http://127.0.0.1:{port}/api/status")
            
            # Start main manager loop
            try:
                main_manager_loop()
            except KeyboardInterrupt:
                ol1("🛑 Received Ctrl+C, shutting down gracefully...")
                cleanup_on_exit()
            
        elif command == 'test':
            # Test command không cần single instance protection
            enabled_items = get_enabled_items_from_db()
            if enabled_items:
                first_item = enabled_items[0]
                ol1(f"✅ Testing enabled monitor item: {first_item.name} (ID: {first_item.id})")
                ol1(f"URL: {first_item.url_check}")
                ol1(f"Type: {first_item.type}")
                ol1("="*80)
                result = check_service(first_item)
                ol1("="*80)
                ol1(f"🏁 Test completed for: {first_item.name}")
                status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
                response_time = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
                ol1(f"Final result: {status} | {response_time} | {result['message']}")
            else:
                ol1("❌ No enabled monitor items found in database")
        else:
            print("Monitor Service 2025 - Single Instance with HTTP API")
            print("="*60) 
            print("Usage:")
            print("  python monitor_service.py start      - Start monitor service with API")
            print("  python monitor_service.py start --test - Start with test environment (.env.test)")
            print("  python monitor_service.py manager    - Same as start")            
            print("  python monitor_service.py status     - Check service status")
            print("  python monitor_service.py stop       - Stop running service")
            print("  python monitor_service.py test       - Test first service once")
            print("")
            print("Chunk Mode (for scaling):")
            print("  --chunk=1-300      - Process items 1-300 (chunk 1, size 300)")
            print("  --chunk=2-300      - Process items 301-600 (chunk 2, size 300)")
            print("  --chunk=3-300      - Process items 601-900 (chunk 3, size 300)")
            print("  Example: python monitor_service.py start --chunk=1-300")
            print("")
            print("Limit Mode (restrict total items):")
            print("  --limit=500        - Process maximum 500 monitor items")
            print("  --limit=1000       - Process maximum 1000 monitor items")
            print("  Example: python monitor_service.py start --limit=500")
            print("")
            print("Scaling Example (3000 items with 300 per instance):")
            print("  Terminal 1: python monitor_service.py start --chunk=1-300")
            print("  Terminal 2: python monitor_service.py start --chunk=2-300")
            print("  Terminal 3: python monitor_service.py start --chunk=3-300")
            print("  ... (up to 10 terminals for 3000 items)")
            print("")
            print("Test Mode:")
            print("  --test flag loads .env.test (port 5006, test database)")
            print("")
            port = get_api_port()
            print(f"HTTP Dashboard: http://127.0.0.1:{port}")
            print("API Endpoints:")
            print("  GET  /api/status    - Service status")
            print("  GET  /api/monitors  - Monitor items") 
            print("  GET  /api/threads   - Thread information")
            print("  GET  /api/logs      - Recent logs")
            print("  POST /api/shutdown  - Shutdown service")
    else:
        # No arguments - show help
        main()
            

if __name__ == "__main__":
    main()
