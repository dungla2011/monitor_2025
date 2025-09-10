"""
Webhook helper for Monitor Service
Gửi webhook alerts cho monitor service
"""

import requests
import json
from datetime import datetime
import os

def send_webhook_alert(webhook_url, service_name, service_url, error_message, alert_type="error", **kwargs):
    """
    Gửi webhook alert
    
    Args:
        webhook_url (str): URL webhook để gửi
        service_name (str): Tên service
        service_url (str): URL service đang monitor
        error_message (str): Message lỗi hoặc recovery
        alert_type (str): "error" hoặc "recovery"
        **kwargs: Các thông tin bổ sung
        
    Returns:
        bool: True nếu gửi thành công, False nếu lỗi
    """
    try:
        # Tạo payload webhook
        payload = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "service": {
                "name": service_name,
                "url": service_url
            },
            "message": error_message,
            "status": "down" if alert_type == "error" else "up"
        }
        
        # Thêm thông tin bổ sung nếu có
        if kwargs:
            payload.update(kwargs)
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'MonitorService/1.0',
        }
        
        # Gửi POST request
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10  # 10 seconds timeout
        )
        
        # Kiểm tra response
        if response.status_code in [200, 201, 202, 204]:
            print(f"✅ Webhook sent successfully to {webhook_url}")
            print(f"   Status: {response.status_code}")
            return True
        else:
            print(f"⚠️ Webhook responded with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Webhook timeout: {webhook_url}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Webhook connection error: {webhook_url}")
        return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

def send_webhook_recovery(webhook_url, service_name, service_url, recovery_message="Service is back online", **kwargs):
    """
    Gửi webhook recovery notification
    
    Args:
        webhook_url (str): URL webhook để gửi
        service_name (str): Tên service
        service_url (str): URL service đang monitor
        recovery_message (str): Message recovery
        **kwargs: Các thông tin bổ sung
        
    Returns:
        bool: True nếu gửi thành công, False nếu lỗi
    """
    return send_webhook_alert(
        webhook_url=webhook_url,
        service_name=service_name,
        service_url=service_url,
        error_message=recovery_message,
        alert_type="recovery",
        **kwargs
    )

def get_webhook_config_for_monitor_item(monitor_item_id):
    """
    Lấy cấu hình webhook cho một monitor item
    
    Args:
        monitor_item_id (int): ID của monitor item
        
    Returns:
        dict: {'webhook_url': str, 'webhook_name': str} hoặc None nếu không tìm thấy
    """
    try:
        from models import SessionLocal, MonitorConfig, MonitorAndConfig
        
        session = SessionLocal()
        
        # Join 3 bảng để lấy webhook config
        result = session.query(MonitorConfig.alert_config, MonitorConfig.name).join(
            MonitorAndConfig, MonitorConfig.id == MonitorAndConfig.config_id
        ).filter(
            MonitorAndConfig.monitor_item_id == monitor_item_id,
            MonitorConfig.alert_type == 'webhook'
        ).first()
        
        session.close()
        
        if not result or not result.alert_config:
            return None
            
        # Parse alert_config: webhook URL
        webhook_url = result.alert_config.strip()
        webhook_name = result.name or f"Webhook for Monitor {monitor_item_id}"
        
        # Validate URL format
        if not webhook_url.startswith(('http://', 'https://')):
            print(f"⚠️ Invalid webhook URL format: {webhook_url}")
            return None
            
        return {
            'webhook_url': webhook_url,
            'webhook_name': webhook_name
        }
        
    except Exception as e:
        print(f"❌ Error getting webhook config for monitor item {monitor_item_id}: {e}")
        return None

if __name__ == "__main__":
    # Test webhook functionality
    print("🧪 Testing webhook functionality...")
    
    # Test data
    test_webhook_url = "https://httpbin.org/post"  # Test endpoint
    test_service_name = "Test Service"
    test_service_url = "https://example.com"
    test_error = "Connection timeout after 30 seconds"
    
    print("\n📤 Testing error webhook...")
    result = send_webhook_alert(
        webhook_url=test_webhook_url,
        service_name=test_service_name,
        service_url=test_service_url,
        error_message=test_error,
        alert_type="error",
        monitor_id=123,
        consecutive_errors=1
    )
    print(f"Error webhook result: {result}")
    
    print("\n📤 Testing recovery webhook...")
    result = send_webhook_recovery(
        webhook_url=test_webhook_url,
        service_name=test_service_name,
        service_url=test_service_url,
        recovery_message="Service is back online",
        monitor_id=123,
        downtime_duration="5 minutes"
    )
    print(f"Recovery webhook result: {result}")
