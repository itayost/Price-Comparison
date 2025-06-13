#!/usr/bin/env python3
"""Test direct Oracle connection without SQLAlchemy"""

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
os.environ['TNS_ADMIN'] = wallet_dir

print(f"TNS_ADMIN: {wallet_dir}")
print(f"Wallet exists: {os.path.exists(wallet_dir)}")
print(f"Wallet files: {os.listdir(wallet_dir) if os.path.exists(wallet_dir) else 'NOT FOUND'}")

# Get credentials
username = os.getenv('ORACLE_USER', 'ADMIN')
password = os.getenv('ORACLE_PASSWORD')
service = os.getenv('ORACLE_SERVICE', 'champdb_low')

print(f"\nConnecting as {username} to {service}")

try:
    # Method 1: Using service name (requires TNS_ADMIN)
    print("\nMethod 1: Using service name with TNS_ADMIN...")
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=service
    )
    
    cursor = connection.cursor()
    cursor.execute("SELECT 'Hello from Oracle!' FROM DUAL")
    result = cursor.fetchone()
    print(f"✅ Success: {result[0]}")
    
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"❌ Method 1 failed: {str(e)}")
    
    try:
        # Method 2: Using full connection string
        print("\nMethod 2: Using full connection string...")
        
        # Read the full connection string from tnsnames.ora
        tnsnames_path = os.path.join(wallet_dir, 'tnsnames.ora')
        with open(tnsnames_path, 'r') as f:
            content = f.read()
            
        # Extract the connection details for your service
        import re
        pattern = f"{service}\\s*=\\s*\\(description=.*?\\)\\)\\)"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            full_dsn = match.group(0).split('=', 1)[1].strip()
            print(f"Found DSN: {full_dsn[:100]}...")
            
            connection = oracledb.connect(
                user=username,
                password=password,
                dsn=full_dsn,
                config_dir=wallet_dir,
                wallet_location=wallet_dir,
                wallet_password=None  # Wallet password if you set one
            )
            
            cursor = connection.cursor()
            cursor.execute("SELECT 'Hello from Oracle!' FROM DUAL")
            result = cursor.fetchone()
            print(f"✅ Success: {result[0]}")
            
            cursor.close()
            connection.close()
            
    except Exception as e2:
        print(f"❌ Method 2 failed: {str(e2)}")
        
        # Show what we need to fix
        print("\n🔧 To fix this:")
        print("1. Make sure wallet files are in ./wallet directory")
        print("2. Check that your .env.oracle has the correct password")
        print("3. Ensure the service name matches what's in tnsnames.ora")
