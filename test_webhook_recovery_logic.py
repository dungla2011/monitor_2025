"""
Test để hiểu rõ webhook recovery logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import class_send_alert_of_thread

def test_webhook_recovery_scenarios():
    """Test các scenario webhook recovery"""
    print("🧪 Testing webhook recovery scenarios...")
    
    # === SCENARIO 1: Service OK từ đầu, không có lỗi ===
    print("\n" + "="*60)
    print("📊 SCENARIO 1: Service OK từ đầu (không có lỗi trước đó)")
    print("="*60)
    
    manager1 = class_send_alert_of_thread(1)
    print(f"Initial state:")
    print(f"  - webhook_error_sent: {manager1.thread_webhook_error_sent}")
    print(f"  - webhook_recovery_sent: {manager1.thread_webhook_recovery_sent}")
    
    should_send = manager1.should_send_webhook_recovery()
    print(f"  - should_send_webhook_recovery(): {should_send}")
    
    if not should_send:
        with manager1._lock:
            if not manager1.thread_webhook_error_sent:
                reason = "No previous error sent"
            elif manager1.thread_webhook_recovery_sent:
                reason = "Already sent"
            else:
                reason = "Unknown reason"
        print(f"  - Reason: {reason}")
    
    # === SCENARIO 2: Có lỗi, chưa recovery ===
    print("\n" + "="*60)
    print("📊 SCENARIO 2: Đã có lỗi, service phục hồi lần đầu")
    print("="*60)
    
    manager2 = class_send_alert_of_thread(2)
    # Giả lập đã gửi error
    manager2.mark_webhook_error_sent()
    
    print(f"After error sent:")
    print(f"  - webhook_error_sent: {manager2.thread_webhook_error_sent}")
    print(f"  - webhook_recovery_sent: {manager2.thread_webhook_recovery_sent}")
    
    should_send = manager2.should_send_webhook_recovery()
    print(f"  - should_send_webhook_recovery(): {should_send}")
    
    if should_send:
        print("  - ✅ Should send recovery webhook")
        manager2.mark_webhook_recovery_sent()
        print("  - Marked recovery as sent")
    
    # === SCENARIO 3: Đã gửi recovery rồi ===
    print("\n" + "="*60)
    print("📊 SCENARIO 3: Service OK lại (đã gửi recovery rồi)")
    print("="*60)
    
    print(f"After recovery sent:")
    print(f"  - webhook_error_sent: {manager2.thread_webhook_error_sent}")
    print(f"  - webhook_recovery_sent: {manager2.thread_webhook_recovery_sent}")
    
    should_send = manager2.should_send_webhook_recovery()
    print(f"  - should_send_webhook_recovery(): {should_send}")
    
    if not should_send:
        with manager2._lock:
            if not manager2.thread_webhook_error_sent:
                reason = "No previous error sent"
            elif manager2.thread_webhook_recovery_sent:
                reason = "Already sent"
            else:
                reason = "Unknown reason"
        print(f"  - Reason: {reason}")
    
    # === SCENARIO 4: Chu kỳ lỗi mới ===
    print("\n" + "="*60)
    print("📊 SCENARIO 4: Chu kỳ lỗi mới (sau khi đã recovery)")
    print("="*60)
    
    # Giả lập lỗi mới
    manager2.mark_webhook_error_sent()
    
    print(f"After new error:")
    print(f"  - webhook_error_sent: {manager2.thread_webhook_error_sent}")
    print(f"  - webhook_recovery_sent: {manager2.thread_webhook_recovery_sent}")
    
    should_send = manager2.should_send_webhook_recovery()
    print(f"  - should_send_webhook_recovery(): {should_send}")
    
    if should_send:
        print("  - ✅ Ready for new recovery webhook")

def explain_logic():
    """Giải thích logic"""
    print("\n" + "="*60)
    print("📋 GIẢI THÍCH LOGIC WEBHOOK RECOVERY")
    print("="*60)
    
    print("🔍 should_send_webhook_recovery() trả về True chỉ khi:")
    print("   1. thread_webhook_error_sent = True  (đã có lỗi trước đó)")
    print("   2. thread_webhook_recovery_sent = False  (chưa gửi recovery)")
    print()
    print("❌ Trả về False trong các trường hợp:")
    print("   - Chưa có lỗi nào (error_sent = False)")
    print("   - Đã gửi recovery rồi (recovery_sent = True)")
    print()
    print("📊 Ý nghĩa messages:")
    print("   - 'No previous error sent': Service OK từ đầu, không cần recovery")
    print("   - 'Already sent': Đã gửi recovery cho lỗi trước đó rồi")
    print()
    print("✅ Logic này đảm bảo:")
    print("   - Chỉ gửi recovery khi thực sự cần (có lỗi trước đó)")
    print("   - Không gửi recovery trùng lặp")
    print("   - Mỗi lỗi chỉ có 1 recovery tương ứng")

if __name__ == "__main__":
    test_webhook_recovery_scenarios()
    explain_logic()
