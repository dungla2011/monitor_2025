"""
Enhanced Monitor Performance Test
Test các cải thiện mới:
1. Rate limiting trong monitor_checks.py
2. Connection pooling với HTTP session
3. Thread safety improvements
"""

import time
import threading
import concurrent.futures
from datetime import datetime
from monitor_checks import ping_web, ping_icmp, check_tcp_port, check_ssl_certificate, get_http_session

def test_connection_pooling_benefit():
    """
    So sánh hiệu suất với và không có connection pooling
    """
    print("🔄 Testing Connection Pooling Benefits...")
    print("=" * 50)
    
    urls = ["httpbin.org/status/200", "httpbin.org/delay/1", "google.com"]
    
    # Test với connection pooling (current implementation)
    print("\n📊 WITH Connection Pooling:")
    start_time = time.time()
    
    for i in range(3):  # 3 rounds
        print(f"  Round {i+1}:")
        for url in urls:
            success, status_code, response_time, message = ping_web(url, timeout=10)
            status = "✅" if success else "❌"
            print(f"    {status} {url:30} - {response_time:.2f}ms")
    
    pooled_time = time.time() - start_time
    print(f"\n⏱️  Total time WITH pooling: {pooled_time:.2f}s")
    
    # Test session reuse
    session = get_http_session()
    print(f"📡 Session info: {len(session.adapters)} adapters, keep-alive headers: {session.headers.get('Connection')}")

def test_rate_limiting_intervals():
    """
    Test các khoảng thời gian rate limiting
    """
    print("\n🔄 Testing Rate Limiting Intervals...")
    print("=" * 50)
    
    host = "8.8.8.8"
    
    print(f"Testing ICMP ping to {host} (rate limited with 0.05s delay):")
    
    times = []
    for i in range(5):
        start = time.time()
        success, response_time, message = ping_icmp(host, timeout=3)
        end = time.time()
        
        call_time = (end - start) * 1000  # ms
        times.append(call_time)
        
        status = "✅" if success else "❌"
        ping_time = f"{response_time:.2f}ms" if response_time else "N/A"
        print(f"  {status} Call {i+1}: {call_time:.2f}ms total (ping: {ping_time})")
    
    avg_call_time = sum(times) / len(times)
    print(f"\n📊 Average call time (including rate limit): {avg_call_time:.2f}ms")

def test_concurrent_thread_safety():
    """
    Test thread safety với concurrent requests
    """
    print("\n🔄 Testing Thread Safety...")
    print("=" * 50)
    
    urls = ["google.com", "github.com", "stackoverflow.com", "microsoft.com", "linkedin.com"] * 2
    
    print(f"Making {len(urls)} concurrent requests...")
    
    results = []
    errors = []
    
    def worker(url):
        try:
            result = ping_web(url, timeout=10)
            results.append((url, result))
            success, status_code, response_time, message = result
            thread_id = threading.current_thread().ident
            print(f"  Thread-{thread_id}: {url} -> {response_time:.2f}ms")
        except Exception as e:
            errors.append((url, str(e)))
            print(f"  ❌ Thread error on {url}: {e}")
    
    # Run concurrent requests
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, url) for url in urls]
        concurrent.futures.wait(futures)
    
    end_time = time.time()
    
    print(f"\n📊 Thread Safety Results:")
    print(f"   Total time: {end_time - start_time:.2f}s")
    print(f"   Successful requests: {len(results)}")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print("   Error details:")
        for url, error in errors:
            print(f"     - {url}: {error}")

def test_ssl_check_performance():
    """
    Test hiệu suất SSL certificate checks
    """
    print("\n🔄 Testing SSL Certificate Check Performance...")
    print("=" * 50)
    
    hosts = ["google.com", "github.com", "microsoft.com", "stackoverflow.com"]
    
    print("Testing SSL certificate expiry checks:")
    
    start_time = time.time()
    
    for host in hosts:
        check_start = time.time()
        is_valid, days_until_expiry, expiry_date, message = check_ssl_certificate(host, 443, timeout=10)
        check_end = time.time()
        
        check_time = (check_end - check_start) * 1000
        status = "✅" if is_valid else "❌"
        days_str = f"{days_until_expiry} days" if days_until_expiry else "N/A"
        
        print(f"  {status} {host:20} - {check_time:.2f}ms (expires in {days_str})")
    
    total_time = time.time() - start_time
    print(f"\n📊 SSL Check Summary:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average per host: {total_time/len(hosts):.2f}s")

def test_tcp_port_scanning():
    """
    Test TCP port check performance với rate limiting
    """
    print("\n🔄 Testing TCP Port Check Performance...")
    print("=" * 50)
    
    host = "google.com"
    ports = [80, 443, 22, 25, 53]
    
    print(f"Testing TCP ports on {host} (rate limited with 0.1s delay):")
    
    start_time = time.time()
    
    for port in ports:
        check_start = time.time()
        is_open, response_time, message = check_tcp_port(host, port, timeout=5)
        check_end = time.time()
        
        check_time = (check_end - check_start) * 1000
        status = "🟢 OPEN" if is_open else "🔴 CLOSED"
        rt_str = f"{response_time:.2f}ms" if response_time else "N/A"
        
        print(f"  {status} {host}:{port:5} - {check_time:.2f}ms total (connect: {rt_str})")
    
    total_time = time.time() - start_time
    print(f"\n📊 TCP Port Scan Summary:")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average per port: {total_time/len(ports):.2f}s")

def test_mixed_workload():
    """
    Test mixed workload với tất cả loại checks
    """
    print("\n🔄 Testing Mixed Workload Performance...")
    print("=" * 50)
    
    # Define mixed tasks
    tasks = [
        ("WEB", "ping_web", "google.com"),
        ("ICMP", "ping_icmp", "8.8.8.8"),  
        ("TCP", "check_tcp_port", ("github.com", 443)),
        ("SSL", "check_ssl_certificate", ("stackoverflow.com", 443)),
        ("WEB", "ping_web", "microsoft.com"),
        ("ICMP", "ping_icmp", "1.1.1.1"),
        ("TCP", "check_tcp_port", ("google.com", 80)),
        ("SSL", "check_ssl_certificate", ("github.com", 443)),
    ]
    
    print(f"Running {len(tasks)} mixed monitoring tasks...")
    
    results = []
    
    def run_task(task_type, func_name, args):
        try:
            start = time.time()
            
            if func_name == "ping_web":
                result = ping_web(args, timeout=8)
            elif func_name == "ping_icmp":
                result = ping_icmp(args, timeout=5)
            elif func_name == "check_tcp_port":
                host, port = args
                result = check_tcp_port(host, port, timeout=5)
            elif func_name == "check_ssl_certificate":
                host, port = args
                result = check_ssl_certificate(host, port, timeout=8)
            
            end = time.time()
            duration = (end - start) * 1000
            
            return (task_type, func_name, args, result, duration)
            
        except Exception as e:
            return (task_type, func_name, args, None, 0, str(e))
    
    # Run tasks concurrently
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for task_type, func_name, args in tasks:
            future = executor.submit(run_task, task_type, func_name, args)
            futures.append(future)
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                
                if len(result) == 6:  # Error case
                    task_type, func_name, args, result_data, duration, error = result
                    print(f"  ❌ {task_type:4} {args} - ERROR: {error}")
                else:
                    task_type, func_name, args, result_data, duration = result
                    success = result_data[0] if result_data else False
                    status = "✅" if success else "❌"
                    print(f"  {status} {task_type:4} {args} - {duration:.2f}ms")
                    
            except Exception as e:
                print(f"  ❌ Task execution error: {e}")
    
    end_time = time.time()
    
    # Summary
    successful_tasks = sum(1 for r in results if len(r) == 5 and r[3] and r[3][0])
    total_tasks = len(results)
    total_time = end_time - start_time
    
    print(f"\n📊 Mixed Workload Summary:")
    print(f"   Total execution time: {total_time:.2f}s")
    print(f"   Successful tasks: {successful_tasks}/{total_tasks}")
    print(f"   Success rate: {successful_tasks/total_tasks*100:.1f}%")
    print(f"   Tasks per second: {total_tasks/total_time:.2f}")

def main():
    """
    Main performance testing suite
    """
    print("🚀 Enhanced Monitor Performance Testing")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test 1: Connection pooling benefits
        test_connection_pooling_benefit()
        
        # Test 2: Rate limiting intervals
        test_rate_limiting_intervals()
        
        # Test 3: Thread safety
        test_concurrent_thread_safety()
        
        # Test 4: SSL performance
        test_ssl_check_performance()
        
        # Test 5: TCP port scanning
        test_tcp_port_scanning()
        
        # Test 6: Mixed workload
        test_mixed_workload()
        
        print(f"\n✅ All enhanced performance tests completed!")
        
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
