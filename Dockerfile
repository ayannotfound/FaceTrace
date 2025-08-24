# Use official Python 3.10 slim image
FROM python:3.10-slim

# Install system dependencies for dlib and face-recognition
RUN apt-get update && \
    apt-get install -y build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --only-binary=:all: --no-cache-dir dlib face-recognition && \
    pip install --no-cache-dir --no-deps -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port (change if your app uses a different port)
EXPOSE 10000

# Start the app
CMD ["python", "main.py"]
