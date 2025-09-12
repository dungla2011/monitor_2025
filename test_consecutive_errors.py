#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script cho consecutive error tracking và extended alert throttling
"""

import os
import sys
import time
from dotenv import load_dotenv
from models import MonitorItem, SessionLocal

def simulate_consecutive_errors():
    """Simulate consecutive errors để test logic"""
    print("🧪 Testing Consecutive Error Logic")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Import after loading env
    from monitor_service import (
        send_telegram_notification,
        thread_consecutive_errors,
        thread_last_alert_time,
        CONSECUTIVE_ERROR_THRESHOLD,
        EXTENDED_ALERT_INTERVAL_MINUTES
    )
    
    # Lấy monitor item để test
    session = SessionLocal()
    test_item = session.query(MonitorItem).filter(MonitorItem.enable == 1).first()
    session.close()
    
    if not test_item:
        print("❌ No enabled monitor items found for testing")
        return
    
    print(f"📋 Testing with: {test_item.name} (ID: {test_item.id})")
    print(f"📊 Settings:")
    print(f"   - Consecutive error threshold: {CONSECUTIVE_ERROR_THRESHOLD}")
    print(f"   - Extended alert interval: {EXTENDED_ALERT_INTERVAL_MINUTES} minutes")
    print(f"   - Check interval: {test_item.check_interval_seconds or 300} seconds")
    
    # Simulate consecutive errors
    print(f"\n🔄 Simulating {CONSECUTIVE_ERROR_THRESHOLD + 5} consecutive errors...")
    
    for i in range(1, CONSECUTIVE_ERROR_THRESHOLD + 6):
        print(f"\n📍 Error #{i}")
        send_telegram_notification(
            monitor_item=test_item,
            is_error=True,
            error_message=f"Simulated error #{i} - Connection timeout"
        )
        
        # Print current state
        consecutive_count = thread_consecutive_errors.get(test_item.id, 0)
        print(f"   📊 Current consecutive errors: {consecutive_count}")
        
        if i <= CONSECUTIVE_ERROR_THRESHOLD:
            print(f"   ✅ Should send alert (under threshold)")
        else:
            print(f"   ⚠️ Should use extended throttling (over threshold)")
        
        # Small delay between errors
        time.sleep(2)
    
    # Test recovery
    print(f"\n💚 Simulating service recovery...")
    send_telegram_notification(
        monitor_item=test_item,
        is_error=False,
        response_time=250.5
    )
    
    consecutive_count = thread_consecutive_errors.get(test_item.id, 0)
    print(f"   📊 Consecutive errors after recovery: {consecutive_count}")
    
    # Test error after recovery
    print(f"\n🔴 Simulating new error after recovery...")
    send_telegram_notification(
        monitor_item=test_item,
        is_error=True,
        error_message="New error after recovery - DNS failure"
    )
    
    consecutive_count = thread_consecutive_errors.get(test_item.id, 0)
    print(f"   📊 Consecutive errors after new error: {consecutive_count}")
    
    print(f"\n📊 Final State:")
    print(f"   - thread_consecutive_errors: {dict(thread_consecutive_errors)}")
    print(f"   - thread_last_alert_time: {dict(thread_last_alert_time)}")

def show_current_settings():
    """Hiển thị settings hiện tại"""
    from monitor_service import (
        CONSECUTIVE_ERROR_THRESHOLD,
        EXTENDED_ALERT_INTERVAL_MINUTES,
        TELEGRAM_THROTTLE_SECONDS
    )
    
    print("⚙️ Current Alert Settings")
    print("=" * 30)
    print(f"📊 Consecutive error threshold: {CONSECUTIVE_ERROR_THRESHOLD}")
    print(f"⏰ Extended alert interval: {EXTENDED_ALERT_INTERVAL_MINUTES} minutes")
    print(f"🔕 Basic throttle: {TELEGRAM_THROTTLE_SECONDS} seconds")
    
    if EXTENDED_ALERT_INTERVAL_MINUTES == 0:
        print("⚠️ Extended throttling is DISABLED")
    else:
        print(f"✅ Extended throttling ENABLED: {EXTENDED_ALERT_INTERVAL_MINUTES}m after {CONSECUTIVE_ERROR_THRESHOLD} errors")

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            simulate_consecutive_errors()
        elif command == 'settings':
            show_current_settings()
        else:
            print("Usage:")
            print("  python test_consecutive_errors.py test      - Test consecutive error logic")
            print("  python test_consecutive_errors.py settings  - Show current settings")
    else:
        show_current_settings()
        print(f"\n💡 Use 'python {sys.argv[0]} test' to simulate consecutive errors")

if __name__ == "__main__":
    main()
