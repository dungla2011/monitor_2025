#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script cho toàn bộ hệ thống monitoring
Sử dụng để test monitor service với Telegram integration
"""

import sys
import os
from dotenv import load_dotenv
from models import MonitorItem
from sqlalchemy.orm import sessionmaker
from db_connection import engine
from monitor_service import check_service
from telegram_helper import test_telegram_connection

def main():
    load_dotenv()
    
    print("🧪 Testing Monitor System with Telegram Integration")
    print("=" * 60)
    
    # Test Telegram connection first
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
    if telegram_enabled:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if bot_token and chat_id:
            print("📱 Testing Telegram connection...")
            result = test_telegram_connection(bot_token, chat_id)
            if result['success']:
                print("   ✅ Telegram connection OK")
            else:
                print(f"   ❌ Telegram connection failed: {result['message']}")
        else:
            print("   ⚠️ Telegram credentials missing in .env")
    else:
        print("📱 Telegram notifications disabled")
    
    print("-" * 60)
    
    # Test database connection and get enabled items
    try:
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        enabled_items = session.query(MonitorItem).filter(MonitorItem.enable == True).all()
        
        if not enabled_items:
            print("❌ No enabled monitor items found in database")
            session.close()
            return
            
        print(f"📊 Found {len(enabled_items)} enabled monitor items:")
        for item in enabled_items:
            print(f"   - {item.name} (ID: {item.id}, Type: {item.type})")
        
        print("\n🔍 Testing first enabled item...")
        test_item = enabled_items[0]
        
        print(f"Testing: {test_item.name}")
        print(f"URL: {test_item.url_check}")
        print(f"Type: {test_item.type}")
        print(f"Current status: {test_item.last_check_status}")
        
        # Kiểm tra service
        result = check_service(test_item)
        
        print("\n📊 Test Results:")
        print(f"   Success: {result['success']}")
        print(f"   Response Time: {result['response_time']:.2f}ms" if result['response_time'] else "   Response Time: N/A")
        print(f"   Message: {result['message']}")
        
        if telegram_enabled:
            print("\n📱 Telegram notification should be sent if status changed!")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    print("\n" + "=" * 60)
    print("🎯 Monitor system test completed!")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--run-manager':
        print("\n🚀 Starting main manager loop...")
        from monitor_service import main_manager_loop
        main_manager_loop()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python test_monitor_system.py [--run-manager]")
        print()
        print("Options:")
        print("  --run-manager    Start the main manager loop after testing")
        print("  --help           Show this help message")
        print()
        print("This script tests the complete monitor system including:")
        print("  - Database connection")
        print("  - Telegram integration")  
        print("  - Service checking")
        print("  - Notification sending")
    else:
        main()
