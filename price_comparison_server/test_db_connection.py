import os
from database.connection import engine, init_db
from database.models import User, Store, Price
from sqlalchemy import text

def test_connection():
    try:
        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
        # Initialize tables
        init_db()
        print("✅ Tables created successfully!")
        
        # List tables
        with engine.connect() as conn:
            if "postgresql" in str(engine.url):
                result = conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ))
            else:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
            
            tables = [row[0] for row in result]
            print(f"✅ Found tables: {tables}")
            
    except Exception as e:
        print(f"❌ Database error: {str(e)}")

if __name__ == "__main__":
    test_connection()
