from config import db
import face_recognition
import numpy as np
import cv2
from datetime import datetime, date, timedelta
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

def register_user(name, roll_number, department, role, captured_frame):
    try:
        rgb_frame = cv2.cvtColor(captured_frame, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_frame)
        if not encodings:
            return False, "No face detected"
        face_encoding = encodings[0].tolist()  # Save as list, not bytes

        db.users.insert_one({
            "name": name,
            "roll_number": roll_number,
            "department": department,
            "role": role,
            "face_encoding": face_encoding
        })
        return True, "User registered"
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False, "Failed"

def get_user_history(user_id):
    try:
        obj_id = ObjectId(user_id)
        user = db.users.find_one({"_id": obj_id})
        if not user:
            return {'error': 'User not found'}

        history_cursor = db.attendance.find({"user_id": obj_id}).sort("timestamp", -1)
        history = [{
            "time": ts["timestamp"].strftime('%H:%M:%S'),
            "date": ts["timestamp"].strftime('%Y-%m-%d')
        } for ts in history_cursor]

        today = date.today()
        first_day = today.replace(day=1)
        next_month = date(today.year + (today.month // 12), (today.month % 12) + 1, 1)

        attended_dates = db.attendance.aggregate([
            {"$match": {
                "user_id": obj_id,
                "timestamp": {
                    "$gte": datetime.combine(first_day, datetime.min.time()),
                    "$lt": datetime.combine(next_month, datetime.min.time())
                }
            }},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}
            }}
        ])

        attended_set = {entry['_id'] for entry in attended_dates}
        working_days = [
            (first_day + timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range((today - first_day).days + 1)
            if (first_day + timedelta(days=i)).weekday() < 5
        ]

        percentage = (len(attended_set) / len(working_days) * 100) if working_days else 0

        return {
            "name": user["name"],
            "roll_number": user["roll_number"],
            "department": user["department"],
            "role": user["role"],
            "history": history,
            "attended_dates": list(attended_set),
            "attendance_percentage": round(percentage, 2)
        }
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return {"error": "Server error"}

