#!/usr/bin/env python3
"""Test Oracle connection with wallet password"""

import os
import oracledb
import getpass

# Load environment variables
if os.path.exists('.env.oracle'):
    with open('.env.oracle', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Set wallet directory
wallet_dir = os.path.abspath('./wallet')
os.environ['TNS_ADMIN'] = wallet_dir

print(f"Wallet directory: {wallet_dir}")

# Get credentials
username = os.getenv('ORACLE_USER', 'ADMIN')
password = os.getenv('ORACLE_PASSWORD')
service = os.getenv('ORACLE_SERVICE', 'champdb_low')

# Get wallet password
wallet_password = getpass.getpass("Enter your wallet password (the one you used when downloading the wallet): ")

print(f"\nConnecting as {username} to {service}")

try:
    # Connection with wallet password
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=service,
        config_dir=wallet_dir,
        wallet_location=wallet_dir,
        wallet_password=wallet_password
    )
    
    print("✅ Connected successfully with wallet password!")
    
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
    
    print("\n✅ Success! Your wallet password works.")
    print("\nTo use this in your application, add to your .env.oracle:")
    print(f"ORACLE_WALLET_PASSWORD={wallet_password}")
    
except oracledb.Error as e:
    print(f"❌ Connection failed: {e}")
    print("\nIf this doesn't work, please re-download the wallet without a password.")
