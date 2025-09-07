#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test ping ICMP function
"""

import time
import subprocess
import platform
from datetime import datetime

def ping_icmp_debug(host, timeout=5):
    """
    Debug version của ping ICMP
    """
    try:
        print(f"🔍 Testing ICMP ping to: {host}")
        print(f"   OS: {platform.system()}")
        print(f"   Timeout: {timeout} seconds")
        
        # Xác định command ping dựa trên OS
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout), host]
        
        print(f"   Command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        print(f"   Execution time: {response_time:.2f}ms")
        print(f"   Return code: {result.returncode}")
        print(f"   STDOUT:")
        print(f"     {result.stdout}")
        print(f"   STDERR:")  
        print(f"     {result.stderr}")
        
        if result.returncode == 0:
            print("   ✅ SUCCESS")
            return True, response_time, "Ping successful"
        else:
            stderr_output = result.stderr.strip() if result.stderr else "No error details"
            print(f"   ❌ FAILED: {stderr_output}")
            return False, None, f"Ping failed (code {result.returncode}): {stderr_output}"
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ TIMEOUT after {timeout} seconds")
        return False, None, f"Ping timeout after {timeout} seconds"
    except Exception as e:
        print(f"   ❌ EXCEPTION: {str(e)}")
        return False, None, f"Ping error: {str(e)}"

def main():
    print("🧪 Testing ping_icmp function")
    print("=" * 50)
    
    hosts = [
        "glx.com.vn",
        "google.com", 
        "8.8.8.8",
        "nonexistent-domain-12345.com"  # Test failure case
    ]
    
    for host in hosts:
        print()
        success, response_time, message = ping_icmp_debug(host, timeout=5)
        print(f"Result: {success}, {response_time}, {message}")
        print("-" * 50)

if __name__ == "__main__":
    main()
