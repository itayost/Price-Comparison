import os
import oracledb
from pathlib import Path

class OracleConfig:
    """Configuration for Oracle Autonomous Database connection"""
    
    @staticmethod
    def init_oracle_client():
        """Initialize Oracle client with wallet files"""
        # Get wallet directory from environment or use default
        wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')

        # Convert to absolute path
        wallet_dir = os.path.abspath(wallet_dir)

        if not os.path.exists(wallet_dir):
            raise Exception(f"Wallet directory not found: {wallet_dir}")

        # Set TNS_ADMIN environment variable
        os.environ['TNS_ADMIN'] = wallet_dir
        print(f"TNS_ADMIN set to: {wallet_dir}")

        # List wallet files for debugging
        wallet_files = os.listdir(wallet_dir)
        print(f"Wallet files found: {wallet_files}")

    @staticmethod
    def get_connection_params():
        """Get connection parameters for Oracle"""
        username = os.getenv('ORACLE_USER', 'ADMIN')
        password = os.getenv('ORACLE_PASSWORD')
        service_name = os.getenv('ORACLE_SERVICE', 'champdb_low')
        wallet_password = os.getenv('ORACLE_WALLET_PASSWORD')

        if not password:
            raise Exception("ORACLE_PASSWORD environment variable not set")

        if not wallet_password:
            raise Exception("ORACLE_WALLET_PASSWORD environment variable not set")

        # Get wallet directory
        wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
        wallet_dir = os.path.abspath(wallet_dir)

        return {
            'user': username,
            'password': password,
            'dsn': service_name,
            'config_dir': wallet_dir,
            'wallet_location': wallet_dir,
            'wallet_password': wallet_password
        }

    @staticmethod
    def get_connection_string():
        """Build Oracle connection string for SQLAlchemy"""
        # For SQLAlchemy, we'll use a creator function instead
        # This is handled in connection.py
        username = os.getenv('ORACLE_USER', 'ADMIN')
        password = os.getenv('ORACLE_PASSWORD')
        service_name = os.getenv('ORACLE_SERVICE', 'champdb_low')

        if not password:
            raise Exception("ORACLE_PASSWORD environment variable not set")

        # Basic connection string - actual connection handled by creator
        return f"oracle+oracledb://{username}:{password}@{service_name}"

    @staticmethod
    def setup_wallet():
        """Extract wallet files if running in production"""
        wallet_zip = os.getenv('ORACLE_WALLET_ZIP')
        wallet_dir = os.getenv('ORACLE_WALLET_DIR', './wallet')
        wallet_dir = os.path.abspath(wallet_dir)

        if wallet_zip and os.path.exists(wallet_zip):
            import zipfile
            os.makedirs(wallet_dir, exist_ok=True)

            with zipfile.ZipFile(wallet_zip, 'r') as zip_ref:
                zip_ref.extractall(wallet_dir)

            print(f"Wallet extracted to {wallet_dir}")

        # Always set TNS_ADMIN
        os.environ['TNS_ADMIN'] = wallet_dir
        print(f"TNS_ADMIN set to: {wallet_dir}")
