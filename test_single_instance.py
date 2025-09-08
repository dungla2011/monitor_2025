"""
Test script để kiểm tra Single Instance và HTTP API
"""

import time
import requests
import subprocess
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_single_instance():
    """Test single instance functionality"""
    print("🧪 Testing Single Instance Manager...")
    print("=" * 60)
    
    # Test 1: Start service
    print("1. Starting first instance...")
    try:
        proc1 = subprocess.Popen([
            sys.executable, "monitor_service.py", "start"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a bit for service to start
        time.sleep(5)
        
        print("   ✅ First instance started")
        
        # Test 2: Try to start second instance (should fail)
        print("2. Trying to start second instance (should be blocked)...")
        proc2 = subprocess.Popen([
            sys.executable, "monitor_service.py", "start"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout2, stderr2 = proc2.communicate(timeout=10)
        print(f"   Second instance output: {stdout2.strip()}")
        
        if "already running" in stdout2:
            print("   ✅ Second instance correctly blocked")
        else:
            print("   ❌ Second instance not blocked properly")
            
        # Test 3: Check status
        print("3. Checking service status...")
        proc_status = subprocess.Popen([
            sys.executable, "monitor_service.py", "status"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout_status, stderr_status = proc_status.communicate(timeout=10)
        print(f"   Status output: {stdout_status.strip()}")
        
        # Test 4: Test API endpoints
        print("4. Testing API endpoints...")
        test_api_endpoints()
        
        # Test 5: Stop service
        print("5. Stopping service...")
        proc_stop = subprocess.Popen([
            sys.executable, "monitor_service.py", "stop"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout_stop, stderr_stop = proc_stop.communicate(timeout=10)
        print(f"   Stop output: {stdout_stop.strip()}")
        
        # Cleanup
        proc1.terminate()
        proc1.wait()
        
    except Exception as e:
        print(f"❌ Test error: {e}")

def test_api_endpoints():
    """Test HTTP API endpoints"""
    port = os.getenv('HTTP_PORT', '5005')
    host = os.getenv('HTTP_HOST', '127.0.0.1')
    base_url = f"http://{host}:{port}"
    
    endpoints = [
        ("/", "Dashboard"),
        ("/api/status", "Status API"),
        ("/api/monitors", "Monitors API"),
        ("/api/threads", "Threads API"),
        ("/api/logs", "Logs API")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK ({response.status_code})")
            else:
                print(f"   ⚠️ {name}: {response.status_code}")
        except requests.RequestException as e:
            print(f"   ❌ {name}: Connection failed ({e})")

def test_lock_file():
    """Test lock file functionality"""
    print("🔒 Testing lock file functionality...")
    print("=" * 60)
    
    from single_instance_api import SingleInstanceManager
    
    # Test lock file creation and cleanup
    manager = SingleInstanceManager("test_monitor.lock", 5001)
    
    # Should not be running initially
    is_running, pid, port = manager.is_already_running()
    print(f"1. Initial state - Running: {is_running}")
    
    # Create lock file
    success = manager.create_lock_file()
    print(f"2. Lock file created: {success}")
    
    # Check if now detected as running
    is_running, pid, port = manager.is_already_running()
    print(f"3. After lock - Running: {is_running}, PID: {pid}, Port: {port}")
    
    # Cleanup
    manager.cleanup()
    print("4. Cleanup completed")
    
    # Check if properly cleaned up
    is_running, pid, port = manager.is_already_running()
    print(f"5. After cleanup - Running: {is_running}")
    
    print("✅ Lock file test completed")

def main():
    print("🚀 Single Instance & HTTP API Test Suite")
    print("=" * 60)
    
    # Check if virtual environment is activated
    if 'venv' not in sys.executable:
        print("⚠️ Warning: Virtual environment might not be activated")
        print(f"   Python executable: {sys.executable}")
    
    # Test 1: Lock file functionality  
    test_lock_file()
    print()
    
    # Test 2: Single instance functionality
    test_single_instance()
    
    print("\n🏁 Test suite completed!")

if __name__ == "__main__":
    main()
