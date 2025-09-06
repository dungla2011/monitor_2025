import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Database configuration from environment variables
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# Encode password to handle special characters like @
encoded_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""

# Create database URL with encoded password
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)  # echo=False để tắt SQL queries logging

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for ORM models
Base = declarative_base()

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def list_all_monitor_items():
    """List all rows from monitor_items table"""
    try:
        with engine.connect() as connection:
            # Execute query to get all records from monitor_items
            query = text("SELECT * FROM monitor_items")
            result = connection.execute(query)
            
            # Fetch all results
            rows = result.fetchall()
            columns = result.keys()
            
            print(f"📊 Found {len(rows)} records in monitor_items table:")
            print("-" * 80)
            
            # Print column headers
            print(" | ".join(columns))
            print("-" * 80)
            
            # Print each row
            for row in rows:
                print(" | ".join(str(value) for value in row))
            
            return rows, columns
            
    except Exception as e:
        print(f"❌ Error querying monitor_items: {e}")
        return None, None

def list_monitor_items_as_dataframe():
    """List all rows from monitor_items table as pandas DataFrame"""
    try:
        query = "SELECT * FROM monitor_items"
        df = pd.read_sql(query, engine)
        
        print(f"📊 Monitor Items DataFrame ({len(df)} records):")
        print(df.to_string(index=False))
        
        return df
        
    except Exception as e:
        print(f"❌ Error creating DataFrame: {e}")
        return None

def get_table_info():
    """Get table structure information"""
    try:
        with engine.connect() as connection:
            # Get table structure
            query = text("DESCRIBE monitor_items")
            result = connection.execute(query)
            columns_info = result.fetchall()
            
            print("📋 Table structure for monitor_items:")
            print("-" * 60)
            print("Field | Type | Null | Key | Default | Extra")
            print("-" * 60)
            
            for col in columns_info:
                print(" | ".join(str(value) for value in col))
            
            return columns_info
            
    except Exception as e:
        print(f"❌ Error getting table info: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting database operations...")
    
    # Test connection first
    if test_connection():
        print("\n" + "="*80)
        
        # Get table structure
        print("\n1. Getting table structure:")
        get_table_info()
        
        print("\n" + "="*80)
        
        # List all items using raw SQL
        print("\n2. Listing all monitor items (Raw SQL):")
        list_all_monitor_items()
        
        print("\n" + "="*80)
        
        # List all items using pandas DataFrame
        print("\n3. Listing all monitor items (Pandas DataFrame):")
        list_monitor_items_as_dataframe()
    else:
        print("Cannot proceed without database connection.")
