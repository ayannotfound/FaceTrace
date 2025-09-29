# 🧑‍💼 FaceTrace

A production-ready, modern web application for automatic attendance tracking using advanced face recognition technology. Built with Flask, real-time WebSocket communication, and optimized for high-performance deployment.

## 🌟 **Live Demo**
Experience FaceTrace in action: **[https://facetrace-c6di.onrender.com](https://facetrace-c6di.onrender.com)**

*Try the face recognition system, register users, and see real-time attendance tracking in your browser!*

---

## 🚀 Features
- 🧑‍💼 **User Registration** with face data capture and validation
- 📸 **Real-time Face Recognition** for instant attendance marking
- 📊 **Attendance Analytics** with history, export (CSV), and percentage tracking
- 🏫 **Role-based Access** for Teachers & Students
- 👥 **User Management** with delete and modify capabilities
- 🖥️ **Responsive Web Interface** with real-time updates
- ⚡ **Performance Monitoring** with health checks and system stats
- 🗃️ **MongoDB Backend** with optimized queries
- 🐳 **Docker Support** for containerized deployment
- 🚀 **Production Ready** with Gunicorn and async processing

---

## 🧩 Tech Stack
- **Backend**: Python (Flask, Flask-SocketIO, Eventlet)
- **Computer Vision**: OpenCV, face-recognition library
- **Database**: MongoDB with PyMongo
- **Async Processing**: Eventlet for real-time WebSocket communication
- **Production Server**: Gunicorn with optimized configuration
- **Deployment**: Docker, Render support
- **Monitoring**: psutil for performance tracking
- **Frontend**: HTML5, CSS3, JavaScript with WebSocket support

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.8+
- MongoDB Atlas account or local MongoDB instance
- Webcam/Camera access

### Quick Start

1. **Clone the repo**
   ```bash
   git clone https://github.com/ayannotfound/FaceTrace.git
   cd FaceTrace
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: The `face_recognition` library requires cmake and dlib. On Windows, you might need Visual Studio Build Tools.*

3. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   MONGO_URI=mongodb://your_connection_string
   DB_NAME=facetrace
   DEBUG=False
   PORT=5000
   ```

4. **Run the application**
   
   **Development:**
   ```bash
   python main.py
   ```
   
   **Production (with Gunicorn):**
   ```bash
   gunicorn -c gunicorn.conf.py main:app
   ```
   
   Visit [http://localhost:5000](http://localhost:5000)

### 🐳 Docker Deployment

1. **Build the image:**
   ```bash
   docker build -t facetrace .
   ```

2. **Run the container:**
   ```bash
   docker run -p 10000:10000 --env-file .env facetrace
   ```

### ☁️ Cloud Deployment (Render)
The app includes Render deployment configuration:
- `Procfile` for process definition
- `start.sh` for optimized startup
- Production-ready Gunicorn configuration

---

## 📁 Project Structure

```
FaceTrace/
├── main.py                 # Main Flask app with WebSocket routes
├── attendance_utils.py     # Face encoding & attendance recording logic
├── user_utils.py          # User registration & history management
├── config.py              # MongoDB configuration
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── Dockerfile            # Container configuration
├── gunicorn.conf.py      # Production server config
├── start.sh              # Optimized startup script
├── Procfile              # Render deployment config
├── static/               # Frontend assets
│   ├── script.js         # WebSocket client & UI logic
│   └── styles.css        # Responsive styling
└── templates/            # HTML templates
    ├── index.html        # Main attendance interface
    └── register_user.html # User registration page
```

## 🔥 Key Features Deep Dive

### Real-time Performance Optimization
- **Frame Skipping**: Processes frames every 1000ms to reduce CPU load
- **Face Encoding Caching**: 5-minute cache with automatic cleanup
- **Memory Management**: Garbage collection after each frame processing
- **Async Processing**: Eventlet-based non-blocking frame processing

### Advanced Face Recognition
- **HOG Model**: Faster face detection for real-time processing
- **Tolerance Optimization**: Configurable face matching sensitivity
- **Batch Processing**: Efficient handling of multiple faces
- **Error Recovery**: Graceful handling of encoding failures

### Production Features
- **Health Monitoring**: `/health` endpoint for system status
- **Performance Stats**: `/performance` endpoint with memory/CPU metrics
- **User Management**: Complete CRUD operations for users
- **Data Export**: CSV export with timestamp formatting
- **Session Management**: Automatic cleanup of inactive sessions

### API Endpoints
- `GET /` - Main attendance interface
- `POST /register` - User registration with face capture
- `POST /start_attendance` - Begin attendance tracking
- `POST /stop_attendance` - Stop attendance tracking
- `GET /history` - Recent attendance records
- `GET /export` - Download attendance CSV
- `GET /health` - System health check
- `GET /performance` - Performance statistics
- `DELETE /delete_user/<id>` - Remove user and their records

---

## 🧠 What I Learned

- **Advanced Flask Architecture**: WebSocket integration with Flask-SocketIO for real-time communication
- **Computer Vision Optimization**: Frame processing, face encoding caching, and memory management
- **Production Deployment**: Docker containerization, Gunicorn configuration, and cloud deployment
- **Database Design**: MongoDB aggregation pipelines for complex attendance analytics
- **Performance Engineering**: Async processing, caching strategies, and resource optimization
- **Real-time Systems**: WebSocket event handling and background task processing
- **System Monitoring**: Health checks, performance metrics, and error handling

## 📊 Performance Optimizations

The application includes several performance optimizations:

- **Memory Efficient**: Automatic garbage collection and frame cleanup
- **CPU Optimized**: Frame skipping and HOG model for faster face detection  
- **Caching Strategy**: 5-minute face encoding cache with automatic refresh
- **Async Processing**: Non-blocking frame processing with Eventlet
- **Database Optimization**: Efficient MongoDB queries and indexing
- **Production Ready**: Gunicorn with optimized worker configuration

## 🔧 Configuration Options

Environment variables for customization:
- `MONGO_URI`: MongoDB connection string
- `DB_NAME`: Database name
- `DEBUG`: Enable/disable debug mode
- `PORT`: Application port (default: 5000)
- `OMP_NUM_THREADS`: OpenMP thread limit
- `MKL_NUM_THREADS`: Intel MKL thread limit

---

## 📫 About Me

[LinkedIn](https://www.linkedin.com/in/ayush-anand-420590306/)  
[GitHub](https://github.com/ayannotfound)

---

**Key Dependencies:**
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - Real-time communication
- [face-recognition](https://github.com/ageitgey/face_recognition) - Face recognition library
- [OpenCV](https://docs.opencv.org/) - Computer vision processing
- [PyMongo](https://pymongo.readthedocs.io/) - MongoDB driver
- [Eventlet](https://eventlet.net/) - Async networking library
- [Gunicorn](https://gunicorn.org/) - Production WSGI server
