import multiprocessing

# Server socket settings
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"
worker_connections = 1000
timeout = 60
keepalive = 2

# Process naming
proc_name = "rally"
default_proc_name = "rally"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

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