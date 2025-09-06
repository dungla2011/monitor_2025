import time
import requests
import subprocess
import platform
from urllib.parse import urlparse
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

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
    Lấy hàng đầu tiên từ bảng monitor_items
    """
    try:
        session = SessionLocal()
        first_item = session.query(MonitorItem).filter(
            MonitorItem.url_check.isnot(None),
            MonitorItem.url_check != ''
        ).first()
        session.close()
        return first_item
    except Exception as e:
        print(f"❌ Error getting first monitor item: {e}")
        return None

def test_first_service():
    """
    Test kiểm tra dịch vụ đầu tiên
    """
    print("🚀 Testing monitor service checker...")
    print("="*80)
    
    # Lấy hàng đầu tiên
    first_item = get_first_monitor_item()
    
    if not first_item:
        print("❌ No monitor items found in database")
        return
    
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
                monitor_service_loop(first_item)
            else:
                print("❌ No monitor items found")
                
        elif command == 'all':
            # Kiểm tra tất cả dịch vụ enabled một lần
            monitor_all_services_once()
            
        elif command == 'test':
            # Test dịch vụ đầu tiên
            test_first_service()
            
        else:
            print("Usage:")
            print("  python monitor_service.py test       - Test first service once")
            print("  python monitor_service.py loop       - Monitor first service continuously (until disabled)")
            print("  python monitor_service.py all        - Check all enabled services once")
    else:
        # Mặc định: test dịch vụ đầu tiên
        test_first_service()

if __name__ == "__main__":
    main()
