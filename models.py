from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from db_connection import engine

Base = declarative_base()

class MonitorItem(Base):
    """
    SQLAlchemy ORM model for monitor_items table
    Based on the actual table structure provided
    """
    __tablename__ = 'monitor_items'
    
    # Exact columns from the actual table structure
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    enable = Column(Boolean, nullable=True)  # tinyint(1) -> Boolean
    last_ok_or_error = Column(Integer, nullable=True)  # -1=lỗi, 1=OK, NULL=chưa check
    url_check = Column(String(500), nullable=True)
    type = Column(String(64), nullable=True)
    maxAlertCount = Column(Integer, nullable=True)
    user_id = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    timeRangeSeconds = Column(Integer, default=360)
    result_check = Column(Text, nullable=True)
    result_error = Column(Text, nullable=True)
    stopTo = Column(DateTime, nullable=True)
    pingType = Column(Integer, default=1)
    log = Column(Text, nullable=True)
    lastCheck = Column(DateTime, nullable=True)
    queuedSendStr = Column(Text, nullable=True)
    forceRestart = Column(Boolean, default=False)  # tinyint(1) -> Boolean
    
    def __repr__(self):
        return f"<MonitorItem(id={self.id}, name='{self.name}', type='{self.type}', enable={self.enable})>"

# Create session factory
SessionLocal = sessionmaker(bind=engine)

def get_all_monitor_items_orm():
    """Get all monitor items using SQLAlchemy ORM"""
    try:
        session = SessionLocal()
        
        # Query all monitor items
        monitor_items = session.query(MonitorItem).all()
        
        print(f"📊 Found {len(monitor_items)} monitor items using ORM:")
        print("-" * 80)
        
        for item in monitor_items:
            enable_status = "✅ Enabled" if item.enable else "❌ Disabled" if item.enable is not None else "⚪ Unknown"
            last_status = "✅ OK" if item.last_ok_or_error == 1 else "❌ Error" if item.last_ok_or_error == -1 else "⚪ Unknown"
            print(f"ID: {item.id:2d} | Name: {item.name:20s} | Type: {item.type:10s} | {enable_status} | Last: {last_status}")
            if item.url_check:
                print(f"     URL: {item.url_check}")
            if item.lastCheck:
                print(f"     Last Check: {item.lastCheck}")
            print("-" * 80)
        
        session.close()
        return monitor_items
        
    except Exception as e:
        print(f"❌ Error using ORM: {e}")
        print("💡 This might be because the table structure doesn't match the model.")
        print("💡 Please check the actual table structure and adjust the MonitorItem model.")
        return None

def get_monitor_items_with_filter_orm(monitor_type=None, enable=None):
    """Get monitor items with filters using SQLAlchemy ORM"""
    try:
        session = SessionLocal()
        
        query = session.query(MonitorItem)
        
        if monitor_type:
            query = query.filter(MonitorItem.type == monitor_type)
        
        if enable is not None:
            query = query.filter(MonitorItem.enable == enable)
        
        monitor_items = query.all()
        
        print(f"📊 Found {len(monitor_items)} filtered monitor items:")
        for item in monitor_items:
            enable_status = "✅ Enabled" if item.enable else "❌ Disabled"
            print(f"ID: {item.id} | Name: {item.name} | Type: {item.type} | {enable_status}")
        
        session.close()
        return monitor_items
        
    except Exception as e:
        print(f"❌ Error filtering with ORM: {e}")
        return None

if __name__ == "__main__":
    print("🔍 Testing ORM operations...")
    
    # Try to get all items using ORM
    print("\n1. Getting all items using ORM:")
    get_all_monitor_items_orm()
    
    print("\n2. Getting filtered items (enabled only):")
    get_monitor_items_with_filter_orm(enable=True)
    
    print("\n3. Getting ping_web type items:")
    get_monitor_items_with_filter_orm(monitor_type='ping_web')
