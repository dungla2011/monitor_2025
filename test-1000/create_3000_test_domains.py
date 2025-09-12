#!/usr/bin/env python3
"""
Script tạo 3000 domain test cho performance testing
Với mỗi domain sẽ tạo 3 loại test: web_content, ping_icmp, ssl_expired_check
1000 domains x 3 types = 3000 test records
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

def generate_1000_unique_domains():
    """Tạo đúng 1000 domain unique từ domains.txt"""
    
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
            'blanksite.com', 'voidsite.com', 'nullsite.com', 'zerosite.com', 'onesite.com'
        ]
        
        # Thêm backup domains với prefix để tránh duplicate
        for i in range(needed):
            backup_domain = backup_domains[i % len(backup_domains)]
            unique_domains.append(f"test{i+1}.{backup_domain}")
    
    # Chỉ lấy đúng 1000 domain đầu tiên
    final_domains = unique_domains[:1000]
    print(f"🎯 Final: {len(final_domains)} unique domains ready")
    
    return final_domains

def create_3000_test_domains():
    """Tạo 3000 test records (1000 domains x 3 types) trong database"""
    print("🚀 Starting to create 3000 test domains (1000 domains x 3 types)...")
    
    # Generate 1000 unique domains
    domains = generate_1000_unique_domains()
    print(f"📝 Will use {len(domains)} unique domains")
    
    # 3 loại monitor type cần test
    monitor_types = ['web_content', 'ping_icmp', 'ssl_expired_check']
    
    session = SessionLocal()
    try:
        # Xóa các test domain cũ (nếu có)
        print("🗑️ Cleaning up old test domains...")
        old_test_items = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).all()
        
        if old_test_items:
            print(f"🗑️ Found {len(old_test_items)} old 3K test domains, deleting...")
            for item in old_test_items:
                session.delete(item)
            session.commit()
        
        created_count = 0
        current_time = datetime.now()
        
        print("📝 Creating 3000 test records...")
        
        # Tạo 3 record cho mỗi domain (web_content, ping_icmp, ssl_expired_check)
        for domain_idx, domain in enumerate(domains, 1):
            for type_idx, monitor_type in enumerate(monitor_types, 1):
                try:
                    # Tạo URL dựa trên monitor type
                    if monitor_type == 'web_content':
                        url_check = f"https://{domain}"
                    elif monitor_type == 'ping_icmp':
                        url_check = domain  # Chỉ domain cho ICMP ping
                    elif monitor_type == 'ssl_expired_check':
                        url_check = f"https://{domain}"
                    
                    # Tạo unique name cho mỗi record
                    record_number = (domain_idx - 1) * 3 + type_idx
                    
                    # Tạo MonitorItem
                    monitor_item = MonitorItem(
                        name=f"TEST_3K_{record_number:04d}_{domain}_{monitor_type}",
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
                    if created_count % 200 == 0:
                        session.commit()
                        print(f"✅ Created {created_count}/3000 test records...")
                        
                except Exception as e:
                    print(f"⚠️ Error creating {monitor_type} for domain {domain}: {e}")
                    continue
        
        # Final commit
        session.commit()
        print(f"🎉 Successfully created {created_count} test records!")
        
        # Thống kê chi tiết
        print("\n📊 Test records statistics:")
        for monitor_type in monitor_types:
            count = session.query(MonitorItem).filter(
                MonitorItem.name.like('TEST_3K_%'),
                MonitorItem.type == monitor_type
            ).count()
            print(f"   - {monitor_type}: {count} records")
        
        total_test = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).count()
        print(f"   - Total TEST_3K records: {total_test}")
        
        # Tính toán load
        if total_test > 0:
            checks_per_second = total_test / 60  # interval = 60 seconds
            print(f"   - Expected load: ~{checks_per_second:.1f} checks/second")
        
        # Show first few examples for each type
        print("\n📋 Sample test records:")
        for monitor_type in monitor_types:
            sample = session.query(MonitorItem).filter(
                MonitorItem.name.like('TEST_3K_%'),
                MonitorItem.type == monitor_type
            ).first()
            
            if sample:
                print(f"   {monitor_type}: {sample.name}")
                print(f"      URL: {sample.url_check}")
                print(f"      Interval: {sample.check_interval_seconds}s")
        
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
        test_3k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_3K_%')).count()
        test_1k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).count()
        
        print(f"\n📊 Current database statistics:")
        print(f"   - Total monitor items: {total_items}")
        print(f"   - Enabled items: {enabled_items}")
        print(f"   - TEST_3K items (3000 test): {test_3k_items}")
        print(f"   - TEST_ items (1000 test): {test_1k_items}")
        
        if test_3k_items > 0:
            load_per_second = test_3k_items / 60
            print(f"   - 3K Test load: ~{load_per_second:.1f} checks/second")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        session.close()

def main():
    """Main function"""
    print("=" * 70)
    print("🧪 CREATE 3000 TEST RECORDS FOR INTENSIVE PERFORMANCE TESTING")
    print("   1000 domains x 3 types (web_content, ping_icmp, ssl_expired_check)")
    print("=" * 70)
    
    # Show current stats
    show_current_stats()
    
    # Confirm with user
    print("\n⚠️  WARNING: This will create 3000 test records in your database!")
    print("   - 1000 domains x 3 monitor types = 3000 records")
    print("   - Each record with check_interval_seconds = 60")
    print("   - Expected load: ~50 checks/second (3000 ÷ 60)")
    print("   - This will generate SIGNIFICANT load on your system")
    print("   - Old 3K test records (name starting with TEST_3K_) will be deleted")
    
    print("\n🔥 PERFORMANCE TEST TYPES:")
    print("   - web_content: HTTP content checking")
    print("   - ping_icmp: ICMP ping testing")
    print("   - ssl_expired_check: SSL certificate monitoring")
    
    response = input("\n❓ Continue with 3000 records creation? (y/N): ").lower().strip()
    
    if response not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return 0
    
    # Create test domains
    success = create_3000_test_domains()
    
    if success:
        print("\n✅ 3000 test records creation completed!")
        show_current_stats()
        
        print("\n🚀 Next steps:")
        print("   1. Start monitor service: python monitor_service.py start --test")
        print("   2. Monitor system resources closely (CPU, Memory, Network)")
        print("   3. Check for any performance bottlenecks")
        print("   4. Monitor database connection pool")
        print("   5. Clean up test data when done")
        
        print("\n🧹 To clean up 3K test records later:")
        print("   python cleanup_3000_test_domains.py")
        print("   OR SQL: DELETE FROM monitor_items WHERE name LIKE 'TEST_3K_%';")
        
        print("\n⚠️  PERFORMANCE WARNING:")
        print("   - 3000 concurrent checks may overwhelm your system")
        print("   - Monitor CPU and memory usage carefully")
        print("   - Consider reducing check intervals if needed")
        
    else:
        print("\n❌ Failed to create 3000 test records")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
