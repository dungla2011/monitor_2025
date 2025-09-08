#!/usr/bin/env python3
"""
Test ping_web với scheme auto-detection
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from monitor_service import ping_web

def test_ping_web():
    """Test ping_web function với các URL khác nhau"""
    print("🧪 Testing ping_web() with auto-scheme")
    
    test_cases = [
        "abc.com",
        "google.com", 
        "mytree.vn",
        "https://mytree.vn",
        "http://google.com",
        "invalid-domain-xyz123.com"
    ]
    
    for url in test_cases:
        print(f"\nTesting: {url}")
        success, status_code, response_time, message = ping_web(url, timeout=5)
        
        if success:
            print(f"  ✅ {message}")
            print(f"     Status: {status_code}, Time: {response_time:.2f}ms")
        else:
            print(f"  ❌ {message}")
            if status_code:
                print(f"     Status: {status_code}")

if __name__ == "__main__":
    test_ping_web()
