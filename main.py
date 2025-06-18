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
import calendar
import base64
import gc
import mysql.connector

from config import DB_CONFIG
from attendance_utils import load_face_encodings, record_attendance
from user_utils import register_user, get_user_history

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app)

# Global state
running = False
last_attendance = {}
last_recognized = {}
current_users = {}
face_encoding_cache = None
face_encoding_cache_timestamp = 0
CACHE_TIMEOUT = 300  # 5 minutes

def get_face_encodings():
    """Get face encodings with caching to improve performance."""
    global face_encoding_cache, face_encoding_cache_timestamp
    current_time = time.time()
    if (face_encoding_cache is None or 
        current_time - face_encoding_cache_timestamp > CACHE_TIMEOUT):
        if face_encoding_cache:
            face_encoding_cache = None
            gc.collect()
        face_encoding_cache, _ = load_face_encodings()
        face_encoding_cache_timestamp = current_time
    return face_encoding_cache

def process_frame(frame_data):
    """Process a base64-encoded frame from the client."""
    try:
        img_data = base64.b64decode(frame_data.split(',')[1])
        nparray = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparray, cv2.IMREAD_COLOR)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if running:
            if not face_locations:
                socketio.emit('recognition_status', {
                    'status': 'no-face',
                    'message': 'No face detected - Please position your face in the frame'
                })
                return
            known_faces = get_face_encodings()
            if not known_faces:
                socketio.emit('recognition_status', {
                    'status': 'error',
                    'message': 'Error loading face encodings'
                })
                return
        else:
            return
        known_encodings = [data["encoding"] for data in known_faces.values()]
        known_names = [data["name"] for data in known_faces.values()]
        known_ids = list(known_faces.keys())
        known_roll_numbers = [data["roll_number"] for data in known_faces.values()]
        detected_users = set()
        face_recognized = False
        if known_encodings and face_locations:
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
                name = "Unknown"
                user_id = None
                roll_number = None
                if True in matches:
                    distances = face_recognition.face_distance(known_encodings, face_encoding)
                    best_match_index = np.argmin(distances)
                    if matches[best_match_index]:
                        name = known_names[best_match_index]
                        user_id = known_ids[best_match_index]
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
                                user_data = get_user_history(user_id)
                                data = {
                                    'name': name,
                                    'roll_number': roll_number,
                                    'user_id': user_id,
                                    'history': user_data['history'],
                                    'attendance_percentage': user_data['attendance_percentage'],
                                    'attended_dates': user_data['attended_dates'],
                                    'department': user_data['department'],
                                    'role': user_data['role']
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
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, roll_number FROM users")
            users = [{"name": name, "roll_number": roll} for name, roll in cursor]
    return jsonify(users)

@app.route('/history')
def get_history():
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            query = """
            SELECT a.id, u.name, u.roll_number, DATE_FORMAT(a.timestamp, '%H:%i:%s'), \
                   DATE_FORMAT(a.timestamp, '%Y-%m-%d')
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC LIMIT 100
            """
            cursor.execute(query)
            history = [{"id": row[0], "name": row[1], "roll_number": row[2], "time": row[3], "date": row[4]} for row in cursor]
    return jsonify(history)

@app.route('/get_user_history')
def get_user_history_endpoint():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    try:
        user_id = int(user_id)
        user_data = get_user_history(user_id)
        if 'error' in user_data:
            return jsonify(user_data), 404
        return jsonify(user_data)
    except ValueError:
        return jsonify({'error': 'Invalid User ID'}), 400

@app.route('/export')
def export_attendance():
    with mysql.connector.connect(**DB_CONFIG) as conn:
        query = """
        SELECT a.id, u.name as user_name, u.roll_number, a.timestamp, u.id as user_id
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        """
        df = pd.read_sql(query, conn)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['time'] = pd.to_datetime(df['timestamp']).dt.time
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
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, roll_number FROM users")
            users = [{"id": row[0], "name": row[1], "roll_number": row[2]} for row in cursor]
    return jsonify(users)

@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM attendance WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
        return jsonify({"success": True, "message": f"User ID {user_id} deleted"})
    except mysql.connector.Error as err:
        return jsonify({"success": False, "message": f"Error deleting user: {err}"})

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}") 