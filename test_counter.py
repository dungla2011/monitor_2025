#!/usr/bin/env python3
"""
Test Counter functionality
"""
import time
import requests
from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def test_counter():
    """Test counter functionality"""
    print("🧪 Testing Counter Functionality")
    print("=" * 50)
    
    # Get monitor items from database
    session = SessionLocal()
    items = session.query(MonitorItem).filter(
        MonitorItem.url_check.isnot(None),
        MonitorItem.url_check != '',
        MonitorItem.enable == 1
    ).limit(3).all()
    
    if not items:
        print("❌ No enabled monitor items found")
        session.close()
        return
    
    print(f"📊 Found {len(items)} enabled monitor items:")
    for item in items:
        print(f"   - ID: {item.id}, Name: {item.name}")
        print(f"     count_online: {item.count_online}, count_offline: {item.count_offline}")
    
    session.close()
    
    # Test API endpoint
    try:
        print("\n🌐 Testing API endpoint...")
        response = requests.get('http://127.0.0.1:5005/api/monitors', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response OK - Found {len(data.get('monitors', []))} monitors")
            
            for monitor in data.get('monitors', []):
                if monitor.get('enabled'):
                    print(f"   📈 ID {monitor['id']}: Success={monitor.get('count_online', 0)}, Failed={monitor.get('count_offline', 0)}")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API Connection Error: {e}")
    
    print("\n✅ Counter test completed!")

if __name__ == "__main__":
    test_counter()
