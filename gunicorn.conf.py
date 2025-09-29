# Gunicorn configuration for production deployment
import os

# Server socket - Render provides PORT environment variable
port = os.environ.get('PORT', 5000)
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes
workers = 1  # Single worker for face recognition to avoid memory issues
worker_class = "eventlet"
worker_connections = 1000
timeout = 120
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info" if os.environ.get('DEBUG', 'False').lower() == 'true' else "warning"

# Process naming
proc_name = 'facetrace-app'

# Memory management
preload_app = True

# Render-specific optimizations
bind_unix_socket = None  # Use TCP socket for cloud deployment