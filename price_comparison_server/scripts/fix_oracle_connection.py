# price_comparison_server/scripts/fix_oracle_connection.py

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import oracledb
from dotenv import load_dotenv
import socket
import ssl

# Load environment variables
load_dotenv()

def check_network_connectivity():
    """Check if we can reach Oracle Cloud endpoints"""
    print("🌐 Checking Network Connectivity...")
    
    # Extract hostname from tnsnames.ora
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    tns_file = os.path.join(wallet_dir, 'tnsnames.ora')
    
    hostname = None
    port = 1522  # Default Oracle port
    
    try:
        with open(tns_file, 'r') as f:
            content = f.read()
            # Look for HOST and PORT
            import re
            host_match = re.search(r'HOST\s*=\s*([^\)]+)', content)
            port_match = re.search(r'PORT\s*=\s*(\d+)', content)
            
            if host_match:
                hostname = host_match.group(1).strip()
            if port_match:
                port = int(port_match.group(1))
                
        print(f"  Oracle Host: {hostname}")
        print(f"  Oracle Port: {port}")
        
        if hostname:
            # Test DNS resolution
            try:
                ip = socket.gethostbyname(hostname)
                print(f"  ✓ DNS Resolution: {hostname} → {ip}")
            except Exception as e:
                print(f"  ✗ DNS Resolution failed: {e}")
                return False
            
            # Test TCP connection
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                result = sock.connect_ex((hostname, port))
                sock.close()
                
                if result == 0:
                    print(f"  ✓ TCP Connection to {hostname}:{port} successful")
                else:
                    print(f"  ✗ TCP Connection to {hostname}:{port} failed (error code: {result})")
                    return False
            except Exception as e:
                print(f"  ✗ TCP Connection test failed: {e}")
                return False
                
        return True
        
    except Exception as e:
        print(f"  Error checking network: {e}")
        return False


def test_ssl_configuration():
    """Check SSL/TLS configuration"""
    print("\n🔐 Checking SSL Configuration...")
    
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    sqlnet_file = os.path.join(wallet_dir, 'sqlnet.ora')
    
    if os.path.exists(sqlnet_file):
        with open(sqlnet_file, 'r') as f:
            content = f.read()
            print("  sqlnet.ora content:")
            for line in content.split('\n'):
                if line.strip() and not line.strip().startswith('#'):
                    print(f"    {line.strip()}")
                    
    # Check if we need to modify sqlnet.ora
    if 'SSL_SERVER_DN_MATCH' not in content:
        print("\n  💡 You might need to add SSL_SERVER_DN_MATCH=yes to sqlnet.ora")


def create_minimal_connection():
    """Try different connection approaches"""
    print("\n🔧 Testing Connection Approaches...")
    
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    username = os.getenv('ORACLE_USER', 'ADMIN')
    password = os.getenv('ORACLE_PASSWORD')
    service = os.getenv('ORACLE_SERVICE', 'champdb_low')
    wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')
    
    # Set TNS_ADMIN
    os.environ['TNS_ADMIN'] = wallet_dir
    
    # Approach 1: Connection with explicit parameters
    print("\n1. Testing with explicit parameters...")
    try:
        dsn = oracledb.makedsn(
            host=None,  # Will use TNS
            port=None,
            service_name=service
        )
        
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,  # Use service name directly
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=wallet_password,
            disable_oob=True,  # Disable out-of-band breaks
            tcp_connect_timeout=30.0  # Increase timeout
        )
        
        print("  ✓ Connection successful!")
        connection.close()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    
    # Approach 2: Try with connection string
    print("\n2. Testing with connection string...")
    try:
        # Read actual connection string from tnsnames.ora
        tns_file = os.path.join(wallet_dir, 'tnsnames.ora')
        with open(tns_file, 'r') as f:
            content = f.read()
            
        # Extract the connection descriptor for our service
        import re
        pattern = rf'{service}\s*=\s*\(DESCRIPTION[^)]+\)\s*\)'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            connection_string = match.group(0)
            print(f"  Found connection descriptor for {service}")
            
            # Try direct connection
            connection = oracledb.connect(
                user=username,
                password=password,
                dsn=connection_string,
                config_dir=wallet_dir,
                wallet_location=wallet_dir,
                wallet_password=wallet_password
            )
            
            print("  ✓ Connection successful!")
            connection.close()
            return True
            
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    
    return False


def modify_sqlnet_ora():
    """Modify sqlnet.ora for better compatibility"""
    print("\n📝 Checking sqlnet.ora configuration...")
    
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    sqlnet_file = os.path.join(wallet_dir, 'sqlnet.ora')
    backup_file = os.path.join(wallet_dir, 'sqlnet.ora.backup')
    
    # Create backup if not exists
    if not os.path.exists(backup_file):
        import shutil
        shutil.copy2(sqlnet_file, backup_file)
        print(f"  Created backup: {backup_file}")
    
    # Read current content
    with open(sqlnet_file, 'r') as f:
        content = f.read()
    
    # Suggested modifications
    modifications = {
        'SSL_SERVER_DN_MATCH': 'yes',
        'SSL_SERVER_CERT_DN_MATCH': 'yes',
        'SQLNET.OUTBOUND_CONNECT_TIMEOUT': '60',
        'SQLNET.RECV_TIMEOUT': '60',
        'SQLNET.SEND_TIMEOUT': '60'
    }
    
    modified = False
    for key, value in modifications.items():
        if key not in content:
            content += f"\n{key}={value}"
            modified = True
            print(f"  Added: {key}={value}")
    
    if modified:
        response = input("\n  Apply these modifications to sqlnet.ora? (yes/no): ")
        if response.lower() == 'yes':
            with open(sqlnet_file, 'w') as f:
                f.write(content)
            print("  ✓ Modifications applied")
        else:
            print("  Skipped modifications")


if __name__ == "__main__":
    print("=== Oracle Connection Troubleshooting ===\n")
    
    # Run diagnostics
    if not check_network_connectivity():
        print("\n❌ Network connectivity issues detected!")
        print("\nPossible solutions:")
        print("1. Check if you're behind a firewall or VPN")
        print("2. Try connecting from a different network")
        print("3. Check if Oracle Cloud instance is running")
    
    test_ssl_configuration()
    modify_sqlnet_ora()
    
    if create_minimal_connection():
        print("\n✅ Connection successful! You can now run create_new_tables.py")
    else:
        print("\n❌ Connection still failing")
        print("\nAdditional steps to try:")
        print("1. Check Oracle Cloud console - is the database running?")
        print("2. Verify the wallet password is correct")
        print("3. Try regenerating the wallet from Oracle Cloud console")
        print("4. Check if your IP is whitelisted in Oracle Cloud Network ACLs")