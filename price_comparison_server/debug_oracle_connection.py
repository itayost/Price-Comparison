#!/usr/bin/env python3
"""Debug Oracle connection issues"""

import os
import oracledb
import ssl

# Load environment variables
if os.path.exists('.env.oracle'):
    with open('.env.oracle', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                try:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
                except ValueError:
                    continue

# Set wallet directory
wallet_dir = os.path.abspath('./wallet')
os.environ['TNS_ADMIN'] = wallet_dir

print("=== Oracle Connection Debug ===")
print(f"Python version: {os.sys.version}")
print(f"oracledb version: {oracledb.__version__}")
print(f"TNS_ADMIN: {wallet_dir}")
print(f"Wallet exists: {os.path.exists(wallet_dir)}")

# Check SSL version
print(f"SSL version: {ssl.OPENSSL_VERSION}")

# Get credentials
username = os.getenv('ORACLE_USER', 'ADMIN')
password = os.getenv('ORACLE_PASSWORD', 'NOT_SET')
service = os.getenv('ORACLE_SERVICE', 'champdb_low')
wallet_password = os.getenv('ORACLE_WALLET_PASSWORD', 'NOT_SET')

print(f"\nCredentials check:")
print(f"Username: {username}")
print(f"Password set: {'YES' if password != 'NOT_SET' else 'NO'}")
print(f"Service: {service}")
print(f"Wallet password set: {'YES' if wallet_password != 'NOT_SET' else 'NO'}")

# Test 1: Basic connection with detailed error handling
print("\n\n=== Test 1: Basic connection ===")
try:
    # Enable debug mode
    oracledb.init_oracle_client = lambda **kwargs: None  # Ensure thin mode
    
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=service,
        config_dir=wallet_dir,
        wallet_location=wallet_dir,
        wallet_password=wallet_password if wallet_password != 'NOT_SET' else None
    )
    
    print("✅ Connection established!")
    
    # Simple query
    cursor = connection.cursor()
    cursor.execute("SELECT 'SUCCESS' FROM DUAL")
    result = cursor.fetchone()
    print(f"✅ Query result: {result[0]}")
    
    cursor.close()
    connection.close()
    print("✅ Connection closed successfully")
    
except oracledb.Error as e:
    error_obj = e.args[0]
    print(f"❌ Oracle Error Code: {error_obj.code if hasattr(error_obj, 'code') else 'N/A'}")
    print(f"❌ Error Message: {str(e)}")
    
    # Common error codes and solutions
    if "DPI-1047" in str(e):
        print("\n💡 Solution: You're in thin mode (good!), no Oracle Client needed")
    elif "ORA-01017" in str(e):
        print("\n💡 Solution: Invalid username/password. Check your ADMIN password")
    elif "ORA-12154" in str(e):
        print("\n💡 Solution: TNS could not resolve the connect identifier. Check service name")
    elif "DPY-6005" in str(e):
        print("\n💡 Solution: SSL/Network error. Check wallet configuration")
    elif "DPY-4027" in str(e):
        print("\n💡 Solution: Cannot find tnsnames.ora. Check TNS_ADMIN path")

# Test 2: Check tnsnames.ora
print("\n\n=== Test 2: Check tnsnames.ora ===")
tnsnames_path = os.path.join(wallet_dir, 'tnsnames.ora')
if os.path.exists(tnsnames_path):
    print("✅ tnsnames.ora found")
    with open(tnsnames_path, 'r') as f:
        content = f.read()
        if service in content:
            print(f"✅ Service '{service}' found in tnsnames.ora")
        else:
            print(f"❌ Service '{service}' NOT found in tnsnames.ora")
            print("Available services:")
            import re
            services = re.findall(r'^(\w+)\s*=', content, re.MULTILINE)
            for svc in services:
                print(f"  - {svc}")
else:
    print("❌ tnsnames.ora not found!")

# Test 3: Check sqlnet.ora
print("\n\n=== Test 3: Check sqlnet.ora ===")
sqlnet_path = os.path.join(wallet_dir, 'sqlnet.ora')
if os.path.exists(sqlnet_path):
    print("✅ sqlnet.ora found")
    with open(sqlnet_path, 'r') as f:
        content = f.read()
        print("Content:")
        print(content)
        if wallet_dir in content:
            print(f"✅ Wallet directory correctly set in sqlnet.ora")
        else:
            print(f"❌ Wallet directory not properly set in sqlnet.ora")
else:
    print("❌ sqlnet.ora not found!")

print("\n\n=== Diagnostic Summary ===")
print("If you're seeing 'NoneType' errors, it usually means:")
print("1. Network connectivity issues to Oracle Cloud")
print("2. Wallet password mismatch")
print("3. SSL certificate issues")
print("\nTry:")
print("1. Verify your internet connection")
print("2. Check if you can access: https://adb.il-jerusalem-1.oraclecloud.com")
print("3. Ensure your wallet password is correct")
print("4. Try regenerating the wallet if issues persist")
