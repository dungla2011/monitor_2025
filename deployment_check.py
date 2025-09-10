#!/usr/bin/env python3
"""
Script to verify and fix the monitor service alert manager integration
This script will ensure all files have the correct code for server deployment
"""

import os
import sys
from pathlib import Path

def check_and_show_diff():
    """Check all files and show what needs to be synced to server"""
    
    print("🔍 CHECKING LOCAL FILES FOR SERVER DEPLOYMENT")
    print("=" * 60)
    
    issues = []
    
    # 1. Check monitor_service.py
    print("\n📋 1. Checking monitor_service.py...")
    try:
        with open('monitor_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check import
        if 'class_send_alert_of_thread' in content:
            print("   ✅ Has class_send_alert_of_thread import")
        else:
            print("   ❌ Missing class_send_alert_of_thread import")
            issues.append("monitor_service.py: Missing class import")
        
        # Check thread_alert_managers declaration
        if 'thread_alert_managers = {}' in content:
            print("   ✅ Has thread_alert_managers declaration")
        else:
            print("   ❌ Missing thread_alert_managers declaration")
            issues.append("monitor_service.py: Missing alert managers dict")
        
        # Check set_monitor_refs call
        if 'thread_alert_managers=thread_alert_managers' in content:
            print("   ✅ Calls set_monitor_refs with NEW parameters")
        else:
            print("   ❌ Still using OLD parameters in set_monitor_refs call")
            issues.append("monitor_service.py: Using old parameters")
            
        # Check for old dictionaries (should NOT exist)
        old_dicts = ['telegram_last_sent_of_each_thread = {}', 
                    'thread_consecutive_errors = {}', 
                    'thread_last_alert_time = {}']
        for old_dict in old_dicts:
            if old_dict in content:
                print(f"   ❌ Still has old dictionary: {old_dict}")
                issues.append(f"monitor_service.py: Has old dict {old_dict}")
            else:
                print(f"   ✅ Removed old dictionary: {old_dict.split('=')[0].strip()}")
        
    except Exception as e:
        print(f"   ❌ Error reading monitor_service.py: {e}")
        issues.append("monitor_service.py: Read error")
    
    # 2. Check single_instance_api.py  
    print("\n📋 2. Checking single_instance_api.py...")
    try:
        with open('single_instance_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check set_monitor_refs signature
        if 'def set_monitor_refs(self, running_threads, thread_alert_managers,' in content:
            print("   ✅ Has NEW set_monitor_refs signature")
        elif 'def set_monitor_refs(self, running_threads, thread_consecutive_errors,' in content:
            print("   ❌ Still has OLD set_monitor_refs signature")
            issues.append("single_instance_api.py: Old signature")
        else:
            print("   ❓ Cannot find set_monitor_refs signature")
            issues.append("single_instance_api.py: Missing signature")
        
        # Check __init__ method
        if 'self.thread_alert_managers = None' in content:
            print("   ✅ __init__ has thread_alert_managers attribute")
        else:
            print("   ❌ __init__ missing thread_alert_managers attribute")
            issues.append("single_instance_api.py: Missing attribute in __init__")
            
    except Exception as e:
        print(f"   ❌ Error reading single_instance_api.py: {e}")
        issues.append("single_instance_api.py: Read error")
    
    # 3. Check utils.py
    print("\n📋 3. Checking utils.py...")
    try:
        with open('utils.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'class class_send_alert_of_thread:' in content:
            print("   ✅ Has class_send_alert_of_thread definition")
            
            # Check key methods
            methods = ['can_send_telegram_alert', 'mark_telegram_sent', 
                      'increment_consecutive_error', 'reset_consecutive_error']
            for method in methods:
                if f'def {method}(' in content:
                    print(f"   ✅ Has method: {method}")
                else:
                    print(f"   ❌ Missing method: {method}")
                    issues.append(f"utils.py: Missing method {method}")
        else:
            print("   ❌ Missing class_send_alert_of_thread definition")
            issues.append("utils.py: Missing class definition")
            
    except Exception as e:
        print(f"   ❌ Error reading utils.py: {e}")
        issues.append("utils.py: Read error")
    
    # Summary
    print("\n" + "=" * 60)
    if not issues:
        print("🎉 ALL FILES ARE READY FOR SERVER DEPLOYMENT!")
        print("\n📤 FILES TO UPLOAD TO SERVER:")
        print("   • monitor_service.py")  
        print("   • single_instance_api.py")
        print("   • utils.py")
        print("\n🚀 After upload, restart the service on server.")
    else:
        print("❌ ISSUES FOUND - NEED TO FIX BEFORE DEPLOYMENT:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    return len(issues) == 0

def show_server_commands():
    """Show commands to run on server after file upload"""
    print("\n" + "=" * 60)
    print("📋 COMMANDS TO RUN ON SERVER AFTER FILE UPLOAD:")
    print("=" * 60)
    print("1. Stop current service:")
    print("   sudo pkill -f monitor_service.py")
    print()
    print("2. Upload these 3 files to /var/www/monitor_v2/:")
    print("   • monitor_service.py")
    print("   • single_instance_api.py") 
    print("   • utils.py")
    print()
    print("3. Start service again:")
    print("   cd /var/www/monitor_v2")
    print("   source venv/bin/activate") 
    print("   python3 monitor_service.py manager")
    print()
    print("4. Check for success (should NOT see the error anymore):")
    print("   ✅ Should see: 'API server initialized successfully'")
    print("   ❌ Should NOT see: 'unexpected keyword argument thread_consecutive_errors'")

if __name__ == "__main__":
    print("🔧 MONITOR SERVICE - SERVER DEPLOYMENT CHECKER")
    print("This script verifies files are ready for server deployment")
    
    all_good = check_and_show_diff()
    show_server_commands()
    
    if all_good:
        print(f"\n✅ Ready to deploy! Exit code: 0")
        sys.exit(0)
    else:
        print(f"\n❌ Fix issues first! Exit code: 1") 
        sys.exit(1)
