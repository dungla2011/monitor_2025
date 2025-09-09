#!/usr/bin/env python3
"""
Script cleanup 1000 test domains sau khi performance testing
"""

import sys
import os
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

def cleanup_test_domains():
    """Xóa tất cả test domains"""
    session = SessionLocal()
    try:
        # Count test domains before cleanup
        test_count = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).count()
        
        if test_count == 0:
            print("ℹ️ No test domains found to clean up")
            return True
        
        print(f"🗑️ Found {test_count} test domains to delete")
        
        # Delete all test domains
        deleted = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).delete()
        
        session.commit()
        print(f"✅ Successfully deleted {deleted} test domains")
        
        # Verify cleanup
        remaining = session.query(MonitorItem).filter(
            MonitorItem.name.like('TEST_%')
        ).count()
        
        if remaining == 0:
            print("🎉 All test domains cleaned up successfully!")
        else:
            print(f"⚠️ Warning: {remaining} test domains still remain")
        
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
        test_items = session.query(MonitorItem).filter(MonitorItem.name.like('TEST_%')).count()
        
        print(f"\n📊 Database statistics:")
        print(f"   - Total monitor items: {total_items}")
        print(f"   - Test items: {test_items}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
    finally:
        session.close()

def main():
    """Main function"""
    print("=" * 50)
    print("🧹 CLEANUP 1000 TEST DOMAINS")
    print("=" * 50)
    
    # Show current stats
    show_stats()
    
    # Confirm with user
    print("\n⚠️  WARNING: This will delete ALL test domains!")
    print("   - All monitor items with name starting with 'TEST_' will be deleted")
    print("   - This action cannot be undone")
    
    response = input("\n❓ Continue with cleanup? (y/N): ").lower().strip()
    
    if response not in ['y', 'yes']:
        print("❌ Cleanup cancelled by user")
        return 0
    
    # Perform cleanup
    success = cleanup_test_domains()
    
    if success:
        show_stats()
        print("\n✅ Cleanup completed successfully!")
    else:
        print("\n❌ Cleanup failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
