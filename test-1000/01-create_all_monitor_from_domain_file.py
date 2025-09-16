#!/usr/bin/env python3
"""
Script tạo 3000 domain test cho performance testing
Với mỗi domain sẽ tạo 3 loại test: web_content, ping_icmp, ssl_expired_check
1000 domains x 3 types = 3000 test records
"""

import sys
import time
import os
import argparse
import random
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to Python path to import modules
domains_file = sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load test environment
print("🧪 Loading test environment (.env)")
load_dotenv(os.path.join('..', '.env'))

from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Create session factory
SessionLocal = sessionmaker(bind=engine)

domains_file = os.path.join(os.path.dirname(__file__), '3000-domains-timeout-10s.txt')


def load_domains_from_file(domains_file):
    """Load domains từ file domains.txt"""
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
    domains_list = load_domains_from_file(domains_file=domains_file)
    
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

def create_test_domains(target_type=None, target_count=3000):
    """Tạo test records với type được chỉ định hoặc random"""
    if target_type:
        print(f"🚀 Starting to create {target_count} test domains with type: {target_type}")
    else:
        print(f"🚀 Starting to create {target_count} test domains with random types...")
    
    # Load all available domains
    all_domains = load_domains_from_file(domains_file)
    print(f"📝 Loaded {len(all_domains)} domains from file")
    
    # 3 loại monitor type available
    monitor_types = ['web_content', 'ping_icmp', 'ssl_expired_check']
    
    # Validate target_type if provided
    if target_type and target_type not in monitor_types:
        print(f"❌ Invalid type '{target_type}'. Available types: {', '.join(monitor_types)}")
        return False
    
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
            try:
                session.commit()
                print("✅ Old test domains cleaned up")
            except Exception as cleanup_error:
                print(f"⚠️ Cleanup error: {cleanup_error}")
                session.rollback()
        
        created_count = 0
        current_time = datetime.now()
        
        print(f"📝 Creating {target_count} test records...")
        
        # Tạo records lần lượt từ domain list
        for record_idx in range(target_count):
            try:
                # Chọn domain theo thứ tự, cycle through nếu hết
                domain = all_domains[record_idx % len(all_domains)]
                
                # Chọn monitor type
                if target_type:
                    monitor_type = target_type
                else:
                    # Random type nếu không chỉ định
                    monitor_type = random.choice(monitor_types)
                
                # Tạo URL dựa trên monitor type
                if monitor_type == 'web_content':
                    url_check = f"https://{domain}"
                elif monitor_type == 'ping_icmp':
                    url_check = domain  # Chỉ domain cho ICMP ping
                elif monitor_type == 'ssl_expired_check':
                    url_check = f"https://{domain}"
                
                # Tạo unique name cho mỗi record
                record_number = record_idx + 1
                
                # Tạo MonitorItem - không set forceRestart để dùng default
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
                    count_offline=0
                    # Không set forceRestart để database dùng default value
                )
                
                session.add(monitor_item)
                created_count += 1
                
                # Commit theo batch nhỏ hơn để tránh SQL timeout
                if created_count % 50 == 0:
                    try:
                        session.commit()
                        print(f"✅ Created {created_count}/{target_count} test records...")
                    except Exception as commit_error:
                        print(f"⚠️ Commit error at batch {created_count}: {commit_error}")
                        session.rollback()
                        # Continue with next batch
                    
            except Exception as e:
                print(f"⚠️ Error creating record {record_idx + 1}: {e}")
                session.rollback()
                continue
        
        # Final commit
        try:
            session.commit()
        except Exception as final_commit_error:
            print(f"⚠️ Final commit error: {final_commit_error}")
            session.rollback()
        print(f"🎉 Successfully created {created_count} test records!")
        
        # Thống kê chi tiết
        print("\n📊 Test records statistics:")
        for monitor_type in monitor_types:
            count = session.query(MonitorItem).filter(
                MonitorItem.name.like('TEST_3K_%'),
                MonitorItem.type == monitor_type
            ).count()
            if count > 0:
                print(f"   - {monitor_type}: {count} records")
        
        total_test = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).count()
        print(f"   - Total TEST_3K records: {total_test}")
        
        # Tính toán load
        if total_test > 0:
            checks_per_second = total_test / 60  # interval = 60 seconds
            print(f"   - Expected load: ~{checks_per_second:.1f} checks/second")
        
        # Show first few examples
        print("\n📋 Sample test records:")
        samples = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).limit(3).all()
        
        for sample in samples:
            print(f"   {sample.type}: {sample.name}")
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Create test monitor records from domain file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py                          # Create 3000 records with random types
  python script.py --type web_content       # Create 3000 web_content records
  python script.py --type ping_icmp --count 1000  # Create 1000 ping_icmp records
  python script.py --count 500              # Create 500 records with random types
        """
    )
    
    parser.add_argument(
        '--type', 
        choices=['web_content', 'ping_icmp', 'ssl_expired_check'],
        help='Specify monitor type (if not provided, types will be random)'
    )
    
    parser.add_argument(
        '--count', 
        type=int, 
        default=3000,
        help='Number of test records to create (default: 3000)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    if args.type:
        print(f"🧪 CREATE {args.count} TEST RECORDS - TYPE: {args.type}")
    else:
        print(f"🧪 CREATE {args.count} TEST RECORDS - RANDOM TYPES")
    print("   Sequential domains from domain file, no duplicates")
    print("=" * 70)
    
    # Show current stats
    show_current_stats()
    
    # Show configuration
    print(f"\n📋 Configuration:")
    print(f"   - Target count: {args.count} records")
    print(f"   - Monitor type: {args.type if args.type else 'random (web_content, ping_icmp, ssl_expired_check)'}")
    print(f"   - Check interval: 60 seconds")
    print(f"   - Expected load: ~{args.count/60:.1f} checks/second")
    
    # Confirm with user
    print(f"\n⚠️  WARNING: This will create {args.count} test records in your database!")
    print("   - Domains will be used sequentially from domains.txt file")
    print("   - Each record with check_interval_seconds = 60")
    print("   - This will generate load on your system")
    print("   - Old 3K test records (name starting with TEST_3K_) will be deleted")
    
    if args.type:
        print(f"\n🎯 MONITOR TYPE: {args.type}")
        if args.type == 'web_content':
            print("   - HTTP content checking")
        elif args.type == 'ping_icmp':
            print("   - ICMP ping testing")
        elif args.type == 'ssl_expired_check':
            print("   - SSL certificate monitoring")
    else:
        print("\n🎲 RANDOM TYPES:")
        print("   - web_content: HTTP content checking")
        print("   - ping_icmp: ICMP ping testing")
        print("   - ssl_expired_check: SSL certificate monitoring")
    
    response = input(f"\n❓ Continue with {args.count} records creation? (y/N): ").lower().strip()
    
    if response not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return 0
    
    # Create test domains
    success = create_test_domains(target_type=args.type, target_count=args.count)
    
    if success:
        print(f"\n✅ {args.count} test records creation completed!")
        show_current_stats()
        
        print("\n🚀 Next steps:")
        print("   1. Start monitor service: python monitor_service.py start --test")
        print("   2. Monitor system resources closely (CPU, Memory, Network)")
        print("   3. Check for any performance bottlenecks")
        print("   4. Monitor database connection pool")
        print("   5. Clean up test data when done")
        
        print("\n🧹 To clean up test records later:")
        print("   python cleanup_3000_test_domains.py")
        print("   OR SQL: DELETE FROM monitor_items WHERE name LIKE 'TEST_3K_%';")
        
        print(f"\n⚠️  PERFORMANCE WARNING:")
        print(f"   - {args.count} concurrent checks may impact your system")
        print("   - Monitor CPU and memory usage carefully")
        print("   - Consider reducing check intervals if needed")
        
    else:
        print(f"\n❌ Failed to create {args.count} test records")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
