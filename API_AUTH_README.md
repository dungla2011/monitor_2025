# Monitor Service API Authentication

## Overview
Monitor Service API hỗ trợ 2 phương thức authentication:

### 1. Web Session Authentication
- Login qua web interface: `http://127.0.0.1:5005/login`
- Username/Password được cấu hình trong `.env`:
  ```
  WEB_ADMIN_USERNAME=admin
  WEB_ADMIN_PASSWORD=....@123
  ```
- Session được lưu trong browser cookies

### 2. Bearer Token Authentication

#### Simple Token (No Expiration)
- Base64 encoded `username:password`
- **Never expires** - valid until credentials change in .env
- Example: `YWRtaW46cXFxcHBwQDEyMw==`

#### JWT Token (With Expiration) 
- JSON Web Token with expiration time
- Default: **24 hours** (configurable)
- Contains user info and expiration timestamp

## Getting Tokens

### Method 1: Using curl with Basic Auth
```bash
# Get Simple Token (never expires)
curl -u admin:....3 \
  -H "Content-Type: application/json" \
  -d '{"type":"simple"}' \
  http://127.0.0.1:5005/api/token

# Get JWT Token (expires in 24 hours)  
curl -u admin:.... \
  -H "Content-Type: application/json" \
  -d '{"type":"jwt","expires_hours":24}' \
  http://127.0.0.1:5005/api/token
```

### Method 2: Using Python script
```bash
python demo_api_auth.py
```

## Using Tokens

### With curl
```bash
# Using Simple Token
curl -H "Authorization: Bearer YWRtaW46cXFxcHBwQDEyMw==" \
  http://127.0.0.1:5005/api/status

# Using JWT Token
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  http://127.0.0.1:5005/api/monitors
```

### With Python
```python
import requests

token = "YWRtaW46cXFxcHBwQDEyMw=="
headers = {"Authorization": f"Bearer {token}"}

response = requests.get("http://127.0.0.1:5005/api/status", headers=headers)
print(response.json())
```

## Protected API Endpoints

All API endpoints require authentication:

- `GET /api/status` - Service status
- `GET /api/monitors` - Monitor items
- `GET /api/threads` - Thread information
- `GET /api/logs` - Recent logs
- `POST /api/shutdown` - Shutdown service

## Token Lifetime Summary

| Token Type | Lifetime | Use Case |
|------------|----------|----------|
| **Simple Token** | ♾️ Never expires | Long-term API access, automation |
| **JWT Token** | ⏰ 1-24 hours (configurable) | Temporary access, security-focused |
| **Web Session** | 🍪 Browser session | Web interface access |

## Security Notes

1. **Simple Tokens** are essentially permanent API keys
2. **JWT Tokens** provide better security with expiration
3. **Credentials** are stored in `.env` file - keep it secure
4. **HTTPS** recommended for production use
5. **Change credentials** regularly in production

## Examples

### Quick Test Commands
```bash
# Test authentication works
python demo_api_auth.py

# Get a simple token manually
python -c "
import base64
token = base64.b64encode(b'admin:qqqppp@123').decode()
print(f'Token: {token}')
"

# Test API with token
curl -H "Authorization: Bearer YWRtaW46cXFxcHBwQDEyMw==" \
  http://127.0.0.1:5005/api/status
```
