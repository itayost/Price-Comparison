#!/usr/bin/env python3
"""
Test Oracle Autonomous Database connection
Run this first to ensure your Oracle setup is working
"""
import os
import sys
import oracledb
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_basic_connection():
    """Test basic Oracle connection without SQLAlchemy"""
    print("=== Testing Basic Oracle Connection ===")

    # Get connection parameters
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    username = os.getenv('ORACLE_USER', 'ADMIN')
    password = os.getenv('ORACLE_PASSWORD')
    service = os.getenv('ORACLE_SERVICE', 'champdb_low')
    wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')

    print(f"Wallet Directory: {wallet_dir}")
    print(f"Username: {username}")
    print(f"Service: {service}")
    print(f"Wallet exists: {os.path.exists(wallet_dir)}")

    if not password:
        print("❌ ORACLE_PASSWORD not set!")
        return False

    if not wallet_password:
        print("❌ ORACLE_WALLET_PASSWORD not set!")
        return False

    # List wallet files
    if os.path.exists(wallet_dir):
        files = os.listdir(wallet_dir)
        print(f"Wallet files: {files}")
    else:
        print("❌ Wallet directory not found!")
        return False

    try:
        # Set TNS_ADMIN
        os.environ['TNS_ADMIN'] = wallet_dir

        # Create connection
        print("\nConnecting to Oracle...")
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=wallet_password
        )

        print("✅ Connected successfully!")

        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Hello from Oracle' FROM DUAL")
        result = cursor.fetchone()
        print(f"Test query result: {result[0]}")

        # Get version
        cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
        version = cursor.fetchone()
        print(f"Oracle version: {version[0]}")

        cursor.close()
        connection.close()

        return True

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\n=== Testing SQLAlchemy Connection ===")

    try:
        from sqlalchemy import create_engine, text

        # Create connection function
        def creator():
            wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
            return oracledb.connect(
                user=os.getenv('ORACLE_USER', 'ADMIN'),
                password=os.getenv('ORACLE_PASSWORD'),
                dsn=os.getenv('ORACLE_SERVICE', 'champdb_low'),
                config_dir=wallet_dir,
                wallet_location=wallet_dir,
                wallet_password=os.getenv('ORACLE_WALLET_PASSWORD')
            )

        # Create engine
        engine = create_engine(
            "oracle+oracledb://",
            creator=creator,
            echo=True
        )

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 'SQLAlchemy works!' FROM DUAL"))
            print(f"✅ SQLAlchemy result: {result.scalar()}")

        return True

    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}")
        return False

def check_environment():
    """Check environment variables"""
    print("=== Checking Environment Variables ===")

    required_vars = [
        'ORACLE_USER',
        'ORACLE_PASSWORD',
        'ORACLE_SERVICE',
        'ORACLE_WALLET_DIR',
        'ORACLE_WALLET_PASSWORD'
    ]

    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var:
                print(f"✅ {var}: ***")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_set = False

    return all_set

def main():
    print("Oracle Connection Test Script")
    print("=" * 50)

    # Check environment
    if not check_environment():
        print("\n❌ Please set all required environment variables!")
        sys.exit(1)

    # Test basic connection
    if not test_basic_connection():
        print("\n❌ Basic connection failed. Fix this before proceeding.")
        sys.exit(1)

    # Test SQLAlchemy
    if not test_sqlalchemy_connection():
        print("\n❌ SQLAlchemy connection failed.")
        sys.exit(1)

    print("\n✅ All tests passed! Oracle connection is working.")

if __name__ == "__main__":
    main()
