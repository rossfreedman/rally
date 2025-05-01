import multiprocessing

# Server socket settings
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = 3  # Fixed number of workers for better stability
worker_class = "eventlet"
worker_connections = 1000
timeout = 120  # Increased timeout
keepalive = 5  # Increased keepalive

# Process naming
proc_name = "rally"
default_proc_name = "rally"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"  # Increased log level for better debugging

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

# Limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Eventlet specific
graceful_timeout = 60
max_requests = 1000
max_requests_jitter = 50 