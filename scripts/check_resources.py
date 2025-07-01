#!/usr/bin/env python3

import psutil
import os
import time
from datetime import datetime

print("=== SYSTEM RESOURCE CHECK ===")
print(f"Timestamp: {datetime.now()}")
print(f"CPU cores: {psutil.cpu_count()}")
print(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")
print(f"Python executable: {os.sys.executable}")

# Test basic performance
start_time = time.time()
total = sum(range(1000000))
end_time = time.time()
print(f"CPU test (sum 1M numbers): {end_time - start_time:.4f} seconds")

# Check if we're on Railway
is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
print(f"Railway environment: {is_railway}")
if is_railway:
    print(f"Railway env: {os.environ.get('RAILWAY_ENVIRONMENT')}")
    
print("=== END RESOURCE CHECK ===") 