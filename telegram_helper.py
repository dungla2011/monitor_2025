import requests
import json
import os
from datetime import datetime

def send_telegram_message(bot_token, chat_id, message):
    """
    Gửi tin nhắn đến Telegram chat
    
    Args:
        bot_token (str): Bot token từ BotFather
        chat_id (str): Chat ID hoặc username (@channel_name)
        message (str): Nội dung tin nhắn
        
    Returns:
        dict: Kết quả gửi tin nhắn
            {
                'success': bool,
                'message': str,
                'response': dict or None
            }
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',  # Hỗ trợ HTML formatting
            'disable_web_page_preview': True  # Tắt preview của URL
        }
        
        # Kiểm tra proxy từ environment variables
        proxies = None
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
        
        try:
            response = requests.post(url, data=payload, timeout=15, proxies=proxies)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            return {
                'success': False,
                'message': f"Network error: {str(e)}",
                'response': None
            }
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('ok'):
                return {
                    'success': True,
                    'message': 'Message sent successfully',
                    'response': response_data
                }
            else:
                return {
                    'success': False,
                    'message': f"Telegram API error: {response_data.get('description', 'Unknown error')}",
                    'response': response_data
                }
        else:
            return {
                'success': False,
                'message': f"HTTP error: {response.status_code}",
                'response': None
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'message': 'Request timeout (15 seconds)',
            'response': None
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'message': 'Connection error - cannot reach Telegram API',
            'response': None
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'response': None
        }

def send_telegram_alert(bot_token, chat_id, service_name, url_admin, service_url, error_message, check_time=None):
    """
    Gửi cảnh báo monitor service đến Telegram
    
    Args:
        bot_token (str): Bot token
        chat_id (str): Chat ID
        service_name (str): Tên dịch vụ
        service_url (str): URL dịch vụ
        error_message (str): Lỗi chi tiết
        check_time (datetime, optional): Thời gian kiểm tra
        
    Returns:
        dict: Kết quả gửi tin nhắn
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Format tin nhắn với HTML
    message = f"""🚨 <b>SERVICE ALERT</b> 🚨

📊 <b>Service:</b> {service_name}
🌐 <b>URL:</b> {service_url}
❌ <b>Status:</b> DOWN
⚠️ <b>Error:</b> {error_message}
🕒 <b>Time:</b> {check_time.strftime('%Y-%m-%d %H:%M:%S')}
🔗 <b>Admin URL:</b> {url_admin}

Please check the service immediately!"""

    return send_telegram_message(bot_token, chat_id, message)

def send_telegram_recovery(bot_token, chat_id, service_name, url_admin, service_url, response_time, check_time=None):
    """
    Gửi thông báo phục hồi service đến Telegram
    
    Args:
        bot_token (str): Bot token
        chat_id (str): Chat ID
        service_name (str): Tên dịch vụ
        service_url (str): URL dịch vụ
        response_time (float): Thời gian phản hồi (ms)
        check_time (datetime, optional): Thời gian kiểm tra
        
    Returns:
        dict: Kết quả gửi tin nhắn
    """
    if check_time is None:
        check_time = datetime.now()
    
    # Format tin nhắn với HTML
    message = f"""✅ <b>SERVICE IS GOOD NOW</b> ✅

📊 <b>Service:</b> {service_name}
🌐 <b>URL:</b> {service_url}
✅ <b>Status:</b> UP
⚡ <b>Response Time:</b> {response_time:.2f}ms
🕒 <b>Time:</b> {check_time.strftime('%Y-%m-%d %H:%M:%S')}
🔗 <b>Admin URL:</b> {url_admin}

Service is back online! 🎉"""

    return send_telegram_message(bot_token, chat_id, message)

def test_telegram_connection(bot_token, chat_id):
    """
    Test kết nối Telegram
    
    Args:
        bot_token (str): Bot token
        chat_id (str): Chat ID
        
    Returns:
        dict: Kết quả test
    """
    test_message = f"🧪 Test message from Monitor System\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return send_telegram_message(bot_token, chat_id, test_message)

# Example usage
if __name__ == "__main__":
    # Test basic message
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    
    result = test_telegram_connection(bot_token, chat_id)
    print(f"Test result: {result}")
    
    # Test alert
    alert_result = send_telegram_alert(
        bot_token=bot_token,
        chat_id=chat_id,
        url_admin="https://admin.example.com",
        service_name="Test Service",
        service_url="https://example.com",
        error_message="Connection timeout"
    )
    print(f"Alert result: {alert_result}")
