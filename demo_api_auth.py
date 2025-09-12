#!/usr/bin/env python3
"""
API Authentication Demo Script
Demo cách sử dụng các loại token khác nhau
"""
import requests
import json
import base64

API_BASE = "http://127.0.0.1:5005"
USERNAME = "admin"
PASSWORD = "....@123"

print("="*60)
print("API AUTHENTICATION DEMO")
print("="*60)

def test_basic_auth():
    """Test Basic Authentication để lấy token"""
    print("\n🔐 1. Testing Basic Auth to get tokens...")
    
    auth = (USERNAME, PASSWORD)
    
    # Test Simple Token (no expiration)
    print("\n📍 Getting Simple Token (never expires):")
    response = requests.post(f"{API_BASE}/api/token", 
                           auth=auth,
                           json={"type": "simple"})
    
    if response.status_code == 200:
        data = response.json()
        simple_token = data['token']
        print(f"✅ Simple Token: {simple_token}")
        print(f"   Type: {data['type']}")
        print(f"   Expires: {data['expires']}")
        print(f"   Usage: {data['usage']}")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None, None
    
    # Test JWT Token (with expiration)
    print("\n📍 Getting JWT Token (expires in 24 hours):")
    response = requests.post(f"{API_BASE}/api/token", 
                           auth=auth,
                           json={"type": "jwt", "expires_hours": 24})
    
    if response.status_code == 200:
        data = response.json()
        jwt_token = data['token']
        print(f"✅ JWT Token: {jwt_token[:50]}...")
        print(f"   Type: {data['type']}")
        print(f"   Expires: {data['expires']}")
        print(f"   Usage: {data['usage'][:80]}...")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        jwt_token = None
    
    return simple_token, jwt_token

def test_api_with_token(token, token_type):
    """Test API endpoints với token"""
    print(f"\n🧪 2. Testing API with {token_type} Token:")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test /api/status
    print("\n📍 Testing /api/status:")
    response = requests.get(f"{API_BASE}/api/status", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data.get('status', 'unknown')}")
        print(f"   Uptime: {data.get('uptime_seconds', 0)} seconds")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
    
    # Test /api/monitors
    print("\n📍 Testing /api/monitors:")
    response = requests.get(f"{API_BASE}/api/monitors", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Monitors: {len(data.get('monitors', []))} items")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
    
    # Test /api/threads
    print("\n📍 Testing /api/threads:")
    response = requests.get(f"{API_BASE}/api/threads", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Threads: {len(data.get('threads', []))} running")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")

def test_without_auth():
    """Test API endpoints without authentication"""
    print(f"\n❌ 3. Testing API without authentication (should fail):")
    
    response = requests.get(f"{API_BASE}/api/status")
    print(f"📍 /api/status without auth: {response.status_code}")
    
    response = requests.get(f"{API_BASE}/api/monitors")
    print(f"📍 /api/monitors without auth: {response.status_code}")

if __name__ == "__main__":
    try:
        # Test getting tokens
        simple_token, jwt_token = test_basic_auth()
        
        if simple_token:
            # Test API with simple token
            test_api_with_token(simple_token, "Simple")
        
        if jwt_token:
            # Test API with JWT token
            test_api_with_token(jwt_token, "JWT")
        
        # Test without authentication
        test_without_auth()
        
        print("\n" + "="*60)
        print("SUMMARY:")
        print("="*60)
        print("📝 Token Types Available:")
        print("   1. Simple Token: Base64 encoded credentials, never expires")
        print("   2. JWT Token: JSON Web Token with expiration (24 hours default)")
        print("🔗 API Usage:")
        print(f'   curl -H "Authorization: Bearer <token>" {API_BASE}/api/status')
        print("🔐 Authentication Methods:")
        print("   1. Web Session: Login via /login page")
        print("   2. Bearer Token: Use tokens from /api/token endpoint")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        print("💡 Make sure monitor service is running:")
        print("   python monitor_service.py start")
