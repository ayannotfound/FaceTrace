# Gunicorn configuration for production deployment
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
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
loglevel = "warning"  # Reduce log verbosity for performance

# Process naming
proc_name = 'facerec-app'

# Memory management
preload_app = True