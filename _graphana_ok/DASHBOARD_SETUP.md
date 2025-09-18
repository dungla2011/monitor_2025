# Complete Dashboard Setup Guide

## Bước 1: Setup Grafana
```bash
# Docker method (dễ nhất)
docker run -d \
  --network host \
  --name grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin123" \
  -e "GF_SECURITY_ALLOW_EMBEDDING=true" \
  grafana/grafana:latest
```

## Bước 2: Configure Data Source
1. Truy cập http://localhost:3000
2. Login: admin/admin123
3. Add PostgreSQL data source:
   - Host: localhost:5432
   - Database: postgres
   - User: postgres
   - Password: [your-password]
   - SSL: disable

## Bước 3: Import Dashboard
1. Go to + → Import
2. Copy nội dung từ `grafana_dashboard.json`
3. Paste và import

## Bước 4: Enable Embedding
1. Configuration → Settings
2. Sửa file grafana.ini:
```ini
[security]
allow_embedding = true

[auth.anonymous]
enabled = true
org_role = Viewer
```

## Bước 5: Get Embed URL
1. Mở dashboard vừa tạo
2. Click Share → Embed
3. Copy iframe URL
4. Paste vào `dashboard_embed.html`

## Bước 6: Test Dashboard
```bash
# Chạy API server (tùy chọn)
pip install flask asyncpg
python dashboard_api.py

# Mở dashboard
# http://localhost:5000 (nếu dùng API)
# hoặc mở dashboard_embed.html trực tiếp
```

## Bước 7: Embed vào website của bạn
```html
<!-- Cách 1: Iframe trực tiếp -->
<iframe 
  src="http://localhost:3000/d-solo/[dashboard-id]/monitor?orgId=1&refresh=30s" 
  width="100%" 
  height="400px" 
  frameborder="0">
</iframe>

<!-- Cách 2: Dùng dashboard_embed.html làm template -->
<!-- Copy code từ dashboard_embed.html vào website của bạn -->
```

## Cấu hình cho Production
1. **Security**: Đổi password Grafana
2. **HTTPS**: Setup SSL cho Grafana
3. **CORS**: Configure Grafana cho cross-origin
4. **Auth**: Setup authentication nếu cần
5. **Reverse Proxy**: Dùng nginx/apache proxy

## URLs cần thiết:
- Grafana: http://localhost:3000
- API (optional): http://localhost:5000
- Dashboard: http://localhost:5000 hoặc dashboard_embed.html