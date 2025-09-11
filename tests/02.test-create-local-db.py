#!/usr/bin/env python3
"""
Test 02: Create Local Database Test
Khởi tạo database local 'monitor_test' với user root, password empty
Tạo 5 bảng tương ứng với 5 models và insert sample data

Tests:
1. Database connection test
2. Create database 'monitor_test' 
3. Create 5 tables from models
4. Insert sample data
5. Verify data integrity
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from models import Base, MonitorItem, MonitorConfig, MonitorAndConfig, MonitorSettings, User
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class LocalDatabaseCreator:
    def __init__(self):
        # Local MySQL connection (root user, empty password)
        self.local_connection_string = "mysql+pymysql://root:@localhost:3306"
        self.local_db_name = "monitor_test"
        self.local_db_connection_string = f"{self.local_connection_string}/{self.local_db_name}"
        
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def log_error(self, message):
        """Log error và add vào errors list"""
        self.errors.append(message)
        print(f"❌ {message}")
        
    def log_warning(self, message):
        """Log warning và add vào warnings list"""
        self.warnings.append(message)
        print(f"⚠️ {message}")
        
    def log_success(self, message):
        """Log success message"""
        self.successes.append(message)
        print(f"✅ {message}")

    def test_mysql_connection(self):
        """Test 1: Kiểm tra kết nối MySQL local"""
        print("\n" + "="*70)
        print("TEST 1: MYSQL LOCAL CONNECTION")
        print("="*70)
        
        try:
            # Test connection without database
            engine = create_engine(self.local_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT VERSION() as version, USER() as user"))
                row = result.fetchone()
                self.log_success(f"MySQL connection successful")
                self.log_success(f"MySQL version: {row[0]}")
                self.log_success(f"Connected as: {row[1]}")
                return True
        except Exception as e:
            self.log_error(f"MySQL connection failed: {e}")
            self.log_error("Please check:")
            self.log_error("1. MySQL server is running")
            self.log_error("2. Root user can connect without password")
            self.log_error("3. MySQL is accessible on localhost:3306")
            return False

    def create_database(self):
        """Test 2: Tạo database monitor_test"""
        print("\n" + "="*70)
        print("TEST 2: CREATE DATABASE")
        print("="*70)
        
        try:
            engine = create_engine(self.local_connection_string)
            with engine.connect() as conn:
                # Drop database if exists
                conn.execute(text(f"DROP DATABASE IF EXISTS {self.local_db_name}"))
                self.log_success(f"Dropped existing database '{self.local_db_name}' (if existed)")
                
                # Create new database
                conn.execute(text(f"CREATE DATABASE {self.local_db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                self.log_success(f"Created database '{self.local_db_name}'")
                
                # Verify database exists
                result = conn.execute(text(f"SHOW DATABASES LIKE '{self.local_db_name}'"))
                if result.fetchone():
                    self.log_success(f"Database '{self.local_db_name}' verified")
                    return True
                else:
                    self.log_error(f"Database '{self.local_db_name}' not found after creation")
                    return False
                    
        except Exception as e:
            self.log_error(f"Database creation failed: {e}")
            return False

    def create_tables(self):
        """Test 3: Tạo 5 bảng từ models"""
        print("\n" + "="*70)
        print("TEST 3: CREATE TABLES FROM MODELS")
        print("="*70)
        
        try:
            # Connect to the new database
            engine = create_engine(self.local_db_connection_string, echo=False)
            
            # Create all tables from models
            Base.metadata.create_all(engine)
            self.log_success("All tables created from SQLAlchemy models")
            
            # Verify tables exist
            with engine.connect() as conn:
                result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result.fetchall()]
                
                expected_tables = ['monitor_items', 'monitor_configs', 'monitor_and_configs', 'monitor_settings', 'users']
                
                print(f"📋 Expected tables: {expected_tables}")
                print(f"📋 Created tables: {tables}")
                
                all_tables_created = True
                for table_name in expected_tables:
                    if table_name in tables:
                        self.log_success(f"Table '{table_name}' created successfully")
                    else:
                        self.log_error(f"Table '{table_name}' missing")
                        all_tables_created = False
                
                return all_tables_created, engine
                
        except Exception as e:
            self.log_error(f"Table creation failed: {e}")
            return False, None

    def insert_sample_data(self, engine):
        """Test 4: Insert sample data"""
        print("\n" + "="*70)
        print("TEST 4: INSERT SAMPLE DATA")
        print("="*70)
        
        try:
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()
            
            # Sample Users
            print("📝 Inserting sample users...")
            users_data = [
                {
                    'username': 'admin_user',
                    'email': 'admin@localhost.com',
                    'password': 'hashed_password_123',
                    'is_admin': 1,
                    'name': 'Administrator',
                    'site_id': 0,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                {
                    'username': 'test_user',
                    'email': 'test@localhost.com',
                    'password': 'hashed_password_456',
                    'is_admin': 0,
                    'name': 'Test User',
                    'site_id': 0,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
            ]
            
            for user_data in users_data:
                user = User(**user_data)
                session.add(user)
            
            session.commit()
            self.log_success(f"Inserted {len(users_data)} sample users")
            
            # Sample Monitor Settings
            print("📝 Inserting sample monitor settings...")
            settings_data = [
                {
                    'user_id': 1,
                    'status': 1,
                    'alert_time_ranges': '06:00-23:00',
                    'timezone': 7,
                    'created_at': datetime.now()
                },
                {
                    'user_id': 2,
                    'status': 1,
                    'alert_time_ranges': '08:00-22:00',
                    'timezone': 7,
                    'created_at': datetime.now()
                }
            ]
            
            for setting_data in settings_data:
                setting = MonitorSettings(**setting_data)
                session.add(setting)
            
            session.commit()
            self.log_success(f"Inserted {len(settings_data)} sample monitor settings")
            
            # Sample Monitor Configs (Alert configs)
            print("📝 Inserting sample monitor configs...")
            configs_data = [
                {
                    'name': 'Local Telegram Test',
                    'user_id': 1,
                    'status': 1,
                    'alert_type': 'telegram',
                    'alert_config': 'TEST_BOT_TOKEN:ABC123,TEST_CHAT_ID',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                {
                    'name': 'Local Webhook Test',
                    'user_id': 1,
                    'status': 1,
                    'alert_type': 'webhook',
                    'alert_config': 'http://localhost:8080/webhook/test',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                },
                {
                    'name': 'Email Alert Test',
                    'user_id': 2,
                    'status': 1,
                    'alert_type': 'email',
                    'alert_config': 'test@localhost.com',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
            ]
            
            for config_data in configs_data:
                config = MonitorConfig(**config_data)
                session.add(config)
            
            session.commit()
            self.log_success(f"Inserted {len(configs_data)} sample monitor configs")
            
            # Sample Monitor Items
            print("📝 Inserting sample monitor items...")
            items_data = [
                {
                    'name': 'Google DNS Check',
                    'enable': 1,
                    'last_check_status': 1,
                    'url_check': '8.8.8.8',
                    'type': 'ping_icmp',
                    'user_id': 1,
                    'check_interval_seconds': 300,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'count_online': 0,
                    'count_offline': 0
                },
                {
                    'name': 'Google Website Check',
                    'enable': 1,
                    'last_check_status': None,
                    'url_check': 'https://google.com',
                    'type': 'ping_web',
                    'user_id': 1,
                    'check_interval_seconds': 600,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'count_online': 0,
                    'count_offline': 0
                },
                {
                    'name': 'Local Web Server',
                    'enable': 0,
                    'last_check_status': -1,
                    'url_check': 'http://localhost:8080',
                    'type': 'ping_web',
                    'user_id': 2,
                    'check_interval_seconds': 60,
                    'result_error': 'Connection refused - server not running',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'count_online': 0,
                    'count_offline': 5
                },
                {
                    'name': 'SSL Certificate Check',
                    'enable': 1,
                    'last_check_status': 1,
                    'url_check': 'https://github.com',
                    'type': 'ssl_expired_check',
                    'user_id': 1,
                    'check_interval_seconds': 86400,  # Daily
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'count_online': 0,
                    'count_offline': 0
                },
                {
                    'name': 'Web Content Check',
                    'enable': 1,
                    'last_check_status': None,
                    'url_check': 'https://httpbin.org/get',
                    'type': 'web_content',
                    'user_id': 2,
                    'check_interval_seconds': 1800,
                    'result_valid': 'Contains JSON response',
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'count_online': 0,
                    'count_offline': 0
                }
            ]
            
            for item_data in items_data:
                item = MonitorItem(**item_data)
                session.add(item)
            
            session.commit()
            self.log_success(f"Inserted {len(items_data)} sample monitor items")
            
            # Sample Monitor-Config relationships
            print("📝 Inserting sample monitor-config relationships...")
            relationships_data = [
                {'monitor_item_id': 1, 'config_id': 1, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # Google DNS -> Telegram
                {'monitor_item_id': 1, 'config_id': 2, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # Google DNS -> Webhook
                {'monitor_item_id': 2, 'config_id': 1, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # Google Web -> Telegram
                {'monitor_item_id': 3, 'config_id': 3, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # Local Server -> Email
                {'monitor_item_id': 4, 'config_id': 1, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # SSL Check -> Telegram
                {'monitor_item_id': 5, 'config_id': 2, 'created_at': datetime.now(), 'updated_at': datetime.now()},  # Web Content -> Webhook
            ]
            
            for rel_data in relationships_data:
                relationship = MonitorAndConfig(**rel_data)
                session.add(relationship)
            
            session.commit()
            self.log_success(f"Inserted {len(relationships_data)} monitor-config relationships")
            
            session.close()
            return True
            
        except Exception as e:
            self.log_error(f"Sample data insertion failed: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False

    def verify_data(self, engine):
        """Test 5: Verify data integrity"""
        print("\n" + "="*70)
        print("TEST 5: VERIFY DATA INTEGRITY")
        print("="*70)
        
        try:
            with engine.connect() as conn:
                # Count records in each table
                tables_to_check = ['users', 'monitor_settings', 'monitor_configs', 'monitor_items', 'monitor_and_configs']
                
                for table_name in tables_to_check:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    self.log_success(f"Table '{table_name}': {count} records")
                
                # Test some relationships
                print("\n📊 Testing data relationships:")
                
                # Test monitor items with configs
                result = conn.execute(text("""
                    SELECT mi.name, mc.name as config_name, mc.alert_type
                    FROM monitor_items mi
                    JOIN monitor_and_configs mac ON mi.id = mac.monitor_item_id
                    JOIN monitor_configs mc ON mac.config_id = mc.id
                    LIMIT 5
                """))
                
                relationships = result.fetchall()
                for rel in relationships:
                    print(f"   📌 '{rel[0]}' → '{rel[1]}' ({rel[2]})")
                
                self.log_success(f"Found {len(relationships)} monitor-config relationships")
                
                # Test users with settings
                result = conn.execute(text("""
                    SELECT u.username, u.email, ms.alert_time_ranges
                    FROM users u
                    LEFT JOIN monitor_settings ms ON u.id = ms.user_id
                """))
                
                user_settings = result.fetchall()
                for us in user_settings:
                    print(f"   👤 '{us[0]}' ({us[1]}) - Alert time: {us[2] or 'No settings'}")
                
                self.log_success(f"Verified {len(user_settings)} users and their settings")
                
                return True
                
        except Exception as e:
            self.log_error(f"Data verification failed: {e}")
            return False

    def run_comprehensive_test(self):
        """Chạy tất cả tests"""
        print("🧪 LOCAL DATABASE CREATION TEST")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        # Test 1: MySQL Connection
        if not self.test_mysql_connection():
            self.generate_summary()
            return False
            
        # Test 2: Create Database
        if not self.create_database():
            self.generate_summary()
            return False
            
        # Test 3: Create Tables
        tables_created, engine = self.create_tables()
        if not tables_created:
            self.generate_summary()
            return False
            
        # Test 4: Insert Sample Data
        if not self.insert_sample_data(engine):
            self.generate_summary()
            return False
            
        # Test 5: Verify Data
        if not self.verify_data(engine):
            self.generate_summary()
            return False
        
        # Generate Summary
        self.generate_summary()
        return len(self.errors) == 0

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️ Warnings:  {len(self.warnings)}")
        print(f"❌ Errors:    {len(self.errors)}")
        
        if self.errors:
            print(f"\n🔥 ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i:2d}. {error}")
                
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i:2d}. {warning}")
        
        print("\n" + "="*80)
        if not self.errors:
            print("🎉 ALL TESTS PASSED!")
            print("💾 Local database 'monitor_test' created successfully")
            print("🔗 Connection string: mysql+pymysql://root:@localhost:3306/monitor_test")
            print("📊 5 tables created with sample data")
            print("")
            print("🚀 Ready for local development and testing!")
            print("")
            print("📝 Next steps:")
            print("   1. Update .env.test with local database settings")
            print("   2. Test monitor service with --test flag")
            print("   3. Verify API endpoints work with local data")
        else:
            print("💥 SOME TESTS FAILED!")
            print("🔧 Please fix the errors above before continuing.")
        
        print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def create_env_test_file():
    """Create .env.test file for local testing"""
    env_test_content = """# Local Test Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=monitor_test

# HTTP API Server Configuration (different port to avoid conflicts)
HTTP_PORT=5006
HTTP_HOST=127.0.0.1

# Admin Domain Configuration
ADMIN_DOMAIN=localhost

# Web Admin Authentication
WEB_ADMIN_USERNAME=admin
WEB_ADMIN_PASSWORD=test123

# Telegram Configuration (Test Bot - Optional)
# TELEGRAM_BOT_TOKEN=TEST_TOKEN
# TELEGRAM_CHAT_ID=TEST_CHAT_ID

# Alert Throttling Configuration
TELEGRAM_THROTTLE_SECONDS=10
CONSECUTIVE_ERROR_THRESHOLD=10
EXTENDED_ALERT_INTERVAL_MINUTES=5

"""
    
    try:
        with open('.env.test', 'w') as f:
            f.write(env_test_content)
        print("✅ Created .env.test file for local testing")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env.test file: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Starting Local Database Creation Test...")
    
    # Create .env.test file first
    create_env_test_file()
    
    creator = LocalDatabaseCreator()
    success = creator.run_comprehensive_test()
    
    # Exit with appropriate code
    exit_code = 0 if success else 1
    print(f"\n🏁 Test finished with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
