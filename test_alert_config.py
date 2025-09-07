#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script cho hệ thống alert config mới
"""

import os
import sys
from dotenv import load_dotenv
from models import (
    MonitorItem, MonitorConfig, MonitorAndConfig,
    get_telegram_config_for_monitor_item,
    get_all_alert_configs_for_monitor_item,
    SessionLocal
)

def test_database_structure():
    """Test xem có thể kết nối và query các bảng mới không"""
    try:
        session = SessionLocal()
        
        print("🔍 Testing database structure...")
        
        # Test query monitor_configs
        configs = session.query(MonitorConfig).all()
        print(f"   📊 Found {len(configs)} monitor configs")
        
        # Test query monitor_and_configs
        relations = session.query(MonitorAndConfig).all()
        print(f"   🔗 Found {len(relations)} monitor-config relations")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database structure test failed: {e}")
        return False

def test_telegram_config_functions():
    """Test các hàm lấy telegram config"""
    try:
        session = SessionLocal()
        
        print("\n🤖 Testing Telegram config functions...")
        
        # Lấy monitor items để test
        monitor_items = session.query(MonitorItem).filter(MonitorItem.enable == True).all()
        
        if not monitor_items:
            print("   ⚠️ No enabled monitor items found")
            session.close()
            return False
            
        print(f"   📋 Testing with {len(monitor_items)} enabled monitor items:")
        
        for item in monitor_items:
            print(f"\n   🔍 Testing item: {item.name} (ID: {item.id})")
            
            # Test get telegram config
            telegram_config = get_telegram_config_for_monitor_item(item.id)
            if telegram_config:
                print(f"      ✅ Telegram config found:")
                print(f"         Bot Token: {telegram_config['bot_token'][:20]}...")
                print(f"         Chat ID: {telegram_config['chat_id']}")
            else:
                print(f"      ❌ No Telegram config found")
                
            # Test get all alert configs
            all_configs = get_all_alert_configs_for_monitor_item(item.id)
            if all_configs:
                print(f"      📊 Total alert configs: {len(all_configs)}")
                for config in all_configs:
                    print(f"         - {config['name']}: {config['alert_type']}")
            else:
                print(f"      📭 No alert configs found")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Telegram config test failed: {e}")
        return False

def create_sample_data():
    """Tạo dữ liệu mẫu để test"""
    try:
        session = SessionLocal()
        
        print("\n🏗️ Creating sample data...")
        
        # Tạo sample monitor config
        sample_config = MonitorConfig(
            name='Telegram Alert Default',
            alert_type='telegram',
            alert_config='8040174107:AAE-XqU-XaV0Y7v30pjZgbfGzHq88LQx0HQ,-4878499254'
        )
        
        session.add(sample_config)
        session.commit()
        
        config_id = sample_config.id
        print(f"   ✅ Created sample config with ID: {config_id}")
        
        # Lấy monitor item đầu tiên để link
        first_item = session.query(MonitorItem).filter(MonitorItem.enable == True).first()
        
        if first_item:
            # Tạo relation
            relation = MonitorAndConfig(
                monitor_item_id=first_item.id,
                config_id=config_id
            )
            
            session.add(relation)
            session.commit()
            
            print(f"   ✅ Created relation: Monitor Item {first_item.id} -> Config {config_id}")
        else:
            print("   ⚠️ No enabled monitor items found to link")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Sample data creation failed: {e}")
        return False

def main():
    # Load environment variables
    load_dotenv()
    
    print("🧪 Testing Alert Config System")
    print("=" * 50)
    
    # Test 1: Database structure
    db_ok = test_database_structure()
    
    # Test 2: Telegram config functions
    config_ok = test_telegram_config_functions()
    
    if not config_ok:
        print("\n💡 Tip: Run with 'create' argument to create sample data")
        if len(sys.argv) > 1 and sys.argv[1].lower() == 'create':
            create_sample_data()
            print("\n🔄 Re-testing after creating sample data...")
            config_ok = test_telegram_config_functions()
    
    print("\n📊 Test Summary:")
    print(f"   Database Structure: {'✅' if db_ok else '❌'}")
    print(f"   Config Functions: {'✅' if config_ok else '❌'}")
    
    if db_ok and config_ok:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check database setup.")

if __name__ == "__main__":
    main()
