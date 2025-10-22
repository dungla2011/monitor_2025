"""
Test Firebase Data-Only Messages
Gửi data-only message (không có notification field) để app Android có thể phát custom sound
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import Firebase helper
from async_firebase_helper import (
    initialize_firebase,
    send_firebase_notification_async
)

async def test_data_only_message():
    """
    Test gửi data-only message giống PHP code
    """
    print("=" * 60)
    print("🧪 TEST: Firebase Data-Only Message (Custom Sound Support)")
    print("=" * 60)
    
    # Initialize Firebase
    try:
        initialize_firebase()
        print("✅ Firebase initialized\n")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}\n")
        return
    
    # Test device token (thay bằng token thực tế từ app Android)
    device_token = os.getenv('FIREBASE_TEST_TOKEN')
    
    if not device_token:
        print("❌ FIREBASE_TEST_TOKEN not set in .env file")
        print("\n💡 Hướng dẫn lấy Device Token:")
        print("-" * 60)
        print("📱 ANDROID (Java):")
        print("""
FirebaseMessaging.getInstance().getToken()
    .addOnCompleteListener(task -> {
        if (!task.isSuccessful()) return;
        String token = task.getResult();
        Log.d("FCM Token", token);
        // Copy token này vào .env: FIREBASE_TEST_TOKEN=...
    });
        """)
        print("\n📱 ANDROID (Kotlin):")
        print("""
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (!task.isSuccessful) return@addOnCompleteListener
    val token = task.result
    Log.d("FCM Token", token)
    // Copy token này vào .env: FIREBASE_TEST_TOKEN=...
}
        """)
        return
    
    # Thông tin test message
    title = "🚨 Cảnh báo từ Monitor System"
    body = f"Test data-only message lúc {datetime.now().strftime('%H:%M:%S')}"
    
    # Custom data (sẽ được app Android xử lý)
    custom_data = {
        # title và body sẽ được tự động thêm vào data
        'device_id': 'TEST_DEVICE',
        'alert_type': 'monitor_alert',
        'severity': 'high',
        'timestamp': datetime.now().isoformat(),
        'monitor_id': '123',
        'monitor_name': 'example.com',
        'action_required': 'check_system_status'
    }
    
    print("📤 Sending Firebase message...")
    print(f"📱 Device Token: {device_token[:20]}...")
    print(f"📢 Title: {title}")
    print(f"📝 Body: {body}")
    print(f"📦 Custom Data: {custom_data}\n")
    
    try:
        result = await send_firebase_notification_async(
            token=device_token,
            title=title,
            body=body,
            data=custom_data
        )
        
        if result['success']:
            print("✅ GỬI THÀNH CÔNG - 2 MESSAGES!")
            print(f"📩 Message 1 (Notification): {result.get('message_id_1', 'N/A')}")
            print(f"📩 Message 2 (Data-only): {result.get('message_id_2', 'N/A')}")
            print(f"🕐 Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("\n💡 Kiểm tra app Android:")
            print("   ✅ Message 1: Notification hiển thị ngay (mặc định)")
            print("   ✅ Message 2: Data message → custom sound (nếu đã implement)")
            print("   ⚠️ Có thể thấy 2 notifications (không sao, đảm bảo nhận được)")
        else:
            print(f"❌ GỬI THẤT BẠI!")
            print(f"📝 Message: {result['message']}")
            
            # Hướng dẫn khắc phục
            print("\n💡 HƯỚNG DẪN KHẮC PHỤC:")
            if 'registration-token-not-registered' in result['message']:
                print("- Device token không hợp lệ hoặc app đã bị gỡ")
                print("- Cần lấy token mới từ client app")
            elif 'invalid-registration-token' in result['message']:
                print("- Device token có định dạng sai")
                print("- Kiểm tra lại token từ client app")
            elif 'authentication' in result['message'].lower():
                print("- Lỗi xác thực với Firebase")
                print("- Kiểm tra file firebase_service_account.json")
            else:
                print("- Kiểm tra kết nối internet")
                print("- Đảm bảo Firebase project đã enable Cloud Messaging")
                
    except Exception as e:
        print(f"❌ LỖI: {e}")
        import traceback
        print(f"\n{traceback.format_exc()}")
    
    print("\n" + "=" * 60)
    print("📚 THÔNG TIN QUAN TRỌNG:")
    print("=" * 60)
    print("""
⚠️ CHIẾN LƯỢC GỬI 2 LẦN:
- Message 1: Notification-only → Hiển thị ngay, đảm bảo user thấy
- Message 2: Data-only → App tự xử lý, custom sound khi background
- Kết quả: Chắc chắn nhận được, trùng cũng không sao!

✅ LỢI ÍCH:
1. App có thể phát custom sound kể cả khi ở background
2. Kiểm soát hoàn toàn cách hiển thị notification
3. Xử lý logic tùy chỉnh (routing, data processing, etc.)

📱 YÊU CẦU ANDROID APP:
1. Implement FirebaseMessagingService
2. Override onMessageReceived(RemoteMessage)
3. Tạo notification với custom sound
4. Đặt sound file vào res/raw/

📖 Xem thêm: async_firebase_helper.py (header comments)
    """)


if __name__ == "__main__":
    asyncio.run(test_data_only_message())
