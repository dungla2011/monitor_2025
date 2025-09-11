#!/usr/bin/env python3
"""
Test 06: Webhook Alert Test
Test webhook alert system khi monitor bị lỗi
- Tạo test webserver port 6000
- Tạo monitor web_content check server này
- Tạo webhook config để nhận alerts
- Test monitor cycle và webhook alert
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

# Load test environment
load_dotenv('.env.test')

class WebhookReceiver(BaseHTTPRequestHandler):
    """Simple webhook receiver to capture alerts"""
    
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
        
        print(f"📨 Webhook received at {timestamp}")
        print(f"   Path: {self.path}")
        print(f"   Data: {post_data}")
        
        # Respond to webhook
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {'status': 'received', 'timestamp': timestamp}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default log messages"""
        pass

class TestWebServer(BaseHTTPRequestHandler):
    """Simple test web server"""
    
    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        response = f"""
        <html>
        <head><title>Test Server</title></head>
        <body>
        <h1>Test Server Running</h1>
        <p>Server time: {datetime.now()}</p>
        <p>Status: OK</p>
        </body>
        </html>
        """
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default log messages"""
        pass

class WebhookAlertTester:
    def __init__(self):
        self.base_url = "http://localhost:5006"
        self.username = "admin"
        self.password = "test123"
        self.errors = []
        self.successes = []
        self.server_process = None
        self.auth_headers = None
        
        # Test servers
        self.test_server = None
        self.test_server_thread = None
        self.webhook_server = None
        self.webhook_server_thread = None
        
        # Test configuration
        self.test_server_port = 6000
        self.webhook_port = 6001
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

    def start_monitor_service(self):
        """Start monitor service"""
        print("🚀 Starting monitor service...")
        try:
            self.server_process = subprocess.Popen([
                "python", "monitor_service.py", "start", "--test"
            ], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            time.sleep(8)
            
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

    def stop_monitor_service(self):
        """Stop monitor service"""
        if self.server_process:
            print("🛑 Stopping monitor service...")
            try:
                auth_kwargs = self.get_auth_headers()
                requests.post(f"{self.base_url}/api/shutdown", timeout=5, **auth_kwargs)
                time.sleep(3)
            except:
                pass
            
            if self.server_process.poll() is None:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            
            self.log_success("Monitor service stopped")

    def start_test_webserver(self):
        """Start test web server on port 6000"""
        print(f"🌐 Starting test web server on port {self.test_server_port}...")
        try:
            self.test_server = HTTPServer(('localhost', self.test_server_port), TestWebServer)
            self.test_server_thread = threading.Thread(target=self.test_server.serve_forever, daemon=True)
            self.test_server_thread.start()
            
            # Test if server is running
            time.sleep(1)
            try:
                response = requests.get(f"http://localhost:{self.test_server_port}", timeout=5)
                if response.status_code == 200:
                    self.log_success(f"Test web server started on port {self.test_server_port}")
                    return True
                else:
                    self.log_error(f"Test server not responding properly")
                    return False
            except Exception as e:
                self.log_error(f"Test server not accessible: {e}")
                return False
                
        except Exception as e:
            self.log_error(f"Failed to start test web server: {e}")
            return False

    def stop_test_webserver(self):
        """Stop test web server"""
        if self.test_server:
            print(f"🛑 Stopping test web server on port {self.test_server_port}...")
            self.test_server.shutdown()
            self.test_server.server_close()
            if self.test_server_thread:
                self.test_server_thread.join(timeout=5)
            self.log_success("Test web server stopped")

    def start_webhook_server(self):
        """Start webhook receiver server"""
        print(f"📨 Starting webhook server on port {self.webhook_port}...")
        try:
            self.webhook_server = HTTPServer(('localhost', self.webhook_port), WebhookReceiver)
            self.webhook_server.webhook_calls = []  # Store webhook calls
            self.webhook_server_thread = threading.Thread(target=self.webhook_server.serve_forever, daemon=True)
            self.webhook_server_thread.start()
            
            time.sleep(1)
            self.log_success(f"Webhook server started on port {self.webhook_port}")
            return True
                
        except Exception as e:
            self.log_error(f"Failed to start webhook server: {e}")
            return False

    def stop_webhook_server(self):
        """Stop webhook server"""
        if self.webhook_server:
            print(f"🛑 Stopping webhook server on port {self.webhook_port}...")
            self.webhook_server.shutdown()
            self.webhook_server.server_close()
            if self.webhook_server_thread:
                self.webhook_server_thread.join(timeout=5)
            self.log_success("Webhook server stopped")

    def get_db_connection(self):
        """Get database connection"""
        try:
            connection = pymysql.connect(**self.db_config)
            return connection
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return None

    def cleanup_all_monitors_configs(self):
        """Clean up ALL monitors and configs from database"""
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                # Delete all monitor_and_configs links
                cursor.execute("DELETE FROM monitor_and_configs")
                
                # Delete all monitor configs
                cursor.execute("DELETE FROM monitor_configs")
                
                # Delete all monitors
                cursor.execute("DELETE FROM monitor_items")
                
                connection.commit()
                
            self.log_success("🧹 Cleaned up ALL monitors and configs from database")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to cleanup all data: {e}")
            return False
        finally:
            connection.close()

    def create_test_monitor(self):
        """Create test monitor for web_content check"""
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                # Create monitor
                sql = """
                INSERT INTO monitor_items 
                (name, enable, type, url_check, check_interval_seconds, user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    'Test Webhook Monitor',
                    1,  # enabled
                    'web_content',
                    f'http://localhost:{self.test_server_port}',
                    10,  # check every 10 seconds
                    1,   # user_id = 1
                    datetime.now()
                )
                cursor.execute(sql, values)
                self.test_monitor_id = cursor.lastrowid
                connection.commit()
                
            self.log_success(f"✅ Created test monitor with ID: {self.test_monitor_id}")
            self.log_info(f"   URL: http://localhost:{self.test_server_port}")
            self.log_info(f"   Interval: 10 seconds")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to create test monitor: {e}")
            return False
        finally:
            connection.close()

    def create_webhook_config(self):
        """Create webhook alert configuration"""
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                # Simple webhook URL - không phải JSON object
                webhook_url = f'http://localhost:{self.webhook_port}/webhook'
                
                sql = """
                INSERT INTO monitor_configs 
                (name, alert_type, alert_config, user_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    'Test Webhook Config',
                    'webhook',
                    webhook_url,  # Chỉ cần URL string
                    1,  # user_id = 1
                    1,  # active
                    datetime.now()
                )
                cursor.execute(sql, values)
                self.test_config_id = cursor.lastrowid
                connection.commit()
                
            self.log_success(f"✅ Created webhook config with ID: {self.test_config_id}")
            self.log_info(f"   Webhook URL: {webhook_url}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to create webhook config: {e}")
            return False
        finally:
            connection.close()

    def link_monitor_and_config(self):
        """Link monitor with alert config"""
        if not self.test_monitor_id or not self.test_config_id:
            self.log_error("Monitor ID or Config ID not available")
            return False
            
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO monitor_and_configs 
                (monitor_item_id, config_id, created_at)
                VALUES (%s, %s, %s)
                """
                values = (self.test_monitor_id, self.test_config_id, datetime.now())
                cursor.execute(sql, values)
                connection.commit()
                
            self.log_success(f"Linked monitor {self.test_monitor_id} with config {self.test_config_id}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to link monitor and config: {e}")
            return False
        finally:
            connection.close()

    def cleanup_test_data(self):
        """Clean up test data from database"""
        # Note: cleanup_all_monitors_configs() đã xóa hết rồi
        # Method này giữ lại để tương thích
        self.log_info("✅ Test data cleanup (already done in cleanup_all_monitors_configs)")

    def wait_for_monitor_cycles(self, cycles=3):
        """Wait for monitor to complete several check cycles"""
        wait_time = cycles * 12  # 10s interval + 2s buffer
        self.log_info(f"⏳ Waiting {wait_time} seconds for {cycles} monitor cycles...")
        time.sleep(wait_time)

    def test_webhook_alerts(self):
        """Main test for webhook alerts"""
        print(f"\n{'='*70}")
        print("📨 WEBHOOK ALERT TEST")
        print(f"{'='*70}")
        
        # Step 0: Clean all existing data
        self.log_info("Step 0: Cleaning all existing monitors and configs...")
        if not self.cleanup_all_monitors_configs():
            return False
        
        # Step 1: Setup test servers
        self.log_info("Step 1: Setting up test servers...")
        
        if not self.start_test_webserver():
            return False
        
        if not self.start_webhook_server():
            return False
        
        # Step 2: Setup database with ONLY our test data
        self.log_info("Step 2: Setting up database with test data...")
        
        if not self.create_test_monitor():
            return False
        
        if not self.create_webhook_config():
            return False
        
        if not self.link_monitor_and_config():
            return False
        
        # Step 3: Restart monitor service để load monitor mới
        self.log_info("Step 3: Restarting monitor service to load new monitor...")
        self.stop_monitor_service()
        time.sleep(2)
        if not self.start_monitor_service():
            return False
        
        # Step 4: Wait for monitor to start checking
        self.log_info("Step 4: Waiting for monitor to start checking...")
        self.wait_for_monitor_cycles(2)
        
        # Check webhook calls from normal operation
        initial_webhook_count = len(self.webhook_server.webhook_calls) if self.webhook_server else 0
        self.log_info(f"Webhook calls after normal operation: {initial_webhook_count}")
        
        # Step 5: Stop test server to trigger alert
        self.log_info("Step 5: Stopping test server to trigger alert...")
        self.stop_test_webserver()
        
        # Step 6: Wait for alert to be sent
        self.log_info("Step 6: Waiting for alert webhook...")
        self.wait_for_monitor_cycles(3)
        
        # Step 7: Check webhook calls
        final_webhook_count = len(self.webhook_server.webhook_calls) if self.webhook_server else 0
        new_webhook_calls = final_webhook_count - initial_webhook_count
        
        self.log_info(f"Final webhook calls received: {final_webhook_count}")
        self.log_info(f"New webhook calls: {new_webhook_calls}")
        
        if new_webhook_calls > 0:
            self.log_success(f"✅ Webhook alert triggered! Received {new_webhook_calls} webhook calls")
            
            # Show webhook details
            for i, call in enumerate(self.webhook_server.webhook_calls[-new_webhook_calls:], 1):
                self.log_info(f"Webhook {i}: {call['timestamp']} - {call['path']}")
                if call['body']:
                    self.log_info(f"  Body: {call['body']}")
        else:
            self.log_error("❌ No webhook alerts received")
        
        return new_webhook_calls > 0

    def run_test(self):
        """Run complete webhook alert test"""
        print("🧪 WEBHOOK ALERT TEST")
        print("📨 Testing webhook alert system")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        success = False
        try:
            # Start monitor service first
            if not self.start_monitor_service():
                return False
            
            # Run webhook test (includes restart of service)
            success = self.test_webhook_alerts()
            
            return success
            
        finally:
            # Cleanup
            self.cleanup_test_data()
            self.stop_test_webserver()
            self.stop_webhook_server()
            self.stop_monitor_service()
            
            # Summary
            print(f"\n{'='*80}")
            print("📊 WEBHOOK ALERT TEST SUMMARY")
            print(f"{'='*80}")
            print(f"✅ Successes: {len(self.successes)}")
            print(f"❌ Errors: {len(self.errors)}")
            
            if self.errors:
                print(f"\n🔥 ERRORS:")
                for error in self.errors:
                    print(f"  - {error}")
            
            if success and len(self.errors) == 0:
                print("\n🎉 WEBHOOK ALERT TEST PASSED!")
                print("📨 Webhook alert system working perfectly!")
            else:
                print(f"\n💥 WEBHOOK ALERT TEST FAILED!")
                print("🚨 Webhook system needs attention")
            
            print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    print("🧪 Starting Webhook Alert Test...")
    tester = WebhookAlertTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
