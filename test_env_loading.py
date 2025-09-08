#!/usr/bin/env python3
"""
Test script to check environment loading
"""
import sys
import os
from dotenv import load_dotenv

print("="*50)
print("TESTING ENVIRONMENT LOADING")
print("="*50)

print(f"Command line arguments: {sys.argv}")

# Check if --test argument exists
if '--test' in sys.argv or 'test' in sys.argv:
    print("🧪 TEST MODE detected - Loading test environment (.env.test)")
    load_dotenv('.env.test')
    print("✅ Loaded .env.test")
else:
    print("📦 PRODUCTION MODE - Loading default environment (.env)")
    load_dotenv()
    print("✅ Loaded .env")

print("\n" + "="*50)
print("ENVIRONMENT VARIABLES:")
print("="*50)

# Check key environment variables
vars_to_check = [
    'HTTP_PORT',
    'HTTP_HOST', 
    'DB_NAME',
    'DB_HOST',
    'DB_PORT',
    'ADMIN_DOMAIN'
]

for var in vars_to_check:
    value = os.getenv(var, 'NOT_SET')
    print(f"{var:15} = {value}")

print("\n" + "="*50)
print("CONCLUSION:")
print("="*50)

http_port = os.getenv('HTTP_PORT', '5005')
db_name = os.getenv('DB_NAME', 'NOT_SET')

if '--test' in sys.argv or 'test' in sys.argv:
    if http_port == '5006' and db_name == 'monitor_test':
        print("✅ SUCCESS: Test environment loaded correctly!")
    else:
        print("❌ FAILED: Test environment not loaded properly!")
        print(f"   Expected: HTTP_PORT=5006, DB_NAME=monitor_test")
        print(f"   Got: HTTP_PORT={http_port}, DB_NAME={db_name}")
else:
    if http_port == '5005':
        print("✅ SUCCESS: Production environment loaded correctly!")
    else:
        print("❌ FAILED: Production environment not loaded properly!")
