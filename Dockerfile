# Use the official face_recognition Docker image (CPU version)
FROM animcogn/face_recognition:cpu

# Set work directory
WORKDIR /app

# Copy requirements and install additional dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port
EXPOSE 10000

# Start the app
CMD ["python", "main.py"]
