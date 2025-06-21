# price_comparison_server/scripts/test_oracle_connection.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import oracledb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_basic_connection():
    """Test basic Oracle connection"""
    print("🔍 Testing Oracle Connection...")
    print(f"Oracle client version: {oracledb.version}")
    
    # Print environment info
    wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
    wallet_dir = os.path.abspath(wallet_dir)
    
    print(f"\n📁 Wallet Configuration:")
    print(f"  Wallet directory: {wallet_dir}")
    print(f"  Wallet exists: {os.path.exists(wallet_dir)}")
    
    if os.path.exists(wallet_dir):
        files = os.listdir(wallet_dir)
        print(f"  Wallet files: {files}")
        
        # Check for essential files
        essential_files = ['tnsnames.ora', 'sqlnet.ora', 'cwallet.sso']
        for file in essential_files:
            exists = file in files
            print(f"  {file}: {'✓' if exists else '✗ MISSING'}")
    
    # Check environment variables
    print(f"\n🔑 Environment Variables:")
    print(f"  ORACLE_USER: {os.getenv('ORACLE_USER', 'NOT SET')}")
    print(f"  ORACLE_PASSWORD: {'***' if os.getenv('ORACLE_PASSWORD') else 'NOT SET'}")
    print(f"  ORACLE_SERVICE: {os.getenv('ORACLE_SERVICE', 'NOT SET')}")
    print(f"  ORACLE_WALLET_PASSWORD: {'***' if os.getenv('ORACLE_WALLET_PASSWORD') else 'NOT SET'}")
    print(f"  TNS_ADMIN: {os.getenv('TNS_ADMIN', 'NOT SET')}")
    
    # Try connection
    try:
        print(f"\n🔌 Attempting connection...")
        
        # Set TNS_ADMIN
        os.environ['TNS_ADMIN'] = wallet_dir
        
        username = os.getenv('ORACLE_USER', 'ADMIN')
        password = os.getenv('ORACLE_PASSWORD')
        service = os.getenv('ORACLE_SERVICE', 'champdb_low')
        wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')
        
        if not password:
            print("❌ ORACLE_PASSWORD environment variable not set!")
            return False
            
        if not wallet_password:
            print("❌ ORACLE_WALLET_PASSWORD environment variable not set!")
            return False
        
        print(f"  Connecting to service: {service}")
        print(f"  Using wallet at: {wallet_dir}")
        
        # Try connection
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=wallet_password
        )
        
        print("✅ Connection successful!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Hello from Oracle' FROM DUAL")
        result = cursor.fetchone()
        print(f"  Test query result: {result[0]}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Common issues
        if "DPY-4011" in str(e):
            print("\n💡 Possible causes:")
            print("  1. Network connectivity issues")
            print("  2. Wallet configuration problems")
            print("  3. Incorrect service name")
            print("  4. Firewall blocking connection")
            
        elif "DPY-4000" in str(e):
            print("\n💡 Wallet password might be incorrect")
            
        elif "ORA-01017" in str(e):
            print("\n💡 Invalid username/password")
            
        return False


def test_tns_configuration():
    """Check TNS configuration"""
    print("\n📋 Checking TNS Configuration...")
    
    wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
    wallet_dir = os.path.abspath(wallet_dir)
    tns_file = os.path.join(wallet_dir, 'tnsnames.ora')
    
    if os.path.exists(tns_file):
        print(f"  Reading {tns_file}")
        try:
            with open(tns_file, 'r') as f:
                content = f.read()
                # Show service names
                import re
                services = re.findall(r'^(\w+)\s*=', content, re.MULTILINE)
                print(f"  Available services: {services}")
                
                # Check if our service exists
                service = os.getenv('ORACLE_SERVICE', 'champdb_low')
                if service in services:
                    print(f"  ✓ Service '{service}' found in tnsnames.ora")
                else:
                    print(f"  ✗ Service '{service}' NOT found in tnsnames.ora")
                    print(f"    Available: {', '.join(services)}")
        except Exception as e:
            print(f"  Error reading tnsnames.ora: {e}")
    else:
        print(f"  ✗ tnsnames.ora not found at {tns_file}")


def test_with_different_modes():
    """Try different connection modes"""
    print("\n🔧 Testing Different Connection Modes...")
    
    # Try thick mode
    print("\n1. Testing with Thick mode...")
    try:
        oracledb.init_oracle_client()
        print("  ✓ Thick mode initialized")
    except Exception as e:
        print(f"  ✗ Thick mode not available: {e}")
        print("  Continuing with Thin mode...")
    
    # Test connection again
    test_basic_connection()


if __name__ == "__main__":
    print("=== Oracle Connection Diagnostic ===\n")
    
    # Run tests
    test_tns_configuration()
    
    if test_basic_connection():
        print("\n✅ Oracle connection is working!")
    else:
        print("\n❌ Oracle connection failed!")
        print("\n📝 Next steps:")
        print("1. Check your .env file has all required variables")
        print("2. Verify wallet files are in the correct location")
        print("3. Check network connectivity to Oracle Cloud")
        print("4. Try updating oracledb: pip install --upgrade oracledb")