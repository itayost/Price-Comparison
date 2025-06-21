# price_comparison_server/scripts/fix_tns_config.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import oracledb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_wallet_setup():
    """Verify wallet files and TNS_ADMIN configuration"""
    print("📁 Verifying Wallet Configuration...")
    
    wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
    wallet_dir = os.path.abspath(wallet_dir)
    
    print(f"\n  Wallet directory: {wallet_dir}")
    print(f"  Directory exists: {os.path.exists(wallet_dir)}")
    
    if os.path.exists(wallet_dir):
        files = os.listdir(wallet_dir)
        print(f"\n  Files in wallet directory:")
        for file in sorted(files):
            print(f"    - {file}")
        
        # Check essential files
        essential_files = {
            'tnsnames.ora': 'TNS configuration',
            'sqlnet.ora': 'SQL*Net configuration',
            'cwallet.sso': 'Auto-login wallet',
            'ewallet.p12': 'Wallet file'
        }
        
        print(f"\n  Essential files check:")
        for file, desc in essential_files.items():
            exists = file in files
            status = "✅" if exists else "❌"
            print(f"    {status} {file} ({desc})")
    
    # Set TNS_ADMIN environment variable
    print(f"\n  Setting TNS_ADMIN environment variable...")
    os.environ['TNS_ADMIN'] = wallet_dir
    print(f"  TNS_ADMIN = {os.environ.get('TNS_ADMIN')}")
    
    return wallet_dir


def test_connection_methods():
    """Test different connection methods"""
    print("\n🔧 Testing Connection Methods...")
    
    wallet_dir = verify_wallet_setup()
    username = os.getenv('ORACLE_USER', 'ADMIN')
    password = os.getenv('ORACLE_PASSWORD')
    service = os.getenv('ORACLE_SERVICE', 'champdb_low')
    wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')
    
    if not password or not wallet_password:
        print("❌ Missing ORACLE_PASSWORD or ORACLE_WALLET_PASSWORD in .env file!")
        return False
    
    # Method 1: Using makedsn with TNS_ADMIN
    print("\n1️⃣ Method 1: Using TNS_ADMIN with config_dir...")
    try:
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,  # Explicitly set config_dir
            wallet_location=wallet_dir,
            wallet_password=wallet_password
        )
        
        print("  ✅ Connection successful!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Method 1 Success' as status FROM DUAL")
        result = cursor.fetchone()
        print(f"  Query result: {result[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
    
    # Method 2: Connection string with wallet
    print("\n2️⃣ Method 2: Using connection parameters...")
    try:
        params = {
            "user": username,
            "password": password,
            "dsn": service,
            "config_dir": wallet_dir,
            "wallet_location": wallet_dir,
            "wallet_password": wallet_password
        }
        
        connection = oracledb.connect(**params)
        
        print("  ✅ Connection successful!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Method 2 Success' as status FROM DUAL")
        result = cursor.fetchone()
        print(f"  Query result: {result[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
    
    # Method 3: Using a connection pool (recommended for production)
    print("\n3️⃣ Method 3: Using connection pool...")
    try:
        pool = oracledb.create_pool(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=wallet_password,
            min=1,
            max=2,
            increment=1
        )
        
        # Get connection from pool
        connection = pool.acquire()
        
        print("  ✅ Connection pool created successfully!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Pool Success' as status FROM DUAL")
        result = cursor.fetchone()
        print(f"  Query result: {result[0]}")
        
        cursor.close()
        pool.release(connection)
        pool.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
    
    return False


def create_working_connection_module():
    """Create a working connection module"""
    print("\n📝 Creating fixed connection module...")
    
    connection_code = '''# price_comparison_server/database/oracle_connection_fixed.py

import os
import oracledb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

def get_oracle_connection():
    """Get a direct Oracle connection"""
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    
    # IMPORTANT: Set TNS_ADMIN
    os.environ['TNS_ADMIN'] = wallet_dir
    
    params = {
        "user": os.getenv('ORACLE_USER', 'ADMIN'),
        "password": os.getenv('ORACLE_PASSWORD'),
        "dsn": os.getenv('ORACLE_SERVICE', 'champdb_low'),
        "config_dir": wallet_dir,
        "wallet_location": wallet_dir,
        "wallet_password": os.getenv('ORACLE_WALLET_PASSWORD')
    }
    
    return oracledb.connect(**params)


def create_oracle_engine():
    """Create SQLAlchemy engine for Oracle"""
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    os.environ['TNS_ADMIN'] = wallet_dir
    
    def creator():
        return get_oracle_connection()
    
    # Create engine with our connection creator
    engine = create_engine(
        "oracle+oracledb://",
        creator=creator,
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )
    
    return engine


# Test the connection
if __name__ == "__main__":
    print("Testing Oracle connection...")
    try:
        conn = get_oracle_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 'Connected!' FROM DUAL")
        result = cursor.fetchone()
        print(f"Success: {result[0]}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed: {e}")
'''
    
    # Save the file
    output_path = Path(__file__).parent.parent / "database" / "oracle_connection_fixed.py"
    with open(output_path, 'w') as f:
        f.write(connection_code)
    
    print(f"  ✅ Created: {output_path}")
    return True


if __name__ == "__main__":
    print("=== Fixing Oracle TNS Configuration ===\n")
    
    if test_connection_methods():
        print("\n✅ Connection is working!")
        
        if create_working_connection_module():
            print("\n🎉 Fixed connection module created!")
            print("\nNow you can run: python3 scripts/create_new_tables.py")
            print("\nThe key fix was adding config_dir parameter to specify where tnsnames.ora is located.")
    else:
        print("\n❌ All connection methods failed")
        print("\nPlease check:")
        print("1. Your .env file has all required variables")
        print("2. The wallet files are in the correct directory")
        print("3. The wallet password is correct")