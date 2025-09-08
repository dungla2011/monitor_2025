#!/usr/bin/env python3
"""
Monitor Service Performance Tester
Kiểm tra hiệu suất và stress test của monitoring system
"""

import os
import sys
import time
import requests
import threading
import concurrent.futures
from datetime import datetime
from statistics import mean, median
from utils import ol1

class PerformanceTester:
    def __init__(self):
        self.api_base_url = 'http://127.0.0.1:5005'
        self.results = {}
        
    def print_header(self, title):
        """Print test section header"""
        print("\n" + "="*60)
        print(f"⚡ {title}")
        print("="*60)
        
    def test_api_response_time(self, endpoint='/', iterations=50):
        """Test API response time"""
        self.print_header(f"API Response Time Test - {endpoint}")
        
        response_times = []
        errors = 0
        
        print(f"🔄 Testing {iterations} requests to {endpoint}...")
        
        for i in range(iterations):
            try:
                start_time = time.time()
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=5)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # ms
                response_times.append(response_time)
                
                if response.status_code not in [200, 201]:
                    errors += 1
                    
                if (i + 1) % 10 == 0:
                    print(f"   Progress: {i+1}/{iterations} requests completed")
                    
            except Exception as e:
                errors += 1
                print(f"   Error in request {i+1}: {e}")
        
        if response_times:
            avg_time = mean(response_times)
            median_time = median(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Results for {endpoint}:")
            print(f"   Total requests: {iterations}")
            print(f"   Successful: {len(response_times)}")
            print(f"   Errors: {errors}")
            print(f"   Average response time: {avg_time:.2f}ms")
            print(f"   Median response time: {median_time:.2f}ms")
            print(f"   Min response time: {min_time:.2f}ms")
            print(f"   Max response time: {max_time:.2f}ms")
            
            self.results[f"api_{endpoint.replace('/', '_')}"] = {
                'avg_time': avg_time,
                'median_time': median_time,
                'min_time': min_time,
                'max_time': max_time,
                'error_rate': errors / iterations * 100
            }
        else:
            print("❌ All requests failed!")
    
    def test_concurrent_requests(self, endpoint='/', concurrent_users=10, requests_per_user=20):
        """Test concurrent API requests"""
        self.print_header(f"Concurrent Requests Test - {endpoint}")
        
        print(f"🔄 Testing {concurrent_users} concurrent users, {requests_per_user} requests each...")
        
        def make_requests(user_id):
            """Function for each concurrent user"""
            user_times = []
            user_errors = 0
            
            for i in range(requests_per_user):
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000
                    user_times.append(response_time)
                    
                    if response.status_code not in [200, 201]:
                        user_errors += 1
                        
                except Exception:
                    user_errors += 1
            
            return user_times, user_errors
        
        # Execute concurrent requests
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, i) for i in range(concurrent_users)]
            
            all_times = []
            total_errors = 0
            
            for future in concurrent.futures.as_completed(futures):
                user_times, user_errors = future.result()
                all_times.extend(user_times)
                total_errors += user_errors
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if all_times:
            total_requests = concurrent_users * requests_per_user
            successful_requests = len(all_times)
            
            avg_time = mean(all_times)
            median_time = median(all_times)
            requests_per_second = successful_requests / total_time
            
            print(f"\n📊 Concurrent Test Results:")
            print(f"   Total requests: {total_requests}")
            print(f"   Successful: {successful_requests}")
            print(f"   Errors: {total_errors}")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Requests/second: {requests_per_second:.2f}")
            print(f"   Average response time: {avg_time:.2f}ms")
            print(f"   Median response time: {median_time:.2f}ms")
            
            self.results[f"concurrent_{endpoint.replace('/', '_')}"] = {
                'requests_per_second': requests_per_second,
                'avg_time': avg_time,
                'error_rate': total_errors / total_requests * 100
            }
        else:
            print("❌ All concurrent requests failed!")
    
    def test_memory_usage(self):
        """Test memory usage via API"""
        self.print_header("Memory Usage Test")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Try to get memory info if available
                print(f"📊 System Status:")
                print(f"   Uptime: {data.get('uptime', 'N/A')}")
                print(f"   Active threads: {data.get('active_threads', 'N/A')}")
                print(f"   Process info: Available via API")
                
                # Make multiple requests to check for memory leaks
                print(f"\n🔄 Testing for memory leaks (100 requests)...")
                
                for i in range(100):
                    response = requests.get(f"{self.api_base_url}/api/status", timeout=5)
                    if (i + 1) % 20 == 0:
                        print(f"   Progress: {i+1}/100 requests")
                
                print("✅ Memory leak test completed (monitor memory manually)")
                
            else:
                print(f"❌ Cannot get status: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Memory test failed: {e}")
    
    def test_database_performance(self):
        """Test database performance"""
        self.print_header("Database Performance Test")
        
        try:
            from sqlalchemy.orm import sessionmaker
            from db_connection import engine
            from models import MonitorItem
            
            SessionLocal = sessionmaker(bind=engine)
            
            # Test query performance
            query_times = []
            
            print("🔄 Testing database query performance (50 queries)...")
            
            for i in range(50):
                start_time = time.time()
                session = SessionLocal()
                items = session.query(MonitorItem).all()
                session.close()
                end_time = time.time()
                
                query_time = (end_time - start_time) * 1000
                query_times.append(query_time)
                
                if (i + 1) % 10 == 0:
                    print(f"   Progress: {i+1}/50 queries completed")
            
            if query_times:
                avg_time = mean(query_times)
                median_time = median(query_times)
                min_time = min(query_times)
                max_time = max(query_times)
                
                print(f"\n📊 Database Query Performance:")
                print(f"   Average query time: {avg_time:.2f}ms")
                print(f"   Median query time: {median_time:.2f}ms")
                print(f"   Min query time: {min_time:.2f}ms")
                print(f"   Max query time: {max_time:.2f}ms")
                
                self.results['database'] = {
                    'avg_query_time': avg_time,
                    'median_query_time': median_time
                }
            
        except Exception as e:
            print(f"❌ Database performance test failed: {e}")
    
    def test_service_check_performance(self):
        """Test service check performance"""
        self.print_header("Service Check Performance Test")
        
        try:
            from monitor_service import ping_web, ping_icmp, check_tcp_port
            
            # Test ping_web performance
            web_times = []
            print("🔄 Testing ping_web performance (20 checks to google.com)...")
            
            for i in range(20):
                start_time = time.time()
                success, status_code, response_time, message = ping_web('https://google.com')
                end_time = time.time()
                
                check_time = (end_time - start_time) * 1000
                web_times.append(check_time)
                
                if (i + 1) % 5 == 0:
                    print(f"   Progress: {i+1}/20 web checks completed")
            
            # Test ping_icmp performance
            icmp_times = []
            print("\n🔄 Testing ping_icmp performance (20 checks to 8.8.8.8)...")
            
            for i in range(20):
                start_time = time.time()
                success, response_time, message = ping_icmp('8.8.8.8')
                end_time = time.time()
                
                check_time = (end_time - start_time) * 1000
                icmp_times.append(check_time)
                
                if (i + 1) % 5 == 0:
                    print(f"   Progress: {i+1}/20 ICMP checks completed")
            
            # Test TCP port check performance
            tcp_times = []
            print("\n🔄 Testing TCP port check performance (20 checks to google.com:80)...")
            
            for i in range(20):
                start_time = time.time()
                is_open, response_time, message = check_tcp_port('google.com', 80)
                end_time = time.time()
                
                check_time = (end_time - start_time) * 1000
                tcp_times.append(check_time)
                
                if (i + 1) % 5 == 0:
                    print(f"   Progress: {i+1}/20 TCP checks completed")
            
            # Print results
            print(f"\n📊 Service Check Performance:")
            if web_times:
                print(f"   ping_web average: {mean(web_times):.2f}ms")
            if icmp_times:
                print(f"   ping_icmp average: {mean(icmp_times):.2f}ms")
            if tcp_times:
                print(f"   TCP check average: {mean(tcp_times):.2f}ms")
            
            self.results['service_checks'] = {
                'ping_web_avg': mean(web_times) if web_times else 0,
                'ping_icmp_avg': mean(icmp_times) if icmp_times else 0,
                'tcp_check_avg': mean(tcp_times) if tcp_times else 0
            }
            
        except Exception as e:
            print(f"❌ Service check performance test failed: {e}")
    
    def print_summary(self):
        """Print performance test summary"""
        self.print_header("Performance Test Summary")
        
        print("📊 Performance Summary:")
        
        for test_name, metrics in self.results.items():
            print(f"\n🔸 {test_name.upper()}:")
            for metric_name, value in metrics.items():
                if 'time' in metric_name:
                    print(f"   {metric_name}: {value:.2f}ms")
                elif 'rate' in metric_name:
                    print(f"   {metric_name}: {value:.2f}%")
                else:
                    print(f"   {metric_name}: {value:.2f}")
        
        # Performance recommendations
        print(f"\n💡 Performance Recommendations:")
        
        # API performance check
        if 'api__' in self.results:
            api_time = self.results['api__'].get('avg_time', 0)
            if api_time > 1000:
                print("   ⚠️ API response time > 1s - consider optimization")
            elif api_time > 500:
                print("   ⚠️ API response time > 500ms - monitor closely")
            else:
                print("   ✅ API response time is good")
        
        # Database performance check
        if 'database' in self.results:
            db_time = self.results['database'].get('avg_query_time', 0)
            if db_time > 100:
                print("   ⚠️ Database queries > 100ms - consider indexing")
            else:
                print("   ✅ Database performance is good")
        
        print(f"\n🎯 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("⚡ Starting Monitor Service Performance Tests...")
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test sequence
        self.test_api_response_time('/')
        self.test_api_response_time('/api/status')
        self.test_api_response_time('/api/monitors')
        
        self.test_concurrent_requests('/api/status', concurrent_users=5, requests_per_user=10)
        
        self.test_memory_usage()
        self.test_database_performance()
        self.test_service_check_performance()
        
        self.print_summary()


def main():
    """Main performance test function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Monitor Service Performance Tester")
        print("Usage:")
        print("  python test_performance.py           - Run all performance tests")
        print("  python test_performance.py --help    - Show this help")
        return
    
    # Check if service is running
    try:
        response = requests.get('http://127.0.0.1:5005/api/status', timeout=5)
        if response.status_code != 200:
            print("❌ Monitor service is not running or not responding")
            print("   Please start the service first: python monitor_service.py start")
            sys.exit(1)
    except:
        print("❌ Cannot connect to monitor service")
        print("   Please start the service first: python monitor_service.py start")
        sys.exit(1)
    
    # Create tester instance
    tester = PerformanceTester()
    
    # Run all tests
    tester.run_all_tests()
    
    print("\n✅ Performance tests completed!")


if __name__ == "__main__":
    main()
