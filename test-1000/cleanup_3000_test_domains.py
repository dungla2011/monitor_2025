#!/usr/bin/env python3
"""
Script cleanup 3000 test domains sau khi performance testing
Xóa tất cả records có tên bắt đầu với TEST_3K_
"""

import sys
import os
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load test environment
print("🧪 Loading test environment (.env.test)")
load_dotenv(os.path.join('..', '.env.test'))

from sqlalchemy.orm import sessionmaker
from db_connection import engine
from models import MonitorItem

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def cleanup_3000_test_domains():
    """Xóa tất cả 3K test domains"""
    session = SessionLocal()
    try:
        # Count test domains before cleanup
        test_count = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).count()
        
        if test_count == 0:
            print("ℹ️ No 3K test records found to clean up")
            return True
        
        print(f"🗑️ Found {test_count} 3K test records to delete")
        
        # Show breakdown by type
        monitor_types = ['web_content', 'ping_icmp', 'ssl_expired_check']
        print("\n📊 Breakdown by type:")
        for monitor_type in monitor_types:
            count = session.query(MonitorItem).filter(
                MonitorItem.name.like('TEST_3K_%'),
                MonitorItem.type == monitor_type
            ).count()
            print(f"   - {monitor_type}: {count} records")
        
        print(f"\n⚠️ This will delete {test_count} test records from database...")
        response = input("❓ Continue with deletion? (y/N): ").lower().strip()
        
        if response not in ['y', 'yes']:
            print("❌ Cleanup cancelled by user")
            return False
        
        # Delete all 3K test domains
        print("🗑️ Deleting 3K test records...")
        deleted = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).delete()
        
        session.commit()
        print(f"✅ Successfully deleted {deleted} 3K test records")
        
        # Verify cleanup
        remaining = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_3K_%')
        ).count()
        
        if remaining == 0:
            print("🎉 All 3K test records cleaned up successfully!")
        else:
            print(f"⚠️ Warning: {remaining} 3K test records still remain")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def show_stats():
    """Hiển thị thống kê"""
    session = SessionLocal()
    try:
        total_items = session.query(MonitorItem).count()
        test_3k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_3K_%')).count()
        test_1k_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).count()
        
        print(f"\n📊 Database statistics:")
        print(f"   - Total monitor items: {total_items}")
        print(f"   - TEST_3K items: {test_3k_items}")
        print(f"   - TEST_ items (1K test): {test_1k_items}")
        
        if test_3k_items > 0:
            load_per_second = test_3k_items / 60
            print(f"   - Current 3K test load: ~{load_per_second:.1f} checks/second")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        session.close()

def main():
    """Main function"""
    print("=" * 60)
    print("🧹 CLEANUP 3000 TEST RECORDS")
    print("   Clean up TEST_3K_ test records after performance testing")
    print("=" * 60)
    
    # Show current stats
    show_stats()
    
    # Perform cleanup
    success = cleanup_3000_test_domains()
    
    if success:
        show_stats()
        print("\n✅ 3K test records cleanup completed successfully!")
        print("\n💡 Tips:")
        print("   - Regular TEST_ records (1K test) are not affected")
        print("   - You can now run other performance tests")
        print("   - Monitor service should have reduced load")
    else:
        print("\n❌ 3K test records cleanup failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
