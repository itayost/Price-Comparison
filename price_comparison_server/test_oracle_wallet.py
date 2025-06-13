#!/usr/bin/env python3
"""Test Oracle connection with proper wallet configuration"""

import os
import oracledb

# Load environment variables
if os.path.exists('.env.oracle'):
    with open('.env.oracle', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Set wallet directory
wallet_dir = os.path.abspath('./wallet')

print(f"Wallet directory: {wallet_dir}")
print(f"Wallet files: {os.listdir(wallet_dir)}")

# Get credentials
username = os.getenv('ORACLE_USER', 'ADMIN')
password = os.getenv('ORACLE_PASSWORD')
service = os.getenv('ORACLE_SERVICE', 'champdb_low')

print(f"\nConnecting as {username} to {service}")

# Read the wallet password from sqlnet.ora to check configuration
sqlnet_path = os.path.join(wallet_dir, 'sqlnet.ora')
print(f"\nChecking sqlnet.ora configuration:")
with open(sqlnet_path, 'r') as f:
    print(f.read())

try:
    # Method 1: Let's use parameters properly
    print("\n\nTrying connection with proper wallet configuration...")
    
    # Create connection with wallet configuration
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=service,
        config_dir=wallet_dir,
        wallet_location=wallet_dir
    )
    
    print("✅ Connected successfully!")
    
    # Test the connection
    cursor = connection.cursor()
    cursor.execute("SELECT 'Hello from Oracle!' as greeting FROM DUAL")
    result = cursor.fetchone()
    print(f"✅ Query result: {result[0]}")
    
    # Get database version
    cursor.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
    version = cursor.fetchone()
    print(f"✅ Oracle version: {version[0]}")
    
    cursor.close()
    connection.close()
    
except oracledb.Error as e:
    print(f"❌ Connection failed: {e}")
    
    # Try another method
    print("\n\nTrying alternative connection method...")
    try:
        # Set TNS_ADMIN environment variable
        os.environ['TNS_ADMIN'] = wallet_dir
        
        # Simple connection with TNS_ADMIN set
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            config_dir=wallet_dir,
            wallet_location=wallet_dir
        )
        
        print("✅ Alternative method succeeded!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT 'Connected!' FROM DUAL")
        result = cursor.fetchone()
        print(f"✅ Result: {result[0]}")
        
        cursor.close()
        connection.close()
        
    except oracledb.Error as e2:
        print(f"❌ Alternative method also failed: {e2}")
        
        print("\n\n📋 Troubleshooting steps:")
        print("1. Check if your wallet needs a password")
        print("2. Verify the ORACLE_PASSWORD in .env.oracle is correct")
        print("3. Make sure all wallet files are present")
        
        # Check for ewallet.pem which indicates SSL wallet
        if 'ewallet.pem' in os.listdir(wallet_dir):
            print("\n⚠️  Found ewallet.pem - this wallet uses SSL certificates")
            print("   The 'Enter PEM pass phrase' prompt suggests the wallet is password-protected")
            print("   You may need to regenerate the wallet without a password")
