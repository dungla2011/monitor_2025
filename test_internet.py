#!/usr/bin/env python3
"""
Test script to verify internet connectivity loop function
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

# Import the function
try:
    from monitor_service_asyncio import internet_connectivity_loop, check_internet_connectivity
    print("✅ Successfully imported internet functions")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def test_internet_functions():
    """Test internet connectivity functions"""
    print("\n=== Testing check_internet_connectivity() ===")
    try:
        result = await check_internet_connectivity()
        print(f"✅ check_internet_connectivity() returned: {result}")
    except Exception as e:
        print(f"❌ check_internet_connectivity() failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing internet_connectivity_loop() for 5 seconds ===")
    try:
        # Run the loop for 5 seconds then cancel
        task = asyncio.create_task(internet_connectivity_loop())
        await asyncio.sleep(5)
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            print("✅ Loop cancelled successfully")
            
    except Exception as e:
        print(f"❌ internet_connectivity_loop() failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Internet Connectivity Functions")
    print("=" * 50)
    
    asyncio.run(test_internet_functions())
    
    print("\n✅ Test completed")