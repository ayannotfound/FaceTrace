import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "admin"),  # Replace with your MySQL username
    "password": os.getenv("DB_PASSWORD", "1234"),  # Replace with your MySQL password
    "database": os.getenv("DB_NAME", "attendance_system")
}