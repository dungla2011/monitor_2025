"""
AsyncIO Firebase Helper - Send push notifications via Firebase Cloud Messaging (FCM)
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, List
import firebase_admin
from firebase_admin import credentials, messaging
from utils import ol1, olerror
from models import get_monitor_settings_for_user

# Global Firebase app instance
_firebase_app = None


async def get_firebase_token_for_user(user_id: int) -> Optional[str]:
    """
    Lấy Firebase token từ monitor_settings theo user_id
    
    Args:
        user_id (int): ID của user
        
    Returns:
        str: Firebase token hoặc None nếu không có
    """
    try:
        settings = get_monitor_settings_for_user(user_id)
        if settings and settings.firebase_token:
            return settings.firebase_token.strip()
        return None
    except Exception as e:
        olerror(f"❌ [Firebase] Error getting token for user {user_id}: {e}")
        return None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    Chỉ khởi tạo 1 lần duy nhất
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        # Đường dẫn đến service account JSON file
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase_service_account.json')
        
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Firebase service account file not found: {service_account_path}")
        
        # Khởi tạo Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        
        ol1(f"✅ [Firebase] Initialized successfully with service account: {service_account_path}")
        return _firebase_app
        
    except Exception as e:
        olerror(f"❌ [Firebase] Initialization failed: {e}")
        raise


async def send_firebase_notification_async(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict] = None,
    image_url: Optional[str] = None
) -> Dict:
    """
    Gửi push notification đến 1 device token (AsyncIO version)
    
    Args:
        token (str): Firebase device token (FCM token)
        title (str): Tiêu đề notification
        body (str): Nội dung notification
        data (dict, optional): Custom data payload
        image_url (str, optional): URL của ảnh hiển thị trong notification
        
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'message_id': str or None
        }
    """
    try:
        # Ensure Firebase is initialized
        initialize_firebase()
        
        # Tạo notification object
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url
        )
        
        # Tạo message
        message = messaging.Message(
            notification=notification,
            data=data or {},
            token=token,
            # Android specific options
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='monitor_alerts'  # Phải tạo channel này trong Android app
                )
            ),
            # iOS specific options
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        # Gửi message (blocking call, wrap trong executor)
        loop = asyncio.get_event_loop()
        message_id = await loop.run_in_executor(
            None,
            messaging.send,
            message
        )
        
        return {
            'success': True,
            'message': 'Notification sent successfully',
            'message_id': message_id
        }
        
    except firebase_admin.exceptions.FirebaseError as e:
        return {
            'success': False,
            'message': f'Firebase error: {e.code} - {e.message}',
            'message_id': None
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'message_id': None
        }


async def send_firebase_multicast_async(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict] = None,
    image_url: Optional[str] = None
) -> Dict:
    """
    Gửi push notification đến nhiều device tokens cùng lúc (AsyncIO version)
    
    Args:
        tokens (list): List of Firebase device tokens
        title (str): Tiêu đề notification
        body (str): Nội dung notification
        data (dict, optional): Custom data payload
        image_url (str, optional): URL của ảnh
        
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'success_count': int,
            'failure_count': int,
            'responses': list
        }
    """
    try:
        # Ensure Firebase is initialized
        initialize_firebase()
        
        # Tạo notification object
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url
        )
        
        # Tạo multicast message
        message = messaging.MulticastMessage(
            notification=notification,
            data=data or {},
            tokens=tokens,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='monitor_alerts'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        # Gửi multicast message (blocking call, wrap trong executor)
        loop = asyncio.get_event_loop()
        batch_response = await loop.run_in_executor(
            None,
            messaging.send_multicast,
            message
        )
        
        return {
            'success': batch_response.failure_count == 0,
            'message': f'Sent to {batch_response.success_count}/{len(tokens)} devices',
            'success_count': batch_response.success_count,
            'failure_count': batch_response.failure_count,
            'responses': [
                {
                    'success': resp.success,
                    'message_id': resp.message_id if resp.success else None,
                    'error': str(resp.exception) if not resp.success else None
                }
                for resp in batch_response.responses
            ]
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Multicast error: {str(e)}',
            'success_count': 0,
            'failure_count': len(tokens),
            'responses': []
        }


async def send_monitor_alert_firebase(
    user_id: int,
    monitor_name: str,
    monitor_url: str,
    error_message: str,
    monitor_id: int,
    admin_url: str
) -> Dict:
    """
    Gửi cảnh báo monitor qua Firebase (giống Telegram alert)
    
    Args:
        user_id (int): ID của user (để lấy Firebase token)
        monitor_name (str): Tên monitor
        monitor_url (str): URL được monitor
        error_message (str): Thông báo lỗi
        monitor_id (int): ID của monitor
        admin_url (str): Link đến trang admin
        
    Returns:
        dict: Result từ send_firebase_notification_async
    """
    # Lấy Firebase token từ user settings
    token = await get_firebase_token_for_user(user_id)
    if not token:
        return {
            'success': False,
            'message': f'No Firebase token found for user {user_id}',
            'message_id': None
        }
    title = f"🚨 ALERT: {monitor_name}"
    body = f"❌ {monitor_url}\n⚠️ {error_message}"
    
    # Custom data để app có thể handle (open specific screen, etc.)
    data = {
        'type': 'monitor_alert',
        'monitor_id': str(monitor_id),
        'monitor_name': monitor_name,
        'monitor_url': monitor_url,
        'error_message': error_message,
        'admin_url': admin_url,
        'timestamp': datetime.now().isoformat()
    }
    
    return await send_firebase_notification_async(
        token=token,
        title=title,
        body=body,
        data=data
    )


async def send_monitor_recovery_firebase(
    user_id: int,
    monitor_name: str,
    monitor_url: str,
    response_time: float,
    monitor_id: int,
    admin_url: str
) -> Dict:
    """
    Gửi thông báo phục hồi monitor qua Firebase (giống Telegram recovery)
    
    Args:
        user_id (int): ID của user (để lấy Firebase token)
        monitor_name (str): Tên monitor
        monitor_url (str): URL được monitor
        response_time (float): Thời gian phản hồi (ms)
        monitor_id (int): ID của monitor
        admin_url (str): Link đến trang admin
        
    Returns:
        dict: Result từ send_firebase_notification_async
    """
    # Lấy Firebase token từ user settings
    token = await get_firebase_token_for_user(user_id)
    if not token:
        return {
            'success': False,
            'message': f'No Firebase token found for user {user_id}',
            'message_id': None
        }
    title = f"✅ SERVICE OK: {monitor_name}"
    body = f"✅ {monitor_url}\n⚡ Response: {response_time:.1f}ms"
    
    # Custom data
    data = {
        'type': 'monitor_recovery',
        'monitor_id': str(monitor_id),
        'monitor_name': monitor_name,
        'monitor_url': monitor_url,
        'response_time': str(response_time),
        'admin_url': admin_url,
        'timestamp': datetime.now().isoformat()
    }
    
    return await send_firebase_notification_async(
        token=token,
        title=title,
        body=body,
        data=data
    )


async def test_firebase_notification():
    """Test Firebase notification"""
    test_token = os.getenv('FIREBASE_TEST_TOKEN')
    
    if not test_token:
        print("❌ FIREBASE_TEST_TOKEN not set in environment")
        return
    
    print("🧪 Testing Firebase notification...")
    
    result = await send_firebase_notification_async(
        token=test_token,
        title="🧪 Test Notification",
        body=f"Test from Monitor Service at {datetime.now().strftime('%H:%M:%S')}",
        data={'test': 'true'}
    )
    
    print(f"Result: {result}")


# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize Firebase
        initialize_firebase()
        
        # Test notification
        await test_firebase_notification()
    
    asyncio.run(main())
