"""
Test Firebase Notification Module (Independent from Telegram)
Verify that Firebase notifications can be called independently
"""

import asyncio
import sys
from datetime import datetime

# Load test environment
if '--test' in sys.argv or 'test' in sys.argv:
    from dotenv import load_dotenv
    load_dotenv('.env.test')
else:
    from dotenv import load_dotenv
    load_dotenv()

from async_telegram_notification import send_firebase_notification_async
from models import MonitorItem


class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self):
        self.id = 999
        self.name = "Test Firebase Monitor"
        self.url_check = "https://google.com"
        self.user_id = 1  # Change this to your user_id
        self.type = "ping_web"
        self.check_interval_seconds = 60


async def test_firebase_alert():
    """Test Firebase alert notification"""
    print("\n=== TEST 1: Firebase Alert Notification ===")
    
    monitor = MockMonitorItem()
    
    print(f"📱 Sending Firebase alert to user {monitor.user_id}...")
    print(f"Monitor: {monitor.name} ({monitor.url_check})")
    
    await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="Test alert from independent Firebase module"
    )
    
    print("✅ Alert sent (check device for notification)")


async def test_firebase_recovery():
    """Test Firebase recovery notification"""
    print("\n=== TEST 2: Firebase Recovery Notification ===")
    
    monitor = MockMonitorItem()
    
    print(f"📱 Sending Firebase recovery to user {monitor.user_id}...")
    print(f"Monitor: {monitor.name} ({monitor.url_check})")
    
    await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=False,
        response_time=123.45
    )
    
    print("✅ Recovery notification sent (check device)")


async def test_no_firebase_token():
    """Test behavior when no Firebase token exists"""
    print("\n=== TEST 3: No Firebase Token Scenario ===")
    
    monitor = MockMonitorItem()
    monitor.user_id = 99999  # Non-existent user
    
    print(f"📱 Sending to non-existent user {monitor.user_id}...")
    
    await send_firebase_notification_async(
        monitor_item=monitor,
        is_error=True,
        error_message="This should not send (no token)"
    )
    
    print("✅ Handled gracefully (no crash)")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Firebase Independent Notification Test")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        await test_firebase_alert()
        await asyncio.sleep(2)
        
        await test_firebase_recovery()
        await asyncio.sleep(2)
        
        await test_no_firebase_token()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
