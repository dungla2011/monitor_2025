#!/usr/bin/env python3
"""
Quick test để check monitor service
"""

import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api():
    """Test API endpoints"""
    port = os.getenv('HTTP_PORT', '5005')
    host = os.getenv('HTTP_HOST', '127.0.0.1')
    base_url = f"http://{host}:{port}"
    
    print("🌐 Testing Monitor Service API")
    print("=" * 40)
    
    endpoints = [
        ("/", "Dashboard"),
        ("/api/status", "Status API"),
        ("/api/monitors", "Monitors API"),
        ("/api/threads", "Threads API"),
    ]
    
    for endpoint, name in endpoints:
        try:
            print(f"Testing {name}...")
            response = requests.get(base_url + endpoint, timeout=5)
            
            if response.status_code == 200:
                print(f"  ✅ {name} - OK")
                if endpoint.startswith('/api/'):
                    try:
                        data = response.json()
                        if 'status' in data:
                            print(f"     Status: {data['status']}")
                        if 'monitor_items' in data:
                            print(f"     Monitor items: {data['monitor_items']}")
                        if 'threads' in data:
                            print(f"     Threads: {data['threads']}")
                    except:
                        print("     (JSON parse error)")
                else:
                    print(f"     Content length: {len(response.text)} chars")
            else:
                print(f"  ❌ {name} - HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ {name} - Connection refused (service not running?)")
        except KeyboardInterrupt:
            print(f"  ⚠️ {name} - Test interrupted")
            break
        except Exception as e:
            print(f"  ❌ {name} - Error: {e}")
    
    print("\n🔗 URLs:")
    print(f"  Dashboard: {base_url}")
    print(f"  Status API: {base_url}/api/status")

if __name__ == "__main__":
    test_api()
