# price_comparison_server/database/oracle_connection_fixed.py

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
