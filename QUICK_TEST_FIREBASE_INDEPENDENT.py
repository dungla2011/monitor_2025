"""
QUICK TEST: Firebase Independent Notification
==============================================

Test độc lập Firebase notification (tách khỏi Telegram)
"""

# TEST 1: Import kiểm tra
print("=" * 60)
print("TEST 1: Import Firebase Notification Function")
print("=" * 60)

try:
    from async_telegram_notification import send_firebase_notification_async
    print("✅ Import thành công: send_firebase_notification_async")
except ImportError as e:
    print(f"❌ Import FAILED: {e}")
    exit(1)

# TEST 2: Import monitor service
print("\n" + "=" * 60)
print("TEST 2: Verify monitor_service_asyncio.py imports Firebase")
print("=" * 60)

import monitor_service_asyncio
import inspect

# Check if monitor_service_asyncio imports send_firebase_notification_async
source = inspect.getsource(monitor_service_asyncio)
if 'send_firebase_notification_async' in source:
    print("✅ monitor_service_asyncio.py imports send_firebase_notification_async")
    
    # Count number of calls
    call_count = source.count('await send_firebase_notification_async(')
    print(f"✅ Function được gọi {call_count} lần trong code")
    
    # Find all call locations
    lines = source.split('\n')
    call_lines = [i+1 for i, line in enumerate(lines) if 'await send_firebase_notification_async(' in line]
    print(f"📍 Được gọi ở các dòng: {call_lines}")
else:
    print("❌ monitor_service_asyncio.py KHÔNG import send_firebase_notification_async")

# TEST 3: Check function signature
print("\n" + "=" * 60)
print("TEST 3: Function Signature")
print("=" * 60)

sig = inspect.signature(send_firebase_notification_async)
print(f"Function: send_firebase_notification_async{sig}")
print(f"Parameters: {list(sig.parameters.keys())}")

# TEST 4: Check it's truly independent
print("\n" + "=" * 60)
print("TEST 4: Independence Verification")
print("=" * 60)

from async_telegram_notification import send_telegram_notification_async
telegram_source = inspect.getsource(send_telegram_notification_async)

# Check if Telegram calls Firebase internally
if 'await send_firebase_notification_async(' in telegram_source:
    print("❌ FAILED: send_telegram_notification_async vẫn gọi Firebase bên trong")
    print("Firebase CHƯA độc lập!")
else:
    print("✅ PASSED: send_telegram_notification_async KHÔNG gọi Firebase")
    print("Firebase đã hoàn toàn độc lập!")

# Check for comment indicating independence
if 'Firebase notification được gọi riêng' in telegram_source:
    print("✅ PASSED: Comment xác nhận Firebase được gọi riêng")
else:
    print("⚠️ WARNING: Thiếu comment giải thích")

# TEST 5: Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

checks = {
    'Import function': True,
    'monitor_service imports': 'send_firebase_notification_async' in source,
    'Called in monitor_service': call_count >= 3,  # Should be called at least 3 times
    'Independent from Telegram': 'await send_firebase_notification_async(' not in telegram_source,
    'Comment exists': 'Firebase notification được gọi riêng' in telegram_source
}

all_passed = all(checks.values())

for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"{status} {check}")

print("\n" + "=" * 60)
if all_passed:
    print("🎉 ALL TESTS PASSED!")
    print("Firebase notification đã được tách riêng thành công!")
else:
    print("❌ SOME TESTS FAILED")
    print("Cần kiểm tra lại code")
print("=" * 60)
