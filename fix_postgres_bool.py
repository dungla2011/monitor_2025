#!/usr/bin/env python3
"""
Fix PostgreSQL Boolean Compatibility
Sửa tất cả enable == True thành enable == 1 cho PostgreSQL compatibility
"""

import os
import re
from pathlib import Path

def fix_enable_comparisons(file_path):
    """Fix enable == True to enable == 1 in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Track changes
        original = content
        
        # Fix various patterns
        patterns = [
            (r'MonitorItem\.enable\s*==\s*True', 'MonitorItem.enable == 1'),
            (r'enable\s*=\s*True(?=[\s,\)])', 'enable=1'),  # Function parameters
            (r'filter_by\(enable=True\)', 'filter_by(enable=1)'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Only write if changed
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all Python files"""
    print("🔧 Fixing PostgreSQL Boolean compatibility...")
    
    # Get all Python files
    python_files = []
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"📋 Found {len(python_files)} Python files")
    
    # Fix each file
    fixed_count = 0
    for file_path in python_files:
        if fix_enable_comparisons(file_path):
            print(f"✅ Fixed: {file_path}")
            fixed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   📁 Total files: {len(python_files)}")
    print(f"   ✅ Fixed files: {fixed_count}")
    print(f"   ❌ No changes: {len(python_files) - fixed_count}")
    
    if fixed_count > 0:
        print("\n🎉 PostgreSQL compatibility fixes applied!")
        print("💡 Now enable == 1 instead of enable == True")
    else:
        print("\n✅ No files needed fixing")

if __name__ == "__main__":
    main()
