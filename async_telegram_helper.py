"""
AsyncIO Telegram Helper - Async version of telegram notifications
Based on telegram_helper.py but with full AsyncIO implementation
"""

import aiohttp
import asyncio
import json
import os
from datetime import datetime
from utils import ol1, format_response_time, safe_get_env_int, safe_get_env_bool


async def send_telegram_message_async(bot_token: str, chat_id: str, message: str):
    """
    Gửi tin nhắn đến Telegram chat (AsyncIO version)
    
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
        if not chat_id or not bot_token:
            return {
                'success': False,
                'message': 'Missing bot token or chat ID',
                'response': None
            }
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',  # Hỗ trợ HTML formatting
            'disable_web_page_preview': True  # Tắt preview của URL
        }
        
        # Kiểm tra proxy từ environment variables
        proxy = None
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        if https_proxy:
            proxy = https_proxy
        elif http_proxy:
            proxy = http_proxy
        
        # Tạo connector với proxy nếu có
        connector = None
        if proxy:
            connector = aiohttp.TCPConnector()
        
        timeout = aiohttp.ClientTimeout(total=15)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Gửi request với proxy nếu có
            if proxy:
                async with session.post(url, data=payload, proxy=proxy) as response:
                    response_text = await response.text()
            else:
                async with session.post(url, data=payload) as response:
                    response_text = await response.text()
            
            if response.status == 200:
                try:
                    response_data = json.loads(response_text)
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
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'message': f"Invalid JSON response: {response_text}",
                        'response': None
                    }
            else:
                return {
                    'success': False,
                    'message': f"HTTP error: {response.status}",
                    'response': None
                }
                
    except asyncio.TimeoutError:
        return {
            'success': False,
            'message': 'Request timeout (15 seconds)',
            'response': None
        }
    except aiohttp.ClientError as e:
        return {
            'success': False,
            'message': f'Network error: {str(e)}',
            'response': None
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Unexpected error: {str(e)}',
            'response': None
        }


async def send_telegram_alert_async(bot_token: str, chat_id: str, service_name: str, 
                                   url_admin: str, service_url: str, error_message: str, 
                                   check_time=None):
    """
    Gửi cảnh báo monitor service đến Telegram (AsyncIO version)
    
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

    return await send_telegram_message_async(bot_token, chat_id, message)


async def send_telegram_recovery_async(bot_token: str, chat_id: str, service_name: str, 
                                      url_admin: str, service_url: str, response_time: float, 
                                      check_time=None):
    """
    Gửi thông báo phục hồi service đến Telegram (AsyncIO version)
    
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

    return await send_telegram_message_async(bot_token, chat_id, message)


async def test_telegram_connection_async(bot_token: str, chat_id: str):
    """
    Test kết nối Telegram (AsyncIO version)
    
    Args:
        bot_token (str): Bot token
        chat_id (str): Chat ID
        
    Returns:
        dict: Kết quả test
    """
    test_message = f"🧪 Test message from AsyncIO Monitor System\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return await send_telegram_message_async(bot_token, chat_id, test_message)


# Example usage
if __name__ == "__main__":
    async def main():
        # Test basic message
        bot_token = "YOUR_BOT_TOKEN"
        chat_id = "YOUR_CHAT_ID"
        
        result = await test_telegram_connection_async(bot_token, chat_id)
        print(f"Test result: {result}")
        
        # Test alert
        alert_result = await send_telegram_alert_async(
            bot_token=bot_token,
            chat_id=chat_id,
            url_admin="https://admin.example.com",
            service_name="Test Service",
            service_url="https://example.com",
            error_message="Connection timeout"
        )
        print(f"Alert result: {alert_result}")
    
    asyncio.run(main())