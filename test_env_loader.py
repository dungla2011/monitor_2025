"""
Test Environment Loader
Load environment variables specifically for testing
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def load_test_environment():
    """
    Load test environment variables from .env.test
    Returns True if successful, False otherwise
    """
    # Get the project root directory
    project_root = Path(__file__).parent
    test_env_file = project_root / '.env.test'
    
    if not test_env_file.exists():
        print(f"❌ Test environment file not found: {test_env_file}")
        print("   Please create .env.test file for testing")
        return False
    
    # Load test environment
    load_dotenv(test_env_file, override=True)
    
    print(f"✅ Test environment loaded from: {test_env_file}")
    print(f"   Database: {os.getenv('DB_USER')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    print(f"   API Server: {os.getenv('HTTP_HOST')}:{os.getenv('HTTP_PORT')}")
    
    return True

def verify_test_environment():
    """
    Verify that all required test environment variables are set
    Returns (success: bool, missing_vars: list)
    """
    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER',
        'HTTP_HOST', 'HTTP_PORT'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False, missing_vars
    
    print("✅ All required test environment variables are set")
    return True, []

def get_test_database_url():
    """
    Get database URL for testing
    """
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'monitor_test')
    
    # Handle empty password
    auth_string = f"{db_user}:{db_password}" if db_password else db_user
    
    return f"mysql+pymysql://{auth_string}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

def get_test_api_url():
    """
    Get API base URL for testing
    """
    host = os.getenv('HTTP_HOST', '127.0.0.1')
    port = os.getenv('HTTP_PORT', '5006')
    return f"http://{host}:{port}"

def is_test_mode():
    """
    Check if we're running in test mode
    """
    return os.getenv('TEST_MODE', 'false').lower() == 'true'

def should_cleanup_test_data():
    """
    Check if test data should be cleaned up after tests
    """
    return os.getenv('TEST_CLEANUP_ENABLED', 'true').lower() == 'true'

def should_reset_test_database():
    """
    Check if test database should be reset before tests
    """
    return os.getenv('TEST_DATABASE_RESET', 'true').lower() == 'true'

def get_test_timeout():
    """
    Get test timeout in seconds
    """
    return int(os.getenv('TEST_TIMEOUT', '30'))

def get_performance_test_settings():
    """
    Get performance test settings
    """
    return {
        'iterations': int(os.getenv('PERFORMANCE_TEST_ITERATIONS', '10')),
        'concurrent_users': int(os.getenv('PERFORMANCE_CONCURRENT_USERS', '3'))
    }

if __name__ == "__main__":
    """Test the environment loader"""
    print("🧪 Testing Environment Loader...")
    
    if load_test_environment():
        success, missing = verify_test_environment()
        
        if success:
            print(f"\n📊 Test Configuration:")
            print(f"   Database URL: {get_test_database_url()}")
            print(f"   API URL: {get_test_api_url()}")
            print(f"   Test Mode: {is_test_mode()}")
            print(f"   Cleanup Enabled: {should_cleanup_test_data()}")
            print(f"   Database Reset: {should_reset_test_database()}")
            print(f"   Test Timeout: {get_test_timeout()}s")
            print(f"   Performance Settings: {get_performance_test_settings()}")
            print("\n✅ Environment loader test passed!")
        else:
            print(f"\n❌ Environment verification failed!")
            sys.exit(1)
    else:
        print(f"\n❌ Environment loading failed!")
        sys.exit(1)
