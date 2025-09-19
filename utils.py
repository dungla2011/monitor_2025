"""
Utility functions for Monitor Service
Các hàm tiện ích dùng chung cho toàn bộ project
"""

import os
from datetime import datetime
import threading
import time

# Global thread lock for logging
_logging_lock = threading.Lock()


class class_send_alert_of_thread:
    """
    Class quản lý alert cho mỗi monitor thread
    """
    
    def __init__(self, monitor_id):
        self.id = monitor_id
        self.thread_telegram_last_sent_alert = 0  # timestamp lần cuối gửi alert
        self.thread_count_consecutive_error = 0   # số lỗi liên tiếp
        self.thread_last_alert_time = 0          # timestamp alert cuối cùng
        self.thread_webhook_error_sent = False   # đã gửi webhook alert chưa
        self.thread_webhook_recovery_sent = False # đã gửi webhook recovery chưa
        self._lock = threading.Lock()            # Thread safety
    
    def can_send_telegram_alert(self, throttle_seconds=30):
        """
        Kiểm tra có thể gửi telegram alert không (dựa trên throttle time)
        """
        with self._lock:
            current_time = time.time()
            return current_time - self.thread_telegram_last_sent_alert >= throttle_seconds
    
    def mark_telegram_sent(self):
        """
        Đánh dấu đã gửi telegram alert
        """
        with self._lock:
            self.thread_telegram_last_sent_alert = time.time()
    
    def increment_consecutive_error(self):
        """
        Tăng số lỗi liên tiếp
        """
        with self._lock:
            self.thread_count_consecutive_error += 1
    
    def reset_consecutive_error(self):
        """
        Reset số lỗi liên tiếp về 0
        """
        with self._lock:
            self.thread_count_consecutive_error = 0
    
    def update_last_alert_time(self):
        """
        Cập nhật thời gian alert cuối cùng
        """
        with self._lock:
            self.thread_last_alert_time = time.time()
    
    def get_consecutive_error_count(self):
        """
        Lấy số lỗi liên tiếp hiện tại
        """
        with self._lock:
            return self.thread_count_consecutive_error
    
    def should_send_extended_alert(self, interval_minutes=5):
        """
        Kiểm tra có nên gửi extended alert không (sau khoảng thời gian dài)
        """
        with self._lock:
            current_time = time.time()
            return current_time - self.thread_last_alert_time >= (interval_minutes * 60)
    
    def should_send_webhook_error(self):
        """
        Kiểm tra có nên gửi webhook alert không (chỉ gửi lần đầu lỗi)
        """
        with self._lock:
            return not self.thread_webhook_error_sent
    
    def mark_webhook_error_sent(self):
        """
        Đánh dấu đã gửi webhook alert
        """
        with self._lock:
            self.thread_webhook_error_sent = True
            self.thread_webhook_recovery_sent = False  # Reset recovery flag
    
    def should_send_webhook_recovery(self):
        """
        Kiểm tra có nên gửi webhook recovery không (chỉ gửi lần đầu recovery)
        """
        with self._lock:
            return self.thread_webhook_error_sent and not self.thread_webhook_recovery_sent
    
    def mark_webhook_recovery_sent(self):
        """
        Đánh dấu đã gửi webhook recovery
        """
        with self._lock:
            self.thread_webhook_recovery_sent = True
            self.thread_webhook_error_sent = False  # Reset error flag
    
    def reset_webhook_flags(self):
        """
        Reset tất cả webhook flags (dùng khi start thread)
        """
        with self._lock:
            self.thread_webhook_error_sent = False
            self.thread_webhook_recovery_sent = False


def ol1(msg, monitorItem=None, newLine=False):
    """
    Output Log function - Ghi log ra console và file (Thread-safe)
    
    Args:
        msg (str): Thông điệp cần log
        id (int, optional): Thread/Monitor ID để tách log file
    """
    # Thread-safe console output
    with _logging_lock:
        print(msg)

    # Nếu monitorItem có .id hoặc [id] thì lấy ID
    monitor_id = None
    if monitorItem is not None:
        # Neu monitorItem = int thì coi như ID
        if isinstance(monitorItem, int):
            monitor_id = monitorItem
        if hasattr(monitorItem, 'id'):
            monitor_id = monitorItem.id
        elif isinstance(monitorItem, dict) and 'id' in monitorItem:
            monitor_id = monitorItem['id']

    user_id = None
    # neu monitorItem khong phai Int
    
    if monitorItem is not None and not isinstance(monitorItem, int):
        if hasattr(monitorItem, 'user_id'):
            user_id = monitorItem.user_id
        elif isinstance(monitorItem, dict) and 'user_id' in monitorItem:
            user_id = monitorItem['user_id']

    # Tạo folder logs nếu chưa có
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Ghi log ra file với utf-8 encoding - Thread-safe approach:
    try:
        log_files = []
        
        padIdItem = None

        if monitorItem is not None:
            # Log file theo monitor ID
            log_files.append(os.getenv('LOG_FILE', f'logs/log_{monitor_id}.txt'))

            padIdItem = f"ID:{monitor_id} "
            # Nếu có user_id thì ghi thêm vào file log theo user
            if user_id is not None:
                log_files.append(f'logs/log_user_{user_id}.txt')
        else:
            # Main log file
            log_files.append(os.getenv('LOG_FILE', 'logs/log_main.txt'))


        
        # Ghi vào tất cả các log files
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp}# {padIdItem} - {msg}\n"
        
        for log_file in log_files:
            with open(log_file, "a", encoding="utf-8") as f:
                if newLine:
                    f.write("\n")
                f.write(log_line)
    except Exception as e:
        # Tránh lỗi khi file không thể write (file busy, permission, etc.)
        # Không print error để tránh recursive loop
        pass


def format_response_time(response_time_ms):
    """
    Format response time cho hiển thị
    
    Args:
        response_time_ms (float): Response time in milliseconds
        
    Returns:
        str: Formatted response time
    """
    if response_time_ms is None:
        return "N/A"
    
    if response_time_ms < 1000:
        return f"{response_time_ms:.2f}ms"
    else:
        return f"{response_time_ms/1000:.2f}s"


def format_uptime(seconds):
    """
    Format uptime từ seconds thành human readable
    
    Args:
        seconds (int/float): Số giây uptime
        
    Returns:
        str: Formatted uptime (e.g., "2d 3h 45m")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m {int(seconds % 60)}s"
    
    hours = int(minutes // 60)
    minutes = minutes % 60
    if hours < 24:
        return f"{hours}h {minutes}m"
    
    days = int(hours // 24)
    hours = hours % 24
    return f"{days}d {hours}h {minutes}m"


def safe_get_env_bool(key, default=False):
    """
    Safely get boolean value from environment variable
    
    Args:
        key (str): Environment variable key
        default (bool): Default value if not found or invalid
        
    Returns:
        bool: Boolean value
    """
    value = os.getenv(key, '').lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    elif value in ('false', '0', 'no', 'off'):
        return False
    else:
        return default


def safe_get_env_int(key, default=0):
    """
    Safely get integer value from environment variable
    
    Args:
        key (str): Environment variable key
        default (int): Default value if not found or invalid
        
    Returns:
        int: Integer value
    """
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def truncate_string(text, max_length=100, suffix="..."):
    """
    Truncate string to max length
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        suffix (str): Suffix to add if truncated
        
    Returns:
        str: Truncated string
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)] + suffix


def validate_url(url):
    """
    Basic URL validation
    
    Args:
        url (str): URL to validate
        
    Returns:
        tuple: (is_valid: bool, normalized_url: str)
    """
    if not url or not url.strip():
        return False, ""
    
    url = url.strip()
    
    # Nếu chỉ là IP hoặc domain, coi như valid
    import re
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    domain_pattern = r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(ip_pattern, url) or re.match(domain_pattern, url):
        return True, url
    
    # Kiểm tra URL với scheme
    if '://' in url:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                return True, url
        except:
            pass
    
    return False, url


def get_service_status_emoji(is_success, last_status=None):
    """
    Get emoji for service status
    
    Args:
        is_success (bool): Current check success
        last_status (int): Last status from database (-1=error, 1=ok, None=unknown)
        
    Returns:
        str: Status emoji
    """
    if is_success:
        return "✅"
    elif last_status == -1:
        return "❌"
    elif last_status == 1:
        return "⚠️"  # Was OK, now failed
    else:
        return "⚪"  # Unknown


def format_service_type(service_type):
    """
    Format service type for display
    
    Args:
        service_type (str): Service type from database
        
    Returns:
        str: Formatted service type
    """
    type_map = {
        'ping_web': '🌐 HTTP/HTTPS',
        'ping_icmp': '📡 ICMP Ping',
        'tcp': '🔌 TCP Port',
        'dns': '🔍 DNS Lookup',
    }
    
    return type_map.get(service_type, f"❓ {service_type}")


def generate_thread_name(monitor_id=None, monitor_name=None):
    """
    Generate consistent thread name
    
    Args:
        monitor_id (int, optional): Monitor ID
        monitor_name (str, optional): Monitor name
        
    Returns:
        str: Thread name
    """
    if monitor_id is None and monitor_name is None:
        # Generate simple timestamp-based name for backward compatibility
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"Monitor-{timestamp}"
    
    # Truncate name để tránh thread name quá dài
    safe_name = truncate_string(monitor_name or "", 20, "")
    # Remove special characters
    safe_name = re.sub(r'[^\w\s-]', '', safe_name).strip()
    safe_name = re.sub(r'[-\s]+', '-', safe_name)
    
    return f"Monitor-{monitor_id}-{safe_name}"


def format_counter_display(online_count, offline_count):
    """
    Format counter for display
    
    Args:
        online_count (int): Number of successful checks
        offline_count (int): Number of failed checks
        
    Returns:
        str: Formatted counter display
    """
    total = online_count + offline_count
    if total == 0:
        return "No checks yet"
    
    online_pct = (online_count / total) * 100
    return f"✅ {online_count} / ❌ {offline_count} ({online_pct:.1f}% uptime)"


# Import regex nếu chưa có
import re


def olerror(msg, monitorItem=None):
    """
    Output Log Error function - Ghi log lỗi ra file logs/log.error (Thread-safe)
    
    Args:
        msg (str): Thông điệp lỗi cần log
        monitorItem (object, optional): Monitor object để lấy ID và user_id
    """
    # Thread-safe console output
    with _logging_lock:
        print(f"❌ ERROR: {msg}")

    # Nếu monitorItem có .id hoặc [id] thì lấy ID
    monitor_id = None
    if monitorItem is not None:
        # Neu monitorItem = int thì coi như ID
        if isinstance(monitorItem, int):
            monitor_id = monitorItem
        if hasattr(monitorItem, 'id'):
            monitor_id = monitorItem.id
        elif isinstance(monitorItem, dict) and 'id' in monitorItem:
            monitor_id = monitorItem['id']

    user_id = None
    # neu monitorItem khong phai Int
    if monitorItem is not None and not isinstance(monitorItem, int):
        if hasattr(monitorItem, 'user_id'):
            user_id = monitorItem.user_id
        elif isinstance(monitorItem, dict) and 'user_id' in monitorItem:
            user_id = monitorItem['user_id']

    # Tạo folder logs nếu chưa có
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Ghi log lỗi ra file với utf-8 encoding - Thread-safe approach:
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Thông tin monitor ID nếu có
        monitor_info = ""
        if monitor_id is not None:
            monitor_info = f"ID:{monitor_id} "
            if user_id is not None:
                monitor_info += f"USER:{user_id} "
        
        log_line = f"{timestamp}# {monitor_info}ERROR: {msg}\n"
        
        # Ghi vào file log.error chính
        error_log_file = 'logs/log.error'
        with open(error_log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
        
        # Nếu có monitor_id, cũng ghi vào log file riêng của monitor đó
        if monitor_id is not None:
            monitor_log_file = f'logs/log_{monitor_id}.txt'
            with open(monitor_log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
                
        # Nếu có user_id, cũng ghi vào log file riêng của user đó
        if user_id is not None:
            user_log_file = f'logs/log_user_{user_id}.txt'
            with open(user_log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
                
    except Exception as e:
        # Tránh lỗi khi file không thể write (file busy, permission, etc.)
        # Không print error để tránh recursive loop
        pass
