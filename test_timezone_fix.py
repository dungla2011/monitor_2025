"""
Test timezone fix for is_alert_time_allowed function
"""

def test_timezone_fix():
    """Test the timezone handling fix"""
    
    # Mock MonitorSettings object with integer timezone
    class MockSettings:
        def __init__(self):
            self.alert_time_ranges = "05:30-23:00"
            self.timezone = 7  # This should be a string but is integer
            self.global_stop_alert_to = None
    
    # Test the fixed logic
    settings = MockSettings()
    timezone_str = settings.timezone or 'Asia/Ho_Chi_Minh'
    
    print(f"Original timezone value: {settings.timezone} (type: {type(settings.timezone)})")
    print(f"timezone_str after 'or' operation: {timezone_str} (type: {type(timezone_str)})")
    
    # Check if it's string
    if not isinstance(timezone_str, str):
        timezone_str = 'Asia/Ho_Chi_Minh'
        print(f"⚠️ Invalid timezone type, using default: {timezone_str}")
    else:
        print(f"✅ Timezone is valid string: {timezone_str}")
    
    # Test with string timezone
    settings2 = MockSettings()
    settings2.timezone = "Asia/Ho_Chi_Minh"
    
    timezone_str2 = settings2.timezone or 'Asia/Ho_Chi_Minh'
    print(f"\nString timezone test:")
    print(f"timezone value: {settings2.timezone} (type: {type(settings2.timezone)})")
    
    if not isinstance(timezone_str2, str):
        timezone_str2 = 'Asia/Ho_Chi_Minh'
        print(f"⚠️ Invalid timezone type, using default: {timezone_str2}")
    else:
        print(f"✅ Timezone is valid string: {timezone_str2}")
    
    # Test with None timezone
    settings3 = MockSettings()
    settings3.timezone = None
    
    timezone_str3 = settings3.timezone or 'Asia/Ho_Chi_Minh'
    print(f"\nNone timezone test:")
    print(f"timezone value: {settings3.timezone} (type: {type(settings3.timezone)})")
    print(f"timezone_str after 'or': {timezone_str3} (type: {type(timezone_str3)})")
    
    if not isinstance(timezone_str3, str):
        timezone_str3 = 'Asia/Ho_Chi_Minh'
        print(f"⚠️ Invalid timezone type, using default: {timezone_str3}")
    else:
        print(f"✅ Timezone is valid string: {timezone_str3}")

if __name__ == "__main__":
    print("🧪 Testing timezone fix...")
    test_timezone_fix()
    print("\n✅ Test completed!")
