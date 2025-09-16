#!/usr/bin/env python3
"""
Monitor Service with Thread Pool - Linux Compatible Version
Solves "can't start new thread" error by using fixed thread pool instead of 1 thread per monitor

Key Changes:
- Uses ThreadPoolExecutor with limited worker threads (default: 50)
- Schedules monitor tasks on thread pool instead of creating individual threads
- Maintains same monitoring logic but with better resource management
- Works within Linux ulimit constraints

Thread Usage:
- Before: 1 monitor = 1 thread (3000 monitors = 3000+ threads) ❌
- After: Fixed thread pool (3000 monitors = 50 worker threads) ✅
"""

import os
import sys
import time
import threading
import signal
import atexit
import traceback
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import concurrent.futures

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
    """Parse --chunk=number-size argument for scaling across multiple instances"""
    if len(sys.argv) < 2:
        return None
        
    chunk_info = None
    for arg in sys.argv:
        if arg.startswith('--chunk='):
            chunk_str = arg.split('=')[1]
            if '-' in chunk_str:
                try:
                    chunk_number, chunk_size = map(int, chunk_str.split('-'))
                    if chunk_number < 1 or chunk_size < 1:
                        print(f"❌ Invalid chunk format: {chunk_str}. Use --chunk=1-300")
                        sys.exit(1)
                    
                    offset = (chunk_number - 1) * chunk_size
                    chunk_info = {
                        'number': chunk_number,
                        'size': chunk_size,
                        'offset': offset,
                        'limit': chunk_size
                    }
                    print(f"📦 Chunk Mode: #{chunk_number} (items {offset+1}-{offset+chunk_size})")
                    break
                except ValueError:
                    print(f"❌ Invalid chunk format: {chunk_str}. Use --chunk=1-300")
                    sys.exit(1)
    
    return chunk_info

# Global chunk info
CHUNK_INFO = parse_chunk_argument()

def get_api_port():
    """Get API port, adjusted for chunk mode"""
    base_port = int(os.getenv('HTTP_PORT', 5005))
    
    if CHUNK_INFO:
        # Each chunk gets its own port: chunk 1 = 5005, chunk 2 = 5006, etc.
        chunk_port = base_port + CHUNK_INFO['number'] - 1
        return chunk_port
    
    return base_port

# Load environment variables FIRST - check for --test argument  
if '--test' in sys.argv or 'test' in sys.argv:
    try:
        print("🧪 Test mode enabled - loading .env.test")
    except UnicodeEncodeError:
        print("Test mode enabled - loading .env.test")
    load_dotenv('.env.test', override=True)  # Force override existing variables
else:
    load_dotenv()

# Now import modules that depend on environment variables
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

# Keep models for schema definition only
from models import MonitorItem, is_alert_time_allowed

class MonitorItemDict:
    """Convert dict to object-like access for backward compatibility"""
    def __init__(self, data_dict):
        for key, value in data_dict.items():
            setattr(self, key, value)
    
    def get(self, key, default=None):
        return getattr(self, key, default)

from telegram_helper import send_telegram_alert, send_telegram_recovery
from webhook_helper import send_webhook_alert, send_webhook_recovery, get_webhook_config_for_monitor_item
from single_instance_api import SingleInstanceManager, MonitorAPI, check_instance_and_get_status
from utils import ol1, class_send_alert_of_thread, format_response_time, safe_get_env_int, safe_get_env_bool, validate_url, generate_thread_name, format_counter_display

# Single Instance Manager - MUST be initialized after loading environment
instance_manager = SingleInstanceManager()

# ===== THREAD POOL CONFIGURATION =====
# Linux-friendly threading limits
MAX_WORKER_THREADS = safe_get_env_int('MAX_WORKER_THREADS', 50)  # Default: 50 worker threads for all monitors
MONITOR_QUEUE_SIZE = safe_get_env_int('MONITOR_QUEUE_SIZE', 10000)  # Queue size for pending tasks
TASK_TIMEOUT_SECONDS = safe_get_env_int('TASK_TIMEOUT_SECONDS', 300)  # Timeout for individual monitor tasks

# Global ThreadPoolExecutor
thread_pool = None
monitor_queue = queue.Queue(maxsize=MONITOR_QUEUE_SIZE)
shutdown_event = threading.Event()

# Track active monitoring tasks
active_monitor_tasks = {}  # {monitor_id: future_object}
active_tasks_lock = threading.Lock()

# Telegram notification throttling
TELEGRAM_THROTTLE_SECONDS = safe_get_env_int('TELEGRAM_THROTTLE_SECONDS', 30)
CONSECUTIVE_ERROR_THRESHOLD = safe_get_env_int('CONSECUTIVE_ERROR_THRESHOLD', 10)
EXTENDED_ALERT_INTERVAL_MINUTES = safe_get_env_int('EXTENDED_ALERT_INTERVAL_MINUTES', 5)

# Alert management
thread_alert_managers = {}
thread_alert_lock = threading.Lock()

# ===== CACHE SYSTEM FOR MONITOR ITEMS =====
all_monitor_items = {}
all_monitor_items_index = {}
last_get_all_monitor_items = 0
cache_thread = None
cache_lock = threading.Lock()
CACHE_REFRESH_INTERVAL = 1
CACHE_EXPIRY_SECONDS = 5

# ===== THREAD POOL FUNCTIONS =====

def initialize_thread_pool():
    """Initialize the thread pool with Linux-friendly settings"""
    global thread_pool
    
    if thread_pool is not None:
        ol1("⚠️ Thread pool already initialized")
        return
    
    ol1(f"🏊 Initializing thread pool with {MAX_WORKER_THREADS} worker threads")
    ol1(f"📊 This will handle {MONITOR_QUEUE_SIZE} queued tasks maximum")
    ol1(f"⏱️ Task timeout: {TASK_TIMEOUT_SECONDS} seconds")
    
    thread_pool = ThreadPoolExecutor(
        max_workers=MAX_WORKER_THREADS,
        thread_name_prefix="MonitorWorker"
    )
    
    ol1(f"✅ Thread pool initialized successfully")
    ol1(f"🐧 Linux-friendly: {MAX_WORKER_THREADS} threads total (vs {len(get_enabled_items_raw())} monitors)")

def shutdown_thread_pool():
    """Gracefully shutdown the thread pool"""
    global thread_pool
    
    if thread_pool is None:
        return
    
    ol1("🛑 Shutting down thread pool...")
    
    # Cancel all pending futures
    with active_tasks_lock:
        for monitor_id, future in active_monitor_tasks.items():
            if not future.done():
                ol1(f"❌ Cancelling task for monitor {monitor_id}")
                future.cancel()
        active_monitor_tasks.clear()
    
    # Shutdown thread pool
    thread_pool.shutdown(wait=True, timeout=30)
    thread_pool = None
    ol1("✅ Thread pool shutdown completed")

def submit_monitor_task(monitor_item):
    """Submit a monitor task to the thread pool"""
    global thread_pool
    
    if thread_pool is None:
        ol1("❌ Thread pool not initialized")
        return None
    
    # Cancel existing task for this monitor if running
    with active_tasks_lock:
        if monitor_item.id in active_monitor_tasks:
            existing_future = active_monitor_tasks[monitor_item.id]
            if not existing_future.done():
                ol1(f"🔄 Cancelling existing task for monitor {monitor_item.id}")
                existing_future.cancel()
    
    # Submit new task
    try:
        future = thread_pool.submit(monitor_service_worker, monitor_item)
        
        with active_tasks_lock:
            active_monitor_tasks[monitor_item.id] = future
        
        ol1(f"📤 Submitted monitor task for {monitor_item.name} (ID: {monitor_item.id})")
        return future
        
    except Exception as e:
        ol1(f"❌ Failed to submit monitor task for {monitor_item.id}: {e}")
        return None

def monitor_service_worker(monitor_item):
    """
    Worker function that runs in thread pool
    This replaces the individual thread approach
    """
    worker_name = f"Worker-{monitor_item.id}-{monitor_item.name}"
    thread_id = threading.current_thread().ident
    
    ol1(f"🔧 [{worker_name}] Starting monitor check on thread {thread_id}")
    
    try:
        # Test DB connection for worker thread
        test_db_connection_worker_thread()
        
        # Perform the actual monitor check
        result = check_service(monitor_item)
        
        # Process results (same logic as before)
        old_status = monitor_item.last_check_status
        new_status = 1 if result['success'] else -1
        monitor_item.last_check_status = new_status
        monitor_item.last_check_time = datetime.now()
        
        # Update counters
        if result['success']:
            if monitor_item.count_online is None:
                monitor_item.count_online = 0
            monitor_item.count_online += 1
        else:
            if monitor_item.count_offline is None:
                monitor_item.count_offline = 0
            monitor_item.count_offline += 1
        
        # Send notifications based on status change
        if result['success'] and old_status == -1:
            # Recovery
            send_telegram_notification(
                monitor_item=monitor_item,
                is_error=False,
                response_time=result['response_time']
            )
            send_webhook_notification(
                monitor_item=monitor_item,
                is_error=False,
                response_time=result['response_time']
            )
        elif not result['success']:
            # Error
            send_telegram_notification(
                monitor_item=monitor_item,
                is_error=True,
                error_message=result['message']
            )
            send_webhook_notification(
                monitor_item=monitor_item,
                is_error=True,
                error_message=result['message']
            )
        
        # Update database
        safe_update_monitor_item_worker_thread(monitor_item)
        
        # Log result
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        response_time_str = f"{result['response_time']:.2f}ms" if result['response_time'] else "N/A"
        ol1(f"[{worker_name}] {status} | {response_time_str} | {result['message']}")
        
        return result
        
    except Exception as e:
        ol1(f"❌ [{worker_name}] Worker error: {e}")
        return {
            'success': False,
            'response_time': None,
            'message': f'Worker error: {str(e)}',
            'monitor_item_id': monitor_item.id
        }
    finally:
        # Clean up active task tracking
        with active_tasks_lock:
            if monitor_item.id in active_monitor_tasks:
                del active_monitor_tasks[monitor_item.id]
        
        ol1(f"🧹 [{worker_name}] Worker cleanup completed")

# ===== CACHE SYSTEM FUNCTIONS =====

def cache_refresh_thread():
    """Background thread to refresh cache monitor items every 1 second"""
    global all_monitor_items, all_monitor_items_index, last_get_all_monitor_items
    
    thread_name = "CacheRefresh"
    threading.current_thread().name = thread_name
    
    ol1(f"🗄️ [Cache] Starting cache refresh thread (interval: {CACHE_REFRESH_INTERVAL}s)")
    
    while not shutdown_event.is_set():
        try:
            start_time = time.time()
            items_raw = get_enabled_items_raw()
            
            # Apply chunking if configured
            if CHUNK_INFO:
                offset = CHUNK_INFO['offset']
                limit = CHUNK_INFO['limit']
                items_raw = items_raw[offset:offset + limit]
            
            # Convert to objects and update cache
            items_dict = {}
            for item_dict in items_raw:
                item_obj = MonitorItemDict(item_dict)
                items_dict[item_obj.id] = item_obj
            
            # Update cache atomically
            with cache_lock:
                all_monitor_items = items_dict
                all_monitor_items_index = items_dict.copy()
                last_get_all_monitor_items = time.time()
            
            cache_time = (time.time() - start_time) * 1000
            ol1(f"🗄️ [Cache] Refreshed {len(items_dict)} items in {cache_time:.1f}ms")
            
        except Exception as e:
            ol1(f"❌ [Cache] Error refreshing cache: {e}")
        
        # Wait or shutdown
        if shutdown_event.wait(timeout=CACHE_REFRESH_INTERVAL):
            break
    
    ol1(f"🗄️ [Cache] Cache refresh thread stopped")

def start_cache_thread():
    """Start cache refresh thread"""
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
    
    # Wait for initial cache load
    time.sleep(1.5)
    ol1(f"✅ [Cache] Cache refresh thread started")

# ===== ALERT MANAGEMENT FUNCTIONS =====

def get_alert_manager(thread_id):
    """Get alert manager for thread ID, create if not exists"""
    with thread_alert_lock:
        if thread_id not in thread_alert_managers:
            thread_alert_managers[thread_id] = class_send_alert_of_thread()
        return thread_alert_managers[thread_id]

def cleanup_alert_manager(thread_id):
    """Cleanup alert manager when thread ends"""
    with thread_alert_lock:
        if thread_id in thread_alert_managers:
            del thread_alert_managers[thread_id]

# ===== CLEANUP AND SIGNAL HANDLING =====

cleanup_running = False

def cleanup_on_exit():
    """Cleanup function when exiting"""
    global instance_manager, cleanup_running, cache_thread, thread_pool
    
    if cleanup_running:
        return
    
    cleanup_running = True
    ol1("🔄 Cleaning up before exit...")
    
    # Signal all threads to stop
    shutdown_event.set()
    
    # Shutdown thread pool
    shutdown_thread_pool()
    
    # Wait for cache thread to stop
    if cache_thread and cache_thread.is_alive():
        ol1("⏳ Waiting for cache thread to stop...")
        cache_thread.join(timeout=2)
    
    # Cleanup instance manager
    if instance_manager:
        instance_manager.cleanup()
    
    ol1("✅ Cleanup completed")

# Register cleanup handlers
atexit.register(cleanup_on_exit)

# Counter for Ctrl+C presses
ctrl_c_count = 0

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global ctrl_c_count
    ctrl_c_count += 1
    
    ol1(f"🛑 Received signal {signum}, shutting down... (press Ctrl+C again for force exit)")
    
    if ctrl_c_count >= 2:
        ol1("⚡ Force exit - killing process immediately!")
        os._exit(1)
    
    cleanup_on_exit()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ===== DATABASE OPERATIONS =====

def test_db_connection_main_thread(retry_delay=10):
    """Test DB connection for MAIN THREAD with infinite retry"""
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
                ol1(f"✅ Database connection restored on attempt {attempt}")
            return True
        except Exception as e:
            ol1(f"💥 DB connection attempt {attempt} failed: {e}")
            ol1(f"🔄 Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)

def test_db_connection_worker_thread():
    """Test DB connection for WORKER THREAD - fail fast"""
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
        raise e

def safe_update_monitor_item_worker_thread(monitor_item):
    """Update monitor item for WORKER THREAD (fail fast)"""
    try:
        status = monitor_item['last_check_status'] if isinstance(monitor_item, dict) else monitor_item.last_check_status
        error_msg = monitor_item.get('result_error') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_error', None)
        valid_msg = monitor_item.get('result_valid') if isinstance(monitor_item, dict) else getattr(monitor_item, 'result_valid', None)
        item_id = monitor_item['id'] if isinstance(monitor_item, dict) else monitor_item.id
        
        update_monitor_result_raw(item_id, status, error_msg, valid_msg)
        return True
        
    except Exception as e:
        ol1(f"💥 Worker thread failed to update monitor item {item_id}: {e}", monitorItem=monitor_item)
        raise e

# ===== API SERVER FUNCTIONS =====

def start_api_server():
    """Start API server in separate thread"""
    try:
        ol1("🔧 Initializing API server...")
        port = get_api_port()
        host = os.getenv('HTTP_HOST', '127.0.0.1')

        print(f"🌐 Starting API server at http://{host}:{port}")
        
        api = MonitorAPI(host=host, port=port)
        
        # Pass references for API access
        api.set_monitor_refs(
            running_threads={},  # Thread pool doesn't use running_threads
            thread_alert_managers=thread_alert_managers,
            get_all_monitor_items=get_all_monitor_items,
            shutdown_event=shutdown_event
        )
        
        ol1("✅ API server initialized successfully")
        api.start_server()
    except Exception as e:
        ol1(f"❌ API Server error: {e}")
        ol1(f"❌ Traceback: {traceback.format_exc()}")

def get_all_monitor_items():
    """Helper function for API to access all monitor items"""
    return get_all_monitor_items_main_thread(CHUNK_INFO)

def get_all_monitor_items_main_thread(chunk_info=None):
    """Get all monitor items for MAIN THREAD (infinite retry)"""
    try:
        all_items_raw = get_enabled_items_raw()
        
        if chunk_info:
            offset = chunk_info['offset']
            limit = chunk_info['limit']
            items_raw = all_items_raw[offset:offset + limit]
            ol1(f"📦 Retrieved {len(items_raw)} items from chunk #{chunk_info['number']}")
        else:
            items_raw = all_items_raw
            ol1(f"📊 Retrieved {len(items_raw)} enabled items from DB")
        
        # Convert to object-like
        items = [MonitorItemDict(item_dict) for item_dict in items_raw]
        return items
    except Exception as e:
        ol1(f"❌ Error getting monitor items: {e}")
        return []

def get_monitor_item_by_id(item_id):
    """Get monitor item by ID from cache first, fallback to DB"""
    global all_monitor_items, last_get_all_monitor_items
    
    current_time = time.time()
    
    # Try cache first if fresh
    with cache_lock:
        cache_age = current_time - last_get_all_monitor_items
        
        if cache_age <= CACHE_EXPIRY_SECONDS and item_id in all_monitor_items:
            item = all_monitor_items[item_id]
            ol1(f"✅ Cache hit for item {item_id}", item)
            return item

    # Cache miss - fallback to DB
    try:
        ol1(f"📊 Cache miss for {item_id}, fetching from DB")
        item_dict = get_monitor_item_by_id_raw(item_id)
        if item_dict:
            item_obj = MonitorItemDict(item_dict)
            
            # Update cache
            with cache_lock:
                all_monitor_items[item_id] = item_obj
            
            return item_obj
        return None
    except Exception as e:
        ol1(f"💥 Failed to get monitor item {item_id}: {e}")
        raise e

# ===== MONITOR CHECKING FUNCTIONS =====

def check_service(monitor_item):
    """Check a service based on database information with retry logic"""
    check_interval = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
    
    ol1(f"=== Checking: (ID: {monitor_item.id})", monitor_item)
    ol1(f"Type: {monitor_item.type}", monitor_item)
    ol1(f"URL: {monitor_item.url_check}", monitor_item)
    ol1(f"Interval: {check_interval}s", monitor_item)

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
    
    # Call appropriate check function
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
    
    # Merge results
    base_result.update({
        'success': check_result['success'],
        'response_time': check_result['response_time'],
        'message': check_result['message'],
        'details': check_result['details']
    })
    
    return base_result

# ===== NOTIFICATION FUNCTIONS =====

def send_telegram_notification(monitor_item, is_error=True, error_message="", response_time=None):
    """Send Telegram notification with consecutive error logic and alert throttling"""
    try:
        thread_id = monitor_item.id
        current_time = time.time()
        alert_manager = get_alert_manager(thread_id)
        
        # Handle consecutive error logic
        if is_error:
            alert_manager.increment_consecutive_error()
            consecutive_errors = alert_manager.get_consecutive_error_count()
            
            ol1(f"📊 [Thread {thread_id}] Consecutive errors: {consecutive_errors}")
            
            # Check interval throttling logic
            check_interval_seconds = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
            check_interval_minutes = check_interval_seconds / 60
            
            should_throttle_extended = (
                check_interval_minutes < 5 and
                consecutive_errors > CONSECUTIVE_ERROR_THRESHOLD and
                EXTENDED_ALERT_INTERVAL_MINUTES > 0
            )
            
            if should_throttle_extended:
                time_since_last = current_time - alert_manager.get_last_alert_time()
                if time_since_last < (EXTENDED_ALERT_INTERVAL_MINUTES * 60):
                    remaining = (EXTENDED_ALERT_INTERVAL_MINUTES * 60) - time_since_last
                    ol1(f"🔇 [Thread {thread_id}] Extended throttle active ({remaining:.0f}s remaining)", monitor_item)
                    return
            
        else:
            # Recovery - reset consecutive error counter
            consecutive_errors = alert_manager.get_consecutive_error_count()
            if consecutive_errors > 0:
                ol1(f"🔄 [Thread {thread_id}] Reset consecutive errors: {consecutive_errors} → 0", monitor_item)
                alert_manager.reset_consecutive_error()
        
        # Check user alert time settings
        user_id = monitor_item.user_id if monitor_item.user_id else 0
        is_allowed, reason = is_alert_time_allowed(user_id)
        
        if not is_allowed:
            ol1(f"🔕 [Thread {thread_id}] Alert blocked for user {user_id}: {reason}", monitor_item)
            return
        else:
            ol1(f"✅ [Thread {thread_id}] Alert allowed for user {user_id}: {reason}", monitor_item)

        # Get Telegram config
        telegram_config = get_telegram_config_for_monitor_raw(monitor_item.id)
        
        if not telegram_config:
            # Fallback to .env config
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                ol1(f"⚠️ [Thread {thread_id}] No Telegram config found", monitor_item)
                return
        else:
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config['chat_id']
            ol1(f"📱 [Thread {thread_id}] Using database Telegram config", monitor_item)
        
        # Basic throttling
        if not alert_manager.can_send_telegram_alert(TELEGRAM_THROTTLE_SECONDS):
            remaining = TELEGRAM_THROTTLE_SECONDS - (current_time - alert_manager.thread_telegram_last_sent_alert)
            ol1(f"🔇 [Thread {thread_id}] Basic throttle active ({remaining:.0f}s remaining)", monitor_item)
            return
        
        # Update send time
        alert_manager.mark_telegram_sent()
        if is_error:
            alert_manager.update_last_alert_time()
        
        # Send notification
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
                ol1(f"📱 [Thread {thread_id}] Telegram recovery notification sent successfully", monitor_item)
            else:
                ol1(f"❌ [Thread {thread_id}] Telegram recovery notification failed: {result['message']}", monitor_item)
                
    except Exception as e:
        ol1(f"❌ [Thread {monitor_item.id}] Telegram notification error: {e}", monitor_item)

def send_webhook_notification(monitor_item, is_error=True, error_message="", response_time=None):
    """Send webhook notification (only once per error and once per recovery)"""
    try:
        thread_id = monitor_item.id
        alert_manager = get_alert_manager(thread_id)
        
        # Get webhook config
        webhook_config = get_webhook_config_for_monitor_raw(monitor_item.id)
        if not webhook_config:
            return
        
        webhook_url = webhook_config['webhook_url']
        webhook_name = webhook_config['webhook_name']
        
        if is_error:
            # Check if should send webhook error
            if not alert_manager.should_send_webhook_error():
                ol1(f"🔕 [Thread {thread_id}] Webhook error already sent, skipping", monitor_item)
                return
            
            # Send webhook error
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
            # Recovery - check if should send webhook recovery
            if not alert_manager.should_send_webhook_recovery():
                return
            
            # Send webhook recovery
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

# ===== SCHEDULER FUNCTIONS =====

def get_enabled_items_from_cache():
    """Get enabled items from cache with chunking support"""
    global all_monitor_items, last_get_all_monitor_items
    
    current_time = time.time()
    
    # Try cache first if fresh
    with cache_lock:
        cache_age = current_time - last_get_all_monitor_items
        
        if cache_age <= CACHE_EXPIRY_SECONDS and all_monitor_items:
            # Cache hit - filter enabled items
            enabled_items = [item for item in all_monitor_items.values() if item.enable]
            return enabled_items
    
    # Cache miss - fallback to DB
    try:
        all_items_raw = get_enabled_items_raw()
        
        # Apply chunking if configured
        if CHUNK_INFO:
            offset = CHUNK_INFO['offset']
            limit = CHUNK_INFO['limit']
            items_raw = all_items_raw[offset:offset + limit]
        else:
            items_raw = all_items_raw
        
        # Convert to objects
        items = [MonitorItemDict(item_dict) for item_dict in items_raw]
        return items
        
    except Exception as e:
        ol1(f"❌ Error getting enabled items: {e}")
        return []

def schedule_monitor_checks():
    """Schedule monitor checks using thread pool instead of individual threads"""
    ol1("🚀 Starting Thread Pool Monitor Scheduler...")
    ol1(f"🏊 Thread Pool: {MAX_WORKER_THREADS} workers")
    ol1(f"⏰ Check Cycle: 5 seconds")
    ol1("="*80)
    
    cycle_count = 0
    next_check_times = {}  # {monitor_id: next_check_time}
    
    try:
        while not shutdown_event.is_set():
            cycle_count += 1
            current_time = time.time()
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Get enabled items
            enabled_items = get_enabled_items_from_cache()
            
            # Schedule checks for monitors that are due
            monitors_to_check = []
            
            for item in enabled_items:
                # Skip disabled items
                if not item.enable:
                    continue
                
                # Handle stopTo pause logic
                should_pause = False
                if item.stopTo:
                    try:
                        if isinstance(item.stopTo, str) and item.stopTo.lower() not in ['stopto', 'null', '']:
                            stop_time = datetime.fromisoformat(item.stopTo.replace('Z', '+00:00'))
                            if datetime.now() < stop_time:
                                should_pause = True
                        elif hasattr(item.stopTo, 'year'):
                            if datetime.now() < item.stopTo:
                                should_pause = True
                    except:
                        pass
                
                if should_pause:
                    continue
                
                # Check if monitor is due for check
                check_interval = item.check_interval_seconds if item.check_interval_seconds else 300
                
                if item.id not in next_check_times:
                    # First time - schedule immediately
                    next_check_times[item.id] = current_time
                
                if current_time >= next_check_times[item.id]:
                    monitors_to_check.append(item)
                    # Schedule next check
                    next_check_times[item.id] = current_time + check_interval
            
            # Submit monitor tasks to thread pool
            if monitors_to_check:
                ol1(f"📊 [Scheduler] Cycle #{cycle_count} at {timestamp}")
                ol1(f"📤 Submitting {len(monitors_to_check)} monitor checks to thread pool")
                
                for monitor_item in monitors_to_check:
                    submit_monitor_task(monitor_item)
            
            # Clean up next_check_times for disabled monitors
            enabled_ids = {item.id for item in enabled_items}
            to_remove = [mid for mid in next_check_times.keys() if mid not in enabled_ids]
            for mid in to_remove:
                del next_check_times[mid]
            
            # Show active tasks info
            with active_tasks_lock:
                active_count = len(active_monitor_tasks)
                if active_count > 0:
                    ol1(f"🏊 Active tasks in thread pool: {active_count}")
            
            # Wait 5 seconds or until shutdown
            if shutdown_event.wait(timeout=5):
                break
                
    except KeyboardInterrupt:
        ol1(f"\n🛑 [Scheduler] Shutting down after {cycle_count} cycles...")
    except Exception as e:
        ol1(f"\n❌ [Scheduler] Error: {e}")
    finally:
        shutdown_event.set()

# ===== MAIN FUNCTION =====

def main():
    """Main function with single instance protection and thread pool"""
    global instance_manager
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            if check_instance_and_get_status():
                return
            else:
                print("❌ No monitor service instance is running")
                return
                
        elif command == 'stop':
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
            # Check single instance
            port = get_api_port()
            instance_manager_check = SingleInstanceManager(port=port)
            is_running, pid, current_port = instance_manager_check.is_already_running()
            if is_running:
                host = os.getenv('HTTP_HOST', '127.0.0.1')
                print(f"⚠️ Monitor service is already running on port {current_port}")
                if pid:
                    print(f"   PID: {pid}")
                print(f"🌐 Dashboard: http://{host}:{current_port}")
                print("Use 'python monitor_service_threadpool.py stop' to shutdown")
                return
            
            # Create lock file
            lock_file = "monitor_service_threadpool.lock"
            if CHUNK_INFO:
                lock_file = f"monitor_service_threadpool_chunk_{CHUNK_INFO['number']}.lock"
            
            instance_manager = SingleInstanceManager(lock_file=lock_file, port=port)
            if not instance_manager.create_lock_file():
                print("❌ Failed to create lock file. Exiting.")
                return
                
            ol1("🚀 Starting Monitor Service with Thread Pool + HTTP API...")
            ol1(f"🔒 Instance locked (PID: {os.getpid()})")
            
            # Show mode info
            if CHUNK_INFO:
                ol1(f"📦 CHUNK MODE: Processing chunk #{CHUNK_INFO['number']} "
                    f"(size: {CHUNK_INFO['size']}, offset: {CHUNK_INFO['offset']})")
            else:
                ol1("📊 FULL MODE: Processing all enabled monitor items")
            
            # Show thread pool info
            ol1(f"🏊 THREAD POOL: {MAX_WORKER_THREADS} worker threads (Linux-friendly)")
            ol1(f"📋 QUEUE SIZE: {MONITOR_QUEUE_SIZE} pending tasks maximum")
            
            # Initialize thread pool
            initialize_thread_pool()
            
            # Start cache refresh thread
            start_cache_thread()
            ol1("✅ Cache system initialized")
            
            # Start HTTP API server
            api_thread = threading.Thread(target=start_api_server, daemon=True)
            api_thread.start()
            
            # Wait for API server
            time.sleep(2)
            ol1(f"🌐 HTTP Dashboard: http://127.0.0.1:{port}")
            ol1(f"📊 API Status: http://127.0.0.1:{port}/api/status")
            
            # Start main scheduler loop
            try:
                schedule_monitor_checks()
            except KeyboardInterrupt:
                ol1("🛑 Received Ctrl+C, shutting down gracefully...")
                cleanup_on_exit()
            
        elif command == 'test':
            # Test first monitor
            enabled_items = get_enabled_items_from_cache()
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
            print("Monitor Service 2025 - Thread Pool Version (Linux Compatible)")
            print("="*70) 
            print("🐧 LINUX OPTIMIZED: Uses thread pool instead of individual threads")
            print(f"🏊 THREAD POOL: {MAX_WORKER_THREADS} workers handle unlimited monitors")
            print("🚀 SCALABLE: No more 'can't start new thread' errors")
            print("")
            print("Usage:")
            print("  python monitor_service_threadpool.py start      - Start with thread pool")
            print("  python monitor_service_threadpool.py start --test - Start with test env")
            print("  python monitor_service_threadpool.py manager    - Same as start")
            print("  python monitor_service_threadpool.py status     - Check service status")
            print("  python monitor_service_threadpool.py stop       - Stop running service")
            print("  python monitor_service_threadpool.py test       - Test first service")
            print("")
            print("Thread Pool Configuration (.env):")
            print("  MAX_WORKER_THREADS=50        - Number of worker threads (default: 50)")
            print("  MONITOR_QUEUE_SIZE=10000     - Task queue size (default: 10000)")
            print("  TASK_TIMEOUT_SECONDS=300     - Task timeout (default: 300)")
            print("")
            print("Chunk Mode (for scaling):")
            print("  --chunk=1-300      - Process items 1-300")
            print("  --chunk=2-300      - Process items 301-600")
            print("  Example: python monitor_service_threadpool.py start --chunk=1-300")
            print("")
            port = get_api_port()
            print(f"HTTP Dashboard: http://127.0.0.1:{port}")
            print("API Endpoints: Same as original version")
    else:
        main()

if __name__ == "__main__":
    main()