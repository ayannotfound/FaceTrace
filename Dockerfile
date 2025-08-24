# Use a pre-built image with dlib and face-recognition already installed
FROM bamos/face-recognition:latest

# Set work directory
WORKDIR /app

# Copy requirements (except face-recognition and dlib, already installed)
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-deps --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port (change if your app uses a different port)
EXPOSE 10000

# Start the app
CMD ["python", "main.py"]
