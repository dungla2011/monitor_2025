#!/usr/bin/env python3
"""
API Authentication Test Script
Demonstrates how to use API with authentication
"""
import requests
import base64
import json
from requests.auth import HTTPBasicAuth

# Configuration
BASE_URL = "http://127.0.0.1:5005"
USERNAME = "admin"
PASSWORD = "qqqppp@123"

print("="*60)
print("🔐 API AUTHENTICATION TEST")
print("="*60)

def test_basic_auth():
    """Test API with Basic Authentication"""
    print("\n1. Testing Basic Authentication:")
    try:
        response = requests.get(f"{BASE_URL}/api/status", 
                              auth=HTTPBasicAuth(USERNAME, PASSWORD))
        if response.status_code == 200:
            print("   ✅ Basic Auth successful")
            data = response.json()
            print(f"   📊 Total monitors: {data.get('total_monitors', 'N/A')}")
        else:
            print(f"   ❌ Basic Auth failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_bearer_token():
    """Test API with Bearer Token"""
    print("\n2. Testing Bearer Token:")
    try:
        # First, get token
        print("   🔑 Getting bearer token...")
        token_response = requests.post(f"{BASE_URL}/api/token", 
                                     auth=HTTPBasicAuth(USERNAME, PASSWORD))
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            token = token_data['token']
            print(f"   ✅ Token obtained: {token[:20]}...")
            
            # Now use token
            print("   📡 Using token for API call...")
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f"{BASE_URL}/api/status", headers=headers)
            
            if response.status_code == 200:
                print("   ✅ Bearer Token auth successful")
                data = response.json()
                print(f"   📊 Running threads: {data.get('running_threads', 'N/A')}")
            else:
                print(f"   ❌ Bearer Token auth failed: {response.status_code}")
        else:
            print(f"   ❌ Token request failed: {token_response.status_code}")
            print(f"   Response: {token_response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_no_auth():
    """Test API without authentication (should fail)"""
    print("\n3. Testing No Authentication (should fail):")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code == 401:
            print("   ✅ Correctly rejected unauthenticated request")
            print(f"   📄 Response: {response.json()}")
        else:
            print(f"   ⚠️ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_all_endpoints():
    """Test all API endpoints with Basic Auth"""
    print("\n4. Testing All API Endpoints:")
    endpoints = [
        '/api/status',
        '/api/monitors', 
        '/api/threads',
        '/api/logs?lines=10'
    ]
    
    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", auth=auth)
            if response.status_code == 200:
                print(f"   ✅ {endpoint}: OK")
            else:
                print(f"   ❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: Error - {e}")

if __name__ == "__main__":
    print(f"🌐 Testing API at: {BASE_URL}")
    print(f"👤 Username: {USERNAME}")
    print(f"🔑 Password: {PASSWORD}")
    
    test_basic_auth()
    test_bearer_token()
    test_no_auth()
    test_all_endpoints()
    
    print("\n" + "="*60)
    print("✅ API Authentication Test Complete!")
    print("="*60)
    
    print(f"\n💡 Usage Examples:")
    print(f"curl -u {USERNAME}:{PASSWORD} {BASE_URL}/api/status")
    print(f"curl -u {USERNAME}:{PASSWORD} -X POST {BASE_URL}/api/token")
    print(f"\n📚 All API endpoints now require authentication!")
