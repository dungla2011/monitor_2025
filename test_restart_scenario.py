"""
Test scenario: Domain sai -> Webhook error -> Sửa domain -> Restart thread -> Check OK -> Webhook recovery?
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import class_send_alert_of_thread

def test_restart_recovery_scenario():
    """Test scenario người dùng hỏi"""
    print("🧪 Testing User Scenario...")
    print("="*80)
    
    # === BƯỚC 1: Domain sai - Thread chạy và gặp lỗi ===
    print("\n🔴 BƯỚC 1: Domain sai - Monitor check fail")
    manager = class_send_alert_of_thread(123)
    
    # Kiểm tra initial state
    print(f"   Initial state:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    print(f"   - can_send_error: {manager.should_send_webhook_error()}")
    print(f"   - can_send_recovery: {manager.should_send_webhook_recovery()}")
    
    # Monitor fail -> gửi webhook error
    if manager.should_send_webhook_error():
        manager.mark_webhook_error_sent()
        print(f"   ✅ Webhook ERROR sent!")
        print(f"   - error_sent: {manager.thread_webhook_error_sent}")
        print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # === BƯỚC 2: User sửa domain trong DB ===
    print(f"\n🔧 BƯỚC 2: User sửa domain trong database")
    print(f"   (Giả sử: domain từ 'wrong.com' -> 'correct.com')")
    print(f"   State trước khi restart:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    
    # === BƯỚC 3: Thread được restart (detect config change) ===
    print(f"\n🔄 BƯỚC 3: Thread restart (detect config change)")
    print(f"   monitor_service.py line 752: reset_webhook_flags() được gọi")
    
    # Simulate thread restart
    manager.reset_webhook_flags()
    print(f"   After reset:")
    print(f"   - error_sent: {manager.thread_webhook_error_sent}")
    print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")
    print(f"   - can_send_error: {manager.should_send_webhook_error()}")
    print(f"   - can_send_recovery: {manager.should_send_webhook_recovery()}")
    
    # === BƯỚC 4: Monitor check OK lần đầu ===
    print(f"\n✅ BƯỚC 4: Monitor check domain mới - SUCCESS")
    print(f"   Domain correct.com -> HTTP 200 OK")
    print(f"   Gọi send_webhook_notification(is_error=False)")
    
    # Logic từ monitor_service.py line 537-538
    can_send_recovery = manager.should_send_webhook_recovery()
    print(f"   should_send_webhook_recovery(): {can_send_recovery}")
    
    if not can_send_recovery:
        with manager._lock:
            if not manager.thread_webhook_error_sent:
                reason = "No previous error sent"
            elif manager.thread_webhook_recovery_sent:
                reason = "Already sent"
            else:
                reason = "Unknown reason"
        print(f"   🔕 Webhook recovery skipped: {reason}")
    else:
        manager.mark_webhook_recovery_sent()
        print(f"   🪝 Webhook RECOVERY sent!")
        print(f"   - error_sent: {manager.thread_webhook_error_sent}")
        print(f"   - recovery_sent: {manager.thread_webhook_recovery_sent}")

def test_should_send_webhook_recovery_logic():
    """Test chi tiết logic should_send_webhook_recovery"""
    print(f"\n" + "="*80)
    print(f"🔍 DETAILED ANALYSIS: should_send_webhook_recovery()")
    print(f"="*80)
    
    # Đọc logic từ utils.py
    print(f"\nLogic từ utils.py:")
    print(f"def should_send_webhook_recovery(self):")
    print(f"    with self._lock:")
    print(f"        # Chỉ gửi recovery nếu:")
    print(f"        # 1. Đã từng gửi error webhook")
    print(f"        # 2. Chưa gửi recovery webhook")
    print(f"        return (self.thread_webhook_error_sent and")
    print(f"               not self.thread_webhook_recovery_sent)")
    
    # Test các cases
    test_cases = [
        {
            "name": "Case 1: Chưa gửi error, chưa gửi recovery",
            "error_sent": False,
            "recovery_sent": False,
            "expected": False
        },
        {
            "name": "Case 2: Đã gửi error, chưa gửi recovery", 
            "error_sent": True,
            "recovery_sent": False,
            "expected": True
        },
        {
            "name": "Case 3: Đã gửi error, đã gửi recovery",
            "error_sent": True,
            "recovery_sent": True,
            "expected": False
        },
        {
            "name": "Case 4: Chưa gửi error, đã gửi recovery (không thể)",
            "error_sent": False,
            "recovery_sent": True,
            "expected": False
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}:")
        manager = class_send_alert_of_thread(999)
        
        # Set states
        with manager._lock:
            manager.thread_webhook_error_sent = case["error_sent"]
            manager.thread_webhook_recovery_sent = case["recovery_sent"]
        
        result = manager.should_send_webhook_recovery()
        status = "✅" if result == case["expected"] else "❌"
        
        print(f"   error_sent: {case['error_sent']}, recovery_sent: {case['recovery_sent']}")
        print(f"   should_send_recovery: {result} {status}")

if __name__ == "__main__":
    test_restart_recovery_scenario()
    test_should_send_webhook_recovery_logic()
    
    print(f"\n" + "="*80)
    print(f"🎯 KẾT LUẬN:")
    print(f"="*80)
    print(f"❌ KHÔNG GỬI webhook recovery!")
    print(f"")
    print(f"LÝ DO:")
    print(f"1. Thread restart -> reset_webhook_flags() -> error_sent = False")
    print(f"2. Monitor check OK -> should_send_webhook_recovery() check:")
    print(f"   - error_sent = False (vì đã reset)")
    print(f"   - recovery_sent = False")
    print(f"   - Điều kiện: error_sent AND not recovery_sent")
    print(f"   - False AND True = False")
    print(f"3. Webhook recovery bị skip với lý do 'No previous error sent'")
    print(f"")
    print(f"💡 ĐỀ XUẤT:")
    print(f"- Đây có thể là behavior mong muốn (thread mới = state sạch)")
    print(f"- Hoặc cần modify logic để track error state across restarts")
    print(f"- Tùy vào business requirement của bạn")
