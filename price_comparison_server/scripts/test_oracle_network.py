# price_comparison_server/scripts/test_oracle_network.py

import os
import sys
import socket
import subprocess
import ssl
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import oracledb

# Load environment variables
load_dotenv()

def test_dns_and_network():
    """Test DNS resolution and network connectivity"""
    host = "adb.il-jerusalem-1.oraclecloud.com"
    port = 1522
    
    print(f"🌐 Testing connectivity to Oracle Cloud")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    
    # 1. Test DNS resolution
    print("\n1️⃣ Testing DNS resolution...")
    try:
        ip_address = socket.gethostbyname(host)
        print(f"  ✅ DNS resolved: {host} → {ip_address}")
    except socket.gaierror as e:
        print(f"  ❌ DNS resolution failed: {e}")
        return False
    
    # 2. Test basic connectivity with ping
    print("\n2️⃣ Testing ping (may not work on all networks)...")
    try:
        # Use ping command (platform-specific)
        if sys.platform.startswith('win'):
            cmd = ['ping', '-n', '1', host]
        else:
            cmd = ['ping', '-c', '1', host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✅ Ping successful")
        else:
            print(f"  ⚠️ Ping failed (this might be normal if ICMP is blocked)")
    except Exception as e:
        print(f"  ⚠️ Ping test skipped: {e}")
    
    # 3. Test TCP connection
    print("\n3️⃣ Testing TCP connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((ip_address, port))
        
        if result == 0:
            print(f"  ✅ TCP connection successful to {ip_address}:{port}")
            sock.close()
            return True
        else:
            print(f"  ❌ TCP connection failed (error code: {result})")
            sock.close()
            return False
    except Exception as e:
        print(f"  ❌ TCP connection error: {e}")
        return False


def test_ssl_connection():
    """Test SSL/TLS connection"""
    host = "adb.il-jerusalem-1.oraclecloud.com"
    port = 1522
    
    print("\n🔐 Testing SSL/TLS connection...")
    try:
        # Create SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Create socket and wrap with SSL
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        ssl_sock = context.wrap_socket(sock, server_hostname=host)
        ssl_sock.connect((host, port))
        
        print(f"  ✅ SSL connection established")
        print(f"  SSL Version: {ssl_sock.version()}")
        
        ssl_sock.close()
        return True
        
    except Exception as e:
        print(f"  ❌ SSL connection failed: {e}")
        return False


def test_oracle_connection_debug():
    """Test Oracle connection with debug output"""
    print("\n🔧 Testing Oracle connection with debugging...")
    
    wallet_dir = os.path.abspath(os.getenv('ORACLE_WALLET_DIR', './wallet'))
    username = os.getenv('ORACLE_USER', 'ADMIN')
    password = os.getenv('ORACLE_PASSWORD')
    service = os.getenv('ORACLE_SERVICE', 'champdb_low')
    wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')
    
    # Set TNS_ADMIN
    os.environ['TNS_ADMIN'] = wallet_dir
    
    # Enable Oracle client debugging
    os.environ['DPI_DEBUG_LEVEL'] = '64'  # Maximum debug output
    
    print(f"  TNS_ADMIN: {wallet_dir}")
    print(f"  Service: {service}")
    print(f"  Wallet location: {wallet_dir}")
    
    # Try connection with various timeout settings
    print("\n  Attempting connection with extended timeouts...")
    try:
        # Create connection with all timeout parameters
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=service,
            wallet_location=wallet_dir,
            wallet_password=wallet_password,
            tcp_connect_timeout=60.0,  # 60 seconds for TCP connection
            retry_count=3,
            retry_delay=2
        )
        
        print("  ✅ Connection successful!")
        
        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT 'SUCCESS' FROM DUAL")
        result = cursor.fetchone()
        print(f"  Query result: {result[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except oracledb.Error as e:
        error, = e.args
        print(f"  ❌ Oracle Error Code: {error.code}")
        print(f"  ❌ Oracle Error Message: {error.message}")
        
        # Specific error handling
        if error.code == 12154:
            print("  💡 TNS could not resolve the connect identifier")
        elif error.code == 12514:
            print("  💡 TNS listener does not know of service")
        elif error.code == 12541:
            print("  💡 TNS no listener")
        elif error.code == 28000:
            print("  💡 Account is locked")
        elif "DPY-4011" in str(error):
            print("  💡 Network timeout - check firewall/VPN")
        elif "DPY-6005" in str(error):
            print("  💡 Cannot connect to database - timeout")
            
    except Exception as e:
        print(f"  ❌ General Error: {type(e).__name__}: {e}")
    
    return False


def check_firewall_suggestions():
    """Provide firewall troubleshooting suggestions"""
    print("\n🔥 Firewall/Network Troubleshooting:")
    print("  If the connection is timing out, try:")
    print("  1. Disable any VPN connections")
    print("  2. Check if your network allows outbound connections on port 1522")
    print("  3. Try from a different network (home vs office)")
    print("  4. Check Oracle Cloud console:")
    print("     - Ensure the database is in 'Available' state")
    print("     - Check the Access Control List (ACL) settings")
    print("     - Verify your IP is not blocked")


if __name__ == "__main__":
    print("=== Oracle Network Connectivity Test ===\n")
    
    # Test network connectivity
    network_ok = test_dns_and_network()
    
    if network_ok:
        ssl_ok = test_ssl_connection()
        
        if ssl_ok:
            if test_oracle_connection_debug():
                print("\n✅ Everything is working! Connection successful!")
            else:
                print("\n❌ Network is OK but Oracle connection fails")
                check_firewall_suggestions()
        else:
            print("\n❌ SSL connection failed")
            check_firewall_suggestions()
    else:
        print("\n❌ Basic network connectivity failed")
        check_firewall_suggestions()
        
        print("\n💡 Quick test: Try accessing this URL in your browser:")
        print("   https://adb.il-jerusalem-1.oraclecloud.com:1522")
        print("   (You should get an error page, but it proves connectivity)")