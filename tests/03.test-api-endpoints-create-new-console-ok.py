#!/usr/bin/env python3
"""
Test 03: API Endpoints Test
Test các API endpoints với database local
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

class APITester:
    def __init__(self):
        self.base_url = "http://localhost:5006"
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
        """Start API server in background"""
        print("🚀 Starting API server...")
        
        # First check if server is already running
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=3)
            if response.status_code in [200, 401]:  # 401 means server running but need auth
                self.log_success("API server already running")
                return True
        except requests.exceptions.ConnectionError:
            pass  # Server not running, continue to start it
        
        try:
            # Start server in background
            print("   📋 Executing: python monitor_service.py start --test")
            self.server_process = subprocess.Popen([
                "python", "monitor_service.py", "start", "--test"
            ], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            # Wait longer for server to start (service has multiple threads)
            print("   ⏱️ Waiting 5 seconds for server startup...")
            time.sleep(5)
            
            # Test if server is running (don't check process exit status yet)
            try:
                print("   🔍 Testing server response...")
                # Test without auth first to see if server is up
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                # Should get 401 (auth required) which means server is running
                if response.status_code in [200, 401]:
                    self.log_success("API server started successfully")
                    return True
                else:
                    self.log_error(f"API server responded with status {response.status_code}")
                    return False
            except requests.exceptions.ConnectionError:
                self.log_error("API server not responding")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start API server: {e}")
            return False

    def test_api_endpoints(self):
        """Test all API endpoints"""
        print("\n" + "="*60)
        print("TESTING API ENDPOINTS WITH AUTHENTICATION")
        print("="*60)
        
        # Get authentication method
        auth_kwargs = self.get_auth_headers()
        
        endpoints = [
            ("/api/status", "GET", "System Status"),
            ("/api/monitors", "GET", "Monitor List"),
            ("/api/threads", "GET", "Thread Status"),
            ("/api/logs", "GET", "Recent Logs"),
            ("/", "GET", "Dashboard Home"),
        ]
        
        for endpoint, method, description in endpoints:
            print(f"\n📡 Testing: {description}")
            print(f"   {method} {self.base_url}{endpoint}")
            
            try:
                if method == "GET":
                    # Use authentication
                    response = requests.get(f"{self.base_url}{endpoint}", 
                                          timeout=10, **auth_kwargs)
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    self.log_success(f"{description}: OK")
                    
                    # Print response preview
                    if endpoint.startswith('/api/'):
                        try:
                            data = response.json()
                            if isinstance(data, dict):
                                # Handle different response structures
                                if 'monitors' in data:
                                    print(f"   📊 Monitors: {len(data['monitors'])} items")
                                elif 'threads' in data:
                                    print(f"   📊 Threads: {len(data['threads'])} active")
                                elif 'logs' in data:
                                    print(f"   📊 Logs: {len(data['logs'])} lines")
                                elif 'running_threads' in data:
                                    print(f"   📊 Running threads: {data['running_threads']}")
                                else:
                                    print(f"   📊 Data keys: {list(data.keys())}")
                            elif isinstance(data, list):
                                print(f"   📊 Items: {len(data)}")
                            else:
                                print(f"   📊 Response: {type(data)}")
                        except:
                            print(f"   📊 Content: {len(response.content)} bytes")
                    else:
                        print(f"   📊 HTML: {len(response.content)} bytes")
                        
                elif response.status_code == 401:
                    self.log_error(f"{description}: Authentication failed")
                    print(f"   🔐 Check username/password: {self.username}/{self.password}")
                else:
                    self.log_error(f"{description}: HTTP {response.status_code}")
                    if response.status_code != 200:
                        print(f"   📄 Response: {response.text[:200]}...")
                    
            except requests.exceptions.Timeout:
                self.log_error(f"{description}: Timeout")
            except requests.exceptions.ConnectionError:
                self.log_error(f"{description}: Connection error")
            except Exception as e:
                self.log_error(f"{description}: {e}")

    def test_authentication(self):
        """Test authentication methods"""
        print("\n" + "="*60)
        print("TESTING AUTHENTICATION")
        print("="*60)
        
        # Test 1: No auth (should fail)
        print(f"\n🔒 Testing without authentication (should fail):")
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=5)
            if response.status_code == 401:
                self.log_success("Properly requires authentication")
            else:
                self.log_error(f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_error(f"Auth test error: {e}")
        
        # Test 2: Wrong credentials
        print(f"\n🔒 Testing wrong credentials:")
        try:
            wrong_auth = HTTPBasicAuth("wrong", "credentials")
            response = requests.get(f"{self.base_url}/api/status", auth=wrong_auth, timeout=5)
            if response.status_code == 401:
                self.log_success("Properly rejects wrong credentials")
            else:
                self.log_error(f"Expected 401 for wrong creds, got {response.status_code}")
        except Exception as e:
            self.log_error(f"Wrong creds test error: {e}")
        
        # Test 3: Correct credentials
        print(f"\n🔒 Testing correct credentials:")
        try:
            correct_auth = HTTPBasicAuth(self.username, self.password)
            response = requests.get(f"{self.base_url}/api/status", auth=correct_auth, timeout=5)
            if response.status_code == 200:
                self.log_success("Accepts correct credentials")
                print(f"   ✅ Response: {response.json().get('status', 'unknown')}")
            else:
                self.log_error(f"Expected 200 for correct creds, got {response.status_code}")
        except Exception as e:
            self.log_error(f"Correct creds test error: {e}")

    def stop_api_server(self):
        """Stop API server"""
        print(f"\n🛑 Stopping API server...")
        
        # Only stop server if we started it
        if self.server_process:
            try:
                # Try graceful shutdown via API
                auth_kwargs = self.get_auth_headers()
                requests.post(f"{self.base_url}/api/shutdown", timeout=5, **auth_kwargs)
                time.sleep(2)
            except:
                pass
            
            # Force terminate if still running
            if self.server_process.poll() is None:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.log_success("API server stopped")
        else:
            print("   📌 Server was already running - not stopping")

    def run_test(self):
        """Run complete API test"""
        print("🧪 API ENDPOINTS TEST WITH AUTHENTICATION")
        print("🔐 Credentials: admin / test123")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        server_started = False
        try:
            # Start server
            server_started = self.start_api_server()
            if not server_started:
                self.log_error("Cannot proceed with tests - API server not available")
                return False
            
            # Test authentication
            self.test_authentication()
            
            # Test endpoints
            self.test_api_endpoints()
            
            return len(self.errors) == 0
            
        finally:
            # Only stop server if we successfully started it
            if server_started and self.server_process:
                self.stop_api_server()
            elif not server_started:
                print("\n📌 No server to stop")
            
            # Summary
            print("\n" + "="*80)
            print("📊 TEST SUMMARY")
            print("="*80)
            print(f"✅ Successes: {len(self.successes)}")
            print(f"❌ Errors: {len(self.errors)}")
            
            if self.errors:
                print(f"\n🔥 ERRORS:")
                for error in self.errors:
                    print(f"  - {error}")
            
            if len(self.errors) == 0:
                print("\n🎉 ALL API TESTS PASSED!")
            else:
                print(f"\n💥 {len(self.errors)} TESTS FAILED!")
            
            print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    tester = APITester()
    success = tester.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
