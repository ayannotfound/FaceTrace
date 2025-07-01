from config import db
import numpy as np
from datetime import datetime
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

def load_face_encodings():
    known_faces = {}
    encoding_errors = 0
    try:
        users = db.users.find()
        for user in users:
            try:
                encoding = np.array(user['face_encoding'], dtype=np.float64)
                known_faces[str(user['_id'])] = {
                    "encoding": encoding,
                    "name": user["name"],
                    "roll_number": user["roll_number"]
                }
            except Exception as e:
                logger.error(f"Decoding error: {e}")
                encoding_errors += 1
        return known_faces, encoding_errors
    except Exception as e:
        logger.error(f"DB error: {e}")
        return {}, encoding_errors

def record_attendance(user_id, last_attendance):
    current_time = datetime.now()
    try:
        db.attendance.insert_one({
            "user_id": ObjectId(user_id),
            "timestamp": current_time
        })
        last_attendance[user_id] = current_time
        logger.info(f"Attendance recorded for {user_id}")
    except Exception as e:
        logger.error(f"Error recording attendance: {e}")