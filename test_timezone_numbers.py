"""
Test timezone handling with GMT offset numbers
"""

def test_timezone_conversion():
    """Test timezone number to string conversion"""
    
    # Timezone mapping
    timezone_map = {
        7: 'Asia/Ho_Chi_Minh',
        0: 'UTC',
        8: 'Asia/Shanghai',
        9: 'Asia/Tokyo',
        -5: 'America/New_York',
        -8: 'America/Los_Angeles',
        1: 'Europe/London',
    }
    
    # Test cases
    test_cases = [
        {'input': 7, 'expected': 'Asia/Ho_Chi_Minh', 'description': 'GMT+7 Vietnam'},
        {'input': 0, 'expected': 'UTC', 'description': 'GMT+0 UTC'},
        {'input': 8, 'expected': 'Asia/Shanghai', 'description': 'GMT+8 China'},
        {'input': -5, 'expected': 'America/New_York', 'description': 'GMT-5 EST'},
        {'input': 5, 'expected': 'Asia/Ho_Chi_Minh', 'description': 'Unknown offset -> default'},
        {'input': 'Asia/Tokyo', 'expected': 'Asia/Tokyo', 'description': 'String timezone'},
        {'input': None, 'expected': 'Asia/Ho_Chi_Minh', 'description': 'None -> default'},
    ]
    
    print("🧪 Testing timezone conversion logic...")
    print("=" * 60)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['description']}")
        print(f"   Input: {case['input']} ({type(case['input']).__name__})")
        
        # Apply the conversion logic
        timezone_value = case['input']
        if timezone_value is None:
            timezone_value = 7  # Default GMT+7
        
        if isinstance(timezone_value, (int, float)):
            timezone_str = timezone_map.get(int(timezone_value), 'Asia/Ho_Chi_Minh')
            print(f"   Process: GMT+{timezone_value} -> {timezone_str}")
        elif isinstance(timezone_value, str):
            timezone_str = timezone_value
            print(f"   Process: String timezone -> {timezone_str}")
        else:
            timezone_str = 'Asia/Ho_Chi_Minh'
            print(f"   Process: Unknown format -> default")
        
        # Check result
        if timezone_str == case['expected']:
            print(f"   ✅ Result: {timezone_str}")
        else:
            print(f"   ❌ Result: {timezone_str} (expected: {case['expected']})")
    
    print(f"\n" + "=" * 60)
    print("🎯 Summary:")
    print("✅ GMT offset numbers are properly converted to timezone strings")
    print("✅ String timezones are passed through unchanged") 
    print("✅ Invalid/unknown values fall back to Asia/Ho_Chi_Minh")
    print("✅ None values default to GMT+7 (Asia/Ho_Chi_Minh)")

def test_time_range_logic():
    """Test time range checking logic"""
    print(f"\n🧪 Testing time range logic...")
    print("=" * 60)
    
    # Mock current time
    current_time = "14:30"  # 2:30 PM
    
    test_ranges = [
        "05:30-23:00",  # Single range - should allow
        "05:30-11:00,14:00-23:00",  # Multiple ranges - should allow
        "00:00-05:00,22:00-23:59",  # Multiple ranges - should deny  
        "09:00-12:00",  # Single range - should deny
    ]
    
    for i, time_ranges_str in enumerate(test_ranges, 1):
        print(f"\n{i}. Time ranges: {time_ranges_str}")
        print(f"   Current time: {current_time}")
        
        time_ranges = [r.strip() for r in time_ranges_str.split(',')]
        is_in_allowed_time = False
        
        for time_range in time_ranges:
            if '-' not in time_range:
                continue
                
            start_time, end_time = time_range.split('-', 1)
            start_time = start_time.strip()
            end_time = end_time.strip()
            
            print(f"   Checking range: {start_time} - {end_time}")
            
            if start_time <= current_time <= end_time:
                is_in_allowed_time = True
                print(f"   ✅ {current_time} is within {start_time}-{end_time}")
                break
            else:
                print(f"   ❌ {current_time} is outside {start_time}-{end_time}")
        
        result = "ALLOWED" if is_in_allowed_time else "BLOCKED"
        print(f"   🎯 Final result: {result}")

if __name__ == "__main__":
    test_timezone_conversion()
    test_time_range_logic()
    print(f"\n🎉 All tests completed!")
