#!/usr/bin/env python3
"""
Script to fix .env.test path in test files
"""
import os
import re
from pathlib import Path

def fix_env_path_in_test_files():
    """Fix .env.test path in test files to use correct relative path"""
    
    test_files = [
        'tests/05.test-enable-disable.py',
        'tests/06.test-webhook-alerts.py', 
        'tests/07.test-telegram-alerts.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📝 Fixing {test_file}")
            
            # Read file content
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix .env.test path (from tests/ folder need ../.env.test)
            old_pattern = r"load_dotenv\('\.env\.test'\)"
            new_replacement = "load_dotenv('../.env.test')"
            
            # Also fix .env.telegram path if exists
            old_telegram = r"telegram_file = '\.env\.telegram'"
            new_telegram = "telegram_file = '../.env.telegram'"
            
            # Apply replacements
            updated_content = re.sub(old_pattern, new_replacement, content)
            updated_content = re.sub(old_telegram, new_telegram, updated_content)
            
            # Write back if changed
            if content != updated_content:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"   ✅ Updated .env paths in {test_file}")
            else:
                print(f"   ℹ️  No changes needed in {test_file}")
        else:
            print(f"   ❌ File not found: {test_file}")

if __name__ == "__main__":
    print("🔧 Fixing .env.test paths in test files...")
    fix_env_path_in_test_files()
    print("\n✅ Path fixing complete!")
