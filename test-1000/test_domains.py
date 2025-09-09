#!/usr/bin/env python3
"""
Quick test script để kiểm tra domains.txt và functions
"""

import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from current directory
from create_1000_test_domains import load_domains_from_file, generate_1000_domains

def main():
    print("=" * 60)
    print("🧪 QUICK TEST DOMAINS.TXT")
    print("=" * 60)
    
    # Test load domains
    print("📁 Testing load_domains_from_file()...")
    domains = load_domains_from_file()
    print(f"   Loaded: {len(domains)} domains")
    
    if domains:
        print(f"   First 5: {domains[:5]}")
        print(f"   Last 5: {domains[-5:]}")
    
    # Test generate 1000 domains
    print("\n🎯 Testing generate_1000_domains()...")
    final_domains = generate_1000_domains()
    
    if final_domains:
        print(f"   Generated: {len(final_domains)} domains")
        
        # Check for duplicates
        unique_check = set(final_domains)
        if len(unique_check) == len(final_domains):
            print("   ✅ No duplicates found!")
        else:
            duplicates = len(final_domains) - len(unique_check)
            print(f"   ⚠️ Found {duplicates} duplicates")
        
        # Show sample
        print(f"   Sample: {final_domains[:3]} ... {final_domains[-3:]}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main()
