from flask import Flask, Response, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
import cv2
import face_recognition
import numpy as np
import mysql.connector
from config import DB_CONFIG
from register_user import register_user
from attendance import load_face_encodings, record_attendance
import pandas as pd
from datetime import datetime, date, timedelta
import io
import time
import logging
import calendar

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app)

def init_camera():
    backend = cv2.CAP_DSHOW
    for i in range(3):
        cam = cv2.VideoCapture(i, backend)
        if cam.isOpened():
            logger.info(f"Camera initialized at index {i} with backend {backend}")
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            for _ in range(10):
                cam.read()
                time.sleep(0.1)
            width = cam.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cam.get(cv2.CAP_PROP_FPS)
            logger.info(f"Camera settings: {width}x{height} @ {fps} FPS")
            return cam
        cam.release()
    logger.error(f"No camera found with backend {backend} after trying indices 0-2")
    return None

camera = init_camera()
running = False
captured_frame = None
last_attendance = {}  # Tracks attendance cooldown (60 seconds)
last_recognized = {}  # Tracks last emission time
current_users = {}    # Tracks currently detected users and their last seen time

def video_feed_generator():
    global captured_frame, running, last_attendance, last_recognized, current_users
    if not camera or not camera.isOpened():
        logger.error("Camera not available in video_feed_generator")
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        ret, buffer = cv2.imencode('.jpg', black_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
        return
    fps = camera.get(cv2.CAP_PROP_FPS)
    sleep_time = 0.1
    logger.info(f"Using sleep time: {sleep_time} seconds (FPS: {fps})")

    known_encodings = []
    known_names = []
    known_ids = []
    known_roll_numbers = []
    last_load_time = 0
    reload_interval = 60

    while True:
        current_time = time.time()
        if current_time - last_load_time > reload_interval:
            try:
                known_faces, _ = load_face_encodings()
                known_ids = list(known_faces.keys())
                known_encodings = [data["encoding"] for data in known_faces.values()]
                known_names = [data["name"] for data in known_faces.values()]
                known_roll_numbers = [data["roll_number"] for data in known_faces.values()]
                logger.info(f"Reloaded {len(known_encodings)} known face encodings in video_feed")
                last_load_time = current_time
            except Exception as e:
                logger.error(f"Failed to reload face encodings in video_feed: {e}")
                known_encodings = []
                known_ids = []
                known_names = []
                known_roll_numbers = []

        success, frame = camera.read()
        if not success:
            logger.warning("Failed to grab frame")
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            ret, buffer = cv2.imencode('.jpg', black_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            continue
        if not frame.any():
            logger.warning("Frame is completely black (all zeros)")
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(black_frame, "Camera feed is black", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', black_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        logger.info(f"Detected {len(face_locations)} faces in frame")

        detected_users = set()  # Users detected in this frame

        if known_encodings and face_locations:
            try:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                logger.info(f"Computed {len(face_encodings)} face encodings")
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
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
                            logger.info(f"Matched face to {name} (ID: {user_id}) with distance {distances[best_match_index]}")
                            detected_users.add(user_id)

                            if running:
                                # Attendance cooldown: 60 seconds
                                should_record = user_id not in last_attendance or (datetime.now() - last_attendance[user_id]).total_seconds() > 60
                                # Emission logic: Only emit if user is new or re-enters after 30 seconds absence
                                current_users[user_id] = datetime.now()  # Update last seen time
                                should_emit = (user_id not in last_recognized or 
                                              (user_id not in current_users or 
                                               (datetime.now() - last_recognized[user_id]).total_seconds() > 300))

                                if should_record:
                                    record_attendance(user_id, last_attendance)
                                    logger.info(f"Attendance recorded for {name} (ID: {user_id})")

                                if should_emit:
                                    user_data = get_user_history(user_id)
                                    data = {
                                        'name': name,
                                        'roll_number': roll_number,
                                        'history': user_data['history'],
                                        'attendance_percentage': user_data['attendance_percentage'],
                                        'attended_dates': user_data['attended_dates']
                                    }
                                    logger.info(f"Emitting user_recognized event for {name} (ID: {user_id})")
                                    socketio.emit('user_recognized', data)
                                    last_recognized[user_id] = datetime.now()
                        else:
                            logger.info(f"No confident match (best distance: {distances[best_match_index]})")
                    else:
                        logger.info("No matches found for this face")
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name, (left, max(10, top - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            except Exception as e:
                logger.warning(f"Face recognition error: {e}")
                for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        else:
            if not known_encodings:
                logger.info("No known encodings available")
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Clear users not detected in this frame after 30 seconds
        for user_id in list(current_users.keys()):
            if user_id not in detected_users and (datetime.now() - current_users[user_id]).total_seconds() > 30:
                logger.info(f"User {user_id} no longer detected, removing from current_users")
                del current_users[user_id]

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ret:
            logger.warning("Failed to encode frame")
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(buffer)).encode() + b'\r\n'
               b'Cache-Control: no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0\r\n'
               b'Pragma: no-cache\r\n'
               b'Connection: close\r\n'
               b'\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(sleep_time)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(video_feed_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/register', methods=['POST'])
def register():
    global captured_frame
    try:
        logger.info("Starting registration process")
        name = request.form['name']
        roll_number = request.form['roll_number']
        department = request.form['department']
        role = request.form['role']
        logger.info(f"Received form data: name={name}, roll_number={roll_number}, department={department}, role={role}")

        if not all([name, roll_number, department, role]):
            logger.warning("Missing required fields")
            return jsonify({"success": False, "message": "All fields are required"})
        
        if role not in ['Teacher', 'Student']:
            logger.warning(f"Invalid role: {role}")
            return jsonify({"success": False, "message": "Invalid role selected"})
        
        if not camera or not camera.isOpened():
            logger.warning("Camera not available")
            return jsonify({"success": False, "message": "Camera not available"})

        logger.info("Capturing frame from camera")
        success, frame = camera.read()
        if not success:
            logger.warning("Failed to capture frame")
            return jsonify({"success": False, "message": "Failed to capture frame"})
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            logger.warning("No face detected in frame")
            return jsonify({"success": False, "message": "No face detected in frame"})
        
        top, right, bottom, left = face_locations[0]
        captured_frame = frame[top:bottom, left:right].copy()
        logger.info("Frame captured successfully")

        logger.info("Calling register_user function")
        success, message = register_user(name, roll_number, department, role, captured_frame)
        logger.info(f"register_user returned: success={success}, message={message}")
        
        captured_frame = None
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Crash in /register endpoint: {e}")
        return jsonify({"success": False, "message": f"Registration crashed: {e}"})

@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    global running, last_recognized, current_users
    if not camera or not camera.isOpened():
        return jsonify({"message": "Cannot start attendance: Camera not available"})
    running = True
    last_recognized.clear()
    current_users.clear()
    logger.info("Attendance system started")
    return jsonify({"message": "Attendance system started"})

@app.route('/stop_attendance', methods=['POST'])
def stop_attendance():
    global running, current_users
    running = False
    current_users.clear()
    logger.info("Attendance system stopped")
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
            SELECT a.id, u.name, u.roll_number, DATE_FORMAT(a.timestamp, '%H:%i:%s'), 
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

def get_user_history(user_id):
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor(prepared=True) as cursor:
                cursor.execute("SELECT name, roll_number FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return {'error': f'User ID {user_id} not found'}, 404
                name, roll_number = user
                query = "SELECT DATE_FORMAT(timestamp, '%H:%i:%s'), DATE_FORMAT(timestamp, '%Y-%m-%d') FROM attendance WHERE user_id = %s ORDER BY timestamp DESC LIMIT 5"
                cursor.execute(query, (user_id,))
                history = [{"time": row[0], "date": row[1]} for row in cursor.fetchall()]
                today = date.today()
                first_day = today.replace(day=1)
                last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
                query = """
                SELECT DATE(timestamp)
                FROM attendance
                WHERE user_id = %s AND timestamp >= %s AND timestamp <= %s
                GROUP BY DATE(timestamp)
                """
                cursor.execute(query, (user_id, first_day, last_day))
                attended_dates = [row[0] for row in cursor.fetchall()]
                attended_days = len(attended_dates)
                working_days_list = [(first_day + timedelta(days=d)).strftime('%Y-%m-%d')
                                    for d in range((today - first_day).days + 1)
                                    if (first_day + timedelta(days=d)).weekday() < 5]
                working_days = len(working_days_list)
                percentage = (attended_days / working_days * 100) if working_days > 0 else 0
                return {
                    'name': name,
                    'roll_number': roll_number,
                    'history': history,
                    'attendance_percentage': round(percentage, 2),
                    'attended_dates': [d.strftime('%Y-%m-%d') for d in attended_dates]
                }
    except mysql.connector.Error as err:
        logger.error(f"Error fetching user history: {err}")
        return {'error': str(err)}, 500

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
    except KeyboardInterrupt:
        if camera and camera.isOpened():
            camera.release()
            logger.info("Camera released")
        cv2.destroyAllWindows()
        shutdown_server()
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
    finally:
        if camera and camera.isOpened():
            camera.release()
            logger.info("Camera released")
        cv2.destroyAllWindows()