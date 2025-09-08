#!/usr/bin/env python3
"""
Test script để kiểm tra web_content functionality
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import MonitorItem
from monitor_service import check_web_content, fetch_web_content
from utils import ol1

def test_fetch_web_content():
    """Test basic web content fetching"""
    print("\n" + "="*60)
    print("🧪 Testing fetch_web_content function")
    print("="*60)
    
    test_url = "httpbin.org/html"
    
    success, status_code, response_time, content, message = fetch_web_content(test_url)
    
    print(f"URL: {test_url}")
    print(f"Success: {success}")
    print(f"Status Code: {status_code}")
    print(f"Response Time: {response_time:.2f}ms")
    print(f"Content Length: {len(content)} chars")
    print(f"Message: {message}")
    
    if success and content:
        print(f"Content Preview (first 200 chars):")
        print(f"'{content[:200]}...'")
    
    return success

def test_web_content_check():
    """Test web content checking with keywords"""
    print("\n" + "="*60)
    print("🧪 Testing check_web_content function")
    print("="*60)
    
    # Create a mock MonitorItem
    monitor_item = MonitorItem()
    monitor_item.id = 999
    monitor_item.name = "Test Web Content"
    monitor_item.url_check = "httpbin.org/html"
    monitor_item.type = "web_content"
    monitor_item.result_valid = "html, Herman Melville"  # Should be found in httpbin.org/html
    monitor_item.result_error = "404, error"  # Should not be found
    
    print(f"Monitor Item: {monitor_item.name}")
    print(f"URL: {monitor_item.url_check}")
    print(f"Required Keywords: {monitor_item.result_valid}")
    print(f"Error Keywords: {monitor_item.result_error}")
    
    result = check_web_content(monitor_item)
    
    print(f"\nResult:")
    print(f"Success: {result['success']}")
    print(f"Response Time: {result['response_time']:.2f}ms" if result['response_time'] else "N/A")
    print(f"Message: {result['message']}")
    print(f"Details: {result['details']}")
    
    return result['success']

def test_web_content_error_case():
    """Test web content with error keywords"""
    print("\n" + "="*60)
    print("🧪 Testing web content with error detection")
    print("="*60)
    
    # Create a mock MonitorItem that should fail
    monitor_item = MonitorItem()
    monitor_item.id = 998
    monitor_item.name = "Test Error Detection"
    monitor_item.url_check = "httpbin.org/status/500"  # This returns 500 status
    monitor_item.type = "web_content"
    monitor_item.result_valid = ""  # No required keywords
    monitor_item.result_error = ""  # No error keywords for now
    
    print(f"Monitor Item: {monitor_item.name}")
    print(f"URL: {monitor_item.url_check}")
    print(f"Expected: Should fail due to 500 status")
    
    result = check_web_content(monitor_item)
    
    print(f"\nResult:")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    
    return not result['success']  # Should return True if it correctly detected error

def main():
    """Run all tests"""
    print("🚀 Starting Web Content Tests")
    
    tests = [
        ("Basic Fetch", test_fetch_web_content),
        ("Content Check", test_web_content_check),
        ("Error Detection", test_web_content_error_case),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
            print(f"\n✅ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n❌ {test_name}: ERROR - {e}")
    
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        if error:
            status += f" (Error: {error})"
        print(f"{status:12} {test_name}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
