"""
Monitor Service Check Functions
Các hàm kiểm tra dịch vụ độc lập và có thể tái sử dụng
"""

import time
import requests
import subprocess
import platform
import socket
import ssl
from urllib.parse import urlparse
from datetime import datetime, timezone
from utils import ol1

# Global session với connection pooling để tái sử dụng connections
_session = None

def get_http_session():
    """
    Tạo hoặc trả về session HTTP với connection pooling
    """
    global _session
    if _session is None:
        _session = requests.Session()
        # Cấu hình connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # Số connection pools
            pool_maxsize=20,      # Số connections tối đa trong pool
            max_retries=2         # Số lần retry
        )
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
        
        # Cấu hình headers mặc định
        _session.headers.update({
            'User-Agent': 'Monitor2025/1.0 Health Check Bot',
            'Accept': 'text/html,application/json,*/*',
            'Connection': 'keep-alive'
        })
    return _session


def extract_domain_from_url(url):
    """
    Trích xuất domain hoặc IP từ URL
    Ví dụ: 
    - https://glx.com.vn/path -> glx.com.vn
    - 10.0.1.11 -> 10.0.1.11 (IP thuần)
    - http://10.0.1.11 -> 10.0.1.11
    """
    try:
        # Nếu URL không có scheme, coi như là hostname/IP thuần
        if '://' not in url:
            # Kiểm tra xem có phải IP hoặc hostname không
            import re
            # Pattern cho IP address
            ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
            # Pattern cho hostname (domain)
            hostname_pattern = r'^[a-zA-Z0-9.-]+$'
            
            if re.match(ip_pattern, url) or re.match(hostname_pattern, url):
                return url
            else:
                return None
        
        # Nếu có scheme, dùng urlparse như bình thường
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
        # Rate limiting: Small delay to avoid network congestion
        time.sleep(0.05)
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
            return True, response_time, f"Ping ok {host}"
        else:
            stderr_output = result.stderr.strip() if result.stderr else "No error details"
            stdout_output = result.stdout.strip() if result.stdout else ""
            
            # Log chi tiết để debug
            ol1(f" Ping failed: {host}")

            return False, None, f"Ping failed (code {result.returncode}): {stderr_output}"
            
    except subprocess.TimeoutExpired:
        return False, None, f"Ping timeout after {timeout} seconds"
    except KeyboardInterrupt:
        return False, None, "Ping stop (Ctrl+C)"
    except Exception as e:
        return False, None, f"Ping error: {str(e)}"

def check_ssl_certificate(host, port=443, timeout=10):
    """
    Kiểm tra SSL certificate và ngày hết hạn
    Returns: (is_valid: bool, days_until_expiry: int, expiry_date: str, error_message: str)
    """
    try:
        # Rate limiting: Small delay to avoid SSL connection flooding
        time.sleep(0.01)
        import ssl
        import socket
        from datetime import datetime, timezone
        
        # Tạo SSL context
        context = ssl.create_default_context()
        
        start_time = time.time()
        
        # Kết nối SSL
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # Lấy certificate
                cert = ssock.getpeercert()
                
                if not cert:
                    return False, None, None, f"No SSL certificate found {host}:{port}"
                
                # Parse ngày hết hạn
                not_after = cert['notAfter']
                # ol1(f"📜 SSL Certificate raw date: {not_after}")
                
                # Thử các format khác nhau
                date_formats = [
                    '%b %d %H:%M:%S %Y %GMT',  # Oct 17 00:58:13 2025 GMT
                    '%b %d %H:%M:%S %Y GMT',   # Oct 17 00:58:13 2025 GMT (không có %)
                    '%b  %d %H:%M:%S %Y %GMT', # Oct  17 00:58:13 2025 GMT (double space)
                    '%b  %d %H:%M:%S %Y GMT',  # Oct  17 00:58:13 2025 GMT (double space, no %)
                    '%Y-%m-%d %H:%M:%S',       # 2025-10-17 00:58:13
                ]
                
                expiry_date = None
                for date_format in date_formats:
                    try:
                        expiry_date = datetime.strptime(not_after, date_format)
                        # ol1(f"SSL date parsed with format: {date_format}")
                        break
                    except ValueError:
                        continue
                
                if not expiry_date:
                    return False, None, None, f"Cannot parse SSL certificate date: {not_after}, {host}:{port}"
                
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                
                # Tính số ngày còn lại
                now = datetime.now(timezone.utc)
                days_until_expiry = (expiry_date - now).days
                
                expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # ol1(f"📜 SSL Certificate expires on: {expiry_str} ({days_until_expiry} days remaining)")
                
                return True, days_until_expiry, expiry_str, f"SSL check successful {host}:{port}, (Response time: {response_time:.2f}ms)"
                
    except ssl.SSLError as e:
        return False, None, None, f"{host}:{port} SSL Error: {str(e)}"
    except socket.timeout:
        return False, None, None, f"{host}:{port} SSL timeout after {timeout} seconds"
    except socket.gaierror as e:
        return False, None, None, f"{host}:{port} DNS resolution error: {str(e)}"
    except Exception as e:
        return False, None, None, f"{host}:{port} SSL check error: {str(e)}"

def check_tcp_port(host, port, timeout=5):
    """
    Kiểm tra TCP port có mở hay không
    Returns: (is_open: bool, response_time: float or None, error_message: str)
    """
    try:
        # Rate limiting: Small delay to avoid port scanning alarms
        time.sleep(0.01)
        import socket
        
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        result = sock.connect_ex((host, int(port)))
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        sock.close()
        
        if result == 0:
            return True, response_time, f"{host}:{port}  is open"
        else:
            return False, response_time, f"{host}:{port} is closed or filtered"
            
    except socket.timeout:
        return False, None, f"{host}:{port} TCP timeout after {timeout} seconds"
    except socket.gaierror as e:
        return False, None, f"{host}:{port} DNS resolution error: {str(e)}"
    except Exception as e:
        return False, None, f"{host}:{port} TCP check error: {str(e)}"

def ping_web(url, timeout=10):
    """
    Kiểm tra HTTP/HTTPS URL
    Tự động thêm scheme nếu không có
    Returns: (success: bool, status_code: int or None, response_time: float, error_message: str)
    """
    try:
        # Rate limiting: Small delay to avoid overwhelming servers
        time.sleep(0.1)
        # Tự động thêm scheme nếu không có
        if '://' not in url:
            # Thử HTTPS trước, nếu fail thì HTTP
            test_url = f"https://{url}"
        else:
            test_url = url
        
        start_time = time.time()
        session = get_http_session()
        response = session.get(test_url, timeout=timeout, allow_redirects=True)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            return True, response.status_code, response_time, "HTTP request successful"
        else:
            return False, response.status_code, response_time, f"HTTP {response.status_code}: {response.reason}"
            
    except requests.exceptions.SSLError as e:
        # Nếu HTTPS fail với SSL error, thử HTTP
        if '://' not in url:
            try:
                test_url = f"http://{url}"
                start_time = time.time()
                session = get_http_session()
                response = session.get(test_url, timeout=timeout, allow_redirects=True)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    return True, response.status_code, response_time, "HTTP request successful (fallback to HTTP)"
                else:
                    return False, response.status_code, response_time, f"HTTP {response.status_code}: {response.reason}"
            except:
                return False, None, None, f"SSL error with HTTPS, HTTP also failed: {str(e)}"
        else:
            return False, None, None, f"SSL error: {str(e)}"
    except requests.exceptions.Timeout:
        return False, None, None, f"HTTP timeout after {timeout} seconds"
    except requests.exceptions.ConnectionError:
        return False, None, None, "Connection error - cannot reach server"
    except requests.exceptions.RequestException as e:
        return False, None, None, f"HTTP request error: {str(e)}"
    except Exception as e:
        return False, None, None, f"Unexpected error: {str(e)}"

def fetch_web_content(url, timeout=10, max_size=102400):
    """
    Fetch web content với giới hạn kích thước
    Tự động thêm scheme nếu không có
    Returns: (success: bool, status_code: int or None, response_time: float, content: str, error_message: str)
    """
    try:
        # Tự động thêm scheme nếu không có
        if '://' not in url:
            # Thử HTTPS trước, nếu fail thì HTTP
            test_url = f"https://{url}"
        else:
            test_url = url
        
        start_time = time.time()
        
        # Stream download để kiểm soát kích thước
        session = get_http_session()
        response = session.get(test_url, timeout=timeout, allow_redirects=True, stream=True)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            # Đọc content với giới hạn kích thước
            content = ""
            content_length = 0
            
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    chunk_size = len(chunk.encode('utf-8'))
                    if content_length + chunk_size > max_size:
                        # Chỉ lấy phần còn lại
                        remaining = max_size - content_length
                        if remaining > 0:
                            # Cắt chunk để fit vào remaining bytes
                            chunk_bytes = chunk.encode('utf-8')[:remaining]
                            content += chunk_bytes.decode('utf-8', errors='ignore')
                        break
                    content += chunk
                    content_length += chunk_size
            
            response.close()
            
            ol1(f"📄 Downloaded {content_length} bytes (max: {max_size})")
            return True, response.status_code, response_time, content, "Content fetched successfully"
        else:
            response.close()
            return False, response.status_code, response_time, "", f"HTTP {response.status_code}: {response.reason}"
            
    except requests.exceptions.SSLError as e:
        # Nếu HTTPS fail với SSL error, thử HTTP
        if '://' not in url:
            try:
                test_url = f"http://{url}"
                start_time = time.time()
                session = get_http_session()
                response = session.get(test_url, timeout=timeout, allow_redirects=True, stream=True)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    content = ""
                    content_length = 0
                    
                    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                        if chunk:
                            chunk_size = len(chunk.encode('utf-8'))
                            if content_length + chunk_size > max_size:
                                remaining = max_size - content_length
                                if remaining > 0:
                                    chunk_bytes = chunk.encode('utf-8')[:remaining]
                                    content += chunk_bytes.decode('utf-8', errors='ignore')
                                break
                            content += chunk
                            content_length += chunk_size
                    
                    response.close()
                    ol1(f"📄 Downloaded {content_length} bytes via HTTP fallback")
                    return True, response.status_code, response_time, content, "Content fetched successfully (fallback to HTTP)"
                else:
                    response.close()
                    return False, response.status_code, response_time, "", f"HTTP {response.status_code}: {response.reason}"
            except:
                return False, None, None, "", f"SSL error with HTTPS, HTTP also failed: {str(e)}"
        else:
            return False, None, None, "", f"SSL error: {str(e)}"
    except requests.exceptions.Timeout:
        return False, None, None, "", f"HTTP timeout after {timeout} seconds"
    except requests.exceptions.ConnectionError:
        return False, None, None, "", "Connection error - cannot reach server"
    except requests.exceptions.RequestException as e:
        return False, None, None, "", f"HTTP request error: {str(e)}"
    except Exception as e:
        return False, None, None, "", f"Unexpected error: {str(e)}"

def check_open_port_tcp_then_error(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra TCP port và báo lỗi nếu port đang mở (ngược lại với ping_web)
    URL format: domain:port hoặc ip:port
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    # Parse host:port từ url_check
    url_check = monitor_item.url_check
    if ':' not in url_check:
        return {
            'success': False,
            'response_time': None,
            'message': "❌ Invalid format. Expected 'host:port' (e.g., '192.168.1.1:22' or 'example.com:80')",
            'details': {'host': None, 'port': None, 'method': 'TCP Port Check (Error if Open)', 'attempt': attempt}
        }
    
    try:
        host, port_str = url_check.rsplit(':', 1)  # Split from right to handle IPv6 correctly
        port = int(port_str)
        
        if not (1 <= port <= 65535):
            return {
                'success': False,
                'response_time': None,
                'message': f"❌ Invalid port number: {port}. Must be 1-65535",
                'details': {'host': host, 'port': port, 'method': 'TCP Port Check (Error if Open)', 'attempt': attempt}
            }
            
    except ValueError:
        return {
            'success': False,
            'response_time': None,
            'message': f"❌ Cannot parse port from '{url_check}'. Expected 'host:port' format",
            'details': {'host': None, 'port': None, 'method': 'TCP Port Check (Error if Open)', 'attempt': attempt}
        }
    
    ol1(f"🔍 TCP Port Check (Error if Open) - {host}:{port} (attempt {attempt}/{max_attempts})...", monitor_item)
    
    is_open, response_time, message = check_tcp_port(host, port)
    
    # Logic ngược lại: SUCCESS nếu port CLOSED, ERROR nếu port OPEN
    result = {
        'success': not is_open,  # SUCCESS nếu port đóng
        'response_time': response_time,
        'message': f"Port {port} is {'CLOSED' if not is_open else 'OPEN'} - {'✅ Good' if not is_open else '❌ Alert'}",
        'details': {
            'host': host,
            'port': port,
            'is_port_open': is_open,
            'original_message': message,
            'method': 'TCP Port Check (Error if Open)',
            'attempt': attempt
        }
    }
    
    if not is_open:  # Port closed = success
        ol1(f"✅ {result['message']} (Time: {response_time:.2f}ms)" if response_time else f"   ✅ {result['message']}", monitor_item)
        return result
    else:  # Port open = error
        ol1(f"❌ Attempt {attempt}: {result['message']} (Time: {response_time:.2f}ms)" if response_time else f"   ❌ Attempt {attempt}: {result['message']}", monitor_item)
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"⏳ Waiting 3s...", monitor_item)
            time.sleep(3)
            return check_open_port_tcp_then_error(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"💥 Port still open after {max_attempts} attempts", monitor_item)
            return result

def check_ssl_expired_check(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra SSL certificate và báo lỗi nếu sắp hết hạn trong 7 ngày
    URL format: domain hoặc domain:port
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    url_check = monitor_item.url_check
    
    # Parse host và port từ url_check
    if '://' in url_check:
        # Nếu có scheme, parse URL
        from urllib.parse import urlparse
        parsed = urlparse(url_check)
        host = parsed.hostname
        port = parsed.port
        if not port:
            port = 443 if parsed.scheme == 'https' else 443  # Default to 443
    elif ':' in url_check:
        # Format host:port
        try:
            host, port_str = url_check.rsplit(':', 1)
            port = int(port_str)
        except ValueError:
            return {
                'success': False,
                'response_time': None,
                'message': f"❌ Cannot parse port from '{url_check}'. Expected 'host:port' format",
                'details': {'host': None, 'port': None, 'method': 'SSL Certificate Check', 'attempt': attempt}
            }
    else:
        # Chỉ có domain
        host = url_check
        port = 443  # Default HTTPS port
    
    if not host:
        return {
            'success': False,
            'response_time': None,
            'message': "❌ Cannot extract host from URL",
            'details': {'host': None, 'port': port, 'method': 'SSL Certificate Check', 'attempt': attempt}
        }
    
    if not (1 <= port <= 65535):
        return {
            'success': False,
            'response_time': None,
            'message': f"❌ Invalid port number: {port}. Must be 1-65535",
            'details': {'host': host, 'port': port, 'method': 'SSL Certificate Check', 'attempt': attempt}
        }
    
    ol1(f"🔒 SSL Certificate Check - {host}:{port} (attempt {attempt}/{max_attempts})...", monitor_item)
    
    is_valid, days_until_expiry, expiry_date, message = check_ssl_certificate(host, port)
    
    if not is_valid:
        result = {
            'success': False,
            'response_time': None,
            'message': message,
            'details': {
                'host': host,
                'port': port,
                'method': 'SSL Certificate Check',
                'attempt': attempt,
                'error_type': 'ssl_connection_failed'
            }
        }
        
        ol1(f"❌ Attempt {attempt}: {message}", monitor_item)
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"⏳ Waiting 3s...", monitor_item)
            time.sleep(3)
            return check_ssl_expired_check(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"💥 SSL check failed after {max_attempts} attempts", monitor_item)
            return result
    
    # SSL certificate valid, kiểm tra ngày hết hạn
    WARNING_DAYS = 7  # Cảnh báo nếu còn <= 7 ngày
    
    result = {
        'success': days_until_expiry > WARNING_DAYS,  # SUCCESS nếu còn > 7 ngày
        'response_time': None,  # SSL check không có response time
        'message': f"SSL expires in {days_until_expiry} days ({expiry_date})",
        'details': {
            'host': host,
            'port': port,
            'days_until_expiry': days_until_expiry,
            'expiry_date': expiry_date,
            'warning_threshold': WARNING_DAYS,
            'method': 'SSL Certificate Check',
            'attempt': attempt
        }
    }
    
    if days_until_expiry > WARNING_DAYS:
        # SSL certificate còn hạn lâu
        result['message'] = f"✅ SSL valid for {days_until_expiry} days (expires: {expiry_date})"
        ol1(f"✅ {result['message']}", monitor_item)
        return result
    elif days_until_expiry > 0:
        # SSL sắp hết hạn (1-7 ngày)
        result['success'] = False
        result['message'] = f"⚠️ SSL expires in {days_until_expiry} days - Sắp hết hạn! (expires: {expiry_date})"
        result['details']['error_type'] = 'ssl_expiring_soon'
        ol1(f"⚠️ {result['message']}", monitor_item)
        return result
    else:
        # SSL đã hết hạn
        result['success'] = False
        result['message'] = f"❌ SSL certificate expired {abs(days_until_expiry)} days ago! (expired: {expiry_date})"
        result['details']['error_type'] = 'ssl_expired'
        ol1(f"❌ {result['message']}", monitor_item)
        return result

def check_open_port_tcp_then_valid(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra TCP port và báo lỗi nếu port KHÔNG mở (ngược lại với open_port_tcp_then_error)
    URL format: domain:port hoặc ip:port
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    # Parse host:port từ url_check
    url_check = monitor_item.url_check
    if ':' not in url_check:
        return {
            'success': False,
            'response_time': None,
            'message': "❌ Invalid format. Expected 'host:port' (e.g., '192.168.1.1:80' or 'example.com:443')",
            'details': {'host': None, 'port': None, 'method': 'TCP Port Check (Valid if Open)', 'attempt': attempt}
        }
    
    try:
        host, port_str = url_check.rsplit(':', 1)  # Split from right to handle IPv6 correctly
        port = int(port_str)
        
        if not (1 <= port <= 65535):
            return {
                'success': False,
                'response_time': None,
                'message': f"❌ Invalid port number: {port}. Must be 1-65535",
                'details': {'host': host, 'port': port, 'method': 'TCP Port Check (Valid if Open)', 'attempt': attempt}
            }
            
    except ValueError:
        return {
            'success': False,
            'response_time': None,
            'message': f"❌ Cannot parse port from '{url_check}'. Expected 'host:port' format",
            'details': {'host': None, 'port': None, 'method': 'TCP Port Check (Valid if Open)', 'attempt': attempt}
        }
    ol1(f"🔍 TCP Port Check (Valid if Open) - {host}:{port} (attempt {attempt}/{max_attempts})...", monitor_item)
    is_open, response_time, message = check_tcp_port(host, port)
    
    # Logic bình thường: SUCCESS nếu port OPEN, ERROR nếu port CLOSED
    result = {
        'success': is_open,  # SUCCESS nếu port mở
        'response_time': response_time,
        'message': f"Port {port} is {'OPEN' if is_open else 'CLOSED'} - {'✅ Good' if is_open else '❌ Alert'}",
        'details': {
            'host': host,
            'port': port,
            'is_port_open': is_open,
            'original_message': message,
            'method': 'TCP Port Check (Valid if Open)',
            'attempt': attempt
        }
    }
    
    if is_open:  # Port open = success
        ol1(f"✅ {result['message']} (Time: {response_time:.2f}ms)" if response_time else f"   ✅ {result['message']}", monitor_item)
        return result
    else:  # Port closed = error
        ol1(f"❌ Attempt {attempt}: {result['message']} (Time: {response_time:.2f}ms)" if response_time else f"   ❌ Attempt {attempt}: {result['message']}", monitor_item)

        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"⏳ Waiting 3s...", monitor_item)
            time.sleep(3)
            return check_open_port_tcp_then_valid(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"💥 Port still closed after {max_attempts} attempts", monitor_item)
            return result

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
    ol1(f"🌐 HTTP/HTTPS check (attempt {attempt}/{max_attempts})...", monitor_item)

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
        ol1(f"✅ {message} (Status: {status_code}, Time: {response_time:.2f}ms)", monitor_item)
        return result
    else:
        ol1(f"❌ Attempt {attempt}: {message}", monitor_item)

        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"⏳ Waiting 3s...", monitor_item)
            time.sleep(3)
            return check_ping_web(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"💥 Failed after {max_attempts} attempts", monitor_item)
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
    
    ol1(f"- Ping {host} (try {attempt}/{max_attempts}) ", monitor_item)
    
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
        ol1(f"✅ {message} (Time: {response_time:.2f}ms)", monitor_item)
        return result
    else:
        ol1(f" Attempt {attempt}: {message}", monitor_item)
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f" Waiting 3s before retry...", monitor_item)
            time.sleep(3)
            return check_ping_icmp(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f" Failed after {max_attempts} attempts", monitor_item)
            return result

def check_web_content(monitor_item, attempt=1, max_attempts=3):
    """
    Kiểm tra web content với retry logic
    
    Args:
        monitor_item: MonitorItem object from database
        attempt: Lần thử hiện tại (1-3)
        max_attempts: Số lần thử tối đa
        
    Returns:
        dict: Kết quả kiểm tra
    """
    ol1(f"📄 Web content check (attempt {attempt}/{max_attempts})...", monitor_item)
    
    # Fetch web content
    success, status_code, response_time, content, message = fetch_web_content(monitor_item.url_check)
    
    result = {
        'success': success,
        'response_time': response_time,
        'message': message,
        'details': {
            'status_code': status_code,
            'method': 'Web Content',
            'attempt': attempt,
            'content_length': len(content) if content else 0
        }
    }
    
    if not success:
        ol1(f"❌ Attempt {attempt}: {message}", monitor_item)
        
        # Nếu chưa thành công và còn lần thử
        if attempt < max_attempts:
            ol1(f"⏳ Waiting 3s...", monitor_item)
            time.sleep(3)
            return check_web_content(monitor_item, attempt + 1, max_attempts)
        else:
            ol1(f"💥 Failed after {max_attempts} attempts", monitor_item)
            return result
    
    # Content đã fetch thành công, bây giờ kiểm tra nội dung
    ol1(f"📄 Content fetched successfully ({len(content)} chars)", monitor_item)

    # Kiểm tra result_error trước (higher priority)
    if monitor_item.result_error and monitor_item.result_error.strip():
        error_keywords = [keyword.strip() for keyword in monitor_item.result_error.split(',') if keyword.strip()]
        ol1(f"🔍 Checking for error keywords: {error_keywords}", monitor_item)

        for keyword in error_keywords:
            if keyword in content:
                result['success'] = False
                result['message'] = f"❌ Found error keyword: '{keyword}'"
                result['details']['failed_keyword'] = keyword
                result['details']['check_type'] = 'error_keyword'
                ol1(f"❌ Found error keyword: '{keyword}'")
                return result
        
        ol1(f"✅ No error keywords found")
    
    # Kiểm tra result_valid (required keywords)
    if monitor_item.result_valid and monitor_item.result_valid.strip():
        valid_keywords = [keyword.strip() for keyword in monitor_item.result_valid.split(',') if keyword.strip()]
        ol1(f"🔍 Checking for required keywords: {valid_keywords}")
        
        missing_keywords = []
        for keyword in valid_keywords:
            if keyword not in content:
                missing_keywords.append(keyword)
        
        if missing_keywords:
            result['success'] = False
            result['message'] = f"❌ Missing required keywords: {', '.join(missing_keywords)}"
            result['details']['missing_keywords'] = missing_keywords
            result['details']['check_type'] = 'missing_required'
            ol1(f"❌ Missing required keywords: {missing_keywords}", monitor_item)
            return result

        ol1(f"✅ All required keywords found", monitor_item)

    # Nếu không có lỗi và tất cả keywords required đều có
    result['success'] = True
    result['message'] = f"✅ Content validation passed (Status: {status_code})"
    result['details']['check_type'] = 'content_validation'
    ol1(f"✅ Content validation passed", monitor_item)
    
    return result
