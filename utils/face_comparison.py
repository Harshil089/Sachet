"""
Utility functions for face comparison using face_recognition library
"""
import face_recognition
import numpy as np
import requests
from io import BytesIO
from PIL import Image
import os

def compare_faces(missing_photo_path, sighting_photo_path):
    """
    Compare two face images and return similarity score (0-100)
    
    Args:
        missing_photo_path: Path or URL to missing child's photo
        sighting_photo_path: Path or URL to sighting photo
    
    Returns:
        float: Confidence score (0-100) or None if faces not detected
    """
    try:
        # Load images
        missing_image = load_image(missing_photo_path)
        sighting_image = load_image(sighting_photo_path)
        
        if missing_image is None or sighting_image is None:
            return None
        
        # Get face encodings
        missing_encodings = face_recognition.face_encodings(missing_image)
        sighting_encodings = face_recognition.face_encodings(sighting_image)
        
        if not missing_encodings or not sighting_encodings:
            print("⚠️ No face detected in one or both images")
            return None
        
        # Compare faces (use first detected face from each image)
        face_distance = face_recognition.face_distance(
            [missing_encodings[0]], 
            sighting_encodings[0]
        )[0]
        
        # Convert distance to percentage (0-100)
        # face_distance: 0 = perfect match, 1 = completely different
        confidence = (1 - face_distance) * 100
        
        # Ensure it's between 0-100
        confidence = max(0, min(100, confidence))
        
        print(f"✅ Face comparison complete: {confidence:.2f}% match")
        return round(confidence, 2)
        
    except Exception as e:
        print(f"❌ Face comparison error: {str(e)}")
        return None


def load_image(image_path):
    """
    Load image from file path or URL
    
    Args:
        image_path: Local file path or HTTP(S) URL
    
    Returns:
        numpy array: Image in RGB format, or None if failed
    """
    try:
        if image_path.startswith('http://') or image_path.startswith('https://'):
            # Download from URL
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
        else:
            # Load from local file
            if not os.path.exists(image_path):
                # Try with static/uploads prefix
                alt_path = os.path.join('static', 'uploads', image_path)
                if os.path.exists(alt_path):
                    image_path = alt_path
                else:
                    print(f"❌ Image not found: {image_path}")
                    return None
            
            image = Image.open(image_path)
        
        # Convert to RGB (face_recognition requires RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert PIL Image to numpy array
        return np.array(image)
        
    except Exception as e:
        print(f"❌ Error loading image {image_path}: {str(e)}")
        return None


def detect_faces_count(image_path):
    """
    Detect number of faces in an image
    
    Args:
        image_path: Path or URL to image
    
    Returns:
        int: Number of faces detected
    """
    try:
        image = load_image(image_path)
        if image is None:
            return 0
        
        face_locations = face_recognition.face_locations(image)
        return len(face_locations)
        
    except Exception as e:
        print(f"❌ Face detection error: {str(e)}")
        return 0
