#!/usr/bin/env python3
# fix_oracle_sequences.py
"""Create triggers for Oracle sequences"""

import os
from dotenv import load_dotenv
import oracledb

load_dotenv()

# Get Oracle connection details
user = os.getenv("ORACLE_USER")
password = os.getenv("ORACLE_PASSWORD")
dsn = os.getenv("ORACLE_SERVICE", "champdb_low")
wallet_dir = os.getenv("ORACLE_WALLET_DIR", "./wallet")

def create_sequence_triggers():
    """Create triggers for auto-incrementing primary keys in Oracle"""

    if os.getenv("USE_ORACLE", "false").lower() != "true":
        print("Not using Oracle, skipping trigger creation")
        return

    print("Creating Oracle sequence triggers...")

    # Set TNS_ADMIN
    os.environ['TNS_ADMIN'] = wallet_dir

    triggers = [
        # Chains
        """
        CREATE OR REPLACE TRIGGER chain_id_trigger
        BEFORE INSERT ON chains
        FOR EACH ROW
        WHEN (new.chain_id IS NULL)
        BEGIN
            SELECT chain_id_seq.NEXTVAL INTO :new.chain_id FROM dual;
        END;
        """,

        # Branches
        """
        CREATE OR REPLACE TRIGGER branch_id_trigger
        BEFORE INSERT ON branches
        FOR EACH ROW
        WHEN (new.branch_id IS NULL)
        BEGIN
            SELECT branch_id_seq.NEXTVAL INTO :new.branch_id FROM dual;
        END;
        """,

        # Chain Products
        """
        CREATE OR REPLACE TRIGGER chain_product_id_trigger
        BEFORE INSERT ON chain_products
        FOR EACH ROW
        WHEN (new.chain_product_id IS NULL)
        BEGIN
            SELECT chain_product_id_seq.NEXTVAL INTO :new.chain_product_id FROM dual;
        END;
        """,

        # Branch Prices
        """
        CREATE OR REPLACE TRIGGER price_id_trigger
        BEFORE INSERT ON branch_prices
        FOR EACH ROW
        WHEN (new.price_id IS NULL)
        BEGIN
            SELECT price_id_seq.NEXTVAL INTO :new.price_id FROM dual;
        END;
        """,

        # Users
        """
        CREATE OR REPLACE TRIGGER user_id_trigger
        BEFORE INSERT ON users
        FOR EACH ROW
        WHEN (new.user_id IS NULL)
        BEGIN
            SELECT user_id_seq.NEXTVAL INTO :new.user_id FROM dual;
        END;
        """,

        # Saved Carts
        """
        CREATE OR REPLACE TRIGGER cart_id_trigger
        BEFORE INSERT ON saved_carts
        FOR EACH ROW
        WHEN (new.cart_id IS NULL)
        BEGIN
            SELECT cart_id_seq.NEXTVAL INTO :new.cart_id FROM dual;
        END;
        """
    ]

    # Connect directly with oracledb
    try:
        connection = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
        )

        cursor = connection.cursor()

        for trigger in triggers:
            try:
                cursor.execute(trigger)
                trigger_name = trigger.split()[4]  # Extract trigger name
                print(f"✅ Created trigger: {trigger_name}")
            except oracledb.Error as e:
                error = e.args[0]
                trigger_name = trigger.split()[4]
                if error.code == 955:  # Object already exists
                    print(f"ℹ️  Trigger {trigger_name} already exists")
                else:
                    print(f"❌ Error creating trigger {trigger_name}: {error.message}")

        connection.commit()
        cursor.close()
        connection.close()

        print("\n✅ All triggers processed!")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    create_sequence_triggers()
