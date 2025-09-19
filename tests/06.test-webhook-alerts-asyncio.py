#!/usr/bin/env python3
"""
Test 06 AsyncIO: Webhook Alert Test for AsyncIO Monitor Service
Test webhook alert system khi monitor bị lỗi với AsyncIO service
- Tạo test webserver port 6001 (khác threading version)
- Tạo monitor web_content check server này  
- Tạo webhook config để nhận alerts
- Test monitor cycle và webhook alert với AsyncIO
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
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
from urllib.parse import urlparse, parse_qs

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

class AsyncIOWebhookReceiver(BaseHTTPRequestHandler):
    """Simple webhook receiver to capture AsyncIO alerts"""
    
    def do_POST(self):
        """Handle webhook POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Log webhook received
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        webhook_data = {
            'timestamp': timestamp,
            'headers': dict(self.headers),
            'body': post_data,
            'path': self.path
        }
        
        # Store webhook data globally
        if hasattr(self.server, 'webhook_calls'):
            self.server.webhook_calls.append(webhook_data)
        else:
            self.server.webhook_calls = [webhook_data]
        
        print(f"📨 AsyncIO Webhook received at {timestamp}")
        print(f"   Path: {self.path}")
        print(f"   Data: {post_data}")
        
        # Respond to webhook
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {'status': 'received', 'timestamp': timestamp, 'service': 'asyncio'}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default log messages"""
        pass

class AsyncIOTestWebServer(BaseHTTPRequestHandler):
    """Simple test web server for AsyncIO testing"""
    
    def do_GET(self):
        """Handle GET requests"""
        # Check for failure trigger
        if hasattr(self.server, 'should_fail') and self.server.should_fail:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = f"""
            <html>
            <head><title>Test Server - FAILED</title></head>
            <body>
            <h1>Test Server - SIMULATED FAILURE</h1>
            <p>Server time: {datetime.now()}</p>
            <p>Status: ERROR 500</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = f"""
            <html>
            <head><title>AsyncIO Test Server</title></head>
            <body>
            <h1>AsyncIO Test Server Running</h1>
            <p>Server time: {datetime.now()}</p>
            <p>Status: OK</p>
            <p>Service: AsyncIO Testing</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default log messages"""
        pass

class AsyncIOWebhookAlertTester:
    def __init__(self):
        self.base_url = "http://localhost:5006"  # AsyncIO service port (corrected)
        self.username = "admin"
        self.password = "test123"
        self.errors = []
        self.successes = []
        self.server_process = None
        self.auth_headers = None
        
        # Test servers (different ports from threading version)
        self.test_server = None
        self.test_server_thread = None
        self.webhook_receiver = None
        self.webhook_receiver_thread = None
        
        # Test configuration
        self.test_server_port = 6001  # Different from threading version (6000)
        self.webhook_port = 7001      # Different from threading version (7000)
        self.test_monitor_id = None
        self.test_config_id = None
        
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

    def start_test_web_server(self):
        """Start test web server for monitoring"""
        try:
            print(f"🌐 Starting AsyncIO test web server on port {self.test_server_port}...")
            
            server_address = ('', self.test_server_port)
            self.test_server = HTTPServer(server_address, AsyncIOTestWebServer)
            self.test_server.should_fail = False  # Initial state: working
            
            def run_server():
                self.test_server.serve_forever()
            
            self.test_server_thread = threading.Thread(target=run_server, daemon=True)
            self.test_server_thread.start()
            
            # Test if server is responding
            time.sleep(2)
            try:
                response = requests.get(f"http://localhost:{self.test_server_port}", timeout=5)
                if response.status_code == 200:
                    self.log_success(f"AsyncIO test web server started on port {self.test_server_port}")
                    return True
                else:
                    self.log_error(f"Test web server responded with status {response.status_code}")
                    return False
            except Exception as e:
                self.log_error(f"Test web server not responding: {e}")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start test web server: {e}")
            return False

    def start_webhook_receiver(self):
        """Start webhook receiver server"""
        try:
            print(f"📨 Starting AsyncIO webhook receiver on port {self.webhook_port}...")
            
            server_address = ('', self.webhook_port)
            self.webhook_receiver = HTTPServer(server_address, AsyncIOWebhookReceiver)
            self.webhook_receiver.webhook_calls = []  # Store received webhooks
            
            def run_receiver():
                self.webhook_receiver.serve_forever()
            
            self.webhook_receiver_thread = threading.Thread(target=run_receiver, daemon=True)
            self.webhook_receiver_thread.start()
            
            # Test if receiver is responding
            time.sleep(2)
            try:
                response = requests.post(f"http://localhost:{self.webhook_port}/test", 
                                       json={'test': 'AsyncIO'}, timeout=5)
                if response.status_code == 200:
                    self.log_success(f"AsyncIO webhook receiver started on port {self.webhook_port}")
                    return True
                else:
                    self.log_error(f"Webhook receiver responded with status {response.status_code}")
                    return False
            except Exception as e:
                self.log_error(f"Webhook receiver not responding: {e}")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start webhook receiver: {e}")
            return False

    def stop_test_servers(self):
        """Stop test servers"""
        if self.test_server:
            try:
                self.test_server.shutdown()
                self.log_success("AsyncIO test web server stopped")
            except Exception as e:
                self.log_error(f"Error stopping test web server: {e}")
        
        if self.webhook_receiver:
            try:
                self.webhook_receiver.shutdown()
                self.log_success("AsyncIO webhook receiver stopped")
            except Exception as e:
                self.log_error(f"Error stopping webhook receiver: {e}")

    def start_monitor_service(self):
        """Start AsyncIO monitor service"""
        print("🚀 Starting AsyncIO monitor service...")
        try:
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
            
            print("   ⏱️ Waiting 10 seconds for AsyncIO service startup...")
            time.sleep(10)
            
            # Test if service is responding
            try:
                response = requests.get(f"{self.base_url}/api/status", timeout=5)
                if response.status_code in [200, 401]:
                    self.log_success("AsyncIO monitor service started successfully")
                    return True
                else:
                    self.log_error(f"AsyncIO monitor service responded with unexpected status: {response.status_code}")
                    return False
            except requests.exceptions.ConnectionError:
                self.log_error("Cannot connect to AsyncIO monitor service after startup")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start AsyncIO monitor service: {e}")
            return False

    def stop_monitor_service(self):
        """Stop monitor service"""
        if self.server_process:
            try:
                print("🛑 Stopping AsyncIO monitor service...")
                self.server_process.terminate()
                time.sleep(3)
                
                if self.server_process.poll() is None:
                    self.server_process.kill()
                    
                self.log_success("AsyncIO monitor service stopped")
            except Exception as e:
                self.log_error(f"Error stopping AsyncIO monitor service: {e}")

    def get_db_connection(self):
        """Get database connection"""
        try:
            return pymysql.connect(**self.db_config)
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return None

    def create_test_monitor_and_webhook_config(self):
        """Create test monitor and webhook configuration"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return None, None
                
            cursor = conn.cursor()
            
            # Create test monitor
            cursor.execute("""
                INSERT INTO monitor_items (
                    name, user_id, url_check, type, 
                    check_interval_seconds, enable, 
                    maxAlertCount, result_valid, result_error
                ) VALUES (
                    'AsyncIO Webhook Test Monitor', 1, %s, 'web_content',
                    10, 1, 5, 'AsyncIO Test Server Running', 'Connection error'
                )
            """, (f"http://localhost:{self.test_server_port}",))
            
            test_monitor_id = cursor.lastrowid
            
            # Create webhook configuration using monitor_configs table (same as threading version)
            cursor.execute("""
                INSERT INTO monitor_configs (
                    name, alert_type, alert_config, user_id, status, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """, (
                'AsyncIO Test Webhook Config',
                'webhook', 
                f"http://localhost:{self.webhook_port}/webhook",
                1,  # user_id
                1,  # active status
                datetime.now()
            ))
            
            test_config_id = cursor.lastrowid
            
            # Link monitor with config (like threading version)
            cursor.execute("""
                INSERT INTO monitor_and_configs (
                    monitor_item_id, config_id, created_at
                ) VALUES (
                    %s, %s, %s
                )
            """, (test_monitor_id, test_config_id, datetime.now()))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success(f"Created AsyncIO test monitor (ID: {test_monitor_id}) and webhook config (ID: {test_config_id})")
            self.log_success(f"Linked monitor {test_monitor_id} with webhook config {test_config_id}")
            return test_monitor_id, test_config_id
            
        except Exception as e:
            self.log_error(f"Failed to create test monitor and webhook config: {e}")
            return None, None

    def cleanup_test_data(self, monitor_id, config_id):
        """Clean up test monitor and webhook config"""
        try:
            conn = self.get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Delete linking first (foreign keys)
            if monitor_id and config_id:
                cursor.execute("DELETE FROM monitor_and_configs WHERE monitor_item_id = %s AND config_id = %s", (monitor_id, config_id))
            
            if config_id:
                cursor.execute("DELETE FROM monitor_configs WHERE id = %s", (config_id,))
            if monitor_id:
                cursor.execute("DELETE FROM monitor_items WHERE id = %s", (monitor_id,))
                
            conn.commit()
            cursor.close()
            conn.close()
            
            self.log_success("Cleaned up AsyncIO test data")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to cleanup test data: {e}")
            return False

    def test_webhook_alert_cycle(self):
        """Test complete webhook alert cycle with AsyncIO"""
        print("\n🧪 Testing AsyncIO Webhook Alert Cycle...")
        
        # Create test monitor and webhook config
        monitor_id, config_id = self.create_test_monitor_and_webhook_config()
        if not monitor_id or not config_id:
            return False
            
        try:
            # Wait for monitor to start and check a few times successfully
            self.log_info("Waiting 30 seconds for AsyncIO monitor to establish baseline...")
            time.sleep(30)
            
            # Clear any existing webhook calls
            if hasattr(self.webhook_receiver, 'webhook_calls'):
                self.webhook_receiver.webhook_calls.clear()
            
            # Cause the test server to fail
            self.log_info("Triggering test server failure...")
            self.test_server.should_fail = True
            
            # Wait for monitor to detect failure and send webhook
            self.log_info("Waiting 30 seconds for AsyncIO monitor to detect failure and send webhook...")
            time.sleep(30)
            
            # Check if webhook was received
            webhook_calls = getattr(self.webhook_receiver, 'webhook_calls', [])
            alert_webhooks = [call for call in webhook_calls if 'alert' in call.get('body', '').lower() or 'error' in call.get('body', '').lower()]
            
            if alert_webhooks:
                self.log_success(f"AsyncIO webhook alert received! ({len(alert_webhooks)} alerts)")
                for webhook in alert_webhooks:
                    print(f"   📨 Alert webhook: {webhook['timestamp']} - {webhook['body'][:100]}...")
            else:
                self.log_error("No AsyncIO webhook alerts received")
                print(f"   📊 Total webhooks received: {len(webhook_calls)}")
                for webhook in webhook_calls:
                    print(f"   📨 Webhook: {webhook['body'][:50]}...")
                return False
            
            # Fix the test server
            self.log_info("Fixing test server...")
            self.test_server.should_fail = False
            
            # Wait for monitor to detect recovery and send recovery webhook
            self.log_info("Waiting 30 seconds for AsyncIO monitor to detect recovery...")
            time.sleep(30)
            
            # Check for recovery webhook
            webhook_calls = getattr(self.webhook_receiver, 'webhook_calls', [])
            recovery_webhooks = [call for call in webhook_calls if 'recovery' in call.get('body', '').lower() or 'up' in call.get('body', '').lower()]
            
            if recovery_webhooks:
                self.log_success(f"AsyncIO webhook recovery received! ({len(recovery_webhooks)} recoveries)")
                for webhook in recovery_webhooks:
                    print(f"   📨 Recovery webhook: {webhook['timestamp']} - {webhook['body'][:100]}...")
            else:
                self.log_error("No AsyncIO webhook recovery received")
                print(f"   📊 Total webhooks received: {len(webhook_calls)}")
            
            return len(alert_webhooks) > 0  # Success if we got at least alert webhooks
            
        finally:
            # Cleanup
            self.cleanup_test_data(monitor_id, config_id)

    def run_all_tests(self):
        """Run all webhook alert tests"""
        print("="*80)
        print("🧪 ASYNCIO WEBHOOK ALERT TEST")
        print("="*80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Monitor Service: {self.base_url}")
        print(f"🌐 Test Server: http://localhost:{self.test_server_port}")
        print(f"📨 Webhook Receiver: http://localhost:{self.webhook_port}")
        print("="*80)
        
        # Test sequence
        tests = [
            ("Start Test Web Server", self.start_test_web_server),
            ("Start Webhook Receiver", self.start_webhook_receiver),
            ("Start AsyncIO Monitor Service", self.start_monitor_service),
            ("Test Webhook Alert Cycle", self.test_webhook_alert_cycle),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                result = test_func()
                results.append((test_name, result))
                
                if not result and test_name in ["Start Test Web Server", "Start Webhook Receiver", "Start AsyncIO Monitor Service"]:
                    print(f"❌ Cannot proceed without {test_name}")
                    break
                    
            except Exception as e:
                self.log_error(f"{test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Cleanup
        self.stop_monitor_service()
        self.stop_test_servers()
        
        # Print summary
        print("\n" + "="*80)
        print("📋 ASYNCIO WEBHOOK ALERT TEST RESULTS")
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
    tester = AsyncIOWebhookAlertTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())