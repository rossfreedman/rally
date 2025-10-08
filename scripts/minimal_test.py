#!/usr/bin/env python3

import os
import sys
import json

# Add project root to path
sys.path.append(os.getcwd())

print("🧪 MINIMAL TEST")
print("=" * 20)

# Test basic imports
try:
    from database_config import get_db
    print("✅ database_config import successful")
except Exception as e:
    print(f"❌ database_config import failed: {e}")
    sys.exit(1)

# Test import_players import
try:
    import data.etl.import.import_players
    print("✅ import_players import successful")
except Exception as e:
    print(f"❌ import_players import failed: {e}")
    sys.exit(1)

# Test specific function import
try:
    from data.etl.import.import_players import upsert_player
    print("✅ upsert_player import successful")
except Exception as e:
    print(f"❌ upsert_player import failed: {e}")
    sys.exit(1)

print("✅ All imports successful")
