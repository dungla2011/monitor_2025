#!/usr/bin/env python3
"""
Test 03 AsyncIO: API Endpoints Test for AsyncIO Monitor Service
Test các API endpoints với AsyncIO service và database local
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

class AsyncIOAPITester:
    def __init__(self):
        self.base_url = "http://localhost:5006"  # AsyncIO service uses port 5006 in test mode
        self.username = "admin"
        self.password = "test123"  # From .env.test
        self.errors = []
        self.successes = []
        self.server_process = None
        self.auth_headers = None  # For Bearer token
        
    def get_auth_headers(self):
        """Get authentication headers (Bearer token or fallback to Basic Auth)"""
        if self.auth_headers:
            return {"headers": self.auth_headers}
        
        # Try to get Bearer token first
        try:
            print("🔑 Getting Bearer token...")
            auth = HTTPBasicAuth(self.username, self.password)
            response = requests.post(f"{self.base_url}/api/token", 
                                   auth=auth,
                                   json={"type": "simple"},
                                   timeout=5)
            
            if response.status_code == 200:
                token_data = response.json()
                bearer_token = token_data['token']
                self.auth_headers = {"Authorization": f"Bearer {bearer_token}"}
                print(f"✅ Bearer token obtained")
                return {"headers": self.auth_headers}
            else:
                print(f"⚠️ Token failed, using Basic Auth")
                return {"auth": HTTPBasicAuth(self.username, self.password)}
                
        except Exception as e:
            print(f"⚠️ Token error: {e}, using Basic Auth")
            return {"auth": HTTPBasicAuth(self.username, self.password)}
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ {message}")
        
    def log_success(self, message):
        self.successes.append(message)
        print(f"✅ {message}")

    def start_api_server(self):
        """Start AsyncIO API server in background"""
        print("🚀 Starting AsyncIO API server...")
        
        # First check if server is already running
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=3)
            if response.status_code in [200, 401]:  # 401 means server running but need auth
                self.log_success("AsyncIO API server already running")
                return True
        except requests.exceptions.ConnectionError:
            pass  # Server not running, continue to start it
        
        try:
            # Start AsyncIO server in background with proper encoding
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
            
            # Wait longer for server to start (AsyncIO may be faster)
            print("   ⏱️ Waiting 8 seconds for AsyncIO server startup...")
            time.sleep(8)
            
            # Test if server is running
            try:
                print("   🔍 Testing AsyncIO server response...")
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                # Should get 401 (auth required) which means server is running
                if response.status_code in [200, 401]:
                    self.log_success("AsyncIO API server started successfully")
                    return True
                else:
                    self.log_error(f"AsyncIO API server responded with status {response.status_code}")
                    return False
            except requests.exceptions.ConnectionError:
                self.log_error("Cannot connect to AsyncIO API server after startup")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start AsyncIO API server: {e}")
            return False

    def stop_server(self):
        """Stop the API server"""
        if self.server_process:
            try:
                print("🛑 Stopping AsyncIO API server...")
                self.server_process.terminate()
                time.sleep(2)
                
                # Force kill if still running
                if self.server_process.poll() is None:
                    self.server_process.kill()
                    
                self.log_success("AsyncIO API server stopped")
            except Exception as e:
                self.log_error(f"Error stopping AsyncIO server: {e}")

    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        print("\n🧪 Testing /api/status endpoint...")
        try:
            auth_config = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/status", timeout=10, **auth_config)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   📊 Response: {data}")
                
                # Verify expected fields
                if 'uptime' in str(data) or 'threads' in str(data) or 'asyncio' in str(data).lower():
                    self.log_success("Status endpoint working (AsyncIO)")
                    return True
                else:
                    self.log_error(f"Status endpoint missing expected AsyncIO fields: {data}")
                    return False
            else:
                self.log_error(f"Status endpoint failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_error(f"Status endpoint error: {e}")
            return False

    def test_monitors_endpoint(self):
        """Test /api/monitors endpoint"""
        print("\n🧪 Testing /api/monitors endpoint...")
        try:
            auth_config = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/monitors", timeout=10, **auth_config)
            
            if response.status_code == 200:
                data = response.json()
                
                # API returns dict with 'monitors' key containing the list
                if isinstance(data, dict) and 'monitors' in data:
                    monitors = data['monitors']
                    total = data.get('total', len(monitors))
                    print(f"   📊 Monitor count: {total}")
                    
                    if isinstance(monitors, list):
                        self.log_success(f"Monitors endpoint working (AsyncIO): {total} monitors")
                        return True
                    else:
                        self.log_error(f"Monitors data is not a list: {type(monitors)}")
                        return False
                elif isinstance(data, list):
                    # Fallback: if API returns list directly
                    print(f"   📊 Monitor count: {len(data)}")
                    self.log_success(f"Monitors endpoint working (AsyncIO): {len(data)} monitors")
                    return True
                else:
                    self.log_error(f"Monitors endpoint returned unexpected format: {type(data)}")
                    print(f"   📊 Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    return False
            else:
                self.log_error(f"Monitors endpoint failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_error(f"Monitors endpoint error: {e}")
            return False

    def test_logs_endpoint(self):
        """Test /api/logs endpoint"""
        print("\n🧪 Testing /api/logs endpoint...")
        try:
            auth_config = self.get_auth_headers()
            response = requests.get(f"{self.base_url}/api/logs?lines=10", timeout=10, **auth_config)
            
            if response.status_code == 200:
                data = response.json()
                
                # API returns dict with 'logs' key containing the list
                if isinstance(data, dict) and 'logs' in data:
                    logs = data['logs']
                    showing_lines = data.get('showing_lines', len(logs))
                    total_lines = data.get('total_lines', 0)
                    print(f"   📊 Logs received: {showing_lines} entries (total: {total_lines})")
                    
                    if isinstance(logs, list):
                        self.log_success(f"Logs endpoint working (AsyncIO): {showing_lines} log entries")
                        return True
                    else:
                        self.log_error(f"Logs data is not a list: {type(logs)}")
                        return False
                elif isinstance(data, list):
                    # Fallback: if API returns list directly
                    print(f"   📊 Logs received: {len(data)} entries")
                    self.log_success(f"Logs endpoint working (AsyncIO): {len(data)} log entries")
                    return True
                else:
                    self.log_error(f"Logs endpoint returned unexpected format: {type(data)}")
                    print(f"   📊 Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    return False
            else:
                self.log_error(f"Logs endpoint failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_error(f"Logs endpoint error: {e}")
            return False

    def test_performance_comparison(self):
        """Test AsyncIO performance vs Threading"""
        print("\n🧪 Testing AsyncIO Performance...")
        try:
            auth_config = self.get_auth_headers()
            
            # Test multiple concurrent requests to measure performance
            import concurrent.futures
            import time
            
            def make_request():
                response = requests.get(f"{self.base_url}/api/status", timeout=5, **auth_config)
                return response.status_code == 200
            
            # Make 10 concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            duration = end_time - start_time
            success_count = sum(results)
            
            print(f"   ⚡ AsyncIO Performance: {success_count}/10 requests in {duration:.2f}s")
            
            if success_count >= 8:  # At least 80% success
                self.log_success(f"AsyncIO performance test passed: {success_count}/10 in {duration:.2f}s")
                return True
            else:
                self.log_error(f"AsyncIO performance test failed: {success_count}/10 in {duration:.2f}s")
                return False
                
        except Exception as e:
            self.log_error(f"AsyncIO performance test error: {e}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("="*80)
        print("🧪 ASYNCIO API ENDPOINTS TEST")
        print("="*80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Base URL: {self.base_url}")
        print("="*80)
        
        # Test sequence
        tests = [
            ("Start AsyncIO Server", self.start_api_server),
            ("Status Endpoint", self.test_status_endpoint),
            ("Monitors Endpoint", self.test_monitors_endpoint),
            ("Logs Endpoint", self.test_logs_endpoint),
            ("Performance Test", self.test_performance_comparison),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                result = test_func()
                results.append((test_name, result))
                
                if not result and test_name == "Start AsyncIO Server":
                    print("❌ Cannot proceed without server")
                    break
                    
            except Exception as e:
                self.log_error(f"{test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Cleanup
        self.stop_server()
        
        # Print summary
        print("\n" + "="*80)
        print("📋 ASYNCIO API TEST RESULTS")
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
    tester = AsyncIOAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())