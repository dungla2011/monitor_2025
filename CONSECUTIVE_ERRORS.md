# Consecutive Error Tracking & Extended Alert Throttling

## Tổng quan
Hệ thống monitoring đã được cập nhật với tính năng theo dõi lỗi liên tiếp và giãn alert thông minh để tránh spam Telegram notification.

## Cách hoạt động

### 1. Theo dõi lỗi liên tiếp
- Mỗi thread sẽ có counter riêng để đếm số lần lỗi liên tiếp
- Counter tăng lên mỗi khi service gặp lỗi
- Counter reset về 0 khi:
  - Service phục hồi (check thành công)
  - Thread được khởi động lại
  - Thread bị dừng

### 2. Logic giãn alert
Khi đáp ứng **TẤT CẢ** các điều kiện sau:
- ✅ Check interval < 5 phút
- ✅ Lỗi liên tiếp > 10 lần (`CONSECUTIVE_ERROR_THRESHOLD`)
- ✅ `EXTENDED_ALERT_INTERVAL_MINUTES` > 0

Hệ thống sẽ chuyển sang chế độ "Extended Throttling":
- **10 lần đầu**: Gửi alert bình thường
- **Từ lần thứ 11+**: Chỉ gửi alert mỗi 5 phút một lần

### 3. Cấu hình

```python
# Trong monitor_service.py
CONSECUTIVE_ERROR_THRESHOLD = 10    # Số lần lỗi liên tiếp trước khi kích hoạt extended throttling
EXTENDED_ALERT_INTERVAL_MINUTES = 5 # Khoảng cách giữa các alert (phút) sau khi vượt ngưỡng
                                   # Đặt = 0 để tắt extended throttling
TELEGRAM_THROTTLE_SECONDS = 30     # Basic throttling (giữa các notification giống nhau)
```

## Ví dụ thực tế

### Service có check interval 60 giây (< 5 phút):
1. **Lỗi lần 1-10**: Gửi Telegram alert mỗi 60 giây
2. **Lỗi lần 11+**: Gửi Telegram alert mỗi 5 phút
3. **Service phục hồi**: Reset counter, gửi recovery notification
4. **Lỗi mới**: Lại bắt đầu từ lần 1

### Service có check interval 10 phút (≥ 5 phút):
- Không áp dụng extended throttling
- Gửi alert bình thường theo check interval

## Logs & Monitoring

### Khi start thread:
```
🚀 [Thread 1] Starting monitoring for: Service Name
   [Thread 1] Reset consecutive error counter
```

### Khi gặp lỗi:
```
📊 [Thread 1] Consecutive errors: 5
📱 [Thread 1] Telegram alert sent successfully
```

### Khi extended throttling active:
```
📊 [Thread 1] Consecutive errors: 12
🔕 [Thread 1] Extended alert throttle active (3.2m remaining)
```

### Khi service phục hồi:
```
✅ [Thread 1] Service recovered! Reset consecutive error count (was: 15)
📱 [Thread 1] Telegram recovery notification sent successfully
```

## Testing

### Xem settings hiện tại:
```bash
python test_consecutive_errors.py settings
```

### Test consecutive error logic:
```bash
python test_consecutive_errors.py test
```

### Test monitor service:
```bash
python monitor_service.py test
```

## Lợi ích
1. **Giảm spam**: Tránh nhận quá nhiều notification khi service liên tục lỗi
2. **Thông minh**: Chỉ áp dụng cho service check thường xuyên (< 5 phút)
3. **Linh hoạt**: Có thể tắt extended throttling bằng cách set `EXTENDED_ALERT_INTERVAL_MINUTES = 0`
4. **Recovery aware**: Tự động reset khi service phục hồi
5. **Per-thread**: Mỗi service được theo dõi riêng biệt

## Telegram Message Enhancement
Alert message sẽ bao gồm thông tin lỗi liên tiếp:
```
❌ Service Error: Connection timeout (Lỗi liên tiếp: 15)
```
