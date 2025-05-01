import multiprocessing
import os

# Server socket settings
port = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 8080)))
bind = f"0.0.0.0:{port}"  # Simplified binding
backlog = 2048

# Worker processes
workers = 1  # Single worker for WebSocket support
worker_class = "sync"  # Use sync worker for simplicity during debugging
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"
capture_output = True
enable_stdio_inheritance = True

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
forwarded_allow_ips = '*'

# Prevent long-running requests from blocking workers
graceful_timeout = 60

# Ensure proper startup
preload_app = True
reload = False  # Disable auto-reload in production

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None

# Performance tuning
keepalive = 65
forwarded_allow_ips = '*'  # Allow forwarded requests

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Prevent long-running requests from blocking workers
graceful_timeout = 60

# Ensure proper proxy handling
proxy_protocol = True
proxy_allow_ips = '*' 