"""
Test script cho class_send_alert_of_thread
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import class_send_alert_of_thread
import time

def test_alert_manager():
    print("🧪 Testing class_send_alert_of_thread...")
    
    # Test tạo instance
    alert_manager = class_send_alert_of_thread(123)
    print(f"✅ Created alert manager for thread ID: {alert_manager.id}")
    
    # Test throttle functions
    print(f"📊 Initial consecutive errors: {alert_manager.get_consecutive_error_count()}")
    print(f"🔕 Can send telegram? {alert_manager.can_send_telegram_alert()}")
    
    # Test increment errors
    alert_manager.increment_consecutive_error()
    alert_manager.increment_consecutive_error()
    print(f"📈 After 2 increments: {alert_manager.get_consecutive_error_count()}")
    
    # Test mark telegram sent
    alert_manager.mark_telegram_sent()
    print(f"📱 Marked telegram sent, can send again? {alert_manager.can_send_telegram_alert()}")
    
    # Wait and test again
    print("⏳ Waiting 2 seconds...")
    time.sleep(2)
    print(f"📱 After 2 seconds, can send again? {alert_manager.can_send_telegram_alert(throttle_seconds=1)}")
    
    # Test extended alert
    alert_manager.update_last_alert_time()
    print(f"⏰ Should send extended alert? {alert_manager.should_send_extended_alert(interval_minutes=0.01)}")  # 0.6 seconds
    
    # Test reset
    alert_manager.reset_consecutive_error()
    print(f"🔄 After reset: {alert_manager.get_consecutive_error_count()}")
    
    print("✅ All tests completed successfully!")

if __name__ == "__main__":
    test_alert_manager()
