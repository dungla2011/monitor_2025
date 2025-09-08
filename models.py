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
    last_check_status = Column(Integer, nullable=True)  # -1=lỗi, 1=OK, NULL=chưa check
    url_check = Column(String(500), nullable=True)
    type = Column(String(64), nullable=True)
    maxAlertCount = Column(Integer, nullable=True)
    user_id = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    check_interval_seconds = Column(Integer, default=360)
    result_valid = Column(Text, nullable=True)
    result_error = Column(Text, nullable=True)
    stopTo = Column(DateTime, nullable=True)
    pingType = Column(Integer, default=1)
    log = Column(Text, nullable=True)
    last_check_time = Column(DateTime, nullable=True)
    queuedSendStr = Column(Text, nullable=True)
    forceRestart = Column(Boolean, default=False)  # tinyint(1) -> Boolean
    count_online = Column(Integer, default=0)  # Đếm số lần check thành công
    count_offline = Column(Integer, default=0)  # Đếm số lần check thất bại
    
    def __repr__(self):
        return f"<MonitorItem(id={self.id}, name='{self.name}', type='{self.type}', enable={self.enable})>"

class MonitorConfig(Base):
    """
    SQLAlchemy ORM model for monitor_configs table
    """
    __tablename__ = 'monitor_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    alert_type = Column(String(64), nullable=True)  # 'telegram', 'email', 'webhook', etc.
    alert_config = Column(Text, nullable=True)  # JSON hoặc string config
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MonitorConfig(id={self.id}, name='{self.name}', alert_type='{self.alert_type}')>"

class MonitorAndConfig(Base):
    """
    SQLAlchemy ORM model for monitor_and_configs table (pivot table)
    """
    __tablename__ = 'monitor_and_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    monitor_item_id = Column(Integer, nullable=False)
    config_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MonitorAndConfig(id={self.id}, monitor_item_id={self.monitor_item_id}, config_id={self.config_id})>"

class MonitorSettings(Base):
    """
    SQLAlchemy ORM model for monitor_settings table
    """
    __tablename__ = 'monitor_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True)  # Unique per user
    status = Column(Integer, default=1)  # 1=active, 0=inactive
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    log = Column(Text, nullable=True)
    alert_time_ranges = Column(String(255), nullable=True)  # Format: "05:30-23:00" hoặc nhiều range
    timezone = Column(String(64), default='Asia/Ho_Chi_Minh')
    global_stop_alert_to = Column(DateTime, nullable=True)  # Dừng alert đến thời gian này
    
    def __repr__(self):
        return f"<MonitorSettings(id={self.id}, user_id={self.user_id}, alert_time_ranges='{self.alert_time_ranges}')>"

def get_telegram_config_for_monitor_item(monitor_item_id):
    """
    Lấy cấu hình Telegram cho một monitor item
    
    Args:
        monitor_item_id (int): ID của monitor item
        
    Returns:
        dict: {'bot_token': str, 'chat_id': str} hoặc None nếu không tìm thấy
    """
    try:
        session = SessionLocal()
        
        # Join 3 bảng để lấy telegram config
        result = session.query(MonitorConfig.alert_config).join(
            MonitorAndConfig, MonitorConfig.id == MonitorAndConfig.config_id
        ).filter(
            MonitorAndConfig.monitor_item_id == monitor_item_id,
            MonitorConfig.alert_type == 'telegram'
        ).first()
        
        session.close()
        
        if not result or not result.alert_config:
            return None
            
        # Parse alert_config: <bot_token>,<chat_id>
        alert_config = result.alert_config.strip()
        
        if ',' not in alert_config:
            return None
            
        parts = alert_config.split(',', 1)  # Split thành 2 phần
        if len(parts) != 2:
            return None
            
        bot_token = parts[0].strip()
        chat_id = parts[1].strip()
        
        # Validate format
        if not bot_token or not chat_id:
            return None
            
        # Validate bot_token format (should be like: 123456:ABC-DEF...)
        if ':' not in bot_token:
            return None
            
        # Validate chat_id (should be number or start with -)
        if not (chat_id.lstrip('-').isdigit() or chat_id.startswith('@')):
            return None
            
        return {
            'bot_token': bot_token,
            'chat_id': chat_id
        }
        
    except Exception as e:
        print(f"❌ Error getting telegram config for monitor item {monitor_item_id}: {e}")
        return None

def get_all_alert_configs_for_monitor_item(monitor_item_id):
    """
    Lấy tất cả cấu hình alert cho một monitor item
    
    Args:
        monitor_item_id (int): ID của monitor item
        
    Returns:
        list: Danh sách các config dict
    """
    try:
        session = SessionLocal()
        
        results = session.query(MonitorConfig).join(
            MonitorAndConfig, MonitorConfig.id == MonitorAndConfig.config_id
        ).filter(
            MonitorAndConfig.monitor_item_id == monitor_item_id
        ).all()
        
        session.close()
        
        configs = []
        for config in results:
            configs.append({
                'id': config.id,
                'name': config.name,
                'alert_type': config.alert_type,
                'alert_config': config.alert_config
            })
            
        return configs
        
    except Exception as e:
        print(f"❌ Error getting alert configs for monitor item {monitor_item_id}: {e}")
        return []

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
            last_status = "✅ OK" if item.last_check_status == 1 else "❌ Error" if item.last_check_status == -1 else "⚪ Unknown"
            print(f"ID: {item.id:2d} | Name: {item.name:20s} | Type: {item.type:10s} | {enable_status} | Last: {last_status}")
            if item.url_check:
                print(f"     URL: {item.url_check}")
            if item.last_check_time:
                print(f"     Last Check: {item.last_check_time}")
            print("-" * 80)
        
        session.close()
        return monitor_items
        
    except Exception as e:
        print(f"❌ Error using ORM: {e}")
        print("💡 This might be because the table structure doesn't match the model.")
        print("💡 Please check the actual table structure and adjust the MonitorItem model.")
        return None

def get_monitor_settings_for_user(user_id):
    """
    Lấy monitor settings cho một user_id
    
    Args:
        user_id (int): ID của user
        
    Returns:
        MonitorSettings object hoặc None nếu không tìm thấy
    """
    try:
        session = SessionLocal()
        
        settings = session.query(MonitorSettings).filter(
            MonitorSettings.user_id == user_id,
            MonitorSettings.deleted_at.is_(None)  # Chưa bị xóa
        ).first()
        
        session.close()
        return settings
        
    except Exception as e:
        print(f"❌ Error getting monitor settings for user {user_id}: {e}")
        return None

def is_alert_time_allowed(user_id):
    """
    Kiểm tra xem hiện tại có được phép gửi alert hay không dựa trên settings của user
    
    Args:
        user_id (int): ID của user
        
    Returns:
        tuple: (is_allowed: bool, reason: str)
    """
    try:
        from datetime import datetime
        import pytz
        
        settings = get_monitor_settings_for_user(user_id)
        if not settings:
            # Không có settings -> cho phép gửi (default behavior)
            return True, "No user settings found, allowing alerts"
        
        # Kiểm tra global_stop_alert_to
        if settings.global_stop_alert_to:
            now_utc = datetime.utcnow()
            if now_utc < settings.global_stop_alert_to:
                return False, f"Global alert stopped until {settings.global_stop_alert_to}"
        
        # Kiểm tra alert_time_ranges
        if settings.alert_time_ranges:
            timezone_str = settings.timezone or 'Asia/Ho_Chi_Minh'
            try:
                tz = pytz.timezone(timezone_str)
                now_local = datetime.now(tz)
                current_time = now_local.strftime('%H:%M')
                
                # Parse alert_time_ranges: "05:30-23:00" hoặc "05:30-11:00,14:00-23:00" (multiple ranges)
                time_ranges = [r.strip() for r in settings.alert_time_ranges.split(',')]
                
                is_in_allowed_time = False
                for time_range in time_ranges:
                    if '-' not in time_range:
                        continue
                        
                    start_time, end_time = time_range.split('-', 1)
                    start_time = start_time.strip()
                    end_time = end_time.strip()
                    
                    # Validate format H:M hoặc HH:MM
                    if ':' not in start_time or ':' not in end_time:
                        continue
                    
                    # Kiểm tra xem current_time có nằm trong range không
                    if start_time <= current_time <= end_time:
                        is_in_allowed_time = True
                        break
                
                if not is_in_allowed_time:
                    return False, f"Outside allowed time ranges: {settings.alert_time_ranges} (current: {current_time} {timezone_str})"
                
            except Exception as tz_error:
                print(f"⚠️ Timezone error for user {user_id}: {tz_error}")
                # Lỗi timezone -> cho phép gửi để tránh miss alert
                return True, "Timezone error, allowing alerts"
        
        return True, "Alert allowed"
        
    except Exception as e:
        print(f"❌ Error checking alert time for user {user_id}: {e}")
        # Lỗi -> cho phép gửi để tránh miss alert quan trọng
        return True, "Error occurred, allowing alerts"

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
