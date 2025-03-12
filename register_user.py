import mysql.connector
import cv2
import face_recognition
import numpy as np
from config import DB_CONFIG
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_user(name, roll_number, department, role, captured_frame):
    try:
        logger.info("Starting register_user function")
        if not all([name, roll_number, department, role]):
            logger.error("Missing required fields for registration")
            return False, "All fields (name, roll number, department, role) are required"

        if role not in ['Teacher', 'Student']:
            logger.error(f"Invalid role: {role}")
            return False, "Invalid role selected. Must be 'Teacher' or 'Student'"

        if captured_frame is None or captured_frame.size == 0:
            logger.error("No valid frame captured for registration")
            return False, "No valid frame captured"

        logger.info("Converting frame to RGB")
        rgb_frame = cv2.cvtColor(captured_frame, cv2.COLOR_BGR2RGB)

        logger.info("Extracting face encoding")
        face_encodings = face_recognition.face_encodings(rgb_frame)
        if not face_encodings:
            logger.error("No face detected in the captured frame")
            return False, "No face detected in the captured frame"
        face_encoding = face_encodings[0]
        logger.info("Face encoding extracted successfully")
        
        # Debug: Save face encoding to file
        np.save("debug_face_encoding.npy", face_encoding)
        logger.info("Saved debug_face_encoding.npy")

        logger.info("Attempting database insertion")
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(prepared=True) as cursor:
                query = """
                INSERT INTO users (name, roll_number, department, role, face_encoding)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (name, roll_number, department, role, face_encoding.tobytes()))
                conn.commit()
                logger.info(f"User {name} (Roll: {roll_number}) registered successfully")
                return True, "User registered successfully"
    except mysql.connector.Error as err:
        logger.error(f"Database error during user registration: {err}")
        return False, f"Database error: {err}"
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {e}")
        return False, f"Unexpected error: {e}"