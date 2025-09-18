# Grafana Setup Guide for TimescaleDB Monitor Data

## 1. Install & Run Grafana

### Option A: Docker (Recommended)
```bash
# Run Grafana container
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_USER=admin" \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin123" \
  -e "GF_SECURITY_ALLOW_EMBEDDING=true" \
  -e "GF_AUTH_ANONYMOUS_ENABLED=true" \
  -e "GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer" \
  grafana/grafana:latest
```

### Option B: Windows Install
- Download từ: https://grafana.com/grafana/download?platform=windows
- Cài đặt và chạy service

## 2. Access Grafana
- URL: http://localhost:3000
- Username: admin
- Password: admin123 (hoặc admin)

## 3. Add PostgreSQL Data Source
1. Go to Configuration → Data Sources
2. Add new data source → PostgreSQL  
3. Configure:
   - Host: localhost:5432
   - Database: postgres
   - User: postgres
   - Password: [your-password]
   - SSL Mode: disable
   - Version: 12+
   - TimescaleDB: Enable

## 4. Test Connection
Click "Save & Test" - should show green success message.

## 5. Import Dashboard
Use the JSON dashboard config (next file) to import pre-built monitor dashboard.

## 6. Enable Embedding
In Grafana settings:
- Go to Configuration → Settings
- Security section:
  - allow_embedding = true
  - cookie_samesite = none
  - cookie_secure = false (for development)

## 7. Get Embed Code
From any dashboard:
1. Click Share icon
2. Choose "Embed" tab  
3. Copy iframe code
4. Paste into your web application