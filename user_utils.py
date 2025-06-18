import mysql.connector
import cv2
import face_recognition
import numpy as np
from config import DB_CONFIG
from datetime import date, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_user(name, roll_number, department, role, captured_frame):
    """
    Register a new user with face encoding and store in the database.
    Returns (success: bool, message: str)
    """
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
        encoding_bytes = face_encoding.tobytes()
        logger.info("Attempting database insertion")
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                with conn.cursor(prepared=True) as cursor:
                    query = """
                    INSERT INTO users (name, roll_number, department, role, face_encoding)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (name, roll_number, department, role, encoding_bytes))
                    conn.commit()
                    logger.info(f"User {name} (Roll: {roll_number}) registered successfully")
                    return True, "User registered successfully"
        except mysql.connector.Error as err:
            logger.error(f"Database error during user registration: {err}")
            return False, f"Database error: {err}"
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {e}")
        return False, f"Unexpected error: {e}"

def get_user_history(user_id):
    """
    Get user history and attendance stats by user_id.
    Returns a dict with user info, history, attendance percentage, and attended dates.
    """
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(prepared=True) as cursor:
                cursor.execute("SELECT name, roll_number, department, role FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return {'error': f'User ID {user_id} not found'}
                name, roll_number, department, role = user
                query = "SELECT DATE_FORMAT(timestamp, '%H:%i:%s'), DATE_FORMAT(timestamp, '%Y-%m-%d') FROM attendance WHERE user_id = %s ORDER BY timestamp DESC"
                cursor.execute(query, (user_id,))
                history = [{"time": row[0], "date": row[1]} for row in cursor.fetchall()]
                today = date.today()
                first_day = today.replace(day=1)
                if today.month == 12:
                    next_month_first_day = date(today.year + 1, 1, 1)
                else:
                    next_month_first_day = date(today.year, today.month + 1, 1)
                query = """
                SELECT DATE(timestamp)
                FROM attendance
                WHERE user_id = %s AND timestamp >= %s AND timestamp < %s
                GROUP BY DATE(timestamp)
                """
                cursor.execute(query, (user_id, first_day, next_month_first_day))
                attended_dates = [row[0] for row in cursor.fetchall()]
                logger.info(f"User ID {user_id} attended_dates: {attended_dates}")
                attended_days = len(attended_dates)
                working_days_list = [(first_day + timedelta(days=d)).strftime('%Y-%m-%d')
                                    for d in range((today - first_day).days + 1)
                                    if (first_day + timedelta(days=d)).weekday() < 5]
                working_days = len(working_days_list)
                percentage = (attended_days / working_days * 100) if working_days > 0 else 0
                return {
                    'name': name,
                    'roll_number': roll_number,
                    'department': department,
                    'role': role,
                    'history': history,
                    'attendance_percentage': round(percentage, 2),
                    'attended_dates': [d.strftime('%Y-%m-%d') for d in attended_dates]
                }
    except mysql.connector.Error as err:
        logger.error(f"Error fetching user history: {err}")
        return {'error': str(err)} 