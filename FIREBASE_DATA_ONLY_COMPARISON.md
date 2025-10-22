# ============================================
# SO SÁNH: PHP vs Python - Firebase Data-Only Messages
# ============================================

## 🎯 MỤC ĐÍCH
Gửi **2 MESSAGES** để đảm bảo chắc chắn nhận được:
1. **Notification-only**: Hiển thị ngay, user thấy được luôn
2. **Data-only**: App tự xử lý, phát custom sound khi ở background

→ Trùng cũng không sao, quan trọng là CHẮC CHẮN nhận được!

---

## 📝 CODE PHP (Mẫu)

```php
<?php
require 'vendor/autoload.php';

use Kreait\Firebase\Factory;
use Kreait\Firebase\Messaging\CloudMessage;

$factory = (new Factory)
    ->withServiceAccount('fb.json');

$cloudMessaging = $factory->createMessaging();

$deviceToken = 'your_device_token_here';

// ⚠️ QUAN TRỌNG: Thêm title và body vào data
$customData = [
    'title' => 'Cảnh báo từ Taxi',
    'body' => 'Test tin nhắn đến ABC123',
    'device_id' => 'ABC123',
    'alert_type' => 'system_warning'
];

// ✅ Tạo message CHỈ với data (KHÔNG có notification)
$message = CloudMessage::new()
    ->withData($customData)  // ✅ Chỉ data
    ->toToken($deviceToken);

$result = $cloudMessaging->send($message);
?>
```

---

## 🐍 CODE PYTHON (Cải tiến - Gửi 2 lần)

```python
import asyncio
from async_firebase_helper import send_firebase_notification_async

async def send_alert():
    device_token = 'your_device_token_here'
    
    custom_data = {
        'device_id': 'ABC123',
        'alert_type': 'system_warning'
    }
    
    # ✅ Gửi 2 messages tự động:
    # Message 1: Notification-only
    # Message 2: Data-only với custom data
    result = await send_firebase_notification_async(
        token=device_token,
        title='Cảnh báo từ Taxi',
        body='Test tin nhắn đến ABC123',
        data=custom_data
    )
    
    if result['success']:
        print(f"✅ Message 1 (Notification): {result['message_id_1']}")
        print(f"✅ Message 2 (Data): {result['message_id_2']}")
    else:
        print(f"❌ Failed: {result['message']}")

asyncio.run(send_alert())
```

---

## 🔍 SO SÁNH CHI TIẾT

| Feature | PHP | Python |
|---------|-----|--------|
| **Library** | kreait/firebase-php | firebase-admin |
| **Message Type** | CloudMessage::new()->withData() | messaging.Message(data=...) |
| **Notification Field** | ❌ Không có (data only) | ❌ Không có (data only) |
| **Title/Body** | Thêm vào $customData | Tự động thêm vào data |
| **Priority** | Tự động high | android.priority='high' |
| **Custom Sound** | ✅ App tự xử lý | ✅ App tự xử lý |

---

## 📱 ANDROID APP - Xử lý Data-Only Message

```java
public class MyFirebaseMessagingService extends FirebaseMessagingService {
    
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        // ✅ Nhận data message (PHP hoặc Python đều giống nhau)
        Map<String, String> data = remoteMessage.getData();
        
        String title = data.get("title");
        String body = data.get("body");
        String deviceId = data.get("device_id");
        String alertType = data.get("alert_type");
        
        // ✅ Tạo notification với CUSTOM SOUND
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.drawable.ic_notification)
            .setSound(getCustomSound(alertType))  // ← Custom sound theo alert type
            .setPriority(NotificationCompat.PRIORITY_HIGH);
        
        NotificationManagerCompat.from(this).notify(notificationId, builder.build());
    }
    
    private Uri getCustomSound(String alertType) {
        // Chọn sound theo loại alert
        int soundRes = "system_warning".equals(alertType) 
            ? R.raw.alert_warning  // ← Sound cho warning
            : R.raw.alert_default;  // ← Sound mặc định
            
        return Uri.parse("android.resource://" + getPackageName() + "/" + soundRes);
    }
}
```

---

## ✅ KẾT LUẬN

### **PHP và Python giờ đã GIỐNG NHAU:**

1. ✅ **Cả 2 đều gửi DATA-ONLY** (không có notification field)
2. ✅ **Title và body trong data** → App tự hiển thị
3. ✅ **App Android kiểm soát hoàn toàn** → Custom sound, UI, logic
4. ✅ **Hoạt động cả khi app ở background**

### **Lợi ích:**
- 🔊 Phát custom sound khác nhau cho từng loại alert
- 🎨 Tùy chỉnh UI notification
- 🔔 Kiểm soát âm lượng, vibration
- 📱 Routing đến màn hình cụ thể khi tap notification

---

## 🧪 TEST

### **Python:**
```bash
python test_firebase_data_only.py
```

### **PHP:**
```bash
php send_firebase_test.php
```

**→ Cả 2 đều gửi data-only message, app Android xử lý giống hệt nhau! 🚀**
