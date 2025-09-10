"""
SUMMARY: Timezone Fix for Monitor Service

PROBLEM IDENTIFIED:
- Database stores timezone as INTEGER (GMT offset) instead of string
- Code was expecting string timezone and calling .upper() method on integer
- This caused error: "'int' object has no attribute 'upper'"

SOLUTION IMPLEMENTED:

1. UPDATED MODEL DEFINITION:
   - Changed timezone column from String(64) to Integer 
   - Default value changed from 'Asia/Ho_Chi_Minh' to 7 (GMT+7)

2. UPDATED TIMEZONE HANDLING LOGIC:
   - Added timezone_map to convert GMT offset numbers to timezone strings
   - Support for common timezones:
     * 7 -> Asia/Ho_Chi_Minh (Vietnam, default)
     * 0 -> UTC
     * 8 -> Asia/Shanghai (China, Singapore, Malaysia)  
     * 9 -> Asia/Tokyo (Japan, Korea)
     * 5.5 -> Asia/Kolkata (India)
     * -5 -> America/New_York (US East Coast)
     * -8 -> America/Los_Angeles (US West Coast)
     * And more...

3. FALLBACK HANDLING:
   - Unknown timezone numbers -> fallback to Asia/Ho_Chi_Minh
   - String timezones -> pass through unchanged (backward compatibility)
   - None values -> default to GMT+7

BENEFITS:
✅ No more 'int' object has no attribute 'upper' error
✅ Support for both integer GMT offsets and string timezones  
✅ Proper timezone conversion with extensive mapping
✅ Backward compatibility with existing string timezones
✅ Clear logging of timezone conversion process
✅ Fallback to safe defaults to avoid missing alerts

TESTING:
✅ All conversion logic tested and working
✅ Time range checking logic verified
✅ Edge cases handled (None, unknown values)

FILES MODIFIED:
- models.py: Updated MonitorSettings model and is_alert_time_allowed function

The timezone error should now be resolved and the system will properly handle
both numeric GMT offsets and string timezone identifiers.
"""

print(__doc__)
