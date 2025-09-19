#!/usr/bin/env python3
"""
Debug subprocess startup for AsyncIO service
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import time
import requests
import os

def test_subprocess_startup():
    print("🧪 Testing subprocess startup...")
    
    try:
        # Start subprocess exactly like in test (NO CONSOLE để capture output)
        print("   📋 Starting subprocess: python monitor_service_asyncio.py start --test")
        
        # Set environment to handle Unicode properly
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen([
            "python", "monitor_service_asyncio.py", "start", "--test"
        ], 
        cwd="..",  # Run from parent directory
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True  # Get text output instead of bytes
        )
        
        print(f"   🆔 Process ID: {process.pid}")
        print("   ⏱️ Waiting 3 seconds...")
        time.sleep(3)
        
        # Check if process is still running
        poll_result = process.poll()
        if poll_result is None:
            print("   ✅ Process still running")
            
            # Try to get partial output while running
            try:
                # Non-blocking read of available output (won't work on Windows)
                print("   📤 Getting partial output...")
            except:
                pass
                
        else:
            print(f"   ❌ Process exited with code: {poll_result}")
            # Get output
            stdout, stderr = process.communicate()
            if stdout:
                print(f"   📤 STDOUT:\n{stdout}")
            if stderr:
                print(f"   📤 STDERR:\n{stderr}")
            return False
        
        # Test connection
        print("   🔍 Testing connection to http://localhost:5006...")
        try:
            response = requests.get("http://localhost:5006/api/status", timeout=3)
            print(f"   📡 Response: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ❌ Connection failed")
        except Exception as e:
            print(f"   ⚠️ Connection error: {e}")
        
        # Wait a bit more
        print("   ⏱️ Waiting 5 more seconds...")  
        time.sleep(5)
        
        # Test connection again
        print("   🔍 Testing connection again...")
        try:
            response = requests.get("http://localhost:5006/api/status", timeout=3)
            print(f"   📡 Response: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ❌ Connection still failed")
        except Exception as e:
            print(f"   ⚠️ Connection error: {e}")
        
        # Check process status again
        poll_result = process.poll()
        if poll_result is None:
            print("   ✅ Process still running after 8 seconds")
            
            # Try to terminate gracefully and get output
            print("   🛑 Terminating process...")
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
                print("   📤 Final STDOUT:")
                if stdout:
                    print(f"{stdout}")
                else:
                    print("   (no stdout)")
                    
                print("   📤 Final STDERR:")
                if stderr:
                    print(f"{stderr}")
                else:
                    print("   (no stderr)")
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                print("   💀 Process killed forcefully")
                if stdout:
                    print(f"   📤 STDOUT: {stdout}")
                if stderr:
                    print(f"   📤 STDERR: {stderr}")
            
            print("   ✅ Process terminated")
            return True
        else:
            print(f"   ❌ Process exited during wait with code: {poll_result}")
            stdout, stderr = process.communicate()
            if stdout:
                print(f"   📤 STDOUT:\n{stdout}")
            if stderr:
                print(f"   📤 STDERR:\n{stderr}")
            return False
            
    except Exception as e:
        print(f"   💥 Exception: {e}")
        return False

if __name__ == "__main__":
    success = test_subprocess_startup()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")