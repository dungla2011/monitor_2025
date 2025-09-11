#!/usr/bin/env python3
"""
Test 01: Model-Database Compatibility Test
Kiểm tra tính tương thích giữa SQLAlchemy models và database schema thực tế

Tests:
1. Database connection
2. Table existence (5 tables: monitor_items, monitor_configs, monitor_and_configs, monitor_settings, users)
3. Column compatibility (names, types, nullable)
4. Primary keys
5. Sample data validation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from db_connection import engine
from models import (
    Base, MonitorItem, MonitorConfig, MonitorAndConfig, 
    MonitorSettings, User
)
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ModelDatabaseTester:
    def __init__(self):
        self.engine = engine
        self.inspector = inspect(self.engine)
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def log_error(self, message):
        """Log error và add vào errors list"""
        self.errors.append(message)
        print(f"❌ {message}")
        
    def log_warning(self, message):
        """Log warning và add vào warnings list"""
        self.warnings.append(message)
        print(f"⚠️ {message}")
        
    def log_success(self, message):
        """Log success message"""
        self.successes.append(message)
        print(f"✅ {message}")

    def test_database_connection(self):
        """Test 1: Kiểm tra kết nối database"""
        print("\n" + "="*70)
        print("TEST 1: DATABASE CONNECTION")
        print("="*70)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test, VERSION() as version"))
                row = result.fetchone()
                if row[0] == 1:
                    self.log_success(f"Database connection successful")
                    self.log_success(f"Database version: {row[1]}")
                    return True
                else:
                    self.log_error("Database connection test failed")
                    return False
        except Exception as e:
            self.log_error(f"Database connection failed: {e}")
            return False

    def test_tables_exist(self):
        """Test 2: Kiểm tra tất cả tables có tồn tại không"""
        print("\n" + "="*70)
        print("TEST 2: TABLE EXISTENCE")
        print("="*70)
        
        # Expected tables từ models
        expected_tables = {
            'monitor_items': MonitorItem,
            'monitor_configs': MonitorConfig,
            'monitor_and_configs': MonitorAndConfig,
            'monitor_settings': MonitorSettings,
            'users': User
        }
        
        # Lấy danh sách tables từ database
        db_tables = self.inspector.get_table_names()
        
        print(f"📋 Expected tables: {list(expected_tables.keys())}")
        print(f"📋 Database tables: {db_tables}")
        
        all_tables_exist = True
        for table_name in expected_tables.keys():
            if table_name in db_tables:
                self.log_success(f"Table '{table_name}' exists")
            else:
                self.log_error(f"Table '{table_name}' MISSING in database")
                all_tables_exist = False
                
        # Check for extra tables
        extra_tables = set(db_tables) - set(expected_tables.keys())
        if extra_tables:
            self.log_warning(f"Extra tables in database (not in models): {list(extra_tables)}")
            
        return all_tables_exist, expected_tables

    def test_table_columns(self, table_name, model_class):
        """Test 3: Kiểm tra columns của một table"""
        print(f"\n--- Testing table: {table_name} ---")
        
        try:
            # Lấy columns từ database
            db_columns = self.inspector.get_columns(table_name)
            db_column_info = {col['name']: col for col in db_columns}
            
            # Lấy columns từ model
            model_columns = model_class.__table__.columns
            
            table_valid = True
            
            print(f"📊 Model has {len(model_columns)} columns, DB has {len(db_column_info)} columns")
            
            # Check model columns exist in database
            for col_name, column in model_columns.items():
                if col_name in db_column_info:
                    db_col = db_column_info[col_name]
                    
                    # Check data type compatibility
                    model_type = str(column.type)
                    db_type = str(db_col['type'])
                    
                    if self.types_compatible(model_type, db_type):
                        self.log_success(f"  Column '{col_name}': {model_type} ↔ {db_type}")
                    else:
                        self.log_error(f"  Column '{col_name}' TYPE MISMATCH: Model={model_type}, DB={db_type}")
                        table_valid = False
                    
                    # Check nullable
                    model_nullable = column.nullable
                    db_nullable = db_col['nullable']
                    if model_nullable == db_nullable:
                        print(f"    ✓ nullable: {model_nullable}")
                    else:
                        self.log_warning(f"    ⚠ nullable MISMATCH: Model={model_nullable}, DB={db_nullable}")
                else:
                    self.log_error(f"  Column '{col_name}' MISSING in database")
                    table_valid = False
            
            # Check for extra columns in database
            model_column_names = set(model_columns.keys())
            db_column_names = set(db_column_info.keys())
            extra_columns = db_column_names - model_column_names
            
            if extra_columns:
                self.log_warning(f"  Extra columns in DB: {list(extra_columns)}")
                
            return table_valid
            
        except Exception as e:
            self.log_error(f"Error testing table {table_name}: {e}")
            return False

    def types_compatible(self, model_type, db_type):
        """Kiểm tra compatibility giữa SQLAlchemy type và database type"""
        # Normalize types for comparison
        model_type = model_type.upper()
        db_type = db_type.upper()
        
        # Common type mappings MySQL/MariaDB
        type_mappings = [
            (['INTEGER', 'INT'], ['INT', 'INTEGER', 'BIGINT', 'MEDIUMINT', 'SMALLINT', 'TINYINT']),
            (['VARCHAR'], ['VARCHAR', 'CHAR']),
            (['TEXT'], ['TEXT', 'LONGTEXT', 'MEDIUMTEXT', 'TINYTEXT']),
            (['DATETIME'], ['DATETIME', 'TIMESTAMP']),
            (['BOOLEAN'], ['TINYINT(1)', 'TINYINT', 'BOOLEAN', 'BOOL']),
            (['FLOAT'], ['FLOAT', 'DOUBLE', 'REAL']),
            (['DECIMAL'], ['DECIMAL', 'NUMERIC'])
        ]
        
        # Direct match
        if model_type == db_type:
            return True
            
        # Check mappings
        for model_types, db_types in type_mappings:
            if any(mt in model_type for mt in model_types):
                if any(dt in db_type for dt in db_types):
                    return True
        
        # VARCHAR với độ dài - allow different lengths
        if 'VARCHAR' in model_type and 'VARCHAR' in db_type:
            return True
        
        # String types compatibility
        if ('STRING' in model_type or 'VARCHAR' in model_type) and ('VARCHAR' in db_type or 'TEXT' in db_type):
            return True
                        
        return False

    def test_primary_keys(self, table_name, model_class):
        """Test 4: Kiểm tra primary keys"""
        try:
            # Get primary key from database
            pk_constraint = self.inspector.get_pk_constraint(table_name)
            db_pk_columns = pk_constraint['constrained_columns']
            
            # Get primary key from model
            model_pk_columns = [col.name for col in model_class.__table__.primary_key.columns]
            
            if set(db_pk_columns) == set(model_pk_columns):
                self.log_success(f"  Primary key MATCH: {model_pk_columns}")
                return True
            else:
                self.log_error(f"  Primary key MISMATCH: Model={model_pk_columns}, DB={db_pk_columns}")
                return False
                
        except Exception as e:
            self.log_error(f"Error checking primary key for {table_name}: {e}")
            return False

    def test_sample_data(self, table_name):
        """Test 5: Test với sample data"""
        try:
            with self.engine.connect() as conn:
                # Try to count rows
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.fetchone()[0]
                
                if count > 0:
                    self.log_success(f"  Sample data: {count} rows found")
                    
                    # Get sample row
                    result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
                    sample_row = result.fetchone()
                    if sample_row:
                        columns = result.keys()
                        sample_data = dict(zip(columns, sample_row))
                        print(f"    📄 Sample row: {sample_data}")
                else:
                    self.log_warning(f"  No data in table {table_name}")
                    
                return True
                
        except Exception as e:
            self.log_error(f"Error reading sample data from {table_name}: {e}")
            return False

    def run_comprehensive_test(self):
        """Chạy tất cả tests"""
        print("🧪 MODEL-DATABASE COMPATIBILITY TEST")
        print("🕒 Test started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*80)
        
        # Test 1: Database Connection
        if not self.test_database_connection():
            print("\n💥 CRITICAL: Cannot connect to database. Aborting tests.")
            return False
            
        # Test 2: Tables exist
        tables_exist, expected_tables = self.test_tables_exist()
        
        if not tables_exist:
            self.log_warning("Some tables are missing - continuing with available tables")
            
        # Test 3-5: Detailed table tests for existing tables
        print("\n" + "="*70)
        print("TEST 3-5: DETAILED TABLE ANALYSIS")
        print("="*70)
        
        db_tables = self.inspector.get_table_names()
        
        for table_name, model_class in expected_tables.items():
            if table_name in db_tables:
                print(f"\n🔍 Testing table: {table_name} ({model_class.__name__})")
                print("-" * 50)
                
                self.test_table_columns(table_name, model_class)
                self.test_primary_keys(table_name, model_class)
                self.test_sample_data(table_name)
            else:
                print(f"\n⏭️ Skipping {table_name} - table not found in database")
        
        # Generate Summary
        self.generate_summary()
        
        return len(self.errors) == 0

    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️ Warnings:  {len(self.warnings)}")
        print(f"❌ Errors:    {len(self.errors)}")
        
        if self.errors:
            print(f"\n🔥 CRITICAL ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i:2d}. {error}")
                
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i:2d}. {warning}")
        
        print("\n" + "="*80)
        if not self.errors:
            print("🎉 ALL CRITICAL TESTS PASSED!")
            print("💡 Models are compatible with database schema.")
            if self.warnings:
                print("📝 Note: There are some warnings above - please review them.")
        else:
            print("💥 SOME TESTS FAILED!")
            print("🔧 Please fix the errors above before deploying.")
        
        print("🕒 Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    """Main test runner"""
    print("🚀 Starting Model-Database Compatibility Test...")
    
    tester = ModelDatabaseTester()
    success = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    exit_code = 0 if success else 1
    print(f"\n🏁 Test finished with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()