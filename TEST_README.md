# Monitor Service Test Suite

Bộ công cụ test toàn diện cho Monitor Service 2025.

## 📁 Files

### 🧪 Test Scripts

1. **`00_run_all_tests.py`** - Master test runner
   - Chạy tất cả tests
   - Health checks cơ bản
   - Quick functional tests
   - Tổng hợp kết quả

2. **`01_test_features.py`** - Feature testing
   - Database connection
   - API endpoints
   - Service check functions
   - Thread management
   - Environment config
   - Utility functions

3. **`02_test_performance.py`** - Performance testing
   - API response time
   - Concurrent requests
   - Memory usage
   - Database performance
   - Service check performance

## 🚀 Usage

### Quick Start
```bash
# Chạy tất cả tests
python 00_run_all_tests.py

# Chỉ chạy quick tests
python 00_run_all_tests.py --quick

# Hiển thị help
python 00_run_all_tests.py --help
```

### Individual Tests
```bash
# Feature tests
python 01_test_features.py

# Performance tests (cần service đang chạy)
python 02_test_performance.py
```

## 📋 Test Categories

### 1. 🩺 Health Checks
- ✅ Python modules availability
- ✅ Environment file existence
- ✅ Database modules import
- ✅ Utility modules import
- ✅ Main service modules import

### 2. 🔧 Feature Tests
- ✅ Database connection
- ✅ Environment configuration
- ✅ Utility functions
- ✅ API server running
- ✅ API endpoints
- ✅ Monitor item creation
- ✅ Service check functions
- ✅ Thread management
- ✅ Database operations
- ✅ Cleanup test data

### 3. ⚡ Performance Tests
- ✅ API response time
- ✅ Concurrent requests
- ✅ Memory usage monitoring
- ✅ Database query performance
- ✅ Service check performance

### 4. 🧪 Service Type Tests
- ✅ `ping_web` - HTTP/HTTPS checks
- ✅ `ping_icmp` - ICMP ping checks
- ✅ `web_content` - Web content validation
- ✅ `open_port_tcp_then_error` - Security monitoring
- ✅ `open_port_tcp_then_valid` - Service monitoring  
- ✅ `ssl_expired_check` - SSL certificate monitoring

## 📊 Test Results

### Success Indicators
- ✅ All tests pass
- 🟢 Service running normally
- 📈 Performance within acceptable range
- 💾 Database operations working
- 🌐 API endpoints responsive

### Failure Indicators
- ❌ Test failures
- 🔴 Service not responding
- 📉 Performance issues
- 💥 Database errors
- ⚠️ API errors

## 🛠️ Prerequisites

### Service Requirements
```bash
# Start monitor service first for performance tests
python monitor_service.py start
```

### Python Dependencies
- `sqlalchemy` - Database ORM
- `flask` - Web framework
- `requests` - HTTP client
- `psutil` - System monitoring
- `python-dotenv` - Environment variables

### Environment Setup
```bash
# Ensure .env file exists with required variables
DB_HOST=localhost
DB_NAME=monitor_db
DB_USER=monitor_user
HTTP_PORT=5005
HTTP_HOST=127.0.0.1
```

## 📈 Performance Benchmarks

### Expected Performance
- **API Response**: < 100ms average
- **Database Query**: < 50ms average
- **Service Checks**: 
  - ping_web: < 2000ms
  - ping_icmp: < 1000ms
  - tcp_check: < 500ms
- **Concurrent Users**: 10+ users simultaneously

### Performance Warnings
- ⚠️ API response > 500ms
- ⚠️ Database query > 100ms
- ⚠️ High error rates (>5%)
- ⚠️ Memory leaks detected

## 🐛 Troubleshooting

### Common Issues

1. **Service Not Running**
   ```bash
   # Start the service
   python monitor_service.py start
   
   # Check status
   python monitor_service.py status
   ```

2. **Database Connection Error**
   - Check `.env` database settings
   - Ensure database server is running
   - Verify user permissions

3. **Import Errors**
   - Install required dependencies
   - Check Python path
   - Verify virtual environment

4. **API Connection Error**
   - Check if port 5005 is available
   - Verify HTTP_HOST and HTTP_PORT in `.env`
   - Check firewall settings

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run specific test with more details
python -v 01_test_features.py
```

## 📁 Test Data

### Test Items Created
Tests automatically create temporary monitor items:
- `TEST_ping_web_success` - Should pass
- `TEST_ping_web_fail` - Should fail
- `TEST_ping_icmp_success` - Should pass
- `TEST_ping_icmp_fail` - Should fail
- `TEST_web_content_success` - Should pass
- `TEST_web_content_fail` - Should fail
- `TEST_open_port_tcp_then_error` - Port monitoring
- `TEST_open_port_tcp_then_valid` - Service monitoring
- `TEST_ssl_expired_check` - SSL certificate check

### Cleanup
Tests automatically cleanup test data after completion.

## 📝 Adding New Tests

### Create New Test Function
```python
def test_new_feature(self):
    """Test new feature"""
    self.print_header("New Feature Test")
    
    try:
        # Test logic here
        result = some_function()
        self.print_test("New Feature", True, "Success message")
        return True
    except Exception as e:
        self.print_test("New Feature", False, str(e))
        return False
```

### Add to Test Sequence
```python
test_sequence = [
    self.test_database_connection,
    self.test_new_feature,  # Add here
    # ... other tests
]
```

## 🎯 Best Practices

1. **Run Tests Regularly**
   - Before deployment
   - After code changes  
   - Weekly health checks

2. **Monitor Performance**
   - Track response times
   - Watch for regressions
   - Set up alerts

3. **Keep Tests Updated**
   - Add tests for new features
   - Update expected values
   - Remove obsolete tests

4. **Document Results**
   - Save test reports
   - Track trends
   - Share with team

## 📞 Support

For issues or questions:
1. Check logs in `logs/` folder
2. Review error messages in test output
3. Verify environment configuration
4. Check service status and connectivity
