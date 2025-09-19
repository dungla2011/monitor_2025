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
    Kiểm tra xem hiện tại có được phép gửi alert hay không dựa trên settings của user
    
    Args:
        user_id (int): ID của user
        
    Returns:
        tuple: (is_allowed: bool, reason: str)
    """
    try:
        from datetime import datetime
        import pytz
        
        # Get user monitor settings
        settings = await get_monitor_settings_for_user_async(user_id)
        if not settings:
            # Không có settings -> cho phép gửi (default behavior)
            return True, "No user settings found, allowing alerts"
        
        # Kiểm tra global_stop_alert_to
        if settings.get('global_stop_alert_to'):
            now_utc = datetime.utcnow()
            if now_utc < settings['global_stop_alert_to']:
                return False, f"Global alert stopped until {settings['global_stop_alert_to']}"
        
        # Kiểm tra alert_time_ranges
        if settings.get('alert_time_ranges'):
            # Xử lý timezone - có thể là số (GMT offset) hoặc string
            timezone_value = settings.get('timezone')
            if timezone_value is None:
                timezone_value = 7  # Default GMT+7
            
            # Convert timezone number to timezone string
            if isinstance(timezone_value, (int, float)):
                timezone_map = {
                    7: 'Asia/Ho_Chi_Minh',   # GMT+7 Vietnam, Laos, Cambodia
                    0: 'UTC',                # GMT+0 UTC
                    8: 'Asia/Shanghai',      # GMT+8 China, Singapore, Malaysia, Philippines
                    9: 'Asia/Tokyo',         # GMT+9 Japan, South Korea
                    5.5: 'Asia/Kolkata',     # GMT+5:30 India
                    6: 'Asia/Dhaka',         # GMT+6 Bangladesh
                    -5: 'America/New_York',  # GMT-5 EST (US East Coast)
                    -8: 'America/Los_Angeles', # GMT-8 PST (US West Coast)
                    -6: 'America/Chicago',   # GMT-6 CST (US Central)
                    1: 'Europe/Berlin',      # GMT+1 Central Europe
                    2: 'Europe/Helsinki',    # GMT+2 Eastern Europe
                    3: 'Europe/Moscow',      # GMT+3 Moscow
                    4: 'Asia/Dubai',         # GMT+4 UAE
                    5: 'Asia/Karachi',       # GMT+5 Pakistan
                    10: 'Australia/Sydney',  # GMT+10 Australia East
                }
                timezone_str = timezone_map.get(int(timezone_value), 'Asia/Ho_Chi_Minh')
                ol1(f"🌍 [AsyncIO] User {user_id} timezone: GMT+{timezone_value} -> {timezone_str}")
            elif isinstance(timezone_value, str):
                timezone_str = timezone_value
                ol1(f"🌍 [AsyncIO] User {user_id} timezone: {timezone_str}")
            else:
                timezone_str = 'Asia/Ho_Chi_Minh'
                ol1(f"⚠️ [AsyncIO] Unknown timezone format for user {user_id}: {timezone_value}, using default")
            
            try:
                tz = pytz.timezone(timezone_str)
                now_local = datetime.now(tz)
                current_time = now_local.strftime('%H:%M')
                
                # Parse alert_time_ranges: "05:30-23:00" hoặc "05:30-11:00,14:00-23:00" (multiple ranges)
                time_ranges = [r.strip() for r in settings['alert_time_ranges'].split(',')]
                
                is_in_allowed_time = False
                for time_range in time_ranges:
                    if '-' not in time_range:
                        continue
                        
                    start_time, end_time = time_range.split('-', 1)
                    start_time = start_time.strip()
                    end_time = end_time.strip()
                    
                    # Validate format H:M hoặc HH:MM
                    if ':' not in start_time or ':' not in end_time:
                        continue
                    
                    # Kiểm tra xem current_time có nằm trong range không
                    if start_time <= current_time <= end_time:
                        is_in_allowed_time = True
                        break
                
                if not is_in_allowed_time:
                    return False, f"Outside allowed time ranges: {settings['alert_time_ranges']} (current: {current_time} {timezone_str})"
                
            except Exception as tz_error:
                ol1(f"⚠️ [AsyncIO] Timezone error for user {user_id}: {tz_error}")
                # Lỗi timezone -> cho phép gửi để tránh miss alert
                return True, "Timezone error, allowing alerts"
        
        return True, "Alert allowed"
        
    except Exception as e:
        ol1(f"❌ [AsyncIO] Error checking alert time for user {user_id}: {e}")
        # Lỗi -> cho phép gửi để tránh miss alert quan trọng
        return True, "Error occurred, allowing alerts"


async def get_monitor_settings_for_user_async(user_id: int) -> Optional[Dict[str, Any]]:
    """
    AsyncIO version of get_monitor_settings_for_user
    Lấy monitor settings cho một user_id
    
    Args:
        user_id (int): ID của user
        
    Returns:
        dict: MonitorSettings data hoặc None nếu không tìm thấy
    """
    try:
        # Import async database modules
        import aiomysql
        import asyncpg
        from sql_helpers import get_database_config
        
        # Get database config
        db_config = get_database_config()
        
        conn = None
        if db_config['type'] == 'mysql':
            # MySQL async connection
            conn = await aiomysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                db=db_config['database'],
                charset='utf8mb4',
                autocommit=True
            )
            cursor = await conn.cursor()
            
            # Execute query
            await cursor.execute("""
                SELECT user_id, timezone, alert_time_ranges, global_stop_alert_to
                FROM monitor_settings 
                WHERE user_id = %s AND deleted_at IS NULL
                LIMIT 1
            """, (user_id,))
            
            row = await cursor.fetchone()
            await cursor.close()
            conn.close()
            
        else:
            # PostgreSQL async connection
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database']
            )
            
            # Execute query
            row = await conn.fetchrow("""
                SELECT user_id, timezone, alert_time_ranges, global_stop_alert_to
                FROM monitor_settings 
                WHERE user_id = $1 AND deleted_at IS NULL
                LIMIT 1
            """, user_id)
            
            await conn.close()
        
        if not row:
            return None
            
        # Convert row to dict
        if db_config['type'] == 'mysql':
            return {
                'user_id': row[0],
                'timezone': row[1],
                'alert_time_ranges': row[2],
                'global_stop_alert_to': row[3]
            }
        else:
            # PostgreSQL row already dict-like
            return dict(row)
        
    except Exception as e:
        ol1(f"❌ [AsyncIO] Error getting monitor settings for user {user_id}: {e}")
        if conn:
            try:
                if hasattr(conn, 'close'):
                    if asyncio.iscoroutinefunction(conn.close):
                        await conn.close()
                    else:
                        conn.close()
            except:
                pass
        return None


async def get_telegram_config_for_monitor_raw_async(monitor_id: int) -> Optional[Dict[str, Any]]:
    """
    AsyncIO version of get_telegram_config_for_monitor_raw
    Lấy cấu hình Telegram cho monitor item từ database
    
    Args:
        monitor_id (int): ID của monitor item
        
    Returns:
        dict: {'bot_token': str, 'chat_id': str} hoặc None
    """
    try:
        # Import async database modules
        import aiomysql
        import asyncpg
        from sql_helpers import get_database_config
        
        # Get database config
        db_config = get_database_config()
        
        conn = None
        if db_config['type'] == 'mysql':
            # MySQL async connection
            conn = await aiomysql.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                db=db_config['database'],
                charset='utf8mb4',
                autocommit=True
            )
            cursor = await conn.cursor()
            
            # Execute query
            await cursor.execute("""
                SELECT mc.alert_config, mc.name
                FROM monitor_configs mc
                JOIN monitor_and_configs mac ON mc.id = mac.config_id
                WHERE mac.monitor_item_id = %s 
                AND mc.alert_type = 'telegram'
                AND mc.deleted_at IS NULL
                LIMIT 1
            """, (monitor_id,))
            
            row = await cursor.fetchone()
            await cursor.close()
            conn.close()
            
        else:
            # PostgreSQL async connection
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database']
            )
            
            # Execute query
            row = await conn.fetchrow("""
                SELECT mc.alert_config, mc.name
                FROM monitor_configs mc
                JOIN monitor_and_configs mac ON mc.id = mac.config_id
                WHERE mac.monitor_item_id = $1 
                AND mc.alert_type = 'telegram'
                AND mc.deleted_at IS NULL
                LIMIT 1
            """, monitor_id)
            
            await conn.close()
        
        if not row or not row[0]:
            return None
            
        # Parse alert_config: <bot_token>,<chat_id>
        alert_config = row[0].strip()
        
        if ',' not in alert_config:
            return None
            
        parts = alert_config.split(',', 1)
        if len(parts) != 2:
            return None
            
        bot_token = parts[0].strip()
        chat_id = parts[1].strip()
        
        # Validate format
        if not bot_token or not chat_id:
            return None
            
        if ':' not in bot_token:
            return None
            
        if not (chat_id.lstrip('-').isdigit() or chat_id.startswith('@')):
            return None
            
        return {
            'bot_token': bot_token,
            'chat_id': chat_id
        }
        
    except Exception as e:
        ol1(f"❌ [AsyncIO {monitor_id}] Error getting telegram config: {e}")
        if conn:
            try:
                if hasattr(conn, 'close'):
                    if asyncio.iscoroutinefunction(conn.close):
                        await conn.close()
                    else:
                        conn.close()
            except:
                pass
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