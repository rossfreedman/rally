import multiprocessing
import os

# Server socket settings
port = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 8080)))
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = 2  # Increased to 2 workers for better performance while maintaining WebSocket support
worker_class = "eventlet"  # Use eventlet for WebSocket support
worker_connections = 1000
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"  # Changed to info for production

# Process naming
proc_name = "rally"

# SSL (if needed)
keyfile = None
certfile = None

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None

# Performance tuning
keepalive = 65
worker_tmp_dir = "/dev/shm"  # Use memory for temp files
forwarded_allow_ips = '*'  # Allow forwarded requests

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Prevent long-running requests from blocking workers
graceful_timeout = 60 