import multiprocessing

# Server socket settings
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = 1  # Single worker for WebSocket support
threads = 4  # Multiple threads for concurrent connections
worker_class = "sync"  # Use standard sync worker
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"

# Server mechanics
daemon = False
pidfile = None

# Limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "rally"
default_proc_name = "rally"

# SSL
keyfile = None
certfile = None

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Eventlet specific
graceful_timeout = 60
max_requests = 1000
max_requests_jitter = 50 