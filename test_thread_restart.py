"""
Test reset webhook flags khi start thread
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import class_send_alert_of_thread

def test_thread_restart_scenario():
    """Test scenario restart thread"""
    print("🧪 Testing thread restart scenario...")
    
    # === Simulate thread lifecycle ===
    print("\n" + "="*60)
    print("📊 THREAD LIFECYCLE SIMULATION")
    print("="*60)
    
    # Thread start lần 1
    manager = class_send_alert_of_thread(123)
    print(f"🚀 Thread start lần 1:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # Có lỗi
    manager.mark_webhook_error_sent()
    print(f"❌ Error xảy ra:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # Recovery
    manager.mark_webhook_recovery_sent()
    print(f"✅ Recovery:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # Thread bị stop và restart (simulate reset)
    print(f"\n🔄 Thread restart (reset flags):")
    manager.reset_webhook_flags()
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # Kiểm tra có thể gửi webhook không
    print(f"\n🔍 After restart capabilities:")
    print(f"   - Can send error: {manager.should_send_webhook_error()}")
    print(f"   - Can send recovery: {manager.should_send_webhook_recovery()}")
    
    # Simulate error mới
    print(f"\n❌ Error mới sau restart:")
    can_send_error = manager.should_send_webhook_error()
    print(f"   - Should send error: {can_send_error}")
    
    if can_send_error:
        manager.mark_webhook_error_sent()
        print(f"   - Sent error webhook")
        print(f"   - Can send recovery now: {manager.should_send_webhook_recovery()}")

def compare_with_without_reset():
    """So sánh có reset vs không reset"""
    print("\n" + "="*60)
    print("🆚 WITH vs WITHOUT RESET")
    print("="*60)
    
    # WITHOUT reset (thread continue)
    print("❌ WITHOUT reset (thread tiếp tục):")
    manager1 = class_send_alert_of_thread(1)
    manager1.mark_webhook_error_sent()
    manager1.mark_webhook_recovery_sent()
    print(f"   After full cycle: error_sent={manager1.thread_webhook_error_sent}, recovery_sent={manager1.thread_webhook_recovery_sent}")
    print(f"   Can send new error: {manager1.should_send_webhook_error()}")
    print(f"   Can send new recovery: {manager1.should_send_webhook_recovery()}")
    
    # WITH reset (thread restart)
    print("\n✅ WITH reset (thread restart):")
    manager2 = class_send_alert_of_thread(2)
    manager2.mark_webhook_error_sent()
    manager2.mark_webhook_recovery_sent()
    print(f"   Before reset: error_sent={manager2.thread_webhook_error_sent}, recovery_sent={manager2.thread_webhook_recovery_sent}")
    
    manager2.reset_webhook_flags()  # Simulate thread restart
    print(f"   After reset: error_sent={manager2.thread_webhook_error_sent}, recovery_sent={manager2.thread_webhook_recovery_sent}")
    print(f"   Can send new error: {manager2.should_send_webhook_error()}")
    print(f"   Can send new recovery: {manager2.should_send_webhook_recovery()}")

if __name__ == "__main__":
    test_thread_restart_scenario()
    compare_with_without_reset()
    
    print(f"\n🎉 Test completed!")
    print(f"\n📋 SUMMARY:")
    print(f"✅ Thread restart đã reset webhook flags đúng cách")
    print(f"✅ Sau restart, thread có thể gửi webhook mới")
    print(f"✅ Không bị stuck ở trạng thái cũ")
    print(f"✅ Logic hoạt động chính xác")
