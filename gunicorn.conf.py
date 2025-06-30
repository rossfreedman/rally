import multiprocessing
import os

# Server socket settings
port = int(os.environ.get("PORT", os.environ.get("RAILWAY_PORT", 8080)))
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = 1  # Single worker for WebSocket support
worker_class = "sync"  # Use sync worker for simplicity during debugging
timeout = 1800  # 30 minutes for long ETL processes

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"
capture_output = True
enable_stdio_inheritance = True

# Process naming
proc_name = "rally"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None

# Performance tuning
keepalive = 65
forwarded_allow_ips = "*"

# Prevent long-running requests from blocking workers
graceful_timeout = 300  # 5 minutes for ETL cleanup

# Ensure proper startup
preload_app = True
reload = False  # Disable auto-reload in production

# Restart workers periodically to prevent memory leaks  
max_requests = 100  # Lower for ETL stability - restart more frequently
max_requests_jitter = 10

# SSL (if needed)
keyfile = None
certfile = None
