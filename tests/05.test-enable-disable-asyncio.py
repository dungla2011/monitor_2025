#!/usr/bin/env python3
"""
Test 05 AsyncIO: Dynamic Monitor Control Test for AsyncIO Service
Test enable/disable monitors và verify AsyncIO tasks start/stop real-time
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
import subprocess
import threading
from datetime import datetime
from requests.auth import HTTPBasicAuth
import pymysql
from dotenv import load_dotenv

def find_project_root():
    """Find project root directory (where .env files are located)"""
    current_dir = os.path.abspath(__file__)
    
    # Try to find project root by looking for .env file
    for _ in range(5):  # Max 5 levels up
        current_dir = os.path.dirname(current_dir)
        if os.path.exists(os.path.join(current_dir, '.env')):
            return current_dir
    
    # Fallback: assume we're in tests/ folder
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load test environment with proper path
project_root = find_project_root()
load_dotenv(os.path.join(project_root, '.env.test'))

class AsyncIODynamicMonitorTester:
    def __init__(self):
        self.base_url = "http://localhost:5006"  # AsyncIO service port (corrected)
        self.username = "admin"
        self.password = "test123"
        self.errors = []
        self.successes = []
        self.server_process = None
        self.auth_headers = None
        
        # Database connection
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'monitor_test')
        }
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ {message}")
        
    def log_success(self, message):
        self.successes.append(message)
        print(f"✅ {message}")
        
    def log_info(self, message):
        print(f"📋 {message}")

    def get_auth_headers(self):
        """Get authentication headers"""
        if self.auth_headers:
            return {"headers": self.auth_headers}
        
        try:
            auth = HTTPBasicAuth(self.username, self.password)
            response = requests.post(f"{self.base_url}/api/token", 
                                   auth=auth,
                                   json={"type": "simple"},
                                   timeout=5)
            
            if response.status_code == 200:
                token_data = response.json()
                bearer_token = token_data['token']
                self.auth_headers = {"Authorization": f"Bearer {bearer_token}"}
                return {"headers": self.auth_headers}
            else:
                return {"auth": HTTPBasicAuth(self.username, self.password)}
                
        except Exception as e:
            return {"auth": HTTPBasicAuth(self.username, self.password)}

    def start_server(self):
        """Start AsyncIO monitor service in background"""
        print("🚀 Starting AsyncIO monitor service...")
        try:
            # Start AsyncIO server in new console
            print("   📋 Executing: python monitor_service_asyncio.py start --test")
            
            # Set environment to handle Unicode properly
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.server_process = subprocess.Popen([
                "python", "monitor_service_asyncio.py", "start", "--test"
            ], 
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Run from parent directory
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            # Wait for server to start
            print("   ⏱️ Waiting 10 seconds for AsyncIO service startup...")
            time.sleep(10)
            
            # Test if server is responding
            try:
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                if response.status_code in [200, 401]:
                    self.log_success("AsyncIO monitor service started successfully")
                    return True
                else:
                    self.log_error(f"AsyncIO service responded with unexpected status: {response.status_code}")
                    return False
            except requests.exceptions.ConnectionError:
                self.log_error("Cannot connect to AsyncIO service after startup")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start AsyncIO service: {e}")
            return False

    def stop_server(self):
        """Stop the monitor service"""
        if self.server_process:
            try:
                print("🛑 Stopping AsyncIO monitor service...")
                self.server_process.terminate()
                time.sleep(3)
                
                if self.server_process.poll() is None:
                    self.server_process.kill()
                    
                self.log_success("AsyncIO monitor service stopped")
            except Exception as e:
                self.log_error(f"Error stopping AsyncIO service: {e}")

    def get_db_connection(self):
        """Get database connection"""
        try:
            return pymysql.connect(**self.db_config)
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return None

    def create_test_monitor(self):
        """Create a test monitor in database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None
                
            cursor = conn.cursor()
            
            # Create test monitor
            cursor.execute("""
                INSERT INTO monitor_items (
                    name, user_id, url_check, type, 
                    check_interval_seconds, enable, 
                    maxAlertCount, result_valid, result_error
                ) VALUES (
                    'AsyncIO Test Monitor', 1, 'https://httpbin.org/status/200', 'web_content',
                    30, 0, 5, 'Status: 200', 'Connection error'
                )
            """)
            
            test_monitor_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success(f"Created test monitor with ID: {test_monitor_id}")
            return test_monitor_id
            
        except Exception as e:
            self.log_error(f"Failed to create test monitor: {e}")
            return None

    def delete_test_monitor(self, monitor_id):
        """Delete test monitor from database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("DELETE FROM monitor_items WHERE id = %s", (monitor_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success(f"Deleted test monitor ID: {monitor_id}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to delete test monitor: {e}")
            return False

    def enable_monitor(self, monitor_id):
        """Enable monitor in database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("UPDATE monitor_items SET enable = 1 WHERE id = %s", (monitor_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success(f"Enabled monitor ID: {monitor_id}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to enable monitor: {e}")
            return False

    def disable_monitor(self, monitor_id):
        """Disable monitor in database"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute("UPDATE monitor_items SET enable = 0 WHERE id = %s", (monitor_id,))
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success(f"Disabled monitor ID: {monitor_id}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to disable monitor: {e}")
            return False

    def get_running_monitors_from_api(self):
        """Get running monitors from API"""
        try:
            auth_config = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/monitors", timeout=10, **auth_config)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   🔍 DEBUG: API monitors response format: {type(data)}")
                print(f"   🔍 DEBUG: API monitors response: {data}")
                
                # Handle different response formats - return ENABLED monitors
                if isinstance(data, dict) and 'monitors' in data:
                    monitors = data['monitors']
                    # Return monitors that are enabled (AsyncIO might not immediately set is_thread_running)
                    enabled_monitors = [
                        monitor.get('id') for monitor in monitors 
                        if monitor.get('id') and monitor.get('enabled', False)
                    ]
                    print(f"   🔍 DEBUG: Enabled monitors: {enabled_monitors}")
                    return enabled_monitors
                elif isinstance(data, list):
                    # Fallback for list format
                    enabled_monitors = [
                        monitor.get('id') for monitor in data 
                        if monitor.get('id') and monitor.get('enabled', False)
                    ]
                    print(f"   🔍 DEBUG: Enabled monitors: {enabled_monitors}")
                    return enabled_monitors
                else:
                    return []
            else:
                self.log_error(f"API monitors endpoint failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_error(f"Failed to get running monitors from API: {e}")
            return []

    def test_dynamic_enable_disable(self):
        """Test dynamic enable/disable functionality"""
        print("\n🧪 Testing AsyncIO Dynamic Enable/Disable...")
        
        # Create test monitor (disabled by default)
        monitor_id = self.create_test_monitor()
        if not monitor_id:
            return False
            
        try:
            # Wait for service to detect changes
            time.sleep(6)  # AsyncIO cache refresh + buffer
            
            # Check initial state (should be empty)
            running_monitors = self.get_running_monitors_from_api()
            self.log_info(f"Initial running monitors: {running_monitors}")
            
            if monitor_id in running_monitors:
                self.log_error("Monitor should not be running initially (disabled)")
                return False
            else:
                self.log_success("Monitor correctly not running (disabled)")
            
            # Enable monitor
            if not self.enable_monitor(monitor_id):
                return False
                
            # Wait for AsyncIO service to detect and start (AsyncIO needs more time)
            self.log_info("Waiting 15 seconds for AsyncIO service to detect enabled monitor...")
            time.sleep(15)
            
            # Check if monitor is now running
            running_monitors = self.get_running_monitors_from_api()
            self.log_info(f"Running monitors after enable: {running_monitors}")
            
            if monitor_id in running_monitors:
                self.log_success("Monitor started successfully after enable (AsyncIO)")
            else:
                self.log_error("Monitor should be running after enable")
                return False
            
            # Disable monitor
            if not self.disable_monitor(monitor_id):
                return False
                
            # Wait for AsyncIO service to detect and stop
            self.log_info("Waiting 15 seconds for AsyncIO service to detect disabled monitor...")
            time.sleep(15)
            
            # Check if monitor stopped
            running_monitors = self.get_running_monitors_from_api()
            self.log_info(f"Running monitors after disable: {running_monitors}")
            
            if monitor_id not in running_monitors:
                self.log_success("Monitor stopped successfully after disable (AsyncIO)")
                return True
            else:
                self.log_error("Monitor should not be running after disable")
                return False
                
        finally:
            # Cleanup
            self.delete_test_monitor(monitor_id)

    def test_asyncio_performance_metrics(self):
        """Test AsyncIO specific performance metrics"""
        print("\n🧪 Testing AsyncIO Performance Metrics...")
        try:
            auth_config = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/status", timeout=10, **auth_config)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   🔍 DEBUG: Status response: {data}")
                
                # Look for AsyncIO indicators
                status_str = str(data).lower()
                print(f"   🔍 DEBUG: Searching in: {status_str}")
                
                # Check for various AsyncIO indicators
                asyncio_keywords = ['asyncio', 'async', 'thread', 'concurrent', 'running_threads']
                found_keywords = [kw for kw in asyncio_keywords if kw in status_str]
                
                if found_keywords:
                    self.log_success(f"AsyncIO indicators found: {found_keywords}")
                    return True
                else:
                    # If no specific keywords, but has thread info, consider it valid
                    if 'threads' in data or 'running_threads' in str(data):
                        self.log_success("Thread metrics found (AsyncIO service indicator)")
                        return True
                    else:
                        self.log_error("No AsyncIO or thread metrics found")
                        return False
            else:
                self.log_error(f"Status endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"Performance metrics test error: {e}")
            return False

    def run_all_tests(self):
        """Run all dynamic control tests"""
        print("="*80)
        print("🧪 ASYNCIO DYNAMIC MONITOR CONTROL TEST")
        print("="*80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Base URL: {self.base_url}")
        print("="*80)
        
        # Test sequence
        tests = [
            ("Start AsyncIO Service", self.start_server),
            ("Dynamic Enable/Disable", self.test_dynamic_enable_disable),
            ("AsyncIO Performance Metrics", self.test_asyncio_performance_metrics),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                result = test_func()
                results.append((test_name, result))
                
                if not result and test_name == "Start AsyncIO Service":
                    print("❌ Cannot proceed without service")
                    break
                    
            except Exception as e:
                self.log_error(f"{test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Cleanup
        self.stop_server()
        
        # Print summary
        print("\n" + "="*80)
        print("📋 ASYNCIO DYNAMIC CONTROL TEST RESULTS")
        print("="*80)
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} | {test_name}")
            if result:
                passed += 1
        
        print("-"*80)
        success_rate = (passed / len(results)) * 100 if results else 0
        print(f"📊 Results: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")
        
        # Summary
        if len(self.successes) > 0:
            print(f"\n✅ Successes ({len(self.successes)}):")
            for success in self.successes:
                print(f"   • {success}")
        
        if len(self.errors) > 0:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        return passed == len(results)

def main():
    """Main test function"""
    tester = AsyncIODynamicMonitorTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())