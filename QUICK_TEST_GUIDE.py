#!/usr/bin/env python3
"""
Monitor Service - Quick Test Guide
Hướng dẫn nhanh để chạy tests
"""

print("""
🧪 MONITOR SERVICE - QUICK TEST GUIDE
=====================================

📁 Test Files (theo thứ tự):
  00_run_all_tests.py      - 🎯 Master test runner (CHẠY FILE NÀY TRƯỚC)
  01_test_features.py      - 🔧 Feature & functionality tests  
  02_test_performance.py   - ⚡ Performance & stress tests

�️ Test Environment Files:
  .env.test               - 🔧 Test environment configuration
  test_env_loader.py      - 🔧 Test environment loader

�🚀 Quick Commands:
  python test_env_loader.py           # Test environment setup
  python 00_run_all_tests.py          # Chạy tất cả tests
  python 00_run_all_tests.py --quick  # Chỉ quick tests
  python 01_test_features.py          # Feature tests riêng
  python 02_test_performance.py       # Performance tests riêng

📋 Prerequisites:
  1. ✅ Virtual environment activated: .\\venv\\Scripts\\Activate.ps1
  2. ✅ MySQL server running on localhost
  3. ✅ Test database 'monitor_test' created (optional - will be auto-created)
  4. ✅ .env.test file configured (already provided)
  5. ✅ Monitor service running on port 5006 (test port)

🔧 Test Database Setup (MySQL):
  CREATE DATABASE monitor_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  # Root user with empty password (default in .env.test)

🎯 Recommended Testing Order:
  Step 1: python test_env_loader.py             (Test environment check)
  Step 2: python 00_run_all_tests.py --quick    (Health check - no service needed)
  
  === FOR FULL TESTS (need service running) ===
  Step 3a: OPTION 1 - Temporary switch environment:
           copy .env.test .env                   (Backup original .env first!)
           python monitor_service.py start      (Start service with test config)
           python 00_run_all_tests.py          (Run full tests)
           copy .env.backup .env                (Restore original .env)
           
  Step 3b: OPTION 2 - Keep production running, test separately:
           # Keep production service running on port 5005
           # Start test service on port 5006:
           python monitor_service.py start --test
           python 00_run_all_tests.py
           
  Step 4: Check logs/ folder for detailed results

⚠️  IMPORTANT NOTES:
  • Option 1: Tạm thời thay thế .env, cần backup trước
  • Option 2: Chạy 2 service song song (production + test)
  • Full tests CẦN service đang chạy (API tests, performance tests)
  • Quick tests KHÔNG cần service (chỉ basic health checks)

📊 Test Environment Features:
  ✅ Separate test database (monitor_test)
  ✅ Test port 5006 (won't conflict with production)
  ✅ Reduced performance test iterations for speed
  ✅ Optional test data cleanup
  ✅ Debug logging enabled

📊 Expected Results:
  ✅ ALL TESTS PASSED  - Ready for production
  ❌ SOME TESTS FAILED - Check error messages and fix issues

🆘 If tests fail:
  • Check if MySQL server is running
  • Verify test database exists and accessible
  • Check if monitor service is running on port 5006
  • Ensure all dependencies installed: pip install -r requirements.txt
  • Check logs/ folder for error details
  • Run: python test_env_loader.py to verify environment

📚 For detailed documentation: see TEST_README.md
""")

if __name__ == "__main__":
    print("💡 TIP: Run 'python test_env_loader.py' first to check test environment!")
