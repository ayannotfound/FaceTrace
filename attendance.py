import mysql.connector
import numpy as np
from config import DB_CONFIG
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_face_encodings():
    known_faces = {}
    encoding_errors = 0
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name, roll_number, face_encoding FROM users")
                for user_id, name, roll_number, encoding_blob in cursor:
                    try:
                        if not isinstance(encoding_blob, bytes):
                            logger.error(f"Encoding for user {user_id} ({name}) is not bytes: {type(encoding_blob)}")
                            encoding_errors += 1
                            continue
                        encoding = np.frombuffer(encoding_blob, dtype=np.float64)
                        known_faces[user_id] = {
                            "encoding": encoding,
                            "name": name,
                            "roll_number": roll_number
                        }
                    except Exception as e:
                        logger.error(f"Error decoding face encoding for user {user_id} ({name}): {e}")
                        encoding_errors += 1
        logger.info(f"Loaded {len(known_faces)} face encodings successfully, {encoding_errors} errors")
        return known_faces, encoding_errors
    except mysql.connector.Error as err:
        logger.error(f"Error loading face encodings: {err}")
        return {}, encoding_errors

def record_attendance(user_id, last_attendance):
    current_time = datetime.now()
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO attendance (user_id, timestamp) VALUES (%s, %s)",
                    (user_id, current_time)
                )
                conn.commit()
        last_attendance[user_id] = current_time
        logger.info(f"Attendance recorded for user {user_id}")
    except mysql.connector.Error as err:
        logger.error(f"Error recording attendance: {err}")