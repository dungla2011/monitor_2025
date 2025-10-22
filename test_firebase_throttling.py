"""
Test Firebase Notification with Throttling
Verifies Firebase notification throttling logic works independently
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_firebase_notification import send_firebase_notification_async


class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self, monitor_id=1, user_id=1):
        self.id = monitor_id
        self.user_id = user_id
        self.name = "Test Monitor Service"
        self.url_check = "https://example.com/api/test"
        self.allow_alert_for_consecutive_error = 0  # 0 = throttle enabled (chỉ gửi lần đầu)
        self.alert_throttle_seconds = 30  # 30 seconds throttle
        self._thread_id = 999


async def test_firebase_throttling():
    """Test Firebase notification throttling logic"""
    print("=" * 80)
    print("🧪 TEST: Firebase Notification Throttling")
    print("=" * 80)
    
    monitor = MockMonitorItem()
    
    # Test 1: Gửi alert lần 1 (nên thành công)
    print("\n📍 Test 1: First alert (should succeed)")
    result1 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Connection timeout - first error"
    )
    print(f"   Result: {result1}")
    
    # Test 2: Gửi alert lần 2 ngay lập tức (nên bị throttle)
    print("\n📍 Test 2: Second alert immediately (should be throttled)")
    await asyncio.sleep(1)  # Wait 1 second
    result2 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Connection timeout - consecutive error #2"
    )
    print(f"   Result: {result2}")
    print(f"   Expected: Throttled (consecutive error > 1)")
    
    # Test 3: Gửi alert lần 3 (nên vẫn bị throttle)
    print("\n📍 Test 3: Third alert (should be throttled)")
    await asyncio.sleep(1)
    result3 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Connection timeout - consecutive error #3"
    )
    print(f"   Result: {result3}")
    
    # Test 4: Gửi recovery (nên thành công, không throttle)
    print("\n📍 Test 4: Recovery notification (should succeed, no throttle)")
    await asyncio.sleep(1)
    result4 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=False,
        response_time=156.78
    )
    print(f"   Result: {result4}")
    
    # Test 5: Gửi alert mới sau recovery (nên reset counter, thành công)
    print("\n📍 Test 5: New alert after recovery (should succeed, counter reset)")
    await asyncio.sleep(1)
    result5 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="New error after recovery"
    )
    print(f"   Result: {result5}")
    
    print("\n" + "=" * 80)
    print("✅ Test completed!")
    print("=" * 80)


async def test_firebase_no_throttle():
    """Test Firebase with throttling disabled"""
    print("\n" + "=" * 80)
    print("🧪 TEST: Firebase No Throttle Mode")
    print("=" * 80)
    
    monitor = MockMonitorItem()
    monitor.allow_alert_for_consecutive_error = 1  # 1 = no throttle (gửi liên tiếp)
    monitor.alert_throttle_seconds = 5  # 5 seconds between alerts
    
    # Test 1: Alert lần 1
    print("\n📍 Test 1: First alert (no throttle mode)")
    result1 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Error #1"
    )
    print(f"   Result: {result1}")
    
    # Test 2: Alert lần 2 ngay (nên bị throttle theo time)
    print("\n📍 Test 2: Second alert immediately (should fail - time throttle)")
    await asyncio.sleep(1)
    result2 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Error #2"
    )
    print(f"   Result: {result2}")
    
    # Test 3: Alert lần 3 sau 6 giây (nên thành công)
    print("\n📍 Test 3: Third alert after 6 seconds (should succeed)")
    print("   Waiting 6 seconds...")
    await asyncio.sleep(6)
    result3 = await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Error #3 after 6 seconds"
    )
    print(f"   Result: {result3}")
    
    print("\n" + "=" * 80)
    print("✅ No throttle test completed!")
    print("=" * 80)


async def main():
    """Run all tests"""
    print(f"\n🚀 Starting Firebase Throttling Tests - {datetime.now()}\n")
    
    # Test 1: Throttle mode
    await test_firebase_throttling()
    
    # Test 2: No throttle mode
    await test_firebase_no_throttle()
    
    print(f"\n🎉 All tests finished - {datetime.now()}")
    print("\n💡 Notes:")
    print("   - FIREBASE_THROTTLE_ENABLED=true: Only first error sent")
    print("   - FIREBASE_THROTTLE_ENABLED=false: All errors sent with time throttle")
    print("   - Recovery notifications always sent (no throttle)")
    print("   - Firebase works independently from Telegram/Webhook\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
