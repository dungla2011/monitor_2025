"""
AsyncIO Webhook Notification System
Port của webhook_helper.py cho AsyncIO với aiohttp
"""

import aiohttp
import asyncio
import json
import time
from datetime import datetime
from utils import ol1, olerror, safe_get_env_bool, safe_get_env_int

# Webhook configuration
WEBHOOK_ENABLED = safe_get_env_bool('WEBHOOK_ENABLED', True)
WEBHOOK_TIMEOUT = safe_get_env_int('WEBHOOK_TIMEOUT', 10)
WEBHOOK_MAX_RETRIES = safe_get_env_int('WEBHOOK_MAX_RETRIES', 2)
WEBHOOK_THROTTLE_SECONDS = safe_get_env_int('WEBHOOK_THROTTLE_SECONDS', 30)


async def send_webhook_alert_async(webhook_url, service_name, service_url, error_message, 
                                  alert_type="error", monitor_id=None, consecutive_errors=0, 
                                  check_interval_seconds=300, webhook_name="Webhook"):
    """
    Gửi webhook alert async (equivalent của send_webhook_alert)
    
    Args:
        webhook_url: URL webhook endpoint
        service_name: Tên service 
        service_url: URL service bị lỗi
        error_message: Message lỗi
        alert_type: Loại alert ("error", "warning", etc)
        monitor_id: ID monitor item
        consecutive_errors: Số lỗi liên tiếp
        check_interval_seconds: Interval check (giây)
        webhook_name: Tên webhook để log
        
    Returns:
        bool: True nếu gửi thành công
    """
    if not WEBHOOK_ENABLED:
        return False
    
    if not webhook_url or not webhook_url.strip():
        ol1(f"⚠️ [Webhook] No webhook URL provided for monitor {monitor_id}")
        return False
    
    # Prepare payload (same format as threading version)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "alert_type": alert_type,
        "status": "down",
        "service": {
            "name": service_name,
            "url": service_url,
            "monitor_id": monitor_id
        },
        "error": {
            "message": error_message,
            "consecutive_count": consecutive_errors,
            "check_interval_seconds": check_interval_seconds
        },
        "metadata": {
            "source": "monitor_service_asyncio",
            "version": "2025.1",
            "webhook_name": webhook_name
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'MonitorService-AsyncIO/2025'
    }
    
    # Retry logic với exponential backoff
    for attempt in range(WEBHOOK_MAX_RETRIES + 1):
        try:
            if attempt > 0:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** (attempt - 1)
                ol1(f"🔄 [Webhook] Retry attempt {attempt} after {wait_time}s for {webhook_name}")
                await asyncio.sleep(wait_time)
            
            timeout = aiohttp.ClientTimeout(total=WEBHOOK_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if 200 <= response.status < 300:
                        ol1(f"✅ [Webhook] Alert sent successfully to {webhook_name} "
                            f"(status: {response.status}, attempt: {attempt + 1})")
                        return True
                    else:
                        ol1(f"⚠️ [Webhook] HTTP {response.status} from {webhook_name}: {response_text}")
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status < 500:
                            ol1(f"❌ [Webhook] Client error {response.status}, not retrying")
                            return False
                            
        except asyncio.TimeoutError:
            ol1(f"⏱️ [Webhook] Timeout after {WEBHOOK_TIMEOUT}s for {webhook_name} (attempt {attempt + 1})")
        except aiohttp.ClientError as e:
            ol1(f"🌐 [Webhook] Connection error to {webhook_name}: {str(e)} (attempt {attempt + 1})")
        except Exception as e:
            ol1(f"💥 [Webhook] Unexpected error sending to {webhook_name}: {str(e)} (attempt {attempt + 1})")
        
        # Continue to next retry attempt
        
    ol1(f"❌ [Webhook] Failed to send alert to {webhook_name} after {WEBHOOK_MAX_RETRIES + 1} attempts")
    return False


async def send_webhook_recovery_async(webhook_url, service_name, service_url, recovery_message,
                                     monitor_id=None, response_time=0, webhook_name="Webhook"):
    """
    Gửi webhook recovery notification async (equivalent của send_webhook_recovery)
    
    Args:
        webhook_url: URL webhook endpoint
        service_name: Tên service
        service_url: URL service đã phục hồi
        recovery_message: Message phục hồi
        monitor_id: ID monitor item
        response_time: Thời gian phản hồi (ms)
        webhook_name: Tên webhook để log
        
    Returns:
        bool: True nếu gửi thành công
    """
    if not WEBHOOK_ENABLED:
        return False
        
    if not webhook_url or not webhook_url.strip():
        ol1(f"⚠️ [Webhook] No webhook URL provided for monitor {monitor_id}")
        return False
    
    # Prepare recovery payload
    payload = {
        "timestamp": datetime.now().isoformat(),
        "alert_type": "recovery",
        "status": "up",
        "service": {
            "name": service_name,
            "url": service_url,
            "monitor_id": monitor_id
        },
        "recovery": {
            "message": recovery_message,
            "response_time_ms": response_time
        },
        "metadata": {
            "source": "monitor_service_asyncio",
            "version": "2025.1",
            "webhook_name": webhook_name
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'MonitorService-AsyncIO/2025'
    }
    
    # Retry logic
    for attempt in range(WEBHOOK_MAX_RETRIES + 1):
        try:
            if attempt > 0:
                wait_time = 2 ** (attempt - 1)
                ol1(f"🔄 [Webhook] Recovery retry attempt {attempt} after {wait_time}s for {webhook_name}")
                await asyncio.sleep(wait_time)
            
            timeout = aiohttp.ClientTimeout(total=WEBHOOK_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if 200 <= response.status < 300:
                        ol1(f"✅ [Webhook] Recovery sent successfully to {webhook_name} "
                            f"(status: {response.status}, attempt: {attempt + 1})")
                        return True
                    else:
                        ol1(f"⚠️ [Webhook] Recovery HTTP {response.status} from {webhook_name}: {response_text}")
                        
                        # Don't retry on client errors
                        if 400 <= response.status < 500:
                            ol1(f"❌ [Webhook] Client error {response.status}, not retrying")
                            return False
                            
        except asyncio.TimeoutError:
            ol1(f"⏱️ [Webhook] Recovery timeout after {WEBHOOK_TIMEOUT}s for {webhook_name} (attempt {attempt + 1})")
        except aiohttp.ClientError as e:
            ol1(f"🌐 [Webhook] Recovery connection error to {webhook_name}: {str(e)} (attempt {attempt + 1})")
        except Exception as e:
            ol1(f"💥 [Webhook] Recovery unexpected error to {webhook_name}: {str(e)} (attempt {attempt + 1})")
    
    ol1(f"❌ [Webhook] Failed to send recovery to {webhook_name} after {WEBHOOK_MAX_RETRIES + 1} attempts")
    return False


async def get_webhook_config_for_monitor_async(monitor_id):
    """
    Async version của get_webhook_config_for_monitor_raw
    """
    try:
        # Import here to avoid circular import
        from sql_helpers import get_webhook_config_for_monitor_raw
        
        # Use existing raw SQL function (it's already fast)
        loop = asyncio.get_event_loop()
        webhook_config = await loop.run_in_executor(None, get_webhook_config_for_monitor_raw, monitor_id)
        return webhook_config
    except Exception as e:
        ol1(f"❌ [Webhook] Error getting webhook config for monitor {monitor_id}: {e}")
        return None


async def send_webhook_notification_async(monitor_item, is_error=True, error_message="", response_time=None):
    """
    Main async webhook notification function (equivalent của send_webhook_notification)
    Tích hợp với alert manager để track webhook flags
    
    Args:
        monitor_item: MonitorItem object
        is_error (bool): True nếu là lỗi, False nếu là phục hồi
        error_message (str): Thông báo lỗi
        response_time (float): Thời gian phản hồi (ms) cho trường hợp phục hồi
    """
    try:
        # Import here to avoid circular import
        from async_alert_manager import get_alert_manager
        
        thread_id = monitor_item.id
        # Get allow_alert_for_consecutive_error from monitor_item (default to None if not present)
        allow_consecutive = getattr(monitor_item, 'allow_alert_for_consecutive_error', None)
        alert_manager = await get_alert_manager(thread_id, monitor_item.id, allow_consecutive)
        
        # Get webhook config
        webhook_config = await get_webhook_config_for_monitor_async(monitor_item.id)
        if not webhook_config:
            return  # No webhook config
        
        webhook_url = webhook_config['webhook_url']
        webhook_name = webhook_config['webhook_name']
        
        # Kiểm tra user alert time settings trước khi gửi
        user_id = monitor_item.user_id if monitor_item.user_id else 0
        
        # Import is_alert_time_allowed_async from telegram notification module
        from async_telegram_notification import is_alert_time_allowed_async
        is_allowed, reason = await is_alert_time_allowed_async(user_id)
        
        if not is_allowed:
            ol1(f"🔕 [AsyncIO {thread_id}] Webhook alert blocked for user {user_id}: {reason}", monitor_item)
            return
        else:
            ol1(f"✅ [AsyncIO {thread_id}] Webhook alert allowed for user {user_id}: {reason}", monitor_item)
        
        if is_error:
            # Basic throttling (30 giây giữa các webhook notification giống nhau)
            if not await alert_manager.can_send_webhook_alert(WEBHOOK_THROTTLE_SECONDS):
                # current_time = time.time()
                # remaining = WEBHOOK_THROTTLE_SECONDS - (current_time - alert_manager.thread_webhook_last_sent_alert)
                # ol1(f"🔇 [AsyncIO {thread_id}] Webhook throttle active {WEBHOOK_THROTTLE_SECONDS}s ({remaining:.0f}s remaining)", monitor_item)
                return
            
            consecutive_errors = await alert_manager.get_consecutive_error_count()
            enhanced_error_message = f"{error_message} (Consecutive Error {consecutive_errors})"
            
            result = await send_webhook_alert_async(
                webhook_url=webhook_url,
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                error_message=enhanced_error_message,
                alert_type="error",
                monitor_id=monitor_item.id,
                consecutive_errors=consecutive_errors,
                check_interval_seconds=getattr(monitor_item, 'check_interval_seconds', 300),
                webhook_name=webhook_name
            )
            
            if result:
                # Cập nhật thời gian gửi webhook
                await alert_manager.mark_webhook_sent()
                ol1(f"🪝 [AsyncIO {thread_id}] webhook alert sent successfully to {webhook_name}", monitor_item)
            else:
                ol1(f"❌ [AsyncIO {thread_id}] webhook alert failed to {webhook_name}", monitor_item)
                
        else:
            # Recovery
            recovery_message = f"Service '{monitor_item.name}' is back online"
            if response_time:
                recovery_message += f" (Response time: {response_time:.0f}ms)"
            
            result = await send_webhook_recovery_async(
                webhook_url=webhook_url,
                service_name=monitor_item.name,
                service_url=monitor_item.url_check,
                recovery_message=recovery_message,
                monitor_id=monitor_item.id,
                response_time=response_time or 0,
                webhook_name=webhook_name
            )
            
            if result:
                ol1(f"🪝 [AsyncIO {thread_id}] Webhook recovery sent successfully to {webhook_name}", monitor_item)
            else:
                ol1(f"❌ [AsyncIO {thread_id}] Webhook recovery failed to {webhook_name}", monitor_item)
                
    except Exception as e:
        ol1(f"❌ [AsyncIO {monitor_item.id}] Webhook notification error: {e}", monitor_item)


async def test_webhook_connection_async(webhook_url, webhook_name="Test Webhook"):
    """
    Test webhook connection (AsyncIO version)
    
    Args:
        webhook_url (str): Webhook URL
        webhook_name (str): Webhook name for logging
        
    Returns:
        dict: Test result
    """
    test_payload = {
        "timestamp": datetime.now().isoformat(),
        "alert_type": "test",
        "status": "test",
        "service": {
            "name": "Test Service",
            "url": "https://example.com",
            "monitor_id": 999
        },
        "test": {
            "message": "Test webhook from AsyncIO Monitor System"
        },
        "metadata": {
            "source": "monitor_service_asyncio",
            "version": "2025.1",
            "webhook_name": webhook_name
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'MonitorService-AsyncIO/2025'
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=WEBHOOK_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(webhook_url, json=test_payload, headers=headers) as response:
                response_text = await response.text()
                
                return {
                    'success': 200 <= response.status < 300,
                    'status_code': response.status,
                    'message': f"HTTP {response.status}",
                    'response': response_text,
                    'webhook_name': webhook_name
                }
                
    except asyncio.TimeoutError:
        return {
            'success': False,
            'status_code': 0,
            'message': f"Timeout after {WEBHOOK_TIMEOUT}s",
            'response': None,
            'webhook_name': webhook_name
        }
    except aiohttp.ClientError as e:
        return {
            'success': False,
            'status_code': 0,
            'message': f"Connection error: {str(e)}",
            'response': None,
            'webhook_name': webhook_name
        }
    except Exception as e:
        return {
            'success': False,
            'status_code': 0,
            'message': f"Unexpected error: {str(e)}",
            'response': None,
            'webhook_name': webhook_name
        }


# Example usage
if __name__ == "__main__":
    async def main():
        # Test webhook
        webhook_url = "https://httpbin.org/post"
        result = await test_webhook_connection_async(webhook_url, "Test Webhook")
        print(f"Test result: {result}")
    
    asyncio.run(main())