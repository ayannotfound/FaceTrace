# register_user.py
import face_recognition
import json
import mysql.connector
import numpy as np
import cv2
from config import DB_CONFIG

def register_user(name: str, image: np.ndarray) -> tuple[bool, str]:
    """
    Register a user by encoding their face from a captured image.
    Includes additional image processing and validation steps.
    """
    # Input validation
    if not name:
        return False, "Name cannot be empty."
    if image is None or not isinstance(image, np.ndarray):
        return False, "Invalid image data: Image is None or not a NumPy array."
    if image.size == 0:
        return False, "Invalid image data: Empty array."

    try:
        # Ensure image is in correct format (BGR)
        if len(image.shape) != 3:
            return False, "Invalid image format: Must be a color image"
        
        # Convert BGR to RGB (face_recognition expects RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_image, model="hog")
        
        if not face_locations:
            return False, "No faces detected in the image. Please ensure your face is clearly visible."
        if len(face_locations) > 1:
            return False, f"Multiple faces detected ({len(face_locations)}). Please ensure only one face is in the frame."

        # Get face encoding with additional parameters for reliability
        face_encodings = face_recognition.face_encodings(
            rgb_image,
            known_face_locations=face_locations,
            num_jitters=3,  # Multiple samples for better accuracy
            model="large"   # Use large model for better accuracy
        )

        if not face_encodings:
            return False, "Failed to compute face encoding. Please try again with better lighting."

        encoding = face_encodings[0]
        
        # Validate encoding
        if not isinstance(encoding, np.ndarray) or encoding.size != 128:
            return False, "Invalid face encoding generated."

        # Convert to JSON-compatible format
        encoded_json = json.dumps(encoding.tolist())

        # Save to database
        try:
            with mysql.connector.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cursor:
                    query = "INSERT INTO users (name, face_encoding) VALUES (%s, %s)"
                    cursor.execute(query, (name, encoded_json))
                    conn.commit()
                    return True, f"User '{name}' registered successfully!"
        except mysql.connector.Error as err:
            return False, f"Database error: {err}"

    except Exception as e:
        return False, f"Error processing image: {str(e)}"