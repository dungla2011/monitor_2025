"""
Main script to test database connection and list monitor items
Run this script to see all monitor items from the database
"""

from db_connection import test_connection, list_all_monitor_items, list_monitor_items_as_dataframe, get_table_info
from models import get_all_monitor_items_orm, get_monitor_items_with_filter_orm

def main():
    print("🚀 Monitor Items Database Connection Test")
    print("="*80)
    
    # Test database connection first
    print("\n1. Testing database connection...")
    if not test_connection():
        print("❌ Cannot connect to database. Please check your .env file settings.")
        return
    
    print("\n" + "="*80)
    print("2. Getting table structure...")
    get_table_info()
    
    print("\n" + "="*80)
    print("3. Listing all monitor items using Raw SQL...")
    rows, columns = list_all_monitor_items()
    
    if rows and len(rows) > 0:
        print(f"\n✅ Successfully found {len(rows)} records!")
        
        print("\n" + "="*80)
        print("4. Displaying data as Pandas DataFrame...")
        df = list_monitor_items_as_dataframe()
        
        print("\n" + "="*80)
        print("5. Using SQLAlchemy ORM...")
        get_all_monitor_items_orm()
        
        print("\n" + "="*80)
        print("6. Filtering examples...")
        
        print("\n6a. Getting enabled items only:")
        get_monitor_items_with_filter_orm(enable=True)
        
        print("\n6b. Getting ping_web type items:")
        get_monitor_items_with_filter_orm(monitor_type='ping_web')
        
        print("\n6c. Getting ping_icmp type items:")
        get_monitor_items_with_filter_orm(monitor_type='ping_icmp')
        
    else:
        print("⚠️ No records found in monitor_items table.")
        print("💡 You might want to add some test data first.")
    
    print("\n" + "="*80)
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()
