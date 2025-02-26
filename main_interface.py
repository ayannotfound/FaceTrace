# main_interface.py
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import cv2
import face_recognition
from PIL import Image, ImageTk
import threading
import winsound
import pandas as pd
from datetime import datetime
from register_user import register_user
from attendance import load_face_encodings, record_attendance
from config import DB_CONFIG
import mysql.connector
import numpy as np

class CameraManager:
    def __init__(self):
        self.cap = None
        self.camera_index = 0
        self.frame_skip = 2  # Process every nth frame
        self.frame_counter = 0
        self.resolution = (640, 480)  # Optimal resolution for face detection
        self.running = False

    def initialize(self):
        """Initialize camera with optimal settings"""
        if self.cap:
            self.cap.release()
        
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Try fallback to default API if DirectShow fails
                self.cap = cv2.VideoCapture(self.camera_index)
            
            if self.cap.isOpened():
                # Set optimal camera properties
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
                return True
            return False
        except Exception as e:
            print(f"Camera initialization error: {e}")
            return False

    def read_frame(self):
        """Read frame with error handling and skip logic"""
        if not self.cap or not self.cap.isOpened():
            return False, None

        self.frame_counter = (self.frame_counter + 1) % self.frame_skip
        
        # Skip frames if needed
        if self.frame_counter != 0:
            return False, None

        try:
            for _ in range(2):  # Clear buffer by reading extra frames
                ret, frame = self.cap.read()
            return ret, frame
        except Exception as e:
            print(f"Frame capture error: {e}")
            return False, None

    def release(self):
        """Safely release camera resources"""
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            finally:
                self.cap = None

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("900x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.camera = CameraManager()
        self.running = False
        self.registering = False
        self.last_attendance = {}
        self.known_faces = {}
        self.known_ids = []
        self.known_encodings = []
        self.known_names = []
        self.frame_count = 0
        self.captured_frame = None

        self.create_widgets()
        self.initialize_camera()

    def initialize_camera(self):
        """Initialize or reinitialize the camera."""
        if not self.camera.initialize():
            messagebox.showerror("Camera Error", "Could not open webcam.")
            self.log_message("Camera error: Could not open webcam")
            return False
        return True

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Face Attendance System", font=("Helvetica", 28, "bold"))
        self.title_label.pack(pady=(10, 20))

        # Main camera view (used for both registration and attendance)
        self.camera_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.camera_frame.pack(pady=10, padx=10, fill="x")
        self.canvas = tk.Canvas(self.camera_frame, width=640, height=360, bg="black")
        self.canvas.pack(pady=10)

        # Registration controls
        self.register_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.register_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.register_frame, text="Register New User:", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(self.register_frame, text="Name:", font=("Arial", 14)).pack(side="left", padx=5)
        self.name_entry = ctk.CTkEntry(self.register_frame, width=200, font=("Arial", 14))
        self.name_entry.pack(side="left", padx=5)
        self.capture_button = ctk.CTkButton(self.register_frame, text="Capture Face", command=self.start_capture, font=("Arial", 14), width=120)
        self.capture_button.pack(side="left", padx=10)

        # User list
        self.user_list_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.user_list_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.user_list_frame, text="Registered Users", font=("Arial", 16)).pack(pady=5)
        self.user_listbox = tk.Listbox(self.user_list_frame, height=5, font=("Arial", 12))
        self.user_listbox.pack(padx=5, pady=5, fill="x")
        self.update_user_list()

        # Attendance controls
        self.attendance_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.attendance_frame.pack(pady=10, padx=10, fill="x")
        self.button_frame = ctk.CTkFrame(self.attendance_frame, fg_color="transparent")
        self.button_frame.pack(pady=5)
        self.start_button = ctk.CTkButton(self.button_frame, text="Start Attendance", command=self.start_attendance, font=("Arial", 14), width=150)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop Attendance", command=self.stop_attendance, font=("Arial", 14), width=150, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        self.history_button = ctk.CTkButton(self.button_frame, text="View History", command=self.view_history, font=("Arial", 14), width=150)
        self.history_button.pack(side="left", padx=5)
        self.export_button = ctk.CTkButton(self.button_frame, text="Export Attendance", command=self.export_attendance, font=("Arial", 14), width=150)
        self.export_button.pack(side="left", padx=5)

        # Log frame
        self.log_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.log_frame.pack(pady=10, fill="x")
        ctk.CTkLabel(self.log_frame, text="Status Log", font=("Arial", 16, "bold")).pack(pady=5)
        self.log_text = ctk.CTkTextbox(self.log_frame, height=100, font=("Arial", 12))
        self.log_text.pack(padx=5, pady=5, fill="x")
        self.log_message("Ready...")

    def log_message(self, message: str):
        self.log_text.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see("end")

    def start_capture(self):
        if self.registering or self.running:
            self.log_message("Cannot capture while already in use.")
            return

        if not self.camera.cap or not self.camera.cap.isOpened():
            self.initialize_camera()
            if not self.camera.cap:
                return

        self.registering = True
        self.capture_button.configure(text="Register", command=self.register_from_webcam)
        self.log_message("Capturing face... Click 'Register' to save.")
        threading.Thread(target=self.update_capture_view, daemon=True).start()

    def update_capture_view(self):
        """Update camera view during registration capture"""
        while self.registering:
            if not self.camera.cap or not self.camera.cap.isOpened():
                self.log_message("Camera disconnected during capture")
                break

            ret, frame = self.camera.cap.read()
            if not ret or frame is None:
                self.log_message("Failed to capture frame")
                continue

            try:
                if frame.shape[2] != 3:
                    self.log_message("Invalid frame format")
                    continue

                # Draw a face alignment guide
                height, width = frame.shape[:2]
                center_x, center_y = width // 2, height // 2
                guide_size = min(width, height) // 4
                
                # Draw a circle and crosshairs
                cv2.circle(frame, (center_x, center_y), guide_size, (0, 255, 0), 2)
                cv2.line(frame, (center_x - guide_size, center_y), (center_x + guide_size, center_y), (0, 255, 0), 1)
                cv2.line(frame, (center_x, center_y - guide_size), (center_x, center_y + guide_size), (0, 255, 0), 1)
                
                # Add text instruction
                cv2.putText(frame, "Align face within circle", (center_x - guide_size, center_y + guide_size + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # Process frame for display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor="nw", image=imgtk)
                self.canvas.image = imgtk
                self.captured_frame = frame.copy()
                self.root.update()

            except Exception as e:
                self.log_message(f"Error in preview: {str(e)}")
                continue

        self.stop_capture()

    def stop_capture(self):
        self.registering = False
        self.capture_button.configure(text="Capture Face", command=self.start_capture)

    def register_from_webcam(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Input Error", "Name cannot be empty.")
            self.log_message("Registration failed: Empty name")
            self.stop_capture()
            return

        if self.captured_frame is None:
            messagebox.showerror("Capture Error", "No frame captured.")
            self.log_message("Registration failed: No frame captured")
            self.stop_capture()
            return

        # Save the frame for debugging if needed
        try:
            cv2.imwrite(f"registration_{name}.jpg", self.captured_frame)
            self.log_message(f"Saved registration image for debugging")
        except:
            self.log_message("Could not save registration image")

        self.log_message(f"Captured frame shape: {self.captured_frame.shape}, dtype: {self.captured_frame.dtype}")
        success, message = register_user(name, self.captured_frame)
        if success:
            messagebox.showinfo("Success", message)
            self.name_entry.delete(0, tk.END)
            self.update_user_list()
            # Reload face encodings immediately to ensure recognition works
            self.reload_face_encodings()
        else:
            messagebox.showerror("Error", message)
        self.log_message(message)
        self.stop_capture()

    def reload_face_encodings(self):
        """Reload face encodings from the database"""
        result, message = load_face_encodings()
        if result is None:
            self.log_message(message)
            return False
        
        self.known_faces = result
        if not self.known_faces:
            self.log_message("No registered users found")
            return False
            
        self.known_ids = list(self.known_faces.keys())
        self.known_encodings = [data["encoding"] for data in self.known_faces.values()]
        self.known_names = [data["name"] for data in self.known_faces.values()]
        self.log_message(f"Reloaded {len(self.known_names)} known faces: {', '.join(self.known_names)}")
        return True

    def update_user_list(self):
        self.user_listbox.delete(0, tk.END)
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name FROM users")
                    for name in cursor:
                        self.user_listbox.insert(tk.END, name[0])
        except mysql.connector.Error as err:
            self.log_message(f"Error fetching users: {err}")

    def start_attendance(self):
        if self.running or self.registering:
            self.log_message("Cannot start attendance while capturing.")
            return

        if not self.reload_face_encodings():
            messagebox.showerror("Error", "Failed to load face encodings")
            return

        if not self.camera.cap or not self.camera.cap.isOpened():
            self.initialize_camera()
            if not self.camera.cap:
                return

        self.running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.log_message("Attendance system started")
        threading.Thread(target=self.update_attendance_view, daemon=True).start()

    def stop_attendance(self):
        self.running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.log_message("Attendance system stopped")

    def update_attendance_view(self):
        """Update camera view during attendance recognition"""
        while self.running:
            ret, frame = self.camera.read_frame()
            if not ret:
                if not self.camera.cap or not self.camera.cap.isOpened():
                    self.log_message("Camera disconnected")
                    if not self.initialize_camera():  # Try to recover
                        break
                continue
            
            # Process frame for face detection
            try:
                # Create a copy for face detection
                process_frame = frame.copy()
                rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces - try to improve performance by adjusting scale
                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                
                if face_locations:
                    # Get face encodings using same parameters as registration
                    face_encodings = face_recognition.face_encodings(
                        rgb_frame,
                        known_face_locations=face_locations,
                        num_jitters=3,  # Match registration parameters
                        model="large"   # Match registration model
                    )
                    
                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        # Calculate face distances and matches
                        distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                        matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.6)
                        
                        # Debug info for distances
                        distance_info = [f"{name}: {dist:.4f}" for name, dist in zip(self.known_names, distances)]
                        self.log_message(f"Face distance info: {distance_info}")
                        
                        name = "Unknown"
                        if True in matches:
                            best_match_index = np.argmin(distances)
                            if matches[best_match_index]:
                                user_id = self.known_ids[best_match_index]
                                name = self.known_names[best_match_index]
                                distance = distances[best_match_index]
                                
                                # Debug matching info
                                self.log_message(f"Match found! {name} (ID: {user_id}, Distance: {distance:.4f})")
                                
                                # Record attendance if match is confident enough
                                if distance < 0.6:  # Adjust threshold for more confident matches
                                    success, message = record_attendance(user_id, self.last_attendance)
                                    if success:
                                        self.log_message(f"Attendance recorded: {name} - {message}")
                                        winsound.Beep(1000, 200)
                                    else:
                                        self.log_message(f"Attendance failed: {message}")
                                else:
                                    self.log_message(f"Match too uncertain (Distance: {distance:.4f})")
                        else:
                            self.log_message(f"No matching face found")
                        
                        # Draw rectangle and name
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        y_position = top - 15 if top - 15 > 15 else top + 15
                        cv2.putText(frame, name, (left, y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        
                        # Add confidence info if face recognized
                        if name != "Unknown":
                            best_match_index = np.argmin(distances)
                            confidence = 100 * (1 - distances[best_match_index])
                            cv2.putText(frame, f"Confidence: {confidence:.1f}%", 
                                       (left, bottom + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
            except Exception as e:
                self.log_message(f"Error in face recognition: {str(e)}")
                continue
            
            # Display frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=imgtk)
            self.canvas.image = imgtk
            self.root.update()

        self.stop_attendance()

    def view_history(self):
        history_window = ctk.CTkToplevel(self.root)
        history_window.title("Attendance History")
        history_window.geometry("800x400")
        
        # Make window modal
        history_window.transient(self.root)  # Set to be on top of the main window
        history_window.grab_set()  # Make window modal
        
        # Center the window relative to main window
        x = self.root.winfo_x() + (self.root.winfo_width() - 800) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        history_window.geometry(f"800x400+{x}+{y}")
        
        # Create scrollable frame for history
        scroll_frame = ctk.CTkScrollableFrame(history_window, width=780, height=380)
        scroll_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Column headers
        headers = ["ID", "User", "Time", "Date"]
        header_frame = ctk.CTkFrame(scroll_frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        for i, header in enumerate(headers):
            ctk.CTkLabel(header_frame, text=header, font=("Arial", 14, "bold"), width=150).grid(
                row=0, column=i, padx=5, pady=5)
        
        # Fetch and display history
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = """
                    SELECT a.id, u.name, DATE_FORMAT(a.timestamp, '%H:%i:%s'), 
                           DATE_FORMAT(a.timestamp, '%Y-%m-%d') 
                    FROM attendance a
                    JOIN users u ON a.user_id = u.id
                    ORDER BY a.timestamp DESC LIMIT 100
                    """
                    cursor.execute(query)
                    
                    results_frame = ctk.CTkFrame(scroll_frame)
                    results_frame.pack(fill="x", padx=5, pady=5)
                    
                    for row_idx, row in enumerate(cursor, start=1):
                        for col_idx, value in enumerate(row):
                            ctk.CTkLabel(results_frame, text=str(value), font=("Arial", 12), width=150).grid(
                                row=row_idx, column=col_idx, padx=5, pady=2, sticky="w")
                    
                    if row_idx == 1:  # No records found
                        ctk.CTkLabel(results_frame, text="No attendance records found", font=("Arial", 12)).grid(
                            row=1, column=0, columnspan=4, padx=5, pady=10)
        
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
            self.log_message(f"History error: {err}")
        
        # Add close button
        close_button = ctk.CTkButton(history_window, text="Close", command=history_window.destroy)
        close_button.pack(pady=10)
        
        # Focus the window
        history_window.focus_set()

    def export_attendance(self):
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                query = """
                SELECT a.id, u.name as user_name, a.timestamp, u.id as user_id
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                """
                df = pd.read_sql(query, conn)
                
                # Format timestamp
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                df['time'] = pd.to_datetime(df['timestamp']).dt.time
                
                # Save to file
                filename = f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False)
                messagebox.showinfo("Success", f"Exported to '{filename}'")
                self.log_message(f"Attendance exported to '{filename}'")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
            self.log_message(f"Export error: {e}")

    def on_closing(self):
        self.stop_attendance()
        self.stop_capture()
        self.camera.release()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = AttendanceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()