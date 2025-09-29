#!/bin/bash

# Render startup script
# This script optimizes the environment for face recognition app

# Set environment variables for production
export DEBUG=False
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

# Check if we should use gunicorn or direct python
if command -v gunicorn &> /dev/null; then
    echo "Starting with gunicorn for production performance..."
    gunicorn -c gunicorn.conf.py main:app
else
    echo "Gunicorn not available, starting with python..."
    python main.py
fi