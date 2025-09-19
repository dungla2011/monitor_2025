"""
AsyncIO Alert Manager for notification throttling and consecutive error tracking
Based on monitor_service.py's alert management but optimized for AsyncIO
"""

import asyncio
import time
from typing import Dict, Optional


class AsyncAlertManager:
    """AsyncIO-compatible alert manager for tracking notifications and errors"""
    
    def __init__(self, thread_id: int):
        self.thread_id = thread_id
        self.consecutive_error_count = 0
        self.thread_last_alert_time = 0
        self.thread_telegram_last_sent_alert = 0
        self._lock = asyncio.Lock()
    
    async def increment_consecutive_error(self):
        """Tăng counter lỗi liên tiếp"""
        async with self._lock:
            self.consecutive_error_count += 1
    
    async def reset_consecutive_error(self):
        """Reset counter lỗi liên tiếp"""
        async with self._lock:
            self.consecutive_error_count = 0
    
    async def get_consecutive_error_count(self) -> int:
        """Lấy số lỗi liên tiếp hiện tại"""
        async with self._lock:
            return self.consecutive_error_count
    
    async def can_send_telegram_alert(self, throttle_seconds: int) -> bool:
        """Kiểm tra có thể gửi telegram alert không (basic throttling)"""
        async with self._lock:
            current_time = time.time()
            return (current_time - self.thread_telegram_last_sent_alert) >= throttle_seconds
    
    async def mark_telegram_sent(self):
        """Đánh dấu đã gửi telegram alert"""
        async with self._lock:
            self.thread_telegram_last_sent_alert = time.time()
    
    async def update_last_alert_time(self):
        """Cập nhật thời gian alert cuối cùng"""
        async with self._lock:
            self.thread_last_alert_time = time.time()
    
    async def should_send_extended_alert(self, interval_minutes: int) -> bool:
        """Kiểm tra có nên gửi extended alert không"""
        async with self._lock:
            current_time = time.time()
            interval_seconds = interval_minutes * 60
            return (current_time - self.thread_last_alert_time) >= interval_seconds


class AsyncAlertManagerRegistry:
    """Registry quản lý các AsyncAlertManager instance"""
    
    def __init__(self):
        self._managers: Dict[int, AsyncAlertManager] = {}
        self._lock = asyncio.Lock()
    
    async def get_alert_manager(self, thread_id: int) -> AsyncAlertManager:
        """Lấy alert manager cho thread ID, tạo mới nếu chưa có"""
        async with self._lock:
            if thread_id not in self._managers:
                self._managers[thread_id] = AsyncAlertManager(thread_id)
            return self._managers[thread_id]
    
    async def cleanup_alert_manager(self, thread_id: int):
        """Cleanup alert manager khi không còn cần thiết"""
        async with self._lock:
            if thread_id in self._managers:
                del self._managers[thread_id]


# Global registry instance
alert_registry = AsyncAlertManagerRegistry()


async def get_alert_manager(thread_id: int) -> AsyncAlertManager:
    """Helper function để lấy alert manager"""
    return await alert_registry.get_alert_manager(thread_id)


async def cleanup_alert_manager(thread_id: int):
    """Helper function để cleanup alert manager"""
    await alert_registry.cleanup_alert_manager(thread_id)