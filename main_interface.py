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

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("900x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.cap = None
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
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open webcam.")
            self.log_message("Camera error: Could not open webcam")
            self.cap = None

    def create_widgets(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Face Attendance System", font=("Helvetica", 28, "bold"))
        self.title_label.pack(pady=(10, 20))

        self.register_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.register_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.register_frame, text="Name:", font=("Arial", 14)).pack(side="left", padx=5)
        self.name_entry = ctk.CTkEntry(self.register_frame, width=200, font=("Arial", 14))
        self.name_entry.pack(side="left", padx=5)
        self.capture_button = ctk.CTkButton(self.register_frame, text="Capture Face", command=self.start_capture, font=("Arial", 14), width=120)
        self.capture_button.pack(side="left", padx=10)

        self.preview_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.preview_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.preview_frame, text="Face Preview", font=("Arial", 16)).pack(pady=5)
        self.preview_canvas = tk.Canvas(self.preview_frame, width=200, height=200, bg="gray")
        self.preview_canvas.pack(pady=5)

        self.user_list_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.user_list_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(self.user_list_frame, text="Registered Users", font=("Arial", 16)).pack(pady=5)
        self.user_listbox = tk.Listbox(self.user_list_frame, height=5, font=("Arial", 12))
        self.user_listbox.pack(padx=5, pady=5, fill="x")
        self.update_user_list()

        self.attendance_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.attendance_frame.pack(pady=10, padx=10, fill="both", expand=True)
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

        self.canvas = tk.Canvas(self.attendance_frame, width=640, height=360, bg="black")
        self.canvas.pack(pady=10)

        self.log_frame = ctk.CTkFrame(self.attendance_frame, corner_radius=10)
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

        if not self.cap or not self.cap.isOpened():
            self.initialize_camera()
            if not self.cap:
                return

        self.registering = True
        self.capture_button.configure(text="Register", command=self.register_from_webcam)
        self.log_message("Capturing face... Click 'Register' to save.")
        threading.Thread(target=self.update_preview, daemon=True).start()

    def update_preview(self):
        while self.registering:
            if not self.cap or not self.cap.isOpened():
                self.log_message("Camera disconnected during capture")
                break

            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.log_message("Failed to capture frame")
                continue

            try:
                if frame.shape[2] != 3:
                    self.log_message("Invalid frame format")
                    continue

                height, width = frame.shape[:2]
                preview_size = (200, 200)
                aspect_ratio = width / height
                
                if aspect_ratio > 1:
                    new_width = preview_size[0]
                    new_height = int(preview_size[0] / aspect_ratio)
                else:
                    new_height = preview_size[1]
                    new_width = int(preview_size[1] * aspect_ratio)

                preview_frame = cv2.resize(frame, (new_width, new_height))
                frame_rgb = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(
                    preview_size[0]//2, 
                    preview_size[1]//2, 
                    anchor="center", 
                    image=imgtk
                )
                self.preview_canvas.image = imgtk
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

        self.log_message(f"Captured frame shape: {self.captured_frame.shape}, dtype: {self.captured_frame.dtype}")
        success, message = register_user(name, self.captured_frame)
        if success:
            messagebox.showinfo("Success", message)
            self.name_entry.delete(0, tk.END)
            self.preview_canvas.delete("all")
            self.update_user_list()
        else:
            messagebox.showerror("Error", message)
        self.log_message(message)
        self.stop_capture()

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

        result, message = load_face_encodings()
        if result is None:
            messagebox.showerror("Error", message)
            self.log_message(message)
            return
        self.known_faces = result
        if not self.known_faces:
            messagebox.showwarning("Warning", "No registered users found.")
            self.log_message("No registered users found")
            return

        self.known_ids = list(self.known_faces.keys())
        self.known_encodings = [data["encoding"] for data in self.known_faces.values()]
        self.known_names = [data["name"] for data in self.known_faces.values()]
        self.log_message(f"Loaded {len(self.known_names)} known faces: {', '.join(self.known_names)}")

        if not self.cap or not self.cap.isOpened():
            self.initialize_camera()
            if not self.cap:
                return

        self.running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.log_message("Attendance system started")
        threading.Thread(target=self.update_video, daemon=True).start()

    def stop_attendance(self):
        self.running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.log_message("Attendance system stopped")

    def update_video(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                self.log_message("Camera disconnected")
                break
            ret, frame = self.cap.read()
            if not ret:
                self.log_message("Failed to capture frame")
                break

            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            self.frame_count = (self.frame_count + 1) % 2
            if self.frame_count == 0:
                rgb_frame = small_frame[:, :, ::-1]
                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                self.log_message(f"Detected face locations: {face_locations}")
                if not face_locations:
                    self.log_message("No faces detected in frame")
                    continue

                try:
                    face_encodings = face_recognition.face_encodings(
                        rgb_frame,
                        known_face_locations=face_locations,
                        num_jitters=3,  # Match registration parameters
                        model="large"   # Match registration model
                    )
                    if not face_encodings:
                        self.log_message("No face encodings computed")
                        continue

                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                        matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.65)
                        name = "Unknown"
                        if matches:
                            best_match_index = np.argmin(distances)
                            if matches[best_match_index]:
                                user_id = self.known_ids[best_match_index]
                                name = self.known_names[best_match_index]
                                success, message = record_attendance(user_id, self.last_attendance)
                                if success:
                                    self.log_message(f"Recognized: {name} (ID: {user_id}, Distance: {distances[best_match_index]:.4f}) - {message}")
                                    winsound.Beep(1000, 200)
                                else:
                                    self.log_message(f"Match found but attendance failed: {name} - {message}")
                            else:
                                self.log_message(f"Face detected but no match (Min distance: {distances[best_match_index]:.4f})")
                        else:
                            self.log_message(f"Face detected but no match (Distances: {[f'{d:.4f}' for d in distances]})")

                        top, right, bottom, left = [int(x * 2) for x in (top, right, bottom, left)]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                except Exception as e:
                    self.log_message(f"Error computing face encodings: {str(e)}")
                    continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor="nw", image=imgtk)
            self.canvas.image = imgtk
            self.root.update()

        self.stop_attendance()

    def view_history(self):
        history_window = ctk.CTkToplevel(self.root)
        history_window.title("Attendance History")
        history_window.geometry("600x400")
        headers = ["ID", "User ID", "Timestamp"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(history_window, text=header, font=("Arial", 14, "bold")).grid(row=0, column=i, padx=5, pady=5)
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, user_id, timestamp FROM attendance ORDER BY timestamp DESC LIMIT 50")
                    for row_idx, row in enumerate(cursor, start=1):
                        for col_idx, value in enumerate(row):
                            ctk.CTkLabel(history_window, text=str(value), font=("Arial", 12)).grid(row=row_idx, column=col_idx, padx=5, pady=2)
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error: {err}")
            self.log_message(f"History error: {err}")

    def export_attendance(self):
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                df = pd.read_sql("SELECT * FROM attendance ORDER BY timestamp DESC", conn)
                df.to_csv("attendance_export.csv", index=False)
                messagebox.showinfo("Success", "Exported to 'attendance_export.csv'")
                self.log_message("Attendance exported to 'attendance_export.csv'")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
            self.log_message(f"Export error: {e}")

    def on_closing(self):
        self.stop_attendance()
        self.stop_capture()
        if self.cap:
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = AttendanceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
