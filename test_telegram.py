#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script cho Telegram helper
Sử dụng để test kết nối và gửi tin nhắn Telegram
"""

import os
import sys
from dotenv import load_dotenv
from telegram_helper import (
    test_telegram_connection, 
    send_telegram_alert, 
    send_telegram_recovery,
    send_telegram_message
)

def main():
    # Load environment variables
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
    
    if not telegram_enabled:
        print("❌ Telegram is disabled in .env file (TELEGRAM_ENABLED=false)")
        print("✅ To enable: Set TELEGRAM_ENABLED=true in .env file")
        return
    
    if not bot_token or not chat_id:
        print("❌ Missing Telegram configuration in .env file:")
        print("   - TELEGRAM_BOT_TOKEN: Bot token from @BotFather")
        print("   - TELEGRAM_CHAT_ID: Your chat ID")
        print("   - TELEGRAM_ENABLED: Set to 'true' to enable")
        return
    
    if bot_token == 'your_bot_token_here' or chat_id == 'your_chat_id_here':
        print("❌ Please update .env file with real Telegram credentials")
        print("   - Get bot token from @BotFather on Telegram")
        print("   - Get chat ID by messaging your bot and visiting:")
        print(f"     https://api.telegram.org/bot{bot_token}/getUpdates")
        return
    
    print("🧪 Testing Telegram connection...")
    print(f"📱 Bot Token: {bot_token[:10]}...{bot_token[-10:] if len(bot_token) > 20 else bot_token}")
    print(f"💬 Chat ID: {chat_id}")
    print("-" * 50)
    
    # Test 1: Basic connection
    print("1️⃣ Testing basic connection...")
    result = test_telegram_connection(bot_token, chat_id)
    if result['success']:
        print("   ✅ Connection successful!")
    else:
        print(f"   ❌ Connection failed: {result['message']}")
        return
    
    # Test 2: Service alert
    print("\n2️⃣ Testing service alert...")
    alert_result = send_telegram_alert(
        bot_token=bot_token,
        chat_id=chat_id,
        service_name="Test Service",
        service_url="https://example.com",
        error_message="Connection timeout - this is a test alert"
    )
    if alert_result['success']:
        print("   ✅ Alert sent successfully!")
    else:
        print(f"   ❌ Alert failed: {alert_result['message']}")
    
    # Test 3: Service recovery
    print("\n3️⃣ Testing service recovery...")
    recovery_result = send_telegram_recovery(
        bot_token=bot_token,
        chat_id=chat_id,
        service_name="Test Service",
        service_url="https://example.com",
        response_time=250.5
    )
    if recovery_result['success']:
        print("   ✅ Recovery notification sent successfully!")
    else:
        print(f"   ❌ Recovery notification failed: {recovery_result['message']}")
    
    # Test 4: Custom message
    print("\n4️⃣ Testing custom message...")
    custom_result = send_telegram_message(
        bot_token=bot_token,
        chat_id=chat_id,
        message="🎉 <b>Monitor System Test</b>\n\nAll Telegram functions are working correctly! ✅"
    )
    if custom_result['success']:
        print("   ✅ Custom message sent successfully!")
    else:
        print(f"   ❌ Custom message failed: {custom_result['message']}")
    
    print("\n" + "=" * 50)
    print("🎯 Telegram testing completed!")
    print("📱 Check your Telegram chat for test messages")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python test_telegram.py")
        print()
        print("This script tests Telegram integration for the monitor system.")
        print("Make sure to configure .env file with:")
        print("  - TELEGRAM_BOT_TOKEN")
        print("  - TELEGRAM_CHAT_ID") 
        print("  - TELEGRAM_ENABLED=true")
    else:
        main()
