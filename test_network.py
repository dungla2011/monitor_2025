#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test network connectivity to Telegram API
"""

import requests
import socket
import os
from dotenv import load_dotenv

def test_dns_resolution():
    """Test DNS resolution for Telegram API"""
    try:
        print("🌐 Testing DNS resolution for api.telegram.org...")
        ip = socket.gethostbyname('api.telegram.org')
        print(f"   ✅ Resolved: api.telegram.org -> {ip}")
        return True
    except Exception as e:
        print(f"   ❌ DNS resolution failed: {e}")
        return False

def test_basic_connectivity():
    """Test basic HTTP connectivity"""
    try:
        print("🔌 Testing basic HTTPS connectivity...")
        response = requests.get('https://httpbin.org/ip', timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Basic connectivity OK: {response.json()}")
            return True
        else:
            print(f"   ❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Connectivity failed: {e}")
        return False

def test_telegram_api_simple():
    """Test simple Telegram API call"""
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ No bot token found in .env")
        return False
        
    try:
        print("🤖 Testing Telegram Bot API (getMe)...")
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"   ✅ Bot API working: {bot_info.get('username', 'Unknown')}")
                return True
            else:
                print(f"   ❌ API error: {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
        return False

def main():
    print("🧪 Network Connectivity Test")
    print("=" * 50)
    
    # Test 1: DNS Resolution
    dns_ok = test_dns_resolution()
    
    # Test 2: Basic connectivity 
    conn_ok = test_basic_connectivity()
    
    # Test 3: Telegram API
    telegram_ok = test_telegram_api_simple()
    
    print("\n📊 Summary:")
    print(f"   DNS Resolution: {'✅' if dns_ok else '❌'}")
    print(f"   Basic HTTPS: {'✅' if conn_ok else '❌'}")  
    print(f"   Telegram API: {'✅' if telegram_ok else '❌'}")
    
    if all([dns_ok, conn_ok, telegram_ok]):
        print("\n🎉 All tests passed! Telegram should work.")
    else:
        print("\n⚠️ Some tests failed. Check network/firewall settings.")

if __name__ == "__main__":
    main()
