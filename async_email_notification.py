"""
AsyncIO Email Notification Module
Handles email notifications via SMTP with throttling support
Independent from Telegram/Webhook/Firebase notifications

NOTE: Email chỉ gửi 1 lần, KHÔNG có consecutive error support (tránh bị coi là spam)
"""
import os
from utils import ol1, olerror, safe_get_env_int
from async_alert_manager import alert_registry


# Throttle settings - Read from environment variables
EMAIL_THROTTLE_SECONDS = safe_get_env_int('EMAIL_THROTTLE_SECONDS', 300)  # 5 phút default (cao hơn Telegram/Firebase để tránh spam)


async def send_email_notification_async(monitor_item, is_error: bool, error_message: str = None, response_time: float = None):
    """
    Send Email notification for monitor alerts/recovery
    Works independently from Telegram/Webhook/Firebase notifications
    Includes throttling logic to prevent spam
    
    IMPORTANT: Email chỉ gửi 1 lần đầu lỗi, KHÔNG gửi consecutive errors (tránh bị coi là spam)
    
    Args:
        monitor_item: Monitor object with configuration (dict or object)
        is_error: True for alert, False for recovery
        error_message: Error message for alerts
        response_time: Response time for recovery notifications
        
    Returns:
        dict: Result with success status
    """
    try:
        # Get values using getattr (works with both dict and object)
        thread_id = monitor_item.id
        
        # Get alert manager for throttling
        alert_manager = await alert_registry.get_alert_manager(
            thread_id=thread_id,
            monitor_id=monitor_item.id,
            allow_consecutive_alert=None  # Will use EMAIL_THROTTLE_ENABLED (always True)
        )
        
        # Check if we should send Email alert (with throttling)
        if is_error:
            # Check throttle before sending (5 phút throttle - cao hơn Telegram 30s)
            if not await alert_manager.can_send_email_alert(EMAIL_THROTTLE_SECONDS):
                return {'success': False, 'message': 'Email alert throttled'}
        
        # Get user_id from monitor_item
        user_id = getattr(monitor_item, 'user_id', None) or monitor_item.user_id
        
        if not user_id:
            ol1(f"⚠️ [Email] No user_id found for monitor {monitor_item.id}", monitor_item)
            return {'success': False, 'message': 'No user_id found'}
        
        # Import inside function to avoid circular imports
        from async_email_helper import send_monitor_alert_email, send_monitor_recovery_email
        
        # Get admin domain from env
        admin_domain = os.getenv('ADMIN_DOMAIN', 'mon.lad.vn')
        admin_url = f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}"
        
        if is_error:
            # Send error alert via Email
            result = await send_monitor_alert_email(
                user_id=user_id,
                monitor_name=monitor_item.name,
                monitor_url=monitor_item.url_check,
                error_message=error_message,
                monitor_id=monitor_item.id,
                admin_url=admin_url
            )
            
            # Mark as sent if successful
            if result.get('success'):
                await alert_manager.mark_email_sent()
                account = result.get('account', 'N/A')
                ol1(f"✅ [Email] Alert sent for monitor {monitor_item.id} via {account}", monitor_item)
            else:
                # Chỉ log lỗi nếu không phải "No email found"
                if 'No email found' not in result.get('message', ''):
                    ol1(f"❌ [Email] Alert failed for monitor {monitor_item.id}: {result.get('message')}", monitor_item)
            
        else:
            # Send recovery notification via Email (no throttling for recovery)
            result = await send_monitor_recovery_email(
                user_id=user_id,
                monitor_name=monitor_item.name,
                monitor_url=monitor_item.url_check,
                response_time=response_time or 0,
                monitor_id=monitor_item.id,
                admin_url=admin_url
            )
            
            if result.get('success'):
                account = result.get('account', 'N/A')
                ol1(f"✅ [Email] Recovery sent for monitor {monitor_item.id} via {account}", monitor_item)
            else:
                # Chỉ log lỗi nếu không phải "No email found"
                if 'No email found' not in result.get('message', ''):
                    ol1(f"❌ [Email] Recovery failed for monitor {monitor_item.id}: {result.get('message')}", monitor_item)
        
        return result
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        olerror(f"❌ [Email] Notification exception for monitor {monitor_item.id}: {e}")
        ol1(f"📍 Traceback:\n{error_traceback}", monitor_item)
        return {'success': False, 'message': str(e)}
