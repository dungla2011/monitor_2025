#!/usr/bin/env python3
"""
Script tạo 1000 domain test cho performance testing
Tạo 1000 hàng test demo trong monitor_items với interval 60 giây
"""

import sys
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load test environment
print("🧪 Loading test environment (.env.test)")
load_dotenv(os.path.join('..', '.env.test'))

from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def load_domains_from_file():
    """Load domains từ file domains.txt"""
    domains_file = os.path.join(os.path.dirname(__file__), 'domains.txt')
    domains = []
    
    try:
        with open(domains_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    domains.append(line)
        
        print(f"📁 Loaded {len(domains)} domains from domains.txt")
        return domains
        
    except FileNotFoundError:
        print(f"❌ File not found: {domains_file}")
        print("📝 Using fallback domain list...")
        # Fallback domains nếu file không tồn tại
        return [
            'google.com', 'microsoft.com', 'amazon.com', 'apple.com', 'meta.com',
            'netflix.com', 'tesla.com', 'nvidia.com', 'intel.com', 'amd.com'
        ] * 100  # Repeat để có 1000 domain
    except Exception as e:
        print(f"❌ Error reading domains file: {e}")
        return []

def generate_1000_domains():
    """Tạo 1000 domain từ domains.txt - remove duplicates và đảm bảo đúng 1000"""
    
    # Load domains từ file
    domains_list = load_domains_from_file()
    
    if not domains_list:
        print("❌ No domains loaded!")
        return []
    
    print(f"📝 Processing {len(domains_list)} domains from file...")
    
    # Remove duplicates giữ thứ tự
    unique_domains = []
    seen = set()
    for domain in domains_list:
        if domain not in seen:
            unique_domains.append(domain)
            seen.add(domain)
    
    print(f"✅ Removed duplicates: {len(unique_domains)} unique domains")
    
    # Nếu không đủ 1000, thêm domain backup
    if len(unique_domains) < 1000:
        needed = 1000 - len(unique_domains)
        print(f"⚠️ Need {needed} more domains, adding backup domains...")
        
        backup_domains = [
            'example.com', 'test.com', 'demo.com', 'sample.com', 'placeholder.com',
            'dummysite.com', 'fakesite.com', 'tempsite.com', 'mocksite.com', 'emptysite.com',
            'blanksite.com', 'voidsite.com', 'nullsite.com', 'zerosite.com', 'onesite.com',
            'twosite.com', 'threesite.com', 'foursite.com', 'fivesite.com', 'sixsite.com'
        ]
        
        # Thêm backup domains với prefix để tránh duplicate
        for i in range(needed):
            if i < len(backup_domains):
                unique_domains.append(f"test{i+1}.{backup_domains[i % len(backup_domains)]}")
            else:
                unique_domains.append(f"backup{i+1}.example.com")
    
    # Chỉ lấy đúng 1000 domain đầu tiên
    final_domains = unique_domains[:1000]
    print(f"🎯 Final: {len(final_domains)} domains ready")
    
    return final_domains

def create_test_domains():
    """Tạo 1000 test domains trong database"""
    print("🚀 Starting to create 1000 test domains...")
    
    # Generate domains
    domains = generate_1000_domains()
    print(f"📝 Generated {len(domains)} domains")
    
    # Các loại monitor type để test
    monitor_types = ['ping_web', 'ping_icmp', 'web_content', 'open_port_tcp_then_error', 
                    'open_port_tcp_then_valid', 'ssl_expired_check']
    
    session = SessionLocal()
    try:
        # Xóa các test domain cũ (nếu có)
        print("🗑️ Cleaning up old test domains...")
        old_test_items = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).all()
        
        if old_test_items:
            print(f"🗑️ Found {len(old_test_items)} old test domains, deleting...")
            for item in old_test_items:
                session.delete(item)
        
        created_count = 0
        current_time = datetime.now()
        
        print("📝 Creating new test domains...")
        for i, domain in enumerate(domains, 1):
            try:
                # Chọn monitor type theo vòng tròn
                monitor_type = monitor_types[i % len(monitor_types)]
                
                # Tạo URL dựa trên monitor type
                if monitor_type in ['ping_web', 'web_content', 'ssl_expired_check']:
                    url_check = f"https://{domain}"
                elif monitor_type == 'ping_icmp':
                    url_check = domain  # Chỉ domain cho ICMP ping
                elif monitor_type in ['open_port_tcp_then_error', 'open_port_tcp_then_valid']:
                    # Sử dụng port 80 và 443 xen kẽ
                    port = 443 if i % 2 == 0 else 80
                    url_check = f"{domain}:{port}"
                
                # Tạo MonitorItem
                monitor_item = MonitorItem(
                    name=f"TEST_PERF_{i:04d}_{domain}",
                    enable=1,  # Enable để test performance
                    url_check=url_check,
                    type=monitor_type,
                    check_interval_seconds=60,  # 60 giây như yêu cầu
                    maxAlertCount=5,
                    user_id=0,
                    created_at=current_time,
                    updated_at=current_time,
                    last_check_status=None,  # Chưa check lần nào
                    pingType=1,
                    count_online=0,
                    count_offline=0,
                    forceRestart=False
                )
                
                session.add(monitor_item)
                created_count += 1
                
                # Commit theo batch để tránh timeout
                if created_count % 100 == 0:
                    session.commit()
                    print(f"✅ Created {created_count}/1000 test domains...")
                    
            except Exception as e:
                print(f"⚠️ Error creating domain {domain}: {e}")
                continue
        
        # Final commit
        session.commit()
        print(f"🎉 Successfully created {created_count} test domains!")
        
        # Thống kê
        print("\n📊 Test domain statistics:")
        for monitor_type in monitor_types:
            count = session.query(MonitorItem).filter(
                MonitorItem.name.like('TEST_%'),
                MonitorItem.type == monitor_type
            ).count()
            print(f"   - {monitor_type}: {count} domains")
        
        total_test = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).count()
        print(f"   - Total TEST domains: {total_test}")
        
        # Show first few examples
        print("\n📋 First 5 test domains:")
        first_domains = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).limit(5).all()
        
        for item in first_domains:
            print(f"   - {item.name} | {item.type} | {item.url_check} | interval: {item.check_interval_seconds}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        return False
    finally:
        session.close()
    
    return True

def show_current_stats():
    """Hiển thị thống kê hiện tại"""
    session = SessionLocal()
    try:
        total_items = session.query(MonitorItem).count()
        enabled_items = session.query(MonitorItem).filter(MonitorItem.enable == 1).count()
        test_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).count()
        
        print(f"\n📊 Current database statistics:")
        print(f"   - Total monitor items: {total_items}")
        print(f"   - Enabled items: {enabled_items}")
        print(f"   - Test items: {test_items}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        session.close()

def main():
    """Main function"""
    print("=" * 60)
    print("🧪 CREATE 1000 TEST DOMAINS FOR PERFORMANCE TESTING")
    print("=" * 60)
    
    # Show current stats
    show_current_stats()
    
    # Confirm with user
    print("\n⚠️  WARNING: This will create 1000 test domains in your database!")
    print("   - Each domain will have check_interval_seconds = 60")
    print("   - This will generate significant load on your system")
    print("   - Old test domains (name starting with TEST_) will be deleted")
    
    response = input("\n❓ Continue? (y/N): ").lower().strip()
    
    if response not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return
    
    # Create test domains
    success = create_test_domains()
    
    if success:
        print("\n✅ Test domain creation completed!")
        show_current_stats()
        
        print("\n🚀 Next steps:")
        print("   1. Start the monitor service: python monitor_service.py start --test")
        print("   2. Monitor system resources during the test")
        print("   3. Check logs for performance metrics")
        print("   4. Clean up test data when done")
        
        print("\n🧹 To clean up test domains later:")
        print("   DELETE FROM monitor_items WHERE name LIKE 'TEST_%';")
    else:
        print("\n❌ Failed to create test domains")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
