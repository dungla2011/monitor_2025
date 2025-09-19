#!/usr/bin/env python3
"""
Test ping3 implementation
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from async_monitor_checks import ping_icmp_async

class MockMonitorItem:
    def __init__(self, url_check):
        self.url_check = url_check

async def test_ping3():
    """Test ping3 implementation"""
    print("🏓 Testing ping3 implementation...")
    
    test_hosts = [
        "8.8.8.8",  # Google DNS - should work
        "1.1.1.1",  # Cloudflare DNS - should work  
        "google.com",  # Domain name - should work
        "192.168.1.1",  # Router - may work
        "invalid-host-12345.com"  # Should fail
    ]
    
    for host in test_hosts:
        print(f"\n🎯 Testing: {host}")
        monitor_item = MockMonitorItem(host)
        
        try:
            result = await ping_icmp_async(monitor_item)
            
            if result['success']:
                print(f"✅ Success: {result['message']}")
                print(f"   Response time: {result['response_time']:.1f}ms")
                if result['details'].get('retry_attempts', 0) > 0:
                    print(f"   Retries: {result['details']['retry_attempts']}")
            else:
                print(f"❌ Failed: {result['message']}")
                if result['details'].get('retry_attempts', 0) > 0:
                    print(f"   Retries: {result['details']['retry_attempts']}")
                    
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print("\n✅ ping3 test completed!")

if __name__ == "__main__":
    asyncio.run(test_ping3())