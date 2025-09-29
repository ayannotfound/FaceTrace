#!/bin/bash

# Render startup script
# This script optimizes the environment for face recognition app on Render

echo "Starting FaceTrace on Render..."

# Set environment variables for production
export DEBUG=${DEBUG:-False}
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Log the port being used (Render sets this automatically)
echo "PORT: ${PORT:-5000}"
echo "DEBUG: ${DEBUG}"

# Check if we should use gunicorn or direct python
if command -v gunicorn &> /dev/null; then
    echo "Starting with gunicorn for production performance..."
    echo "Gunicorn config: workers=1, worker_class=eventlet, port=${PORT:-5000}"
    gunicorn -c gunicorn.conf.py main:app
else
    echo "Gunicorn not available, starting with python..."
    echo "Python direct mode on port ${PORT:-5000}"
    python main.py
fi