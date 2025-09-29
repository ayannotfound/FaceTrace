# Use the official face_recognition Docker image (CPU version)
FROM animcogn/face_recognition:cpu

# Set work directory
WORKDIR /app

# Copy requirements and install additional dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Set environment variables for production optimization
ENV DEBUG=False
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# Expose port
EXPOSE 10000

# Start the app with optimized startup script
CMD ["./start.sh"]
