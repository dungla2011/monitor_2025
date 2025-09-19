#!/usr/bin/env python3
"""
Test 05: Dynamic Monitor Control Test
Test enable/disable monitors và verify threads start/stop real-time
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

class DynamicMonitorTester:
    def __init__(self):
        self.base_url = "http://localhost:5006"
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
        """Start monitor service in background"""
        print("🚀 Starting monitor service...")
        try:
            # Start server in new console
            print("   📋 Executing: python monitor_service.py start --test")
            self.server_process = subprocess.Popen([
                "python", "monitor_service.py", "start", "--test"
            ], 
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Run from parent directory
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            # Wait for server to start
            print("   ⏱️ Waiting 8 seconds for server startup...")
            time.sleep(8)
            
            # Verify server started
            try:
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                if response.status_code in [200, 401]:
                    self.log_success("Monitor service started successfully")
                    return True
                else:
                    self.log_error(f"Server responded with status {response.status_code}")
                    return False
            except:
                self.log_error("Server not responding")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop monitor service"""
        if self.server_process:
            print("🛑 Stopping monitor service...")
            try:
                # Try graceful shutdown
                auth_kwargs = self.get_auth_headers()
                requests.post(f"{self.base_url}/api/shutdown", timeout=5, **auth_kwargs)
                time.sleep(3)
            except:
                pass
            
            # Force terminate
            if self.server_process.poll() is None:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.log_success("Monitor service stopped")

    def get_db_connection(self):
        """Get database connection"""
        try:
            connection = pymysql.connect(**self.db_config)
            return connection
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return None

    def update_monitor_status(self, monitor_id, enable_status):
        """Update monitor enable/disable status in database"""
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                sql = "UPDATE monitor_items SET enable = %s WHERE id = %s"
                cursor.execute(sql, (enable_status, monitor_id))
                connection.commit()
                
            action = "enabled" if enable_status else "disabled"
            self.log_info(f"Database: Monitor {monitor_id} {action}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to update monitor {monitor_id}: {e}")
            return False
        finally:
            connection.close()

    def get_api_threads(self):
        """Get current threads from API"""
        try:
            auth_kwargs = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/threads", timeout=10, **auth_kwargs)
            
            if response.status_code == 200:
                data = response.json()
                threads = data.get('threads', [])
                return {t.get('id'): t for t in threads}
            else:
                self.log_error(f"Failed to get threads: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_error(f"API threads error: {e}")
            return {}

    def get_api_monitors(self):
        """Get current monitors from API"""
        try:
            auth_kwargs = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/monitors", timeout=10, **auth_kwargs)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   🔍 DEBUG: Monitors API response: {data}")
                
                # Handle different response formats
                if isinstance(data, dict) and 'monitors' in data:
                    monitors = data['monitors']
                    return {m.get('id'): m for m in monitors}
                elif isinstance(data, list):
                    return {m.get('id'): m for m in data}
                else:
                    return {}
            else:
                self.log_error(f"Failed to get monitors: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_error(f"API monitors error: {e}")
            return {}

    def wait_for_system_update(self, seconds=10):
        """Wait for system to process database changes"""
        self.log_info(f"⏳ Waiting {seconds} seconds for system to process changes...")
        time.sleep(seconds)

    def test_dynamic_enable_disable(self):
        """Test dynamic enable/disable of monitors"""
        print(f"\n{'='*70}")
        print("🔄 DYNAMIC MONITOR CONTROL TEST")
        print(f"{'='*70}")
        
        # Step 1: Get initial state
        self.log_info("Step 1: Getting initial system state...")
        initial_threads = self.get_api_threads()
        initial_monitors = self.get_api_monitors()
        
        self.log_info(f"Initial state:")
        self.log_info(f"  📊 Active threads: {len(initial_threads)}")
        self.log_info(f"  📊 Total monitors: {len(initial_monitors)}")
        
        # Find a monitor to test with
        test_monitor_id = None
        test_monitor_name = None
        
        for monitor_id, monitor in initial_monitors.items():
            if monitor.get('enabled', False):  # API field is 'enabled', not 'enable'
                test_monitor_id = monitor_id
                test_monitor_name = monitor.get('name', f'Monitor {monitor_id}')
                break
        
        if not test_monitor_id:
            self.log_error("No enabled monitors found for testing")
            return
        
        self.log_info(f"🎯 Testing with: {test_monitor_name} (ID: {test_monitor_id})")
        
        # Step 2: Disable the monitor
        self.log_info(f"\nStep 2: Disabling monitor {test_monitor_id}...")
        if not self.update_monitor_status(test_monitor_id, False):
            return
        
        self.wait_for_system_update(12)
        
        # Check if thread stopped
        after_disable_threads = self.get_api_threads()
        after_disable_monitors = self.get_api_monitors()
        
        self.log_info(f"After disable:")
        self.log_info(f"  📊 Active threads: {len(after_disable_threads)}")
        self.log_info(f"  📊 Enabled monitors: {sum(1 for m in after_disable_monitors.values() if m.get('enabled'))}")
        
        # Verify monitor was disabled (check enabled status or absence from API)
        target_monitor = after_disable_monitors.get(test_monitor_id)
        if target_monitor is None:
            self.log_success(f"✅ Monitor {test_monitor_id} removed from API (disabled successfully)")
        elif target_monitor and not target_monitor.get('enabled', True):
            self.log_success(f"✅ Monitor {test_monitor_id} disabled successfully in API")
        else:
            self.log_error(f"❌ Monitor {test_monitor_id} still appears enabled in API")
        
        # Also check thread count as secondary indicator
        if len(after_disable_threads) < len(initial_threads):
            self.log_success(f"✅ Thread count decreased: {len(initial_threads)} → {len(after_disable_threads)}")
        elif len(after_disable_threads) == len(initial_threads):
            self.log_info(f"⚠️ Thread count unchanged (may be expected): {len(initial_threads)}")
        else:
            self.log_error(f"❌ Unexpected thread count change: {len(initial_threads)} → {len(after_disable_threads)}")
        
        # Step 3: Re-enable the monitor
        self.log_info(f"\nStep 3: Re-enabling monitor {test_monitor_id}...")
        if not self.update_monitor_status(test_monitor_id, True):
            return
        
        self.wait_for_system_update(12)
        
        # Check if thread restarted
        after_enable_threads = self.get_api_threads()
        after_enable_monitors = self.get_api_monitors()
        
        self.log_info(f"After re-enable:")
        self.log_info(f"  📊 Active threads: {len(after_enable_threads)}")
        self.log_info(f"  📊 Enabled monitors: {sum(1 for m in after_enable_monitors.values() if m.get('enabled'))}")
        
        # Verify monitor was re-enabled (check enabled status)
        target_monitor = after_enable_monitors.get(test_monitor_id)
        if target_monitor and target_monitor.get('enabled', False):
            self.log_success(f"✅ Monitor {test_monitor_id} re-enabled successfully in API")
        else:
            self.log_error(f"❌ Monitor {test_monitor_id} still appears disabled in API")
        
        # Also check thread count as secondary indicator
        if len(after_enable_threads) >= len(after_disable_threads):
            self.log_success(f"✅ Thread count maintained/increased: {len(after_disable_threads)} → {len(after_enable_threads)}")
        else:
            self.log_error(f"❌ Thread count decreased unexpectedly: {len(after_disable_threads)} → {len(after_enable_threads)}")
        
        # Step 4: Verify final state
        if len(after_enable_threads) == len(initial_threads):
            self.log_success("✅ System returned to initial state")
        else:
            self.log_error(f"❌ Final thread count mismatch: {len(initial_threads)} → {len(after_enable_threads)}")

    def run_test(self):
        """Run complete dynamic control test"""
        print("🧪 DYNAMIC MONITOR CONTROL TEST")
        print("🔄 Testing real-time enable/disable functionality")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        try:
            # Start server
            if not self.start_server():
                return False
            
            # Run dynamic test
            self.test_dynamic_enable_disable()
            
            return len(self.errors) == 0
            
        finally:
            # Stop server
            self.stop_server()
            
            # Summary
            print(f"\n{'='*80}")
            print("📊 DYNAMIC CONTROL TEST SUMMARY")
            print(f"{'='*80}")
            print(f"✅ Successes: {len(self.successes)}")
            print(f"❌ Errors: {len(self.errors)}")
            
            if self.errors:
                print(f"\n🔥 ERRORS:")
                for error in self.errors:
                    print(f"  - {error}")
            
            if len(self.errors) == 0:
                print("\n🎉 DYNAMIC CONTROL TEST PASSED!")
                print("🔄 Real-time monitor control working perfectly!")
            else:
                print(f"\n💥 {len(self.errors)} ISSUES DETECTED!")
                print("🚨 Dynamic control needs attention")
            
            print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    start_time = datetime.now()
    print("🧪 Starting Dynamic Monitor Control Test...")
    print(f"🕒 Test started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = DynamicMonitorTester()
    success = tester.run_test()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"⏱️  Test duration: {duration:.2f} seconds")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
