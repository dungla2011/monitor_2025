"""
Quick check for set_monitor_refs signature compatibility
"""

import inspect

# Mock classes to test signature
class MockMonitorAPI:
    def __init__(self):
        pass
    
    def set_monitor_refs(self, running_threads, thread_alert_managers, 
                        get_all_monitor_items, shutdown_event):
        """New signature with thread_alert_managers"""
        print("✅ NEW signature called successfully!")
        return True

class OldMockMonitorAPI:
    def __init__(self):
        pass
    
    def set_monitor_refs(self, running_threads, thread_consecutive_errors, 
                        thread_last_alert_time, get_all_monitor_items, shutdown_event):
        """Old signature with separate dictionaries"""
        print("❌ OLD signature called!")
        return False

def test_signature_compatibility():
    """Test which signature is expected"""
    print("🔍 Testing set_monitor_refs signature compatibility...\n")
    
    # Test new API
    new_api = MockMonitorAPI()
    try:
        new_api.set_monitor_refs(
            running_threads={},
            thread_alert_managers={},
            get_all_monitor_items=lambda: [],
            shutdown_event=None
        )
    except Exception as e:
        print(f"❌ New signature failed: {e}")
    
    # Test what happens with old parameters
    try:
        new_api.set_monitor_refs(
            running_threads={},
            thread_consecutive_errors={},  # Old parameter
            thread_last_alert_time={},     # Old parameter
            get_all_monitor_items=lambda: [],
            shutdown_event=None
        )
    except TypeError as e:
        print(f"✅ Expected error with old parameters: {e}")

def check_current_signature():
    """Check the actual signature in single_instance_api.py"""
    print("\n🔍 Checking actual signature in files...")
    
    try:
        with open('single_instance_api.py', 'r') as f:
            content = f.read()
            
        if 'thread_alert_managers' in content:
            print("✅ single_instance_api.py has NEW signature")
        elif 'thread_consecutive_errors' in content:
            print("⚠️ single_instance_api.py might have OLD signature")
        else:
            print("❓ Cannot determine signature in single_instance_api.py")
            
        # Check specific function signature
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'def set_monitor_refs(' in line:
                # Get full signature (might span multiple lines)
                sig_lines = []
                j = i
                while j < len(lines) and not lines[j].strip().endswith('):'):
                    sig_lines.append(lines[j].strip())
                    j += 1
                if j < len(lines):
                    sig_lines.append(lines[j].strip())
                
                full_signature = ' '.join(sig_lines)
                print(f"\n📝 Current signature:")
                print(f"   {full_signature}")
                
                if 'thread_alert_managers' in full_signature:
                    print("✅ Signature is NEW (correct)")
                elif 'thread_consecutive_errors' in full_signature:
                    print("❌ Signature is OLD (needs update)")
                break
                
    except FileNotFoundError:
        print("❌ single_instance_api.py not found")
    except Exception as e:
        print(f"❌ Error checking file: {e}")

def solution_summary():
    """Print solution for the server error"""
    print("\n" + "="*50)
    print("🔧 SOLUTION FOR SERVER ERROR:")
    print("="*50)
    print("The error 'unexpected keyword argument thread_consecutive_errors'")
    print("means the server code has mismatched signatures between:")
    print("  • monitor_service.py (calling with OLD parameters)")
    print("  • single_instance_api.py (expecting NEW parameters)")
    print()
    print("✅ SOLUTION:")
    print("1. Make sure BOTH files use the NEW signature")
    print("2. monitor_service.py should call:")
    print("   api.set_monitor_refs(")
    print("       running_threads=running_threads,")
    print("       thread_alert_managers=thread_alert_managers,")
    print("       get_all_monitor_items=get_all_monitor_items,")
    print("       shutdown_event=shutdown_event")
    print("   )")
    print("3. single_instance_api.py should have:")
    print("   def set_monitor_refs(self, running_threads, thread_alert_managers,")
    print("                       get_all_monitor_items, shutdown_event):")
    print()
    print("📁 Files to verify on server:")
    print("   • monitor_service.py (around line 326)")
    print("   • single_instance_api.py (around line 305)")
    print("   • utils.py (should have class_send_alert_of_thread)")

if __name__ == "__main__":
    test_signature_compatibility()
    check_current_signature()
    solution_summary()
