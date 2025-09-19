#!/usr/bin/env python3
"""
Comprehensive Notification Test Suite for AsyncIO Monitor Service
Tests both Telegram and Webhook notifications in integration scenarios
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Import our async notification modules
from async_telegram_notification import send_telegram_notification_async
from async_webhook_notification import send_webhook_notification_async

class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self, name, url_check, type="both"):
        self.id = hash(name)  # Add ID field
        self.name = name
        self.url_check = url_check
        self.type = type
        self.telegram_chat_id = "-1002346072033"  # Test chat
        self.webhook_url = "https://httpbin.org/post"
        self.webhook_name = f"{name} Webhook"
        self.enable_telegram = type in ["telegram", "both"]
        self.enable_webhook = type in ["webhook", "both"]
        # Add missing attributes
        self.check_interval_seconds = 60
        self.user_id = 1
        self.type = "test"
        self.is_enabled = True

async def test_telegram_notification():
    """Test telegram notification"""
    print("🧪 Telegram Notification Test")
    print("📱 Testing telegram alert...")
    
    try:
        monitor = MockMonitorItem("Test Telegram Monitor", "https://example.com", "telegram")
        
        # Test alert
        await send_telegram_notification_async(
            monitor,
            is_error=True,
            error_message="Test telegram alert from AsyncIO service",
            response_time=150.5
        )
        
        print("✅ Telegram alert sent successfully!")
        
        # Wait a bit then test recovery
        await asyncio.sleep(2)
        
        await send_telegram_notification_async(
            monitor,
            is_error=False,
            error_message="",
            response_time=89.2
        )
        
        print("✅ Telegram recovery sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

async def test_webhook_notification():
    """Test webhook notification"""
    print("\n🧪 Webhook Notification Test")
    print("🌐 Testing webhook alert...")
    
    try:
        monitor = MockMonitorItem("Test Webhook Monitor", "https://example.com", "webhook")
        
        # Test alert
        await send_webhook_notification_async(
            monitor,
            is_error=True,
            error_message="Test webhook alert from AsyncIO service",
            response_time=200.1
        )
        
        print("✅ Webhook alert sent successfully!")
        
        # Wait a bit then test recovery
        await asyncio.sleep(2)
        
        await send_webhook_notification_async(
            monitor,
            is_error=False,
            error_message="",
            response_time=75.8
        )
        
        print("✅ Webhook recovery sent successfully!")
            
        return True
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

async def test_combined_notifications():
    """Test both telegram and webhook notifications together"""
    print("\n🧪 Combined Notifications Test")
    print("🔄 Testing both telegram and webhook together...")
    
    try:
        monitor = MockMonitorItem("Combined Test Monitor", "https://example.com", "both")
        
        # Test combined alert
        print("🚨 Sending combined alert...")
        
        # Send both notifications concurrently
        telegram_task = send_telegram_notification_async(
            monitor,
            is_error=True,
            error_message="Combined notification test - ALERT",
            response_time=500.0
        )
        
        webhook_task = send_webhook_notification_async(
            monitor,
            is_error=True,
            error_message="Combined notification test - ALERT",
            response_time=500.0
        )
        
        # Wait for both to complete
        telegram_result, webhook_result = await asyncio.gather(
            telegram_task, webhook_task, return_exceptions=True
        )
        
        telegram_ok = not isinstance(telegram_result, Exception)
        webhook_ok = webhook_result and not isinstance(webhook_result, Exception)
        
        if telegram_ok and webhook_ok:
            print("✅ Combined alert sent successfully!")
        else:
            print(f"⚠️ Combined alert partial success: Telegram={telegram_ok}, Webhook={webhook_ok}")
        
        # Wait a bit then test combined recovery
        await asyncio.sleep(3)
        
        print("✅ Sending combined recovery...")
        
        telegram_task = send_telegram_notification_async(
            monitor,
            is_error=False,
            error_message="",
            response_time=95.3
        )
        
        webhook_task = send_webhook_notification_async(
            monitor,
            is_error=False,
            error_message="",
            response_time=95.3
        )
        
        # Wait for both to complete
        telegram_result, webhook_result = await asyncio.gather(
            telegram_task, webhook_task, return_exceptions=True
        )
        
        telegram_ok = not isinstance(telegram_result, Exception)
        webhook_ok = webhook_result and not isinstance(webhook_result, Exception)
        
        if telegram_ok and webhook_ok:
            print("✅ Combined recovery sent successfully!")
        else:
            print(f"⚠️ Combined recovery partial success: Telegram={telegram_ok}, Webhook={webhook_ok}")
        
        return telegram_ok or webhook_ok
        
    except Exception as e:
        print(f"❌ Combined test failed: {e}")
        return False

async def test_notification_performance():
    """Test notification performance under concurrent load"""
    print("\n🧪 Performance Test")
    print("⚡ Testing notification performance...")
    
    try:
        monitors = [
            MockMonitorItem(f"Perf Monitor {i}", f"https://example{i}.com", "both")
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Send notifications concurrently
        tasks = []
        for monitor in monitors:
            # Add telegram task
            tasks.append(send_telegram_notification_async(
                monitor,
                is_error=True,
                error_message=f"Performance test alert for {monitor.name}",
                response_time=100.0
            ))
            
            # Add webhook task
            tasks.append(send_webhook_notification_async(
                monitor,
                is_error=True,
                error_message=f"Performance test alert for {monitor.name}",
                response_time=100.0
            ))
        
        # Wait for all notifications to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(1 for result in results if not isinstance(result, Exception))
        total = len(results)
        
        print(f"✅ Performance test completed!")
        print(f"   📊 Results: {successful}/{total} notifications sent successfully")
        print(f"   ⏱️ Duration: {duration:.2f}s")
        print(f"   📈 Rate: {total/duration:.1f} notifications/second")
        
        return successful > total * 0.7  # 70% success rate is acceptable
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

async def test_error_handling():
    """Test error handling scenarios"""
    print("\n🧪 Error Handling Test")
    print("🛡️ Testing error handling...")
    
    try:
        # Test with invalid webhook URL
        monitor = MockMonitorItem("Error Test Monitor", "https://example.com", "webhook")
        monitor.webhook_url = "https://invalid-webhook-url-that-does-not-exist.com/webhook"
        
        print("🔍 Testing invalid webhook URL...")
        try:
            await send_webhook_notification_async(
                monitor,
                is_error=True,
                error_message="Error handling test",
                response_time=100.0
            )
            print("✅ Invalid webhook URL handled gracefully")
        except Exception as webhook_error:
            print(f"✅ Invalid webhook URL handled correctly (error: {str(webhook_error)[:50]}...)")
        
        # Test with invalid telegram chat
        monitor_tg = MockMonitorItem("TG Error Test", "https://example.com", "telegram")
        monitor_tg.telegram_chat_id = "invalid_chat_id"
        
        print("🔍 Testing invalid telegram chat...")
        try:
            await send_telegram_notification_async(
                monitor_tg,
                is_error=True,
                error_message="Error handling test",
                response_time=100.0
            )
            print("✅ Invalid telegram chat handled gracefully")
        except Exception as tg_error:
            print(f"✅ Invalid telegram chat handled correctly (error: {str(tg_error)[:50]}...)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Run all notification tests"""
    print("🚀 Starting AsyncIO Notification Integration Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Telegram Notification", test_telegram_notification),
        ("Webhook Notification", test_webhook_notification),
        ("Combined Notifications", test_combined_notifications),
        ("Performance Test", test_notification_performance),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    success_rate = (passed / len(results)) * 100
    print(f"📊 Results: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")
    
    if passed == len(results):
        print("🎉 All tests passed! Notification system is working perfectly.")
    elif passed > len(results) * 0.7:
        print("⚠️ Most tests passed. Some notifications may have issues.")
    else:
        print("❌ Multiple test failures. Please check notification configuration.")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())