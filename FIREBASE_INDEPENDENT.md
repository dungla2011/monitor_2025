# 🔥 Firebase Notification - Independent Module với Throttling

## 📋 Tổng Quan

Firebase notification đã được **tách riêng** thành module độc lập, hoạt động song song với Telegram và Webhook, **có throttling logic riêng**.

## 🏗️ Kiến Trúc

```
monitor_service_asyncio.py
    ├── send_telegram_notification_async()   ← async_telegram_notification.py
    ├── send_webhook_notification_async()    ← async_webhook_notification.py
    └── send_firebase_notification_async()   ← async_firebase_notification.py ✅ MỚI
                                                      ↓
                                              async_firebase_helper.py
                                                      ↓
                                              Firebase Cloud Messaging (FCM)
```

## ✨ Tính Năng

### 1️⃣ **Throttling Logic (Giống Telegram/Webhook)**

```python
# async_firebase_notification.py
async def send_firebase_notification_async(monitor_item, is_error, error_message, response_time):
    """
    ✅ Độc lập với Telegram/Webhook
    ✅ Có throttling riêng
    ✅ Tracking riêng (thread_firebase_last_sent_alert)
    ✅ Gửi 2 messages tự động (notification + data-only)
    """
```

### 2️⃣ **Alert Manager Support**

```python
# async_alert_manager.py
class AsyncAlertManager:
    def __init__(self):
        self.thread_telegram_last_sent_alert = 0   # Telegram tracking
        self.thread_webhook_last_sent_alert = 0    # Webhook tracking
        self.thread_firebase_last_sent_alert = 0   # Firebase tracking ✅
    
    async def can_send_firebase_alert(self, throttle_seconds):
        """
        ✅ Kiểm tra throttle riêng cho Firebase
        ✅ Chế độ throttle: Chỉ gửi lần đầu lỗi
        ✅ Chế độ no-throttle: Gửi theo time interval
        """
    
    async def mark_firebase_sent(self):
        """✅ Đánh dấu đã gửi Firebase alert"""
```

## ⚙️ Cấu Hình (.env)

```bash
# Firebase Throttle Settings
FIREBASE_THROTTLE_ENABLED=true  # true = chỉ gửi lần đầu, false = gửi theo time
```

## 🎯 Logic Hoạt Động

### **Chế Độ 1: Throttle Enabled (Default)**

```python
FIREBASE_THROTTLE_ENABLED=true

# Lỗi liên tiếp #1 → ✅ Gửi Firebase
# Lỗi liên tiếp #2 → 🔇 SKIP (throttled)
# Lỗi liên tiếp #3 → 🔇 SKIP (throttled)
# Recovery         → ✅ Gửi Firebase (reset counter)
# Lỗi mới #1       → ✅ Gửi Firebase (counter reset)
```

### **Chế Độ 2: No Throttle (Time-based)**

```python
FIREBASE_THROTTLE_ENABLED=false
monitor_item.alert_throttle_seconds=30  # 30 giây

# Lỗi lần 1 (0s)    → ✅ Gửi Firebase
# Lỗi lần 2 (5s)    → 🔇 SKIP (chưa đủ 30s)
# Lỗi lần 3 (35s)   → ✅ Gửi Firebase (đã qua 30s)
# Lỗi lần 4 (40s)   → 🔇 SKIP (chưa đủ 30s)
```

## 📝 Sử Dụng Trong Code

### **monitor_service_asyncio.py**

```python
# Import
from async_firebase_notification import send_firebase_notification_async

# Alert notification
if result['success']:
    # Recovery
    await send_telegram_notification_async(...)  # Telegram
    await send_webhook_notification_async(...)   # Webhook
    await send_firebase_notification_async(...)  # Firebase ✅
else:
    # Error
    await send_telegram_notification_async(...)  # Telegram
    await send_webhook_notification_async(...)   # Webhook
    await send_firebase_notification_async(...)  # Firebase ✅
```

### **Gọi Độc Lập**

```python
# Gửi alert
result = await send_firebase_notification_async(
    monitor_item=monitor,
    is_error=True,
    error_message="Connection timeout"
)

# Gửi recovery
result = await send_firebase_notification_async(
    monitor_item=monitor,
    is_error=False,
    response_time=156.78
)
```

## 🧪 Test

```bash
# Test Firebase throttling
python test_firebase_throttling.py
```

## 📊 So Sánh Với Các Module Khác

| Feature | Telegram | Webhook | Firebase |
|---------|----------|---------|----------|
| **Module** | `async_telegram_notification.py` | `async_webhook_notification.py` | `async_firebase_notification.py` ✅ |
| **Throttling** | ✅ | ✅ | ✅ |
| **Alert Manager** | ✅ | ✅ | ✅ |
| **Recovery** | ✅ | ✅ | ✅ |
| **Independent** | ✅ | ✅ | ✅ |
| **ENV Variable** | `TELEGRAM_THROTTLE_ENABLED` | `WEBHOOK_THROTTLE_ENABLED` | `FIREBASE_THROTTLE_ENABLED` ✅ |

## 🔄 Flow Chart

```
Monitor Check Failed
    ↓
┌───────────────────────────────────┐
│  AsyncAlertManager                │
│  - increment_consecutive_error()  │
└───────────────────────────────────┘
    ↓
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│  Telegram Throttle      │  Webhook Throttle       │  Firebase Throttle      │
│  ✅ can_send_telegram   │  ✅ can_send_webhook    │  ✅ can_send_firebase   │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
    ↓                           ↓                           ↓
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│  Send Telegram          │  Send Webhook           │  Send Firebase          │
│  (Async)                │  (Async)                │  (Async)                │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
    ↓                           ↓                           ↓
┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
│  mark_telegram_sent()   │  mark_webhook_sent()    │  mark_firebase_sent()   │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

## ✅ Kết Luận

- ✅ **Firebase notification hoạt động độc lập**
- ✅ **Có throttling logic riêng**
- ✅ **Không ảnh hưởng Telegram/Webhook**
- ✅ **Gửi 2 messages tự động (notification + data-only)**
- ✅ **Tracking riêng biệt cho từng channel**
- ✅ **Kiến trúc nhất quán với Telegram/Webhook**

## 🚀 Next Steps

1. ✅ Code đã hoàn thành
2. 🔧 Test throttling: `python test_firebase_throttling.py`
3. 🔧 Thêm `FIREBASE_THROTTLE_ENABLED=true` vào `.env`
4. 🚀 Deploy và monitor logs
