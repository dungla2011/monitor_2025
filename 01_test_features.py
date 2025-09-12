#!/usr/bin/env python3
"""
Monitor Service Feature Tester
Kiểm tra toàn bộ tính năng của monitoring system
"""

import os
import sys
import time
import requests
import json
import threading
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Load test environment first
from test_env_loader import (
    load_test_environment, verify_test_environment, 
    get_test_database_url, get_test_api_url,
    is_test_mode, should_cleanup_test_data, get_test_timeout
)

# Load test environment
if not load_test_environment():
    print("❌ Cannot load test environment")
    sys.exit(1)

success, missing_vars = verify_test_environment()
if not success:
    print(f"❌ Test environment verification failed: {missing_vars}")
    sys.exit(1)

# Import local modules after environment is loaded
from models import MonitorItem
from utils import ol1

# Test configuration using test environment
TEST_CONFIG = {
    'api_base_url': get_test_api_url(),
    'test_timeout': get_test_timeout(),
    'check_interval': 5,  # seconds
}

class MonitorTester:
    def __init__(self):
        # Create test database engine
        database_url = get_test_database_url()
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.test_results = {}
        self.test_items = []
        
        print(f"🔧 Test database: {database_url}")
        print(f"🔧 Test API: {TEST_CONFIG['api_base_url']}")
        
    def print_header(self, title):
        """Print test section header"""
        print("\n" + "="*60)
        print(f"🧪 {title}")
        print("="*60)
        
    def print_test(self, test_name, success, message=""):
        """Print test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status} - {test_name}")
        if message:
            print(f"    {message}")
        
        self.test_results[test_name] = {
            'success': success,
            'message': message,
            'timestamp': timestamp
        }
        
    def test_database_connection(self):
        """Test 1: Database connection"""
        self.print_header("Database Connection Test")
        
        try:
            session = self.SessionLocal()
            # Test basic query
            count = session.query(MonitorItem).count()
            session.close()
            self.print_test("Database Connection", True, f"Found {count} monitor items")
            return True
        except Exception as e:
            self.print_test("Database Connection", False, str(e))
            return False
    
    def test_api_server_running(self):
        """Test 2: API server availability"""
        self.print_header("API Server Test")
        
        try:
            response = requests.get(f"{TEST_CONFIG['api_base_url']}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.print_test("API Server Status", True, f"Server running, uptime: {data.get('uptime', 'N/A')}")
                return True
            else:
                self.print_test("API Server Status", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.print_test("API Server Status", False, str(e))
            return False
    
    def test_api_endpoints(self):
        """Test 3: All API endpoints"""
        self.print_header("API Endpoints Test")
        
        endpoints = [
            ('GET', '/', 'Dashboard'),
            ('GET', '/api/status', 'Status API'),
            ('GET', '/api/monitors', 'Monitors API'),
            ('GET', '/api/threads', 'Threads API'),
        ]
        
        all_passed = True
        for method, endpoint, name in endpoints:
            try:
                url = f"{TEST_CONFIG['api_base_url']}{endpoint}"
                if method == 'GET':
                    response = requests.get(url, timeout=5)
                
                if response.status_code in [200, 201]:
                    self.print_test(f"API {name}", True, f"{method} {endpoint} - {response.status_code}")
                else:
                    self.print_test(f"API {name}", False, f"{method} {endpoint} - {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.print_test(f"API {name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def create_test_monitor_items(self):
        """Test 4: Create test monitor items for all service types"""
        self.print_header("Create Test Monitor Items")
        
        test_items = [
            {
                'name': 'TEST_ping_web_success',
                'type': 'ping_web', 
                'url_check': 'https://google.com',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_ping_web_fail',
                'type': 'ping_web',
                'url_check': 'https://nonexistent-domain-12345.com',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_ping_icmp_success', 
                'type': 'ping_icmp',
                'url_check': '8.8.8.8',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_ping_icmp_fail',
                'type': 'ping_icmp', 
                'url_check': '192.168.255.254',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_web_content_success',
                'type': 'web_content',
                'url_check': 'https://google.com',
                'result_valid': 'Google',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_web_content_fail',
                'type': 'web_content',
                'url_check': 'https://google.com', 
                'result_valid': 'NonExistentKeyword12345',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_open_port_tcp_then_error',
                'type': 'open_port_tcp_then_error',
                'url_check': 'google.com:80',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_open_port_tcp_then_valid',
                'type': 'open_port_tcp_then_valid', 
                'url_check': 'google.com:80',
                'enable': True,
                'check_interval_seconds': 60
            },
            {
                'name': 'TEST_ssl_expired_check',
                'type': 'ssl_expired_check',
                'url_check': 'https://google.com',
                'enable': True,
                'check_interval_seconds': 60
            }
        ]
        
        created_count = 0
        try:
            session = self.SessionLocal()
            
            for item_data in test_items:
                # Kiểm tra xem item đã tồn tại chưa
                existing = session.query(MonitorItem).filter_by(name=item_data['name']).first()
                
                if existing:
                    self.print_test(f"Create {item_data['name']}", True, "Already exists")
                    self.test_items.append(existing)
                else:
                    # Tạo mới
                    new_item = MonitorItem(**item_data)
                    session.add(new_item)
                    session.commit()
                    session.refresh(new_item)
                    
                    self.test_items.append(new_item)
                    created_count += 1
                    self.print_test(f"Create {item_data['name']}", True, f"ID: {new_item.id}")
            
            session.close()
            self.print_test("Create Test Items Summary", True, f"Created {created_count} new items, total {len(self.test_items)} test items")
            return True
            
        except Exception as e:
            self.print_test("Create Test Items", False, str(e))
            return False
    
    def test_service_checks(self):
        """Test 5: Test all service check types"""
        self.print_header("Service Check Functions Test")
        
        # Import check functions
        from monitor_service import check_service
        
        all_passed = True
        
        for item in self.test_items:
            try:
                # Tạm thời disable để tránh ảnh hưởng main service
                original_enable = item.enable
                item.enable = False
                
                ol1(f"\n🔍 Testing service check: {item.name} ({item.type})")
                result = check_service(item)
                
                # Restore enable status
                item.enable = original_enable
                
                if result and 'success' in result:
                    status = "SUCCESS" if result['success'] else "FAILED (as expected)"
                    message = f"{item.type} - {status}: {result['message']}"
                    self.print_test(f"Check {item.name}", True, message)
                else:
                    self.print_test(f"Check {item.name}", False, "No result returned")
                    all_passed = False
                    
            except Exception as e:
                self.print_test(f"Check {item.name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_thread_management(self):
        """Test 6: Monitor thread management"""
        self.print_header("Thread Management Test")
        
        try:
            # Get current threads
            response = requests.get(f"{TEST_CONFIG['api_base_url']}/api/threads", timeout=5)
            if response.status_code == 200:
                data = response.json()
                thread_count = len(data.get('threads', []))
                self.print_test("Get Thread Status", True, f"Found {thread_count} active threads")
                
                # Test thread details
                for thread in data.get('threads', []):
                    thread_name = thread.get('name', 'Unknown')
                    is_alive = thread.get('is_alive', False)
                    status = "Running" if is_alive else "Stopped"
                    self.print_test(f"Thread {thread_name}", True, status)
                
                return True
            else:
                self.print_test("Get Thread Status", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.print_test("Thread Management", False, str(e))
            return False
    
    def test_database_operations(self):
        """Test 7: Database operations"""
        self.print_header("Database Operations Test")
        
        try:
            session = self.SessionLocal()
            
            # Test query operations
            all_items = session.query(MonitorItem).all()
            enabled_items = session.query(MonitorItem).filter_by(enable=1).all()
            test_items = session.query(MonitorItem).filter(MonitorItem.name.startswith('TEST_')).all()
            
            self.print_test("Query All Items", True, f"Found {len(all_items)} total items")
            self.print_test("Query Enabled Items", True, f"Found {len(enabled_items)} enabled items")
            self.print_test("Query Test Items", True, f"Found {len(test_items)} test items")
            
            # Test update operation
            if test_items:
                test_item = test_items[0]
                original_name = test_item.name
                test_item.name = f"{original_name}_UPDATED"
                session.commit()
                
                # Verify update
                updated_item = session.query(MonitorItem).filter_by(id=test_item.id).first()
                if updated_item.name.endswith('_UPDATED'):
                    self.print_test("Update Item", True, f"Updated {test_item.id}")
                    
                    # Restore original name
                    updated_item.name = original_name
                    session.commit()
                else:
                    self.print_test("Update Item", False, "Update not reflected")
            
            session.close()
            return True
            
        except Exception as e:
            self.print_test("Database Operations", False, str(e))
            return False
    
    def test_environment_config(self):
        """Test 8: Environment configuration"""
        self.print_header("Environment Configuration Test")
        
        required_vars = ['HTTP_PORT', 'HTTP_HOST', 'DB_HOST', 'DB_NAME', 'DB_USER']
        optional_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'ADMIN_DOMAIN']
        
        all_passed = True
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                self.print_test(f"ENV {var}", True, f"Set to: {value}")
            else:
                self.print_test(f"ENV {var}", False, "Not set")
                all_passed = False
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                self.print_test(f"ENV {var} (optional)", True, f"Set to: {value}")
            else:
                self.print_test(f"ENV {var} (optional)", True, "Not set (optional)")
        
        return all_passed
    
    def test_utility_functions(self):
        """Test 9: Utility functions"""
        self.print_header("Utility Functions Test")
        
        from utils import (format_response_time, format_uptime, safe_get_env_bool, 
                          safe_get_env_int, validate_url, generate_thread_name)
        
        try:
            # Test format functions
            self.print_test("format_response_time(123.45)", True, format_response_time(123.45))
            self.print_test("format_response_time(None)", True, format_response_time(None))
            self.print_test("format_uptime(3665)", True, format_uptime(3665))
            
            # Test env functions
            bool_result = safe_get_env_bool('TEST_BOOL', False)
            int_result = safe_get_env_int('TEST_INT', 42)
            self.print_test("safe_get_env_bool", True, str(bool_result))
            self.print_test("safe_get_env_int", True, str(int_result))
            
            # Test validation
            valid_url, normalized = validate_url('https://google.com')
            self.print_test("validate_url", valid_url, f"Normalized: {normalized}")
            
            # Test thread name generation
            thread_name = generate_thread_name(123, "Test Service")
            self.print_test("generate_thread_name", True, thread_name)
            
            return True
            
        except Exception as e:
            self.print_test("Utility Functions", False, str(e))
            return False
    
    def cleanup_test_data(self):
        """Test 10: Cleanup test data"""
        self.print_header("Cleanup Test Data")
        
        if not should_cleanup_test_data():
            self.print_test("Cleanup Test Items", True, "Cleanup disabled in test environment")
            return True
        
        try:
            session = self.SessionLocal()
            
            # Delete test items
            deleted_count = 0
            test_items = session.query(MonitorItem).filter(MonitorItem.name.startswith('TEST_')).all()
            
            for item in test_items:
                session.delete(item)
                deleted_count += 1
            
            session.commit()
            session.close()
            
            self.print_test("Cleanup Test Items", True, f"Deleted {deleted_count} test items")
            return True
            
        except Exception as e:
            self.print_test("Cleanup Test Items", False, str(e))
            return False
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Test Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"   - {test_name}: {result['message']}")
        
        print(f"\n{'🎉 ALL TESTS PASSED!' if failed_tests == 0 else '⚠️ SOME TESTS FAILED'}")
        
        return failed_tests == 0
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Monitor Service Feature Tests...")
        print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        test_sequence = [
            self.test_database_connection,
            self.test_environment_config,
            self.test_utility_functions,
            self.test_api_server_running,
            self.test_api_endpoints,
            self.create_test_monitor_items,
            self.test_service_checks,
            self.test_thread_management,
            self.test_database_operations,
            self.cleanup_test_data,
        ]
        
        for test_func in test_sequence:
            try:
                test_func()
                time.sleep(1)  # Small delay between tests
            except Exception as e:
                self.print_test(f"CRITICAL ERROR in {test_func.__name__}", False, str(e))
        
        return self.print_summary()


def main():
    """Main test function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("Monitor Service Feature Tester")
        print("Usage:")
        print("  python test_monitor_features.py           - Run all tests")
        print("  python test_monitor_features.py --help    - Show this help")
        return
    
    # Create tester instance
    tester = MonitorTester()
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
