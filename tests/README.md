# Test Suite Runner

## 📋 Mô tả
File `run_all_tests.py` trong folder `tests/` là test runner chính để chạy tất cả các test của Monitor 2025 system.

## 🚀 Cách sử dụng

### Từ project root:
```bash
python tests/run_all_tests.py                   # Chạy tất cả test
python tests/run_all_tests.py --stop-on-error  # Dừng khi có lỗi đầu tiên
python tests/run_all_tests.py --help           # Xem hướng dẫn
```

### Từ folder tests/:
```bash
cd tests
python run_all_tests.py                    # Chạy tất cả test
python run_all_tests.py --stop-on-error   # Dừng khi có lỗi đầu tiên  
python run_all_tests.py --help            # Xem hướng dẫn
```

## 📊 Kết quả

Test runner sẽ:
- ✅ Chạy tất cả test files có format `XX.test-name.py`
- ✅ Hiển thị kết quả real-time
- ✅ Tạo report tổng hợp cuối cùng
- ✅ Lưu JSON report với timestamp: `test_report_YYYYMMDD_HHMMSS.json`
- 🛑 **--stop-on-error**: Dừng ngay khi có test đầu tiên fail (tiết kiệm thời gian)

## 🧪 Test Files được chạy

| File | Mô tả |
|------|-------|
| `01.test-models.py` | Database schema compatibility |
| `02.test-create-local-db.py` | Local database creation |
| `03.test-api-endpoints-create-new-console-ok.py` | API endpoints & authentication |
| `05.test-dynamic-control.py` | Real-time monitor control |
| `06.test-webhook-alerts.py` | Webhook alert system |
| `07.test-telegram-alerts.py` | Telegram alert system |

## ⚙️ Cấu trúc

```
tests/
├── run_all_tests.py          # Test runner chính
├── 01.test-models.py         # Test 1
├── 02.test-create-local-db.py # Test 2
├── 03.test-api-endpoints...   # Test 3
├── 05.test-dynamic-control.py # Test 5
├── 06.test-webhook-alerts.py  # Test 6
├── 07.test-telegram-alerts.py # Test 7
├── 06.test.md                # Documentation Test 6
└── 07.test.md                # Documentation Test 7
```

## 📈 Output Example

```
🧪 MONITOR 2025 - COMPREHENSIVE TEST SUITE
📅 Started at: 2025-09-11 14:12:53
📋 Found 6 test files

==================== TEST 1/6 ====================
🧪 Running 01.test-models.py...
✅ 01.test-models.py - PASSED (2.4s)

[... other tests ...]

📊 TEST SUITE SUMMARY REPORT
📈 OVERALL STATISTICS:
   📊 Total Tests: 6
   ✅ Passed: 6
   🎯 Success Rate: 100.0%

🎉 ALL TESTS PASSED! 🎉
```

## 🔧 Technical Notes

- Test runner tự động exclude chính nó khỏi danh sách test
- Chạy từ project root để access được các module
- Timeout mỗi test: 5 phút
- Output real-time, không buffer
- JSON report lưu tại project root
