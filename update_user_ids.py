"""
Script to update user_id in monitor_items table
Logic: Every 10 rows get the same user_id (1-10: user_id=1, 11-20: user_id=2, etc.)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import database modules
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from db_connection import engine
from models import MonitorItem

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_user_ids():
    """Update user_id for all monitor items - 10 rows per user_id"""
    
    session = SessionLocal()
    try:
        print("🔄 Starting user_id update process...")
        
        # Get all monitor items ordered by id
        items = session.query(MonitorItem).order_by(MonitorItem.id).all()
        total_items = len(items)
        
        print(f"📊 Found {total_items} monitor items")
        
        if total_items == 0:
            print("❌ No monitor items found!")
            return
        
        # Update user_id theo logic: 10 hàng/user_id
        updated_count = 0
        batch_size = 100  # Commit every 100 updates
        
        for index, item in enumerate(items):
            # Calculate user_id: (index // 10) + 1
            # index 0-9 -> user_id = 1
            # index 10-19 -> user_id = 2, etc.
            new_user_id = (index // 10) + 1
            
            if item.user_id != new_user_id:
                old_user_id = item.user_id
                item.user_id = new_user_id
                updated_count += 1
                
                if updated_count % 50 == 0:
                    print(f"📝 Updated {updated_count} items... (Item {item.id}: {old_user_id} -> {new_user_id})")
            
            # Commit in batches
            if (index + 1) % batch_size == 0:
                session.commit()
                print(f"💾 Committed batch at item {index + 1}")
        
        # Final commit
        session.commit()
        
        # Verify results
        print("\n🔍 Verifying update results...")
        user_counts = {}
        for item in session.query(MonitorItem).order_by(MonitorItem.id).all():
            if item.user_id not in user_counts:
                user_counts[item.user_id] = 0
            user_counts[item.user_id] += 1
        
        print(f"✅ Update completed! {updated_count} items updated")
        print(f"📊 Total users created: {len(user_counts)}")
        
        # Show first few user counts
        print("\n📈 Sample user distribution:")
        for user_id in sorted(user_counts.keys())[:10]:
            print(f"   User {user_id}: {user_counts[user_id]} items")
        
        if len(user_counts) > 10:
            print(f"   ... and {len(user_counts) - 10} more users")
            
        # Show expected vs actual
        expected_users = (total_items + 9) // 10  # Round up
        print(f"\n🎯 Expected users: {expected_users}, Actual users: {len(user_counts)}")
        
    except Exception as e:
        print(f"❌ Error updating user_ids: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def show_sample_data():
    """Show sample of current user_id distribution"""
    session = SessionLocal()
    try:
        print("📋 Current user_id distribution (first 50 items):")
        items = session.query(MonitorItem).order_by(MonitorItem.id).limit(50).all()
        
        current_user = None
        count_in_group = 0
        
        for item in items:
            if item.user_id != current_user:
                if current_user is not None:
                    print(f"   User {current_user}: {count_in_group} items")
                current_user = item.user_id
                count_in_group = 1
            else:
                count_in_group += 1
                
        if current_user is not None:
            print(f"   User {current_user}: {count_in_group} items")
            
    except Exception as e:
        print(f"❌ Error showing sample data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Monitor Items User ID Updater")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_sample_data()
    else:
        print("This will update user_id for ALL monitor items.")
        print("Logic: Every 10 consecutive items get the same user_id")
        print("Example: Items 1-10 = user_id:1, Items 11-20 = user_id:2, etc.")
        print("")
        
        confirm = input("Continue? (y/N): ").lower().strip()
        if confirm == 'y':
            update_user_ids()
        else:
            print("❌ Operation cancelled")
    
    print("\nUse --show flag to view current distribution without updating")
