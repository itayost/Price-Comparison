#!/usr/bin/env python3
"""Fix wallet configuration files for proper paths"""

import os
import shutil

wallet_dir = os.path.abspath('./wallet')

# Backup original sqlnet.ora
sqlnet_path = os.path.join(wallet_dir, 'sqlnet.ora')
backup_path = os.path.join(wallet_dir, 'sqlnet.ora.backup')

if not os.path.exists(backup_path):
    shutil.copy(sqlnet_path, backup_path)
    print(f"✅ Backed up original sqlnet.ora to sqlnet.ora.backup")

# Create new sqlnet.ora with absolute path
new_content = f"""WALLET_LOCATION = (SOURCE = (METHOD = file) (METHOD_DATA = (DIRECTORY="{wallet_dir}")))
SSL_SERVER_DN_MATCH=yes
SSL_SERVER_CERT_DN_MATCH=yes
"""

with open(sqlnet_path, 'w') as f:
    f.write(new_content)

print(f"✅ Updated sqlnet.ora with absolute path: {wallet_dir}")
print(f"\nNew content:")
print(new_content)

# Also check if we need to update cwallet.sso permissions
cwallet_path = os.path.join(wallet_dir, 'cwallet.sso')
if os.path.exists(cwallet_path):
    # Make sure it's readable
    os.chmod(cwallet_path, 0o600)
    print(f"✅ Set permissions on cwallet.sso")

print("\n✅ Wallet configuration updated!")
print("\nNow try running the test again:")
print("  python test_oracle_wallet.py")
