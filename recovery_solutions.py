"""
Giải pháp để gửi webhook recovery sau restart thread
"""

# OPTION 1: Lưu error state vào database
def reset_webhook_flags_with_persistence(self):
    """Reset flags nhưng lưu lại error state"""
    with self._lock:
        # Lưu vào DB hoặc persistent storage
        if self.thread_webhook_error_sent:
            save_error_state_to_db(self.thread_id, True)
        
        self.thread_webhook_error_sent = False
        self.thread_webhook_recovery_sent = False

def should_send_webhook_recovery_with_persistence(self):
    """Check recovery với persistent state"""
    with self._lock:
        # Kiểm tra cả current thread và DB
        has_previous_error = (
            self.thread_webhook_error_sent or 
            get_error_state_from_db(self.thread_id)
        )
        
        return (has_previous_error and 
               not self.thread_webhook_recovery_sent)

# OPTION 2: Special flag cho restart recovery
def reset_webhook_flags_with_restart_flag(self):
    """Reset flags nhưng đánh dấu đây là restart"""
    with self._lock:
        if self.thread_webhook_error_sent:
            self.restart_after_error = True  # Flag đặc biệt
        
        self.thread_webhook_error_sent = False
        self.thread_webhook_recovery_sent = False

def should_send_webhook_recovery_after_restart(self):
    """Allow recovery ngay sau restart nếu trước đó có error"""
    with self._lock:
        return (
            (self.thread_webhook_error_sent or self.restart_after_error) and
            not self.thread_webhook_recovery_sent
        )

# OPTION 3: Config option
class AlertManager:
    def __init__(self, thread_id, send_recovery_after_restart=False):
        self.send_recovery_after_restart = send_recovery_after_restart
        # ... other init
    
    def should_send_webhook_recovery(self):
        with self._lock:
            if self.send_recovery_after_restart:
                # Gửi recovery cho success đầu tiên của thread mới
                return not self.thread_webhook_recovery_sent
            else:
                # Logic hiện tại
                return (self.thread_webhook_error_sent and 
                       not self.thread_webhook_recovery_sent)
