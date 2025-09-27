# GLX Monitor Service - SystemD Installation

## Cài đặt Service

### 1. Chuẩn bị
```bash
cd /var/glx/monitor
```

### 2. Cài đặt service
```bash
sudo chmod +x install_service.sh
sudo ./install_service.sh
```

### 3. Kiểm tra service
```bash
sudo systemctl status monitor-service
```

## Quản lý Service

### Khởi động service
```bash
sudo systemctl start monitor-service
```

### Dừng service
```bash
sudo systemctl stop monitor-service
```

### Khởi động lại service
```bash
sudo systemctl restart monitor-service
```

### Xem logs real-time
```bash
sudo journalctl -u monitor-service -f
```

### Xem logs với timestamp
```bash
sudo journalctl -u monitor-service -f --since "1 hour ago"
```

### Enable/Disable tự khởi động
```bash
# Enable (tự khởi động khi boot)
sudo systemctl enable monitor-service

# Disable (không tự khởi động)
sudo systemctl disable monitor-service
```

## Gỡ cài đặt Service

```bash
sudo chmod +x uninstall_service.sh
sudo ./uninstall_service.sh
```

## Troubleshooting

### Kiểm tra trạng thái chi tiết
```bash
sudo systemctl status monitor-service -l --no-pager
```

### Xem logs lỗi
```bash
sudo journalctl -u monitor-service --since today --no-pager
```

### Reload service sau khi sửa code
```bash
sudo systemctl restart monitor-service
```

### Test service trước khi cài đặt
```bash
# Test chạy manual trước
python3 monitor_service_asyncio.py start
```

## Files quan trọng

- `monitor_service.service` - SystemD service configuration
- `install_service.sh` - Script cài đặt service  
- `uninstall_service.sh` - Script gỡ cài đặt service
- `/etc/systemd/system/monitor-service.service` - Service file đã cài đặt

## Lưu ý

1. Service sẽ tự khởi động lại nếu crash (RestartSec=10)
2. Service sử dụng virtual environment tại `/var/glx/monitor/venv/`
3. Working directory là `/var/glx/monitor`
4. Logs được ghi vào systemd journal (xem bằng journalctl)
5. Service chạy với user `root` (có thể thay đổi trong service file)