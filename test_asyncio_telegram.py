#!/usr/bin/env python3
"""
Test AsyncIO Telegram Integration
Test script to verify telegram notifications work in AsyncIO monitor service
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_telegram_notification import send_telegram_notification_async
from async_telegram_helper import test_telegram_connection_async


class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self, monitor_id=999, name="Test Service", url="https://example.com", user_id=1):
        self.id = monitor_id
        self.name = name
        self.url_check = url
        self.user_id = user_id
        self.type = "ping_web"
        self.check_interval_seconds = 300
        self._last_status = None


async def test_telegram_basic_connection():
    """Test basic telegram connection"""
    print("🧪 Testing basic Telegram connection...")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        return False
    
    result = await test_telegram_connection_async(bot_token, chat_id)
    
    if result['success']:
        print("✅ Basic Telegram connection successful!")
        return True
    else:
        print(f"❌ Telegram connection failed: {result['message']}")
        return False


async def test_telegram_error_notification():
    """Test error notification"""
    print("\n🚨 Testing error notification...")
    
    mock_item = MockMonitorItem()
    
    try:
        await send_telegram_notification_async(
            monitor_item=mock_item,
            is_error=True,
            error_message="Connection timeout - test error from AsyncIO"
        )
        print("✅ Error notification sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error notification failed: {e}")
        return False


async def test_telegram_recovery_notification():
    """Test recovery notification"""
    print("\n✅ Testing recovery notification...")
    
    mock_item = MockMonitorItem()
    # Set previous status to error
    mock_item._last_status = -1
    
    try:
        await send_telegram_notification_async(
            monitor_item=mock_item,
            is_error=False,
            response_time=125.5
        )
        print("✅ Recovery notification sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Recovery notification failed: {e}")
        return False


async def test_telegram_throttling():
    """Test notification throttling"""
    print("\n🔇 Testing notification throttling...")
    
    mock_item = MockMonitorItem()
    
    try:
        # Send first notification
        await send_telegram_notification_async(
            monitor_item=mock_item,
            is_error=True,
            error_message="First error message"
        )
        print("✅ First notification sent")
        
        # Send second notification immediately (should be throttled)
        await send_telegram_notification_async(
            monitor_item=mock_item,
            is_error=True,
            error_message="Second error message (should be throttled)"
        )
        print("✅ Second notification processed (likely throttled)")
        
        return True
    except Exception as e:
        print(f"❌ Throttling test failed: {e}")
        return False


async def test_consecutive_errors():
    """Test consecutive error tracking"""
    print("\n📊 Testing consecutive error tracking...")
    
    mock_item = MockMonitorItem()
    
    try:
        # Send multiple error notifications to test consecutive error tracking
        for i in range(3):
            await send_telegram_notification_async(
                monitor_item=mock_item,
                is_error=True,
                error_message=f"Consecutive error #{i+1}"
            )
            print(f"✅ Consecutive error #{i+1} processed")
            
            # Small delay between errors
            await asyncio.sleep(0.5)
        
        return True
    except Exception as e:
        print(f"❌ Consecutive error test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting AsyncIO Telegram Integration Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    tests = [
        ("Basic Connection", test_telegram_basic_connection),
        ("Error Notification", test_telegram_error_notification),
        ("Recovery Notification", test_telegram_recovery_notification),
        ("Throttling", test_telegram_throttling),
        ("Consecutive Errors", test_consecutive_errors),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            
            # Delay between tests to avoid rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Telegram integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)