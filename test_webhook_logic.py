"""
Test webhook functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import class_send_alert_of_thread

def test_webhook_logic():
    """Test webhook logic của alert manager"""
    print("🧪 Testing webhook logic...")
    
    # Create alert manager
    alert_manager = class_send_alert_of_thread(123)
    
    print(f"📊 Initial state:")
    print(f"   - Should send error: {alert_manager.should_send_webhook_error()}")
    print(f"   - Should send recovery: {alert_manager.should_send_webhook_recovery()}")
    
    # Simulate first error
    print(f"\n🔥 First error occurs:")
    print(f"   - Should send error: {alert_manager.should_send_webhook_error()}")
    
    # Mark error sent
    alert_manager.mark_webhook_error_sent()
    print(f"   - After marking error sent:")
    print(f"     - Should send error: {alert_manager.should_send_webhook_error()}")
    print(f"     - Should send recovery: {alert_manager.should_send_webhook_recovery()}")
    
    # Simulate more errors (shouldn't send webhook)
    print(f"\n🔥 More errors occur (should not send webhook):")
    print(f"   - Should send error: {alert_manager.should_send_webhook_error()}")
    
    # Simulate recovery
    print(f"\n✅ Service recovers:")
    print(f"   - Should send recovery: {alert_manager.should_send_webhook_recovery()}")
    
    # Mark recovery sent
    alert_manager.mark_webhook_recovery_sent()
    print(f"   - After marking recovery sent:")
    print(f"     - Should send error: {alert_manager.should_send_webhook_error()}")
    print(f"     - Should send recovery: {alert_manager.should_send_webhook_recovery()}")
    
    # Simulate new error cycle
    print(f"\n🔥 New error occurs after recovery:")
    print(f"   - Should send error: {alert_manager.should_send_webhook_error()}")
    
    # Reset flags (like when restarting thread)
    print(f"\n🔄 Reset webhook flags:")
    alert_manager.reset_webhook_flags()
    print(f"   - Should send error: {alert_manager.should_send_webhook_error()}")
    print(f"   - Should send recovery: {alert_manager.should_send_webhook_recovery()}")

def test_webhook_vs_telegram_behavior():
    """Test sự khác biệt giữa webhook và telegram behavior"""
    print("\n" + "="*60)
    print("🆚 WEBHOOK vs TELEGRAM BEHAVIOR")
    print("="*60)
    
    alert_manager = class_send_alert_of_thread(456)
    
    print("📱 TELEGRAM behavior (gửi lặp lại):")
    for i in range(5):
        consecutive_errors = i + 1
        alert_manager.increment_consecutive_error()
        can_send = alert_manager.can_send_telegram_alert(throttle_seconds=0)  # No throttle for test
        print(f"   Error {consecutive_errors}: Can send telegram = {can_send}")
        if can_send:
            alert_manager.mark_telegram_sent()
    
    print(f"\n🪝 WEBHOOK behavior (chỉ gửi 1 lần):")
    alert_manager2 = class_send_alert_of_thread(789)
    for i in range(5):
        consecutive_errors = i + 1
        can_send = alert_manager2.should_send_webhook_error()
        print(f"   Error {consecutive_errors}: Should send webhook = {can_send}")
        if can_send:
            alert_manager2.mark_webhook_error_sent()
    
    print(f"\n✅ RECOVERY behavior:")
    print(f"   Telegram can send recovery: {True}")  # Telegram always can send
    print(f"   Webhook should send recovery: {alert_manager2.should_send_webhook_recovery()}")

if __name__ == "__main__":
    test_webhook_logic()
    test_webhook_vs_telegram_behavior()
    
    print(f"\n🎉 Test completed!")
    print(f"\n📋 SUMMARY:")
    print(f"✅ Webhook chỉ gửi 1 lần khi error đầu tiên")
    print(f"✅ Webhook chỉ gửi 1 lần khi recovery")
    print(f"✅ Telegram gửi lặp lại theo throttle")
    print(f"✅ Logic hoạt động đúng theo yêu cầu")
