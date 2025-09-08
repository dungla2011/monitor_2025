#!/usr/bin/env python3
"""
Debug ping functionality
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from urllib.parse import urlparse
from monitor_service import extract_domain_from_url, ping_icmp

def test_extract_domain():
    """Test extract domain function"""
    print("🧪 Testing extract_domain_from_url()")
    
    test_cases = [
        "10.0.1.11",
        "http://10.0.1.11", 
        "https://10.0.1.11",
        "glx.com.vn",
        "http://glx.com.vn",
        "https://mytree.vn/path"
    ]
    
    for url in test_cases:
        domain = extract_domain_from_url(url)
        print(f"  {url:25s} -> {domain}")

def test_ping_icmp():
    """Test ping ICMP function"""
    print("\n🧪 Testing ping_icmp()")
    
    hosts = [
        "10.0.1.11",
        "8.8.8.8",
        "127.0.0.1",
        "invalid-host"
    ]
    
    for host in hosts:
        print(f"\nTesting ping to {host}...")
        success, response_time, message = ping_icmp(host, timeout=3)
        
        if success:
            print(f"  ✅ {message} (Time: {response_time:.2f}ms)")
        else:
            print(f"  ❌ {message}")

def test_urlparse():
    """Test Python's urlparse for different formats"""
    print("\n🧪 Testing urlparse behavior")
    
    test_cases = [
        "10.0.1.11",
        "http://10.0.1.11", 
        "https://10.0.1.11"
    ]
    
    for url in test_cases:
        parsed = urlparse(url)
        print(f"  URL: {url}")
        print(f"    scheme: '{parsed.scheme}'")
        print(f"    netloc: '{parsed.netloc}'")
        print(f"    hostname: '{parsed.hostname}'")
        print(f"    path: '{parsed.path}'")
        print()

if __name__ == "__main__":
    test_extract_domain()
    test_ping_icmp()
    test_urlparse()
