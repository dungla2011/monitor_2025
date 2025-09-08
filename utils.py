"""
Utility functions for Monitor Service
Các hàm tiện ích dùng chung cho toàn bộ project
"""

import os
from datetime import datetime


def ol1(msg):
    """
    Output Log function - Ghi log ra console và file
    
    Args:
        msg (str): Thông điệp cần log
    """
    print(msg)
    # Ghi log ra file với utf-8 encoding:
    try:
        log_file = os.getenv('LOG_FILE', 'log.txt')
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    except Exception as e:
        # Tránh lỗi khi file không thể write
        # Không print error để tránh loop
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
