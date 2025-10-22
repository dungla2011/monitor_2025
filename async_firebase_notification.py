"""
AsyncIO Firebase Notification Module
Handles Firebase Cloud Messaging notifications with throttling support
Independent from Telegram/Webhook notifications
"""
import os
from utils import ol1, olerror, safe_get_env_int
from async_alert_manager import alert_registry


# Throttle settings - Read from environment variables
FIREBASE_THROTTLE_SECONDS = safe_get_env_int('FIREBASE_THROTTLE_SECONDS', 30)


async def send_firebase_notification_async(monitor_item, is_error: bool, error_message: str = None, response_time: float = None):
    """
    Send Firebase notification for monitor alerts/recovery
    Works independently from Telegram/Webhook notifications
    Includes throttling logic to prevent spam
    
    Args:
        monitor_item: Monitor object with configuration (dict or object)
        is_error: True for alert, False for recovery
        error_message: Error message for alerts
        response_time: Response time for recovery notifications
        
    Returns:
        dict: Result with success status and message IDs
    """
    try:
        # Get values using getattr (works with both dict and object)
        thread_id = monitor_item.id
        allow_consecutive = getattr(monitor_item, 'allow_alert_for_consecutive_error', None)
        
        # Get alert manager for throttling
        alert_manager = await alert_registry.get_alert_manager(
            thread_id=thread_id,
            monitor_id=monitor_item.id,
            allow_consecutive_alert=allow_consecutive
        )
        
        # Check if we should send Firebase alert (with throttling)
        if is_error:
            # Check throttle before sending (giống Telegram - 30 giây throttle)
            if not await alert_manager.can_send_firebase_alert(FIREBASE_THROTTLE_SECONDS):
                return {'success': False, 'message': 'Firebase alert throttled'}
        
        # Get user_id from monitor_item
        user_id = getattr(monitor_item, 'user_id', None) or monitor_item.user_id
        
        if not user_id:
            ol1(f"⚠️ [Firebase] No user_id found for monitor {monitor_item.id}", monitor_item)
            return {'success': False, 'message': 'No user_id found'}
        
        # Import inside function to avoid circular imports
        from async_firebase_helper import send_monitor_alert_firebase, send_monitor_recovery_firebase
        
        # Get admin domain from env
        admin_domain = os.getenv('ADMIN_DOMAIN', 'mon.lad.vn')
        admin_url = f"https://{admin_domain}/member/monitor-item/edit/{monitor_item.id}"
        
        if is_error:
            # Send error alert via Firebase
            result = await send_monitor_alert_firebase(
                user_id=user_id,
                monitor_name=monitor_item.name,
                monitor_url=monitor_item.url_check,
                error_message=error_message,
                monitor_id=monitor_item.id,
                admin_url=admin_url
            )
            
            # Mark as sent if successful
            if result.get('success'):
                await alert_manager.mark_firebase_sent()
                message_id_1 = result.get('message_id_1', 'N/A')[:20]
                message_id_2 = result.get('message_id_2', 'N/A')[:20]
                ol1(f"✅ [Firebase] Alert sent for monitor {monitor_item.id} [Msg1: {message_id_1}..., Msg2: {message_id_2}...]", monitor_item)
            else:
                ol1(f"❌ [Firebase] Alert failed for monitor {monitor_item.id}: {result.get('message')}", monitor_item)
            
        else:
            # Send recovery notification via Firebase (no throttling for recovery)
            result = await send_monitor_recovery_firebase(
                user_id=user_id,
                monitor_name=monitor_item.name,
                monitor_url=monitor_item.url_check,
                response_time=response_time or 0,
                monitor_id=monitor_item.id,
                admin_url=admin_url
            )
            
            if result.get('success'):
                message_id_1 = result.get('message_id_1', 'N/A')[:20]
                message_id_2 = result.get('message_id_2', 'N/A')[:20]
                ol1(f"✅ [Firebase] Recovery sent for monitor {monitor_item.id} [Msg1: {message_id_1}..., Msg2: {message_id_2}...]", monitor_item)
            else:
                ol1(f"❌ [Firebase] Recovery failed for monitor {monitor_item.id}: {result.get('message')}", monitor_item)
        
        return result
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        olerror(f"❌ [Firebase] Notification exception for monitor {monitor_item.id}: {e}")
        ol1(f"📍 Traceback:\n{error_traceback}", monitor_item)
        return {'success': False, 'message': str(e)}
