#!/usr/bin/env python3
"""
Database Switcher Utility
Tiện ích chuyển đổi giữa MySQL và PostgreSQL
"""

import os
import shutil
from pathlib import Path

def switch_to_mysql():
    """Switch to MySQL configuration"""
    env_file = Path('.env')
    
    # Backup current .env
    if env_file.exists():
        shutil.copy(env_file, '.env.backup')
        print("✅ Backed up current .env to .env.backup")
    
    # Read current .env and update DB_TYPE
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace DB_TYPE
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('DB_TYPE='):
                new_lines.append('DB_TYPE=mysql')
            else:
                new_lines.append(line)
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        print("✅ Switched to MySQL database")
        print("📋 Config: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME")
    else:
        print("❌ .env file not found")

def switch_to_postgresql():
    """Switch to PostgreSQL configuration"""
    env_file = Path('.env')
    
    # Backup current .env
    if env_file.exists():
        shutil.copy(env_file, '.env.backup')
        print("✅ Backed up current .env to .env.backup")
    
    # Read current .env and update DB_TYPE
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace DB_TYPE
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('DB_TYPE='):
                new_lines.append('DB_TYPE=postgresql')
            else:
                new_lines.append(line)
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        print("✅ Switched to PostgreSQL database")
        print("📋 Config: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_NAME")
    else:
        print("❌ .env file not found")

def show_current_config():
    """Show current database configuration"""
    from dotenv import load_dotenv
    load_dotenv()
    
    db_type = os.getenv('DB_TYPE', 'mysql')
    print(f"🔗 Current database type: {db_type.upper()}")
    
    if db_type == 'postgresql':
        host = os.getenv('POSTGRES_HOST', 'not set')
        port = os.getenv('POSTGRES_PORT', 'not set')
        user = os.getenv('POSTGRES_USER', 'not set')
        name = os.getenv('POSTGRES_NAME', 'not set')
        print(f"📊 PostgreSQL: {user}@{host}:{port}/{name}")
    else:
        host = os.getenv('MYSQL_HOST') or os.getenv('DB_HOST', 'not set')
        port = os.getenv('MYSQL_PORT') or os.getenv('DB_PORT', 'not set')
        user = os.getenv('MYSQL_USER') or os.getenv('DB_USER', 'not set')
        name = os.getenv('MYSQL_NAME') or os.getenv('DB_NAME', 'not set')
        print(f"📊 MySQL: {user}@{host}:{port}/{name}")

def main():
    """Main function"""
    print("🔄 Database Switcher Utility")
    print("="*40)
    
    show_current_config()
    
    print("\nOptions:")
    print("1. Switch to MySQL")
    print("2. Switch to PostgreSQL") 
    print("3. Show current config")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        switch_to_mysql()
    elif choice == '2':
        switch_to_postgresql()
    elif choice == '3':
        show_current_config()
    elif choice == '4':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
