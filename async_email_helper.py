"""
AsyncIO Email Helper
Handles email sending via SMTP (Gmail)
Similar to async_firebase_helper.py but for email
"""
import os
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
import aiosmtplib

from utils import ol1, olerror


# SMTP Configuration from environment
SMTP_ENABLED = os.getenv('SMTP_ENABLED', 'false').lower() == 'true'
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

# Multiple SMTP accounts (like PHP ClassMail1::$mAcc)
# Format: email,password (encrypted with dfh1b in PHP, plain in Python for now)
SMTP_ACCOUNTS = [
    {
        'email': os.getenv('SMTP_ACCOUNT_1_EMAIL', ''),
        'password': os.getenv('SMTP_ACCOUNT_1_PASSWORD', ''),
    },
    {
        'email': os.getenv('SMTP_ACCOUNT_2_EMAIL', ''),
        'password': os.getenv('SMTP_ACCOUNT_2_PASSWORD', ''),
    },
    {
        'email': os.getenv('SMTP_ACCOUNT_3_EMAIL', ''),
        'password': os.getenv('SMTP_ACCOUNT_3_PASSWORD', ''),
    },
]

# Filter out empty accounts
SMTP_ACCOUNTS = [acc for acc in SMTP_ACCOUNTS if acc['email'] and acc['password']]

SMTP_FROM_NAME = os.getenv('SMTP_FROM_NAME', 'Monitor Alert System')


def dfh1b(encrypted_str: str) -> str:
    """
    Placeholder for PHP's dfh1b() decryption function
    For now, return input as-is (you can implement actual decryption later)
    
    Args:
        encrypted_str: Encrypted password string
        
    Returns:
        str: Decrypted password (currently returns input)
    """
    # TODO: Implement actual decryption if needed
    # For now, store passwords plain in .env
    return encrypted_str


async def get_email_for_user(user_id: int) -> Optional[str]:
    """
    Lấy email từ bảng users (users.email where users.id = user_id)
    
    Args:
        user_id (int): User ID
        
    Returns:
        str: Email address hoặc None nếu không tìm thấy
    """
    try:
        import aiomysql
        import asyncpg
        from sql_helpers import get_database_config
        
        db_config = get_database_config()
        
        conn = None
        if db_config['type'] == 'mysql':
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
            await cursor.execute("""
                SELECT email 
                FROM users 
                WHERE id = %s AND deleted_at IS NULL
                LIMIT 1
            """, (user_id,))
            row = await cursor.fetchone()
            await cursor.close()
            conn.close()
            
            if row and row[0]:
                return row[0]
            return None
            
        else:  # PostgreSQL
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database']
            )
            
            TIMESCALEDB_SCHEMA = os.getenv('TIMESCALEDB_SCHEMA', 'glx_monitor_v2')
            await conn.execute(f"SET search_path TO {TIMESCALEDB_SCHEMA}, public")
            
            row = await conn.fetchrow("""
                SELECT email 
                FROM users 
                WHERE id = $1 AND deleted_at IS NULL
                LIMIT 1
            """, user_id)
            
            await conn.close()
            
            if row and row['email']:
                return row['email']
            return None
            
    except Exception as e:
        ol1(f"❌ [Email] Error getting email for user {user_id}: {e}")
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


async def send_email_async(to_email: str, subject: str, html_body: str, text_body: str = None) -> Dict:
    """
    Send email via SMTP using random account from SMTP_ACCOUNTS
    Similar to PHP ClassMail1::sendMail()
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_body: HTML content
        text_body: Plain text content (fallback)
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    if not SMTP_ENABLED:
        return {'success': False, 'message': 'SMTP is disabled'}
    
    if not SMTP_ACCOUNTS:
        return {'success': False, 'message': 'No SMTP accounts configured'}
    
    try:
        # Random account selection (like PHP: $rand = rand(0, count($mAcc) - 1))
        import random
        account = random.choice(SMTP_ACCOUNTS)
        smtp_user = account['email']
        smtp_password = dfh1b(account['password'])
        
        # Create message
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = f"{SMTP_FROM_NAME} <{smtp_user}>"
        message['To'] = to_email
        message['Reply-To'] = smtp_user
        
        # Add text and HTML parts
        if text_body:
            message.attach(MIMEText(text_body, 'plain', 'utf-8'))
        message.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # Send via SMTP
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=smtp_user,
            password=smtp_password,
            start_tls=SMTP_USE_TLS,  # Changed from use_tls to start_tls
            timeout=30
        )
        
        ol1(f"📧 [Email] Sent to {to_email} using account {smtp_user}")
        return {'success': True, 'message': 'Email sent successfully', 'account': smtp_user}
        
    except Exception as e:
        olerror(f"❌ [Email] Failed to send to {to_email}: {e}")
        return {'success': False, 'message': str(e)}


async def send_monitor_alert_email(
    user_id: int,
    monitor_name: str,
    monitor_url: str,
    error_message: str,
    monitor_id: int,
    admin_url: str
) -> Dict:
    """
    Gửi cảnh báo monitor qua Email (tương tự send_monitor_alert_firebase)
    
    Args:
        user_id (int): ID của user (để lấy email)
        monitor_name (str): Tên monitor
        monitor_url (str): URL được monitor
        error_message (str): Thông báo lỗi
        monitor_id (int): ID của monitor
        admin_url (str): Link đến trang admin
        
    Returns:
        dict: Result từ send_email_async
    """
    # Lấy email từ user settings
    email = await get_email_for_user(user_id)
    if not email:
        return {
            'success': False,
            'message': f'No email found for user {user_id}'
        }
    
    subject = f"🚨 ALERT: {monitor_name} is DOWN"
    
    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545; margin: 0 0 20px 0; font-size: 24px;">🚨 Service Alert</h1>
            
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px;">
                <h2 style="margin: 0 0 5px 0; color: #856404; font-size: 18px;">{monitor_name}</h2>
                <p style="margin: 0; color: #856404;"><strong>Status: DOWN ❌</strong></p>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; width: 120px;"><strong>🌐 URL:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; word-break: break-all;">{monitor_url}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>❌ Error:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #dc3545;">{error_message}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>🔢 Monitor ID:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{monitor_id}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>🕒 Time:</strong></td>
                    <td style="padding: 10px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{admin_url}" style="background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    View Monitor Details →
                </a>
            </div>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px; text-align: center;">
                This is an automated alert from <strong>Ping24</strong><br>
                Please check your service immediately
            </p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
🚨 ALERT: {monitor_name} is DOWN

Monitor: {monitor_name}
URL: {monitor_url}
Status: DOWN
Error: {error_message}
Monitor ID: {monitor_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

View details: {admin_url}

This is an automated alert from Ping24
Please check your service immediately
    """
    
    return await send_email_async(email, subject, html_body, text_body)


async def send_monitor_recovery_email(
    user_id: int,
    monitor_name: str,
    monitor_url: str,
    response_time: float,
    monitor_id: int,
    admin_url: str
) -> Dict:
    """
    Gửi thông báo phục hồi monitor qua Email (tương tự send_monitor_recovery_firebase)
    
    Args:
        user_id (int): ID của user (để lấy email)
        monitor_name (str): Tên monitor
        monitor_url (str): URL được monitor
        response_time (float): Thời gian phản hồi (ms)
        monitor_id (int): ID của monitor
        admin_url (str): Link đến trang admin
        
    Returns:
        dict: Result từ send_email_async
    """
    # Lấy email từ user settings
    email = await get_email_for_user(user_id)
    if not email:
        return {
            'success': False,
            'message': f'No email found for user {user_id}'
        }
    
    subject = f"✅ RECOVERY: {monitor_name} is BACK ONLINE"
    
    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #28a745; margin: 0 0 20px 0; font-size: 24px;">✅ Service Recovery</h1>
            
            <div style="background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin-bottom: 20px;">
                <h2 style="margin: 0 0 5px 0; color: #155724; font-size: 18px;">{monitor_name}</h2>
                <p style="margin: 0; color: #155724;"><strong>Status: ONLINE ✅</strong></p>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; width: 140px;"><strong>🌐 URL:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; word-break: break-all;">{monitor_url}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>⚡ Response Time:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #28a745;"><strong>{response_time:.2f}ms</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>🔢 Monitor ID:</strong></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;">{monitor_id}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>🕒 Time:</strong></td>
                    <td style="padding: 10px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{admin_url}" style="background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                    View Monitor Details →
                </a>
            </div>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 12px; text-align: center;">
                Service is back online! 🎉<br>
                <strong>Ping24</strong>
            </p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
✅ RECOVERY: {monitor_name} is BACK ONLINE

Monitor: {monitor_name}
URL: {monitor_url}
Status: ONLINE
Response Time: {response_time:.2f}ms
Monitor ID: {monitor_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

View details: {admin_url}

Service is back online! 🎉
    """
    
    return await send_email_async(email, subject, html_body, text_body)
