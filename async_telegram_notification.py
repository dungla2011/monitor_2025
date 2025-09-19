"""
AsyncIO Telegram Notification Module
Port of monitor_service.py telegram notification logic to AsyncIO
"""

import asyncio
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any

from async_telegram_helper import send_telegram_alert_async, send_telegram_recovery_async
from async_alert_manager import get_alert_manager
from utils import ol1, olerror, safe_get_env_int, safe_get_env_bool


# Throttle settings - Read from environment variables
TELEGRAM_THROTTLE_SECONDS = safe_get_env_int('TELEGRAM_THROTTLE_SECONDS', 30)
CONSECUTIVE_ERROR_THRESHOLD = safe_get_env_int('CONSECUTIVE_ERROR_THRESHOLD', 10)
EXTENDED_ALERT_INTERVAL_MINUTES = safe_get_env_int('EXTENDED_ALERT_INTERVAL_MINUTES', 5)


async def send_telegram_notification_async(monitor_item, is_error=True, error_message="", response_time=None):
    """
    Gửi thông báo Telegram với logic lỗi liên tiếp và giãn alert (AsyncIO version)
    
    Args:
        monitor_item: MonitorItem object
        is_error (bool): True nếu là lỗi, False nếu là phục hồi
        error_message (str): Thông báo lỗi
        response_time (float): Thời gian phản hồi (ms) cho trường hợp phục hồi
    """
    try:
        thread_id = monitor_item.id
        current_time = time.time()
        alert_manager = await get_alert_manager(thread_id)
        
        # Xử lý logic lỗi liên tiếp
        if is_error:
            # Tăng counter lỗi liên tiếp
            await alert_manager.increment_consecutive_error()
            consecutive_errors = await alert_manager.get_consecutive_error_count()
            
            ol1(f"📊 [AsyncIO {thread_id}] Consecutive errors: {consecutive_errors}")
            
            # Kiểm tra check interval
            check_interval_seconds = monitor_item.check_interval_seconds if monitor_item.check_interval_seconds else 300
            check_interval_minutes = check_interval_seconds / 60
            
            # Logic giãn alert nếu:
            # 1. Check interval < 5 phút
            # 2. Lỗi liên tiếp >= 10 lần
            # 3. EXTENDED_ALERT_INTERVAL_MINUTES > 0
            should_throttle_extended = (
                check_interval_minutes < 5 and
                consecutive_errors > CONSECUTIVE_ERROR_THRESHOLD and
                EXTENDED_ALERT_INTERVAL_MINUTES > 0
            )
            
            if should_throttle_extended:
                # Kiểm tra thời gian gửi alert cuối cùng
                if not await alert_manager.should_send_extended_alert(EXTENDED_ALERT_INTERVAL_MINUTES):
                    time_since_last_alert = current_time - alert_manager.thread_last_alert_time
                    remaining_minutes = (EXTENDED_ALERT_INTERVAL_MINUTES * 60 - time_since_last_alert) / 60
                    ol1(f"🔕 [AsyncIO {thread_id}] Extended alert throttle active ({remaining_minutes:.1f}m remaining)", monitor_item)
                    return
                
                ol1(f"⚠️ [AsyncIO {thread_id}] Throttled alert (every {EXTENDED_ALERT_INTERVAL_MINUTES}m, {CONSECUTIVE_ERROR_THRESHOLD} consecutive errs)", monitor_item)
        
        else:
            # Phục hồi - reset counter lỗi liên tiếp
            consecutive_errors = await alert_manager.get_consecutive_error_count()
            if consecutive_errors > 0:
                await alert_manager.reset_consecutive_error()
                ol1(f"✅ [AsyncIO {thread_id}] Service recovered! Reset consecutive error count (was: {consecutive_errors})", monitor_item)
        
        # Kiểm tra user alert time settings trước khi gửi
        user_id = monitor_item.user_id if monitor_item.user_id else 0
        is_allowed, reason = await is_alert_time_allowed_async(user_id)
        
        if not is_allowed:
            ol1(f"🔕 [AsyncIO {thread_id}] Alert blocked for user {user_id}: {reason}", monitor_item)
            return
        else:
            ol1(f"✅ [AsyncIO {thread_id}] Alert allowed for user {user_id}: {reason}", monitor_item)

        # Lấy config Telegram
        telegram_config = await get_telegram_config_for_monitor_raw_async(monitor_item.id)
        
        if not telegram_config:
            # Fallback to .env config
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                ol1(f"⚠️ [AsyncIO {thread_id}] No Telegram config found (database or .env)", monitor_item)
                return
        else:
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config['chat_id']
            ol1(f"📱 [AsyncIO {thread_id}] Using database Telegram config", monitor_item)
        
        # Basic throttling (30 giây giữa các notification giống nhau)
        if not await alert_manager.can_send_telegram_alert(TELEGRAM_THROTTLE_SECONDS):
            remaining = TELEGRAM_THROTTLE_SECONDS - (current_time - alert_manager.thread_telegram_last_sent_alert)
            ol1(f"🔇 [AsyncIO {thread_id}] Basic throttle active {TELEGRAM_THROTTLE_SECONDS} ({remaining:.0f}s remaining)", monitor_item)
            return
        
        # Cập nhật thời gian gửi
        await alert_manager.mark_telegram_sent()
        if is_error:
            await alert_manager.update_last_alert_time()
        
        # Gửi notification
        if is_error:
            consecutive_errors = await alert_manager.get_consecutive_error_count()
            enhanced_error_message = f"{error_message} (Lỗi liên tiếp: {consecutive_errors})"
            
            admin_domain = os.getenv('ADMIN_DOMAIN', 'monitor.mytree.vn')
            result = await send_telegram_alert_async(
                bot_token=bot_token,
                chat_id=chat_id,
                url_admin=f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}",
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                error_message=enhanced_error_message
            )
            if result['success']:
                ol1(f"📱 [AsyncIO {thread_id}] Telegram alert sent successfully", monitor_item)
            else:
                ol1(f"❌ [AsyncIO {thread_id}] Telegram alert failed: {result['message']}", monitor_item)
                olerror(f"Telegram alert error details: {result}")
        else:
            admin_domain = os.getenv('ADMIN_DOMAIN', 'monitor.mytree.vn')
            result = await send_telegram_recovery_async(
                bot_token=bot_token,
                chat_id=chat_id,
                service_name=monitor_item.name,
                url_admin=f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}",
                service_url=monitor_item.url_check,
                response_time=response_time or 0
            )
            if result['success']:
                ol1(f"📱 [AsyncIO {thread_id}] Telegram recovery notification sent successfully", monitor_item)
            else:
                ol1(f"❌ [AsyncIO {thread_id}] Telegram recovery notification failed: {result['message']}", monitor_item)
                olerror(f"Telegram recovery error details: {result}")
                
    except Exception as e:
        ol1(f"❌ [AsyncIO {monitor_item.id}] Telegram notification error: {e}", monitor_item)


async def is_alert_time_allowed_async(user_id: int) -> tuple:
    """
    AsyncIO version of is_alert_time_allowed
    For now, returns (True, "AsyncIO implementation") as placeholder
    TODO: Implement actual user alert time checking logic
    """
    # TODO: Implement async database query for user alert time settings
    # This would need to query the database for user's alert time preferences
    return (True, "AsyncIO implementation - always allowed for now")


async def get_telegram_config_for_monitor_raw_async(monitor_id: int) -> Optional[Dict[str, Any]]:
    """
    AsyncIO version of get_telegram_config_for_monitor_raw
    For now, returns None to fallback to .env config
    TODO: Implement actual async database query for telegram config
    """
    # TODO: Implement async database query for telegram configuration
    # This would need to query the database for monitor-specific telegram settings
    return None


async def reset_consecutive_error_on_enable(monitor_id: int):
    """
    Reset consecutive error count khi monitor được enable lại (enable=0 → enable=1)
    Điều này đảm bảo monitor không bị alert ngay lập tức với số lỗi cũ
    
    Args:
        monitor_id (int): ID của monitor được enable lại
    """
    try:
        alert_manager = await get_alert_manager(monitor_id)
        consecutive_errors = await alert_manager.get_consecutive_error_count()
        
        if consecutive_errors > 0:
            await alert_manager.reset_consecutive_error()
            ol1(f"🔄 [AsyncIO {monitor_id}] Reset consecutive error count on re-enable (was: {consecutive_errors})")
        else:
            ol1(f"🔄 [AsyncIO {monitor_id}] Monitor re-enabled, consecutive error count already 0")
    except Exception as e:
        olerror(f"[AsyncIO {monitor_id}] Error resetting consecutive error count: {e}")