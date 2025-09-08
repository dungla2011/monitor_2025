#!/usr/bin/env python3
"""
Monitor Service Master Test Runner
Chạy tất cả các test của monitoring system
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def print_banner():
    """Print test banner"""
    print("="*80)
    print("🧪 MONITOR SERVICE COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🖥️  Platform: {sys.platform}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("="*80)

def check_service_status():
    """Check if monitor service is running"""
    print("\n🔍 Checking Monitor Service Status...")
    
    try:
        import requests
        response = requests.get('http://127.0.0.1:5005/api/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Monitor service is running (uptime: {data.get('uptime', 'N/A')})")
            return True
        else:
            print(f"⚠️ Monitor service responding with status {response.status_code}")
            return False
    except ImportError:
        print("⚠️ requests module not available - cannot check service status")
        return False
    except:
        print("❌ Monitor service is not responding")
        return False

def run_test_script(script_name, description):
    """Run a test script and return success status"""
    print(f"\n🔧 {description}")
    print("-" * 60)
    
    if not os.path.exists(script_name):
        print(f"⚠️ Test script {script_name} not found - skipping")
        return True  # Don't fail if optional test is missing
    
    try:
        # Run the test script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def run_basic_health_check():
    """Run basic health checks without external scripts"""
    print(f"\n🩺 Basic Health Check")
    print("-" * 60)
    
    checks_passed = 0
    total_checks = 0
    
    # Check 1: Python modules
    total_checks += 1
    try:
        import sqlalchemy
        import flask
        import requests
        import psutil
        print("✅ Required Python modules available")
        checks_passed += 1
    except ImportError as e:
        print(f"❌ Missing Python module: {e}")
    
    # Check 2: Environment file
    total_checks += 1
    if os.path.exists('.env'):
        print("✅ .env file exists")
        checks_passed += 1
    else:
        print("❌ .env file not found")
    
    # Check 3: Database modules
    total_checks += 1
    try:
        from db_connection import engine
        from models import MonitorItem
        print("✅ Database modules can be imported")
        checks_passed += 1
    except Exception as e:
        print(f"❌ Database module error: {e}")
    
    # Check 4: Utility modules
    total_checks += 1
    try:
        from utils import ol1, format_response_time
        print("✅ Utility modules can be imported")
        checks_passed += 1
    except Exception as e:
        print(f"❌ Utility module error: {e}")
    
    # Check 5: Main service module
    total_checks += 1
    try:
        from monitor_service import check_service
        print("✅ Main service modules can be imported")
        checks_passed += 1
    except Exception as e:
        print(f"❌ Main service module error: {e}")
    
    print(f"\n📊 Health Check: {checks_passed}/{total_checks} checks passed")
    return checks_passed == total_checks

def run_quick_functional_test():
    """Run quick functional tests"""
    print(f"\n⚡ Quick Functional Test")
    print("-" * 60)
    
    try:
        from monitor_service import ping_web, ping_icmp
        
        # Test ping_web
        print("🔄 Testing ping_web...")
        success, status_code, response_time, message = ping_web('https://google.com', timeout=10)
        if success:
            print(f"✅ ping_web: {message} ({response_time:.2f}ms)")
        else:
            print(f"⚠️ ping_web: {message}")
        
        # Test ping_icmp  
        print("🔄 Testing ping_icmp...")
        success, response_time, message = ping_icmp('8.8.8.8', timeout=10)
        if success:
            print(f"✅ ping_icmp: {message} ({response_time:.2f}ms)")
        else:
            print(f"⚠️ ping_icmp: {message}")
        
        print("✅ Quick functional test completed")
        return True
        
    except Exception as e:
        print(f"❌ Quick functional test failed: {e}")
        return False

def print_test_instructions():
    """Print instructions for manual testing"""
    print(f"\n📋 Manual Testing Instructions")
    print("-" * 60)
    print("1. 🌐 Open browser and visit: http://127.0.0.1:5005")
    print("2. 📊 Check dashboard displays correctly")
    print("3. 🔧 Test API endpoints:")
    print("   - http://127.0.0.1:5005/api/status")
    print("   - http://127.0.0.1:5005/api/monitors")
    print("   - http://127.0.0.1:5005/api/threads")
    print("4. 📱 Test Telegram notifications (if configured)")
    print("5. 💾 Check database for test data")
    print("6. 📁 Check logs folder for log files")

def print_summary(all_passed, service_running):
    """Print final test summary"""
    print("\n" + "="*80)
    print("🎯 TEST SUMMARY")
    print("="*80)
    
    print(f"📊 Overall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print(f"🔧 Service Status: {'✅ RUNNING' if service_running else '❌ NOT RUNNING'}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if all_passed and service_running:
        print("\n🎉 Monitor Service is ready for production!")
    elif all_passed and not service_running:
        print("\n✅ All tests passed, but service is not running")
        print("   Start the service with: python monitor_service.py start")
    else:
        print("\n⚠️ Please fix the failed tests before deploying")
    
    print("\n📚 Next Steps:")
    print("   • Review any failed tests above")
    print("   • Check logs for detailed error information")
    print("   • Ensure all environment variables are set correctly")
    print("   • Verify database connection and tables exist")
    print("   • Test manually using the web dashboard")
    
    print("="*80)

def main():
    """Main test runner"""
    print_banner()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Monitor Service Master Test Runner")
            print("Usage:")
            print("  python run_all_tests.py              - Run all available tests")
            print("  python run_all_tests.py --quick      - Run only quick tests")
            print("  python run_all_tests.py --help       - Show this help")
            return
        elif sys.argv[1] == '--quick':
            print("🚀 Running QUICK tests only...")
            quick_mode = True
        else:
            print(f"Unknown option: {sys.argv[1]}")
            return
    else:
        quick_mode = False
    
    # Check service status
    service_running = check_service_status()
    
    # Run basic health check
    health_passed = run_basic_health_check()
    
    if not health_passed:
        print("\n❌ Basic health check failed - cannot continue with advanced tests")
        print("   Please fix the basic issues first")
        print_summary(False, service_running)
        return
    
    # Run quick functional test
    quick_passed = run_quick_functional_test()
    
    all_passed = health_passed and quick_passed
    
    if not quick_mode:
        print(f"\n🔧 Running Advanced Tests...")
        
        # List of test scripts to run
        test_scripts = [
            ('test_monitor_features.py', 'Comprehensive Feature Tests'),
        ]
        
        # Only run performance tests if service is running
        if service_running:
            test_scripts.append(('test_performance.py', 'Performance Tests'))
        else:
            print("⚠️ Skipping performance tests - service not running")
        
        # Run each test script
        for script_name, description in test_scripts:
            script_passed = run_test_script(script_name, description)
            if not script_passed:
                all_passed = False
            time.sleep(2)  # Brief pause between tests
    
    # Print manual testing instructions
    print_test_instructions()
    
    # Print final summary
    print_summary(all_passed, service_running)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
