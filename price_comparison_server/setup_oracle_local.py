#!/usr/bin/env python3
"""
Setup script for Oracle wallet and environment variables
Run this before starting the server locally
"""

import os
import sys
from pathlib import Path

def setup_oracle_local():
    """Set up Oracle connection for local development"""
    
    print("Oracle Autonomous Database Setup")
    print("=" * 50)
    
    # Create wallet directory
    wallet_dir = Path("./wallet")
    wallet_dir.mkdir(exist_ok=True)
    
    print(f"\n1. Extract your wallet zip file to: {wallet_dir.absolute()}")
    print("   The directory should contain:")
    print("   - cwallet.sso")
    print("   - ewallet.p12")
    print("   - tnsnames.ora")
    print("   - sqlnet.ora")
    print("   - And other .ora files")
    
    # Check if wallet files exist
    wallet_files = ['cwallet.sso', 'ewallet.p12', 'tnsnames.ora', 'sqlnet.ora']
    missing_files = [f for f in wallet_files if not (wallet_dir / f).exists()]
    
    if missing_files:
        print(f"\n❌ Missing wallet files: {', '.join(missing_files)}")
        print("Please extract your wallet zip to the ./wallet directory first!")
        return False
    
    print("\n✅ Wallet files found!")
    
    # Read tnsnames.ora to find service names
    with open(wallet_dir / "tnsnames.ora", 'r') as f:
        content = f.read()
        print("\n2. Available service names in your wallet:")
        lines = content.split('\n')
        for line in lines:
            if '_low' in line or '_medium' in line or '_high' in line:
                service_name = line.split('=')[0].strip()
                print(f"   - {service_name}")
    
    # Create .env.oracle file
    env_file = Path(".env.oracle")
    
    print(f"\n3. Creating {env_file} with Oracle settings...")
    
    admin_password = input("\nEnter your ADMIN password: ")
    service_name = input("Enter service name (e.g., champdb_low): ")
    
    env_content = f"""# Oracle Database Configuration
USE_ORACLE=true
ORACLE_USER=ADMIN
ORACLE_PASSWORD={admin_password}
ORACLE_SERVICE={service_name}
ORACLE_WALLET_DIR=./wallet

# Keep your existing settings
SECRET_KEY=your_secret_key_here
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Created {env_file}")
    
    # Create run script
    run_script = """#!/bin/bash
# Load Oracle environment variables
export $(cat .env.oracle | grep -v '^#' | xargs)

# Set TNS_ADMIN to wallet directory
export TNS_ADMIN=./wallet

echo "Starting server with Oracle database..."
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""
    
    with open("run_oracle.sh", 'w') as f:
        f.write(run_script)
    
    os.chmod("run_oracle.sh", 0o755)
    
    print("\n✅ Created run_oracle.sh")
    
    print("\n4. To run the server with Oracle:")
    print("   ./run_oracle.sh")
    print("\n   Or manually:")
    print("   export $(cat .env.oracle | grep -v '^#' | xargs)")
    print("   export TNS_ADMIN=./wallet")
    print("   python -m uvicorn api_server:app --host 0.0.0.0 --reload")
    
    return True

if __name__ == "__main__":
    if setup_oracle_local():
        print("\n✅ Oracle setup completed successfully!")
    else:
        print("\n❌ Oracle setup failed!")
        sys.exit(1)
