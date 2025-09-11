#!/usr/bin/env python3
"""
Database Switcher Utility
Dễ dàng chuyển đổi giữa MySQL và PostgreSQL
"""

import os
import shutil
from pathlib import Path

def create_env_backup():
    """Tạo backup của file .env hiện tại"""
    if os.path.exists('.env'):
        shutil.copy('.env', '.env.backup')
        print("✅ Đã backup file .env hiện tại -> .env.backup")

def switch_to_mysql():
    """Chuyển sang sử dụng MySQL"""
    create_env_backup()
    
    # Đọc file .env hiện tại
    lines = []
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Thay đổi DB_TYPE
    new_lines = []
    db_type_found = False
    
    for line in lines:
        if line.startswith('DB_TYPE='):
            new_lines.append('DB_TYPE=mysql\n')
            db_type_found = True
        else:
            new_lines.append(line)
    
    # Nếu không tìm thấy DB_TYPE, thêm vào
    if not db_type_found:
        new_lines.insert(0, 'DB_TYPE=mysql\n')
    
    # Ghi lại file
    with open('.env', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ Đã chuyển sang MySQL")
    print("🔗 Database: MYSQL")

def switch_to_postgresql():
    """Chuyển sang sử dụng PostgreSQL"""
    create_env_backup()
    
    # Đọc file .env hiện tại
    lines = []
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # Thay đổi DB_TYPE
    new_lines = []
    db_type_found = False
    
    for line in lines:
        if line.startswith('DB_TYPE='):
            new_lines.append('DB_TYPE=postgresql\n')
            db_type_found = True
        else:
            new_lines.append(line)
    
    # Nếu không tìm thấy DB_TYPE, thêm vào
    if not db_type_found:
        new_lines.insert(0, 'DB_TYPE=postgresql\n')
    
    # Ghi lại file
    with open('.env', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("✅ Đã chuyển sang PostgreSQL")
    print("🔗 Database: POSTGRESQL")

def show_current_config():
    """Hiển thị cấu hình database hiện tại"""
    from db_connection import db_config
    
    print("📋 CURRENT DATABASE CONFIGURATION:")
    print("="*50)
    print(f"Type: {db_config['type'].upper()}")
    print(f"Host: {db_config['host']}")
    print(f"Port: {db_config['port']}")
    print(f"User: {db_config['user']}")
    print(f"Database: {db_config['name']}")
    print("="*50)

def test_connection():
    """Test kết nối database"""
    try:
        from db_connection import engine
        
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test").fetchone()
            if result:
                print("✅ Database connection successful!")
                show_current_config()
            else:
                print("❌ Database connection failed!")
                
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        print("💡 Check your database configuration in .env file")

def main():
    """Main function"""
    print("🔄 DATABASE SWITCHER UTILITY")
    print("="*40)
    
    while True:
        print("\nOptions:")
        print("1. Switch to MySQL")
        print("2. Switch to PostgreSQL") 
        print("3. Show current config")
        print("4. Test connection")
        print("5. Exit")
        
        choice = input("\nChoose option (1-5): ").strip()
        
        if choice == '1':
            switch_to_mysql()
        elif choice == '2':
            switch_to_postgresql()
        elif choice == '3':
            show_current_config()
        elif choice == '4':
            test_connection()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please choose 1-5.")

if __name__ == "__main__":
    main()
