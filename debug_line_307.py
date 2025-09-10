"""
Debug script to check exact line 307 in monitor_service.py
"""

def check_line_307():
    """Check what's at line 307"""
    import os
    filepath = 'monitor_service.py'
    abs_path = os.path.abspath(filepath)
    print(f"📁 Reading file: {abs_path}")
    print(f"📊 File exists: {os.path.exists(filepath)}")
    print(f"📏 File size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'} bytes")
    
    try:
        with open('monitor_service.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print("🔍 Checking line 307 in monitor_service.py...")
        print(f"📏 Total lines in file: {len(lines)}")
        
        if len(lines) >= 307:
            print(f"\n📍 Line 307: {repr(lines[306])}")  # 306 because 0-indexed
            print(f"📝 Line 307 content: {lines[306].strip()}")
            
            # Show context around line 307
            print(f"\n📋 Context around line 307:")
            start = max(0, 306-3)  # 3 lines before
            end = min(len(lines), 306+4)  # 3 lines after
            
            for i in range(start, end):
                marker = " >>> " if i == 306 else "     "
                print(f"{i+1:3d}{marker}{lines[i].rstrip()}")
                
        else:
            print(f"❌ File only has {len(lines)} lines, line 307 does not exist!")
            
        # Check for set_monitor_refs calls
        print(f"\n🔍 Searching for set_monitor_refs calls...")
        for i, line in enumerate(lines):
            if 'set_monitor_refs(' in line:
                print(f"📍 Line {i+1}: {line.strip()}")
                
                # Show the full call (might span multiple lines)
                j = i
                full_call = []
                paren_count = 0
                while j < len(lines):
                    line_part = lines[j].strip()
                    full_call.append(line_part)
                    paren_count += line_part.count('(') - line_part.count(')')
                    if paren_count <= 0 and ')' in line_part:
                        break
                    j += 1
                
                print(f"📝 Full call:")
                for k, call_line in enumerate(full_call):
                    print(f"    {i+k+1}: {call_line}")
                print()
                
    except Exception as e:
        print(f"❌ Error reading file: {e}")

def check_imports():
    """Check class_send_alert_of_thread import"""
    try:
        with open('monitor_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 Checking imports...")
        if 'class_send_alert_of_thread' in content:
            print("✅ class_send_alert_of_thread is imported")
        else:
            print("❌ class_send_alert_of_thread is NOT imported")
            
        if 'thread_alert_managers' in content:
            print("✅ thread_alert_managers is used")
        else:
            print("❌ thread_alert_managers is NOT used")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🐛 DEBUGGING LINE 307 ERROR")
    print("="*50)
    check_line_307()
    print("\n" + "="*50)  
    check_imports()
