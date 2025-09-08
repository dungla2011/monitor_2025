#!/usr/bin/env python3
"""
001_create_db_and_table.py
Script to create test database and tables using .env.test configuration
"""
import sys
import os
import pymysql
from dotenv import load_dotenv

print("="*60)
print("CREATE TEST DATABASE AND TABLES")
print("="*60)

# Load test environment
print("🧪 Loading test environment (.env.test)...")
load_dotenv('.env.test')

# Get database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'monitor_test')
DB_CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')

print(f"📊 Database Configuration:")
print(f"   Host: {DB_HOST}")
print(f"   Port: {DB_PORT}")
print(f"   User: {DB_USER}")
print(f"   Password: {'***' if DB_PASSWORD else '(empty)'}")
print(f"   Database: {DB_NAME}")
print(f"   Charset: {DB_CHARSET}")

try:
    # Step 1: Connect to MySQL server (without database)
    print(f"\n🔌 Connecting to MySQL server at {DB_HOST}:{DB_PORT}...")
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset=DB_CHARSET
    )
    
    with connection.cursor() as cursor:
        # Step 2: Create database if not exists
        print(f"🏗️ Creating database '{DB_NAME}' if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET {DB_CHARSET} COLLATE {DB_CHARSET}_unicode_ci")
        print(f"✅ Database '{DB_NAME}' created/verified successfully")
        
        # Step 3: Use the database
        cursor.execute(f"USE {DB_NAME}")
        
        # Step 4: Create tables using SQLAlchemy models
        print(f"🔧 Creating tables using SQLAlchemy models...")
        
    connection.close()
    print(f"✅ MySQL connection closed")
    
    # Step 5: Use SQLAlchemy to create all tables
    print(f"🏗️ Using SQLAlchemy to create tables...")
    
    # Import SQLAlchemy after environment is loaded
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create database URL
    if DB_PASSWORD:
        DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}"
    else:
        DATABASE_URL = f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}"
    
    print(f"🔗 Database URL: mysql+pymysql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}")
    
    # Create engine
    engine = create_engine(DATABASE_URL, echo=False)
    
    # Import models to register them with SQLAlchemy
    from models import Base, MonitorItem
    
    # Create all tables
    print(f"📋 Creating tables...")
    Base.metadata.create_all(engine)
    
    # Verify tables
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Test connection by counting monitor items
    count = session.query(MonitorItem).count()
    print(f"📊 Monitor items count: {count}")
    
    session.close()
    
    print(f"\n" + "="*60)
    print(f"✅ SUCCESS: Test database and tables created!")
    print(f"="*60)
    print(f"✅ Database: {DB_NAME}")
    print(f"✅ Host: {DB_HOST}:{DB_PORT}")
    print(f"✅ Tables: Created from SQLAlchemy models")
    print(f"✅ Connection: Tested successfully")
    print(f"\n🚀 You can now run:")
    print(f"   python monitor_service.py start --test")
    print(f"   python 00_run_all_tests.py")
    
except pymysql.Error as e:
    print(f"\n❌ MySQL Error: {e}")
    print(f"💡 Make sure:")
    print(f"   - MySQL server is running on {DB_HOST}:{DB_PORT}")
    print(f"   - User '{DB_USER}' has database creation privileges")
    print(f"   - Connection details in .env.test are correct")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
