# 🧑‍💼 FaceTrace

A simple, modern web app for automatic attendance using face recognition, built with [Flask](https://flask.palletsprojects.com/) and [OpenCV](https://opencv.org/). Capture face data, register users, and mark attendance in real time—all from your browser.

---

## 🚀 Features
- 🧑‍💼 Register users with face data
- 📸 Real-time face recognition for attendance
- 📊 Attendance history and export (CSV)
- 🏫 Separate roles: Teacher & Student
- 🖥️ Responsive web interface
- 🗃️ MySQL database backend

---

## 🧩 Tech Stack
- Python (Flask, Flask-SocketIO)
- OpenCV, face-recognition
- MySQL
- HTML, CSS, JavaScript

---

## 🛠️ Getting Started

1. **Clone the repo**
   ```bash
   git clone https://github.com/ayannotfound/FaceTrace.git
   cd FaceTrace
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure the database**
   - Edit `config.py` with your MySQL credentials.
   - Make sure your MySQL server is running and the required tables exist.

4. **Run the app**
   ```bash
   python main.py
   ```
   Visit [http://localhost:5000](http://localhost:5000)

---

## 📁 Project Structure

- `main.py` — Main app and routes
- `attendance_utils.py` — Attendance logic
- `user_utils.py` — User registration/history logic
- `config.py` — Database config
- `static/` and `templates/` — Frontend files

---

## 🧠 What I Learned

- Flask routes, templates, and SocketIO events
- Integrating OpenCV and face-recognition with Flask
- MySQL database operations in Python
- Building a real-time web app

---

## 📫 About Me

[LinkedIn](https://www.linkedin.com/in/ayush-anand-420590306/)  
[GitHub](https://github.com/ayannotfound)

---

**References:**
- [Flask Quickstart](https://github.com/pallets/flask/blob/main/docs/quickstart.rst#_snippet_5)
- [face-recognition Docs](https://github.com/ageitgey/face_recognition)
- [OpenCV Docs](https://docs.opencv.org/)
