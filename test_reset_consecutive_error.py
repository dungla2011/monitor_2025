#!/usr/bin/env python3
"""
Test Reset Consecutive Error Logic
Test script to verify reset_consecutive_error_on_enable functionality
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

from async_telegram_notification import (
    send_telegram_notification_async, 
    reset_consecutive_error_on_enable
)
from async_alert_manager import get_alert_manager


class MockMonitorItem:
    """Mock monitor item for testing"""
    def __init__(self, monitor_id=888, name="Test Reset Service", url="https://example.com", user_id=1):
        self.id = monitor_id
        self.name = name
        self.url_check = url
        self.user_id = user_id
        self.type = "ping_web"
        self.check_interval_seconds = 300
        self._last_status = None


async def test_consecutive_error_buildup():
    """Build up consecutive errors"""
    print("🔥 Building up consecutive errors...")
    
    mock_item = MockMonitorItem()
    
    # Send 5 consecutive errors
    for i in range(5):
        await send_telegram_notification_async(
            monitor_item=mock_item,
            is_error=True,
            error_message=f"Test error #{i+1} before reset"
        )
        await asyncio.sleep(0.1)  # Small delay
    
    # Check final count
    alert_manager = await get_alert_manager(mock_item.id)
    count = await alert_manager.get_consecutive_error_count()
    print(f"✅ Built up {count} consecutive errors")
    return count


async def test_reset_consecutive_error():
    """Test reset consecutive error function"""
    print("\n🔄 Testing reset consecutive error function...")
    
    mock_item = MockMonitorItem()
    
    # Get current count
    alert_manager = await get_alert_manager(mock_item.id)
    before_count = await alert_manager.get_consecutive_error_count()
    print(f"📊 Before reset: {before_count} consecutive errors")
    
    # Reset using the function
    await reset_consecutive_error_on_enable(mock_item.id)
    
    # Check count after reset
    after_count = await alert_manager.get_consecutive_error_count()
    print(f"📊 After reset: {after_count} consecutive errors")
    
    return before_count > 0 and after_count == 0


async def test_reset_then_new_error():
    """Test that new errors start counting from 0 after reset"""
    print("\n🆕 Testing new error counting after reset...")
    
    mock_item = MockMonitorItem()
    
    # Send one new error
    await send_telegram_notification_async(
        monitor_item=mock_item,
        is_error=True,
        error_message="New error after reset"
    )
    
    # Check count
    alert_manager = await get_alert_manager(mock_item.id)
    count = await alert_manager.get_consecutive_error_count()
    print(f"📊 New consecutive error count: {count}")
    
    return count == 1


async def test_reset_then_recovery():
    """Test recovery notification after reset"""
    print("\n✅ Testing recovery after reset...")
    
    mock_item = MockMonitorItem()
    mock_item._last_status = -1  # Set previous status to error
    
    # Send recovery
    await send_telegram_notification_async(
        monitor_item=mock_item,
        is_error=False,
        response_time=89.5
    )
    
    # Check count should be 0
    alert_manager = await get_alert_manager(mock_item.id)
    count = await alert_manager.get_consecutive_error_count()
    print(f"📊 Count after recovery: {count}")
    
    return count == 0


async def test_multiple_monitor_isolation():
    """Test that reset affects only specific monitor"""
    print("\n🔒 Testing monitor isolation...")
    
    # Create two different monitors
    monitor1 = MockMonitorItem(monitor_id=111, name="Monitor 1")
    monitor2 = MockMonitorItem(monitor_id=222, name="Monitor 2")
    
    # Build up errors for both
    for i in range(3):
        await send_telegram_notification_async(
            monitor_item=monitor1,
            is_error=True,
            error_message=f"Monitor 1 error #{i+1}"
        )
        await send_telegram_notification_async(
            monitor_item=monitor2,
            is_error=True,
            error_message=f"Monitor 2 error #{i+1}"
        )
        await asyncio.sleep(0.1)
    
    # Check both counts
    alert1 = await get_alert_manager(monitor1.id)
    alert2 = await get_alert_manager(monitor2.id)
    count1_before = await alert1.get_consecutive_error_count()
    count2_before = await alert2.get_consecutive_error_count()
    
    print(f"📊 Before reset - Monitor 1: {count1_before}, Monitor 2: {count2_before}")
    
    # Reset only monitor 1
    await reset_consecutive_error_on_enable(monitor1.id)
    
    # Check counts after reset
    count1_after = await alert1.get_consecutive_error_count()
    count2_after = await alert2.get_consecutive_error_count()
    
    print(f"📊 After reset - Monitor 1: {count1_after}, Monitor 2: {count2_after}")
    
    return count1_after == 0 and count2_after == count2_before


async def main():
    """Main test function"""
    print("🚀 Starting Reset Consecutive Error Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    tests = [
        ("Build Consecutive Errors", test_consecutive_error_buildup),
        ("Reset Functionality", test_reset_consecutive_error),
        ("New Error After Reset", test_reset_then_new_error),
        ("Recovery After Reset", test_reset_then_recovery),
        ("Monitor Isolation", test_multiple_monitor_isolation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 {test_name}")
            result = await test_func()
            
            # For buildup test, result is the count, others are boolean
            if test_name == "Build Consecutive Errors":
                success = result > 0
                print(f"Result: {result} errors built up")
            else:
                success = result
                print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
            
            results.append((test_name, success))
            
            # Small delay between tests
            await asyncio.sleep(1)
            
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
        print("🎉 All tests passed! Reset consecutive error logic is working correctly.")
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