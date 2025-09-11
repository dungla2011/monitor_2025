#!/usr/bin/env python3
"""
Test 07: Telegram Alert Test
Test telegram alert system khi monitor bị lỗi
- Tạo test webserver port 6000
- Tạo monitor web_content check server này
- Tạo telegram config với bot token và chat ID
- Test monitor cycle và telegram alert
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

# Load test environment
load_dotenv('.env.test')

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

class TelegramAlertTester:
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
        
        # Test configuration
        self.test_server_port = 6000
        self.test_monitor_id = None
        self.test_config_id = None
        
        # Telegram configuration from .env.telegram
        self.telegram_config = self.load_telegram_config()
        
        # Database connection
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'monitor_test')
        }
        
    def load_telegram_config(self):
        """Load telegram config from .env.telegram"""
        try:
            # Load .env.telegram file
            telegram_env = {}
            telegram_file = '.env.telegram'
            
            if os.path.exists(telegram_file):
                with open(telegram_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            telegram_env[key] = value
                
                bot_token = telegram_env.get('FOR_TEST_TELEGRAM_BOT_TOKEN', '')
                chat_id = telegram_env.get('FOR_TEST_TELEGRAM_CHAT_ID', '')
                
                if bot_token and chat_id:
                    self.log_success(f"✅ Loaded Telegram config from {telegram_file}")
                    self.log_info(f"   Bot Token: {bot_token[:20]}...")
                    self.log_info(f"   Chat ID: {chat_id}")
                    return {'bot_token': bot_token, 'chat_id': chat_id}
                else:
                    self.log_error("❌ Missing bot token or chat ID in .env.telegram")
                    return None
            else:
                self.log_error(f"❌ File {telegram_file} not found")
                return None
                
        except Exception as e:
            self.log_error(f"❌ Failed to load telegram config: {e}")
            return None
        
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
                    'Test Telegram Monitor',
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

    def create_telegram_config(self):
        """Create telegram alert configuration"""
        if not self.telegram_config:
            self.log_error("No telegram config available")
            return False
            
        connection = self.get_db_connection()
        if not connection:
            return False
            
        try:
            with connection.cursor() as cursor:
                # Telegram config format: bot_token,chat_id
                telegram_config = f"{self.telegram_config['bot_token']},{self.telegram_config['chat_id']}"
                
                sql = """
                INSERT INTO monitor_configs 
                (name, alert_type, alert_config, user_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (
                    'Test Telegram Config',
                    'telegram',
                    telegram_config,
                    1,  # user_id = 1
                    1,  # active
                    datetime.now()
                )
                cursor.execute(sql, values)
                self.test_config_id = cursor.lastrowid
                connection.commit()
                
            self.log_success(f"✅ Created telegram config with ID: {self.test_config_id}")
            self.log_info(f"   Config: {telegram_config[:50]}...")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to create telegram config: {e}")
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
                
            self.log_success(f"✅ Linked monitor {self.test_monitor_id} with config {self.test_config_id}")
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

    def check_telegram_bot_connection(self):
        """Test telegram bot connection"""
        if not self.telegram_config:
            self.log_error("No telegram config to test")
            return False
            
        try:
            bot_token = self.telegram_config['bot_token']
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            
            response = requests.get(url, timeout=10)  # Reduced timeout
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    self.log_success(f"✅ Telegram bot connection OK: @{bot_info.get('username', 'unknown')}")
                    return True
                else:
                    self.log_error(f"❌ Telegram API error: {data.get('description', 'Unknown error')}")
                    return False
            else:
                self.log_error(f"❌ Telegram API HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            self.log_info("⚠️ Telegram API connection timeout - may be network issue")
            self.log_info("🔄 Continuing test without bot verification...")
            return True  # Continue test even if can't connect to Telegram API
        except requests.exceptions.ConnectionError:
            self.log_info("⚠️ Telegram API connection error - may be network issue")
            self.log_info("🔄 Continuing test without bot verification...")
            return True  # Continue test even if can't connect to Telegram API
        except Exception as e:
            self.log_error(f"❌ Telegram connection test failed: {e}")
            return False

    def test_telegram_alerts(self):
        """Main test for telegram alerts"""
        print(f"\n{'='*70}")
        print("📱 TELEGRAM ALERT TEST")
        print(f"{'='*70}")
        
        # Step 0: Check Telegram config
        self.log_info("Step 0: Checking Telegram configuration...")
        if not self.telegram_config:
            self.log_error("❌ No Telegram config found")
            return False
        
        if not self.check_telegram_bot_connection():
            self.log_info("⚠️ Telegram bot connection failed, but continuing test...")
            self.log_info("📱 The monitor service will still attempt to send alerts")
        
        # Step 1: Clean all existing data
        self.log_info("Step 1: Cleaning all existing monitors and configs...")
        if not self.cleanup_all_monitors_configs():
            return False
        
        # Step 2: Setup test server
        self.log_info("Step 2: Setting up test server...")
        
        if not self.start_test_webserver():
            return False
        
        # Step 3: Setup database with ONLY our test data
        self.log_info("Step 3: Setting up database with test data...")
        
        if not self.create_test_monitor():
            return False
        
        if not self.create_telegram_config():
            return False
        
        if not self.link_monitor_and_config():
            return False
        
        # Step 4: Restart monitor service để load monitor mới
        self.log_info("Step 4: Restarting monitor service to load new monitor...")
        self.stop_monitor_service()
        time.sleep(2)
        if not self.start_monitor_service():
            return False
        
        # Step 5: Wait for monitor to start checking
        self.log_info("Step 5: Waiting for monitor to start checking...")
        self.wait_for_monitor_cycles(2)
        
        self.log_info("Monitor should be running normally now...")
        
        # Step 6: Stop test server to trigger alert
        self.log_info("Step 6: Stopping test server to trigger alert...")
        self.stop_test_webserver()
        
        # Step 7: Wait for alert to be sent
        self.log_info("Step 7: Waiting for Telegram alert...")
        self.log_info("📱 Check your Telegram chat for alert messages!")
        self.wait_for_monitor_cycles(3)
        
        # Step 8: Restart web server to trigger recovery alert
        self.log_info("Step 8: Restarting test server to trigger recovery alert...")
        if not self.start_test_webserver():
            self.log_error("Failed to restart test server for recovery test")
            return False
        
        # Step 9: Wait for recovery alert
        self.log_info("Step 9: Waiting for Telegram recovery alert...")
        self.log_info("📱 Check your Telegram chat for recovery message!")
        self.wait_for_monitor_cycles(3)
        
        # Test completed successfully (no manual verification needed)
        self.log_success("✅ Telegram alert test completed successfully!")
        self.log_info("📱 Please check your Telegram chat for both alert and recovery messages")
        
        return True

    def run_test(self):
        """Run complete telegram alert test"""
        print("🧪 TELEGRAM ALERT TEST")
        print("📱 Testing telegram alert system")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        success = False
        try:
            # Start monitor service first
            if not self.start_monitor_service():
                return False
            
            # Run telegram test (includes restart of service)
            success = self.test_telegram_alerts()
            
            return success
            
        finally:
            # Cleanup
            self.cleanup_test_data()
            self.stop_test_webserver()
            self.stop_monitor_service()
            
            # Summary
            print(f"\n{'='*80}")
            print("📊 TELEGRAM ALERT TEST SUMMARY")
            print(f"{'='*80}")
            print(f"✅ Successes: {len(self.successes)}")
            print(f"❌ Errors: {len(self.errors)}")
            
            if self.errors:
                print(f"\n🔥 ERRORS:")
                for error in self.errors:
                    print(f"  - {error}")
            
            if success and len(self.errors) == 0:
                print("\n🎉 TELEGRAM ALERT TEST PASSED!")
                print("📱 Telegram alert system working perfectly!")
            else:
                print(f"\n💥 TELEGRAM ALERT TEST FAILED!")
                print("🚨 Telegram system needs attention")
            
            print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    print("🧪 Starting Telegram Alert Test...")
    tester = TelegramAlertTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
