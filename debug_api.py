#!/usr/bin/env python3
"""
Test isolated để debug API server
"""

import sys
import threading
import time

def test_flask_basic():
    """Test Flask cơ bản"""
    print("🧪 Testing basic Flask...")
    
    try:
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def hello():
            return "Hello World!"
        
        print("✅ Flask imported and app created successfully")
        
        # Test WSGI server
        from wsgiref.simple_server import make_server
        server = make_server('127.0.0.1', 8888, app)
        
        print("✅ WSGI server created successfully")
        
        # Start server in thread
        def run_server():
            print("🌐 Starting test server on http://127.0.0.1:8888")
            server.serve_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait a bit
        time.sleep(2)
        
        # Test request
        import requests
        response = requests.get("http://127.0.0.1:8888", timeout=5)
        if response.status_code == 200:
            print("✅ Test request successful:", response.text)
        else:
            print("❌ Test request failed:", response.status_code)
            
        server.shutdown()
        print("✅ Server shutdown successfully")
        
    except Exception as e:
        print(f"❌ Flask basic test failed: {e}")
        import traceback
        traceback.print_exc()

def test_monitor_api():
    """Test MonitorAPI class"""
    print("\n🧪 Testing MonitorAPI class...")
    
    try:
        # Add current directory to path
        import os
        sys.path.insert(0, os.getcwd())
        
        from single_instance_api import MonitorAPI
        print("✅ MonitorAPI import successful")
        
        api = MonitorAPI(host="127.0.0.1", port=8889)
        print("✅ MonitorAPI instance created")
        
        # Start in thread
        def run_api():
            api.start_server()
        
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        
        time.sleep(3)
        
        # Test request
        import requests
        response = requests.get("http://127.0.0.1:8889/api/status", timeout=5)
        if response.status_code == 200:
            print("✅ API test successful")
            data = response.json()
            print(f"   Status: {data.get('status')}")
        else:
            print(f"❌ API test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ MonitorAPI test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flask_basic()
    test_monitor_api()
