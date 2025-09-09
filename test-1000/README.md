# 🚀 Performance Testing với 1000 Domains

Thư mục này chứa các công cụ để test hiệu suất của monitor service với 1000 domains concurrent.

## 📁 Files

- **`create_1000_test_domains.py`** - Tạo 1000 test domains với interval 60s
- **`cleanup_test_domains.py`** - Xóa tất cả test domains  
- **`performance_monitor.py`** - Monitor hiệu suất realtime
- **`performance_test_toolkit.py`** - Menu tổng hợp tất cả tools

## 🔧 Cách sử dụng

### Option 1: Sử dụng Toolkit (Đơn giản)
```bash
cd test-1000
python performance_test_toolkit.py
```

### Option 2: Manual (Chi tiết)

#### Bước 1: Chuẩn bị
```bash
# Activate venv từ thư mục gốc
cd ..
.\venv\Scripts\Activate.ps1
cd test-1000
```

#### Bước 2: Tạo test data
```bash
python create_1000_test_domains.py
```

#### Bước 3: Chạy performance monitor (Terminal 1)
```bash
python performance_monitor.py
```

#### Bước 4: Start monitor service (Terminal 2)
```bash
cd ..
python monitor_service.py start --test
```

#### Bước 5: Cleanup sau test
```bash
# Stop service
python monitor_service.py stop

# Delete test domains  
cd test-1000
python cleanup_test_domains.py
```

## 📊 Test Specifications

- **Domains**: 1000 domains từ các site phổ biến
- **Types**: ping_web, ping_icmp, web_content, ssl_expired_check, open_port_tcp
- **Interval**: 60 giây cho tất cả
- **Expected Load**: ~16.7 checks/second
- **Database**: Test environment (.env.test)

## 🎯 Performance Metrics

### System Metrics
- CPU Usage (target: <80%)
- Memory Usage (stable, no leaks)
- Thread Count (stable, no continuous growth)
- Network I/O
- Database Response Time

### Application Metrics  
- Total Items
- Online/Offline Status
- Test Progress
- Error Rate
- Response Times

## ⚠️ Lưu ý

1. **Resource Usage**: 1000 concurrent threads sẽ tốn nhiều tài nguyên
2. **Test Environment**: Sử dụng `.env.test` (port 5006, localhost MySQL)
3. **Cleanup**: Luôn xóa test data sau khi test xong
4. **Monitoring**: Quan sát system metrics trong suốt quá trình test

## 🧹 Cleanup

Để xóa tất cả test domains:
```bash
python cleanup_test_domains.py
```

Hoặc SQL trực tiếp:
```sql
DELETE FROM monitor_items WHERE name LIKE 'TEST_%';
```

## 📈 Expected Results

- Service ổn định với 1000 concurrent checks
- CPU usage reasonable (<80%)
- Memory usage stable (no leaks)
- Database connections managed properly
- Error rate acceptable (<5%)
- Response times consistent

## 🔍 Troubleshooting

**Import Errors**: Scripts đã được cập nhật để import modules từ thư mục cha

**Database Connection**: Kiểm tra `.env.test` có đúng thông tin MySQL

**Resource Issues**: Giảm số test domains hoặc tăng interval nếu hệ thống quá tải
