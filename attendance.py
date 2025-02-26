# attendance.py
import mysql.connector
import json
from datetime import datetime
from config import DB_CONFIG

# Cache for face encodings
_encoding_cache = {}

def load_face_encodings() -> tuple[dict | None, str]:
    """Load face encodings from the database with caching."""
    global _encoding_cache
    if _encoding_cache:
        return _encoding_cache, "Loaded from cache."

    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = "SELECT id, name, face_encoding FROM users"
                cursor.execute(query)
                face_encodings = {}
                for user_id, name, encoded_json in cursor:
                    encoding = json.loads(encoded_json)
                    face_encodings[user_id] = {"name": name, "encoding": encoding}
                _encoding_cache.update(face_encodings)
                return face_encodings, "Face encodings loaded successfully!"
    except mysql.connector.Error as err:
        return None, f"Database error: {err}"

def record_attendance(user_id: int, last_attendance: dict, cooldown: int = 60) -> tuple[bool, str]:
    """Record attendance for a user if cooldown period has passed."""
    current_time = datetime.now()
    if user_id in last_attendance and (current_time - last_attendance[user_id]).seconds < cooldown:
        return False, f"Cooldown active for user ID {user_id}"
    
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                query = "INSERT INTO attendance (user_id, timestamp) VALUES (%s, %s)"
                cursor.execute(query, (user_id, current_time))
                conn.commit()
                last_attendance[user_id] = current_time
                return True, f"Attendance recorded for user ID {user_id} at {current_time}"
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"