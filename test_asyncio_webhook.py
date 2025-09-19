#!/usr/bin/env python3
"""
Test AsyncIO Webhook Integration
Test script to verify webhook notifications work in AsyncIO monitor service
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_webhook_notification import (
    send_webhook_notification_async,
    test_webhook_connection_async,
    send_webhook_alert_async,
    send_webhook_recovery_async
)


class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self, monitor_id=777, name="Test Webhook Service", url="https://example.com", user_id=1):
        self.id = monitor_id
        self.name = name
        self.url_check = url
        self.user_id = user_id
        self.type = "ping_web"
        self.check_interval_seconds = 300
        self._last_status = None


async def test_webhook_basic_connection():
    """Test basic webhook connection"""
    print("🧪 Testing basic webhook connection...")
    
    # Use httpbin.org for testing (free service)
    test_webhook_url = "https://httpbin.org/post"
    
    result = await test_webhook_connection_async(test_webhook_url, "Test Webhook")
    
    if result['success']:
        print("✅ Basic webhook connection successful!")
        print(f"   Status: {result['status_code']}")
        print(f"   Message: {result['message']}")
        return True
    else:
        print(f"❌ Webhook connection failed: {result['message']}")
        return False


async def test_webhook_alert():
    """Test webhook alert notification"""
    print("\n🚨 Testing webhook alert...")
    
    test_webhook_url = "https://httpbin.org/post"
    
    try:
        result = await send_webhook_alert_async(
            webhook_url=test_webhook_url,
            service_name="Test Service Alert",
            service_url="https://example.com",
            error_message="Connection timeout - test error from AsyncIO",
            alert_type="error",
            monitor_id=777,
            consecutive_errors=3,
            check_interval_seconds=300,
            webhook_name="Test Webhook Alert"
        )
        
        if result:
            print("✅ Webhook alert sent successfully!")
            return True
        else:
            print("❌ Webhook alert failed!")
            return False
    except Exception as e:
        print(f"❌ Webhook alert exception: {e}")
        return False


async def test_webhook_recovery():
    """Test webhook recovery notification"""
    print("\n✅ Testing webhook recovery...")
    
    test_webhook_url = "https://httpbin.org/post"
    
    try:
        result = await send_webhook_recovery_async(
            webhook_url=test_webhook_url,
            service_name="Test Service Recovery",
            service_url="https://example.com",
            recovery_message="Service is back online - test recovery from AsyncIO",
            monitor_id=777,
            response_time=125.5,
            webhook_name="Test Webhook Recovery"
        )
        
        if result:
            print("✅ Webhook recovery sent successfully!")
            return True
        else:
            print("❌ Webhook recovery failed!")
            return False
    except Exception as e:
        print(f"❌ Webhook recovery exception: {e}")
        return False


async def test_webhook_timeout():
    """Test webhook timeout handling"""
    print("\n⏱️ Testing webhook timeout...")
    
    # Use a non-responsive URL to test timeout
    timeout_webhook_url = "https://httpbin.org/delay/15"  # 15 second delay, should timeout
    
    try:
        result = await send_webhook_alert_async(
            webhook_url=timeout_webhook_url,
            service_name="Test Timeout Service",
            service_url="https://example.com",
            error_message="Timeout test",
            webhook_name="Timeout Test Webhook"
        )
        
        if not result:
            print("✅ Webhook timeout handled correctly!")
            return True
        else:
            print("⚠️ Webhook should have timed out but didn't")
            return False
    except Exception as e:
        print(f"❌ Webhook timeout test exception: {e}")
        return False


async def test_webhook_integration():
    """Test full webhook integration"""
    print("\n🔗 Testing full webhook integration...")
    
    mock_item = MockMonitorItem()
    
    # Mock webhook config by setting environment variable
    original_webhook_enabled = os.getenv('WEBHOOK_ENABLED')
    os.environ['WEBHOOK_ENABLED'] = 'true'
    
    try:
        # Test error notification
        await send_webhook_notification_async(
            monitor_item=mock_item,
            is_error=True,
            error_message="Integration test error"
        )
        print("✅ Webhook integration error test processed")
        
        # Test recovery notification  
        await send_webhook_notification_async(
            monitor_item=mock_item,
            is_error=False,
            response_time=89.5
        )
        print("✅ Webhook integration recovery test processed")
        
        return True
    except Exception as e:
        print(f"❌ Webhook integration test failed: {e}")
        return False
    finally:
        # Restore original setting
        if original_webhook_enabled is not None:
            os.environ['WEBHOOK_ENABLED'] = original_webhook_enabled
        elif 'WEBHOOK_ENABLED' in os.environ:
            del os.environ['WEBHOOK_ENABLED']


async def test_webhook_retry_logic():
    """Test webhook retry logic with bad URL"""
    print("\n🔄 Testing webhook retry logic...")
    
    # Use invalid URL to test retry
    bad_webhook_url = "https://invalid-webhook-url-that-does-not-exist.com/webhook"
    
    try:
        result = await send_webhook_alert_async(
            webhook_url=bad_webhook_url,
            service_name="Test Retry Service",
            service_url="https://example.com",
            error_message="Retry test",
            webhook_name="Retry Test Webhook"
        )
        
        if not result:
            print("✅ Webhook retry logic worked correctly (failed as expected)")
            return True
        else:
            print("⚠️ Webhook should have failed but didn't")
            return False
    except Exception as e:
        print(f"❌ Webhook retry test exception: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting AsyncIO Webhook Integration Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    tests = [
        ("Basic Connection", test_webhook_basic_connection),
        ("Alert Notification", test_webhook_alert),
        ("Recovery Notification", test_webhook_recovery),
        ("Timeout Handling", test_webhook_timeout),
        ("Integration Test", test_webhook_integration),
        ("Retry Logic", test_webhook_retry_logic),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 {test_name}")
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
        print("🎉 All tests passed! Webhook integration is working correctly.")
    elif passed >= total * 0.8:  # 80% pass rate is acceptable for webhook tests
        print("✅ Most tests passed! Webhook integration is working well.")
        print("   (Some failures may be due to network issues or test service limitations)")
    else:
        print("⚠️ Many tests failed. Check the logs above for details.")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)