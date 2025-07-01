import os
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
import cv2
import face_recognition
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
import io
import time
import logging
import base64
import gc
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

from attendance_utils import load_face_encodings, record_attendance
from user_utils import register_user, get_user_history

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env
load_dotenv()  # <-- Added

# Flask setup
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Global state
running = False
last_attendance = {}
last_recognized = {}
current_users = {}
face_encoding_cache = None
face_encoding_cache_timestamp = 0
CACHE_TIMEOUT = 300

@app.before_request
def log_request_info():
    logger.info(f"{request.method} {request.path} - form: {request.form.to_dict()} - args: {request.args.to_dict()}")

def get_face_encodings():
    global face_encoding_cache, face_encoding_cache_timestamp
    current_time = time.time()
    if (face_encoding_cache is None or 
        current_time - face_encoding_cache_timestamp > CACHE_TIMEOUT):
        if face_encoding_cache:
            face_encoding_cache = None
            gc.collect()
        face_encoding_cache, errors = load_face_encodings()
        face_encoding_cache_timestamp = current_time
        if errors > 0:
            logger.warning(f"{errors} face encodings failed to load.")
    return face_encoding_cache

def process_frame(frame_data):
    try:
        img_data = base64.b64decode(frame_data.split(',')[1])
        nparray = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparray, cv2.IMREAD_COLOR)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        known_faces = get_face_encodings()
        if known_faces is None or len(known_faces) == 0:
            if running:
                socketio.emit('recognition_status', {
                    'status': 'error',
                    'message': 'No known users found or face encodings missing'
                })
            return

        if not face_locations:
            if running:
                socketio.emit('recognition_status', {
                    'status': 'no-face',
                    'message': 'No face detected - Please position your face in the frame'
                })
            return

        known_encodings = [data["encoding"] for data in known_faces.values()]
        known_names = [data["name"] for data in known_faces.values()]
        known_ids = list(known_faces.keys())
        known_roll_numbers = [data["roll_number"] for data in known_faces.values()]
        detected_users = set()
        face_recognized = False

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
            if True in matches:
                best_match_index = np.argmin(face_recognition.face_distance(known_encodings, face_encoding))
                if matches[best_match_index]:
                    user_id = known_ids[best_match_index]
                    name = known_names[best_match_index]
                    roll_number = known_roll_numbers[best_match_index]
                    detected_users.add(user_id)
                    face_recognized = True
                    if running:
                        should_record = user_id not in last_attendance or (datetime.now() - last_attendance[user_id]).total_seconds() > 60
                        current_users[user_id] = datetime.now()
                        should_emit = (user_id not in last_recognized or 
                                       (datetime.now() - last_recognized[user_id]).total_seconds() > 300)
                        if should_record:
                            record_attendance(user_id, last_attendance)
                        if should_emit:
                            user_data = get_user_history(str(user_id))
                            if not user_data or 'error' in user_data:
                                logger.warning(f"Failed to get history for user {user_id}")
                                continue
                            data = {
                                'name': name,
                                'roll_number': roll_number,
                                'user_id': str(user_id),
                                'history': user_data.get('history', []),
                                'attendance_percentage': user_data.get('attendance_percentage', 0),
                                'attended_dates': user_data.get('attended_dates', []),
                                'department': user_data.get('department', ''),
                                'role': user_data.get('role', '')
                            }
                            socketio.emit('user_recognized', data)
                            last_recognized[user_id] = datetime.now()

        if face_recognized:
            socketio.emit('recognition_status', {
                'status': 'face-recognized',
                'message': f'Face recognized - Welcome {name}'
            })
        else:
            socketio.emit('recognition_status', {
                'status': 'face-detected',
                'message': 'Face detected but not recognized - Please register first'
            })

        for user_id in list(current_users.keys()):
            if user_id not in detected_users and (datetime.now() - current_users[user_id]).total_seconds() > 30:
                del current_users[user_id]

        del rgb_frame, face_locations
        gc.collect()
    except Exception as e:
        logger.error(f"Error processing frame: {e}")

@socketio.on('video_frame')
def handle_video_frame(data):
    process_frame(data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    try:
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        role = request.form.get('role')
        frame_data = request.form.get('frame')
        if not all([name, roll_number, department, role, frame_data]):
            return jsonify({"success": False, "message": "All fields are required"})
        if role not in ['Teacher', 'Student']:
            return jsonify({"success": False, "message": "Invalid role selected"})

        img_data = base64.b64decode(frame_data.split(',')[1])
        nparray = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparray, cv2.IMREAD_COLOR)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            return jsonify({"success": False, "message": "No face detected in frame"})
        top, right, bottom, left = face_locations[0]
        h, w = frame.shape[:2]  # bounds check
        top, bottom = max(0, top), min(h, bottom)
        left, right = max(0, left), min(w, right)
        if top >= bottom or left >= right:
            return jsonify({"success": False, "message": "Invalid face crop"})

        captured_frame = frame[top:bottom, left:right]
        success, message = register_user(name, roll_number, department, role, captured_frame)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Crash in /register endpoint: {e}")
        return jsonify({"success": False, "message": f"Registration crashed: {e}"})

@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    global running, last_recognized, current_users
    running = True
    last_recognized.clear()
    current_users.clear()
    return jsonify({"message": "Attendance system started"})

@app.route('/stop_attendance', methods=['POST'])
def stop_attendance():
    global running, current_users
    running = False
    current_users.clear()
    return jsonify({"message": "Attendance system stopped"})

@app.route('/users')
def get_users():
    users = db.users.find({}, {"name": 1, "roll_number": 1})
    return jsonify([{"name": u["name"], "roll_number": u["roll_number"]} for u in users])

@app.route('/history')
def get_history():
    try:
        attendance = db.attendance.aggregate([
            {"$sort": {"timestamp": -1}},
            {"$limit": 100},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$project": {
                "_id": 0,
                "name": "$user.name",
                "roll_number": "$user.roll_number",
                "time": {"$dateToString": {"format": "%H:%M:%S", "date": "$timestamp"}},
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}
            }}
        ])
        return jsonify(list(attendance))
    except Exception as e:
        logger.error(f"/history route error: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

@app.route('/get_user_history')
def get_user_history_endpoint():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    try:
        user_data = get_user_history(user_id)
        if 'error' in user_data:
            return jsonify(user_data), 404
        return jsonify(user_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/export')
def export_attendance():
    attendance = list(db.attendance.find())
    user_map = {str(u['_id']): u for u in db.users.find()}
    export_rows = []
    for a in attendance:
        u = user_map.get(str(a['user_id']))
        if u:
            if isinstance(a['timestamp'], str):
                a['timestamp'] = datetime.fromisoformat(a['timestamp'])
            export_rows.append({
                "user_id": str(a['user_id']),
                "user_name": u['name'],
                "roll_number": u['roll_number'],
                "timestamp": a['timestamp'],
                "date": a['timestamp'].date(),
                "time": a['timestamp'].time()
            })
    df = pd.DataFrame(export_rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

@app.route('/register_user')
def register_user_page():
    return render_template('register_user.html')

@app.route('/manage_users_data')
def manage_users_data():
    users = db.users.find({}, {"_id": 1, "name": 1, "roll_number": 1})
    return jsonify([{"id": str(u["_id"]), "name": u["name"], "roll_number": u["roll_number"]} for u in users])

@app.route('/delete_user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        db.attendance.delete_many({"user_id": ObjectId(user_id)})
        db.users.delete_one({"_id": ObjectId(user_id)})
        return jsonify({"success": True, "message": f"User ID {user_id} deleted"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting user: {e}"})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

if __name__ == '__main__':
    import eventlet
    eventlet.monkey_patch()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
