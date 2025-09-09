#!/usr/bin/env python3
"""
Simple test để đọc domains.txt
"""

import os

def test_domains_file():
    domains_file = 'domains.txt'
    domains = []
    
    try:
        with open(domains_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    domains.append(line)
        
        print(f"✅ Loaded {len(domains)} domains from {domains_file}")
        
        if domains:
            print(f"First 5: {domains[:5]}")
            print(f"Last 5: {domains[-5:]}")
            
            # Check duplicates
            unique = set(domains)
            if len(unique) == len(domains):
                print("✅ No duplicates found")
            else:
                print(f"⚠️ Found {len(domains) - len(unique)} duplicates")
        
        return domains
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    print("🧪 Testing domains.txt file...")
    domains = test_domains_file()
    print(f"📊 Result: {len(domains)} domains ready for use")
