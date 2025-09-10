"""
Simple test for class_send_alert_of_thread without dependencies
"""

import time
import threading

class class_send_alert_of_thread:
    """
    Class quản lý alert cho mỗi monitor thread
    """
    
    def __init__(self, monitor_id):
        self.id = monitor_id
        self.thread_telegram_last_sent_alert = 0  # timestamp lần cuối gửi alert
        self.thread_count_consecutive_error = 0   # số lỗi liên tiếp
        self.thread_last_alert_time = 0          # timestamp alert cuối cùng
        self._lock = threading.Lock()            # Thread safety
    
    def can_send_telegram_alert(self, throttle_seconds=30):
        """
        Kiểm tra có thể gửi telegram alert không (dựa trên throttle time)
        """
        with self._lock:
            current_time = time.time()
            return current_time - self.thread_telegram_last_sent_alert >= throttle_seconds
    
    def mark_telegram_sent(self):
        """
        Đánh dấu đã gửi telegram alert
        """
        with self._lock:
            self.thread_telegram_last_sent_alert = time.time()
    
    def increment_consecutive_error(self):
        """
        Tăng số lỗi liên tiếp
        """
        with self._lock:
            self.thread_count_consecutive_error += 1
    
    def reset_consecutive_error(self):
        """
        Reset số lỗi liên tiếp về 0
        """
        with self._lock:
            self.thread_count_consecutive_error = 0
    
    def update_last_alert_time(self):
        """
        Cập nhật thời gian alert cuối cùng
        """
        with self._lock:
            self.thread_last_alert_time = time.time()
    
    def get_consecutive_error_count(self):
        """
        Lấy số lỗi liên tiếp hiện tại
        """
        with self._lock:
            return self.thread_count_consecutive_error
    
    def should_send_extended_alert(self, interval_minutes=5):
        """
        Kiểm tra có nên gửi extended alert không (sau khoảng thời gian dài)
        """
        with self._lock:
            current_time = time.time()
            return current_time - self.thread_last_alert_time >= (interval_minutes * 60)

def test_basic_functionality():
    """Test basic functionality"""
    print("🧪 Testing basic functionality...")
    
    manager = class_send_alert_of_thread(123)
    
    # Test initial state
    assert manager.id == 123
    assert manager.get_consecutive_error_count() == 0
    assert manager.can_send_telegram_alert()
    print("✅ Initial state correct")
    
    # Test increment errors
    manager.increment_consecutive_error()
    manager.increment_consecutive_error()
    assert manager.get_consecutive_error_count() == 2
    print("✅ Increment errors works")
    
    # Test telegram throttling
    manager.mark_telegram_sent()
    assert not manager.can_send_telegram_alert(throttle_seconds=1)
    time.sleep(1.1)
    assert manager.can_send_telegram_alert(throttle_seconds=1)
    print("✅ Telegram throttling works")
    
    # Test reset
    manager.reset_consecutive_error()
    assert manager.get_consecutive_error_count() == 0
    print("✅ Reset works")
    
    # Test extended alert
    manager.update_last_alert_time()
    assert not manager.should_send_extended_alert(interval_minutes=0.01)
    time.sleep(0.7)  # 0.7 seconds > 0.6 seconds (0.01 * 60)
    assert manager.should_send_extended_alert(interval_minutes=0.01)
    print("✅ Extended alert timing works")

def test_thread_safety():
    """Test thread safety"""
    print("\n🧪 Testing thread safety...")
    
    manager = class_send_alert_of_thread(456)
    results = []
    
    def worker():
        for _ in range(100):
            manager.increment_consecutive_error()
    
    threads = []
    for _ in range(5):  # 5 threads, each increment 100 times
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Should be exactly 500 (5 threads * 100 increments)
    final_count = manager.get_consecutive_error_count()
    assert final_count == 500, f"Expected 500, got {final_count}"
    print("✅ Thread safety works - all increments counted correctly")

if __name__ == "__main__":
    print("🚀 Testing class_send_alert_of_thread...")
    
    try:
        test_basic_functionality()
        test_thread_safety()
        print("\n🎉 All tests passed!")
        
        print("\n📋 Summary:")
        print("✅ Class initialization works")
        print("✅ Error counting works") 
        print("✅ Telegram throttling works")
        print("✅ Extended alert timing works")
        print("✅ Thread safety works")
        print("✅ Reset functionality works")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
