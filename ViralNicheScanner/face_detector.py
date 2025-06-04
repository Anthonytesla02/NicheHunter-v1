import cv2
import numpy as np
import requests
import logging
from typing import Tuple, Optional
import os
from config import Config

logger = logging.getLogger(__name__)

class FaceDetector:
    def __init__(self):
        self.cascade_path = self._get_cascade_path()
        self.face_cascade = None
        self._load_cascade()
    
    def _get_cascade_path(self) -> str:
        """Get the path to the Haar cascade file"""
        # Try to find the cascade file in common locations
        possible_paths = [
            'haarcascade_frontalface_default.xml',
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If not found, download it
        return self._download_cascade()
    
    def _download_cascade(self) -> str:
        """Download the Haar cascade file if not found"""
        try:
            url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
            response = requests.get(url)
            response.raise_for_status()
            
            cascade_path = "haarcascade_frontalface_default.xml"
            with open(cascade_path, 'w') as f:
                f.write(response.text)
            
            logger.info(f"Downloaded Haar cascade to {cascade_path}")
            return cascade_path
            
        except Exception as e:
            logger.error(f"Error downloading Haar cascade: {str(e)}")
            return ""
    
    def _load_cascade(self):
        """Load the Haar cascade classifier"""
        try:
            if self.cascade_path and os.path.exists(self.cascade_path):
                self.face_cascade = cv2.CascadeClassifier(self.cascade_path)
                logger.info("Face cascade loaded successfully")
            else:
                logger.warning("Face cascade file not found")
        except Exception as e:
            logger.error(f"Error loading face cascade: {str(e)}")
    
    def detect_faces_in_url(self, image_url: str) -> Tuple[bool, float]:
        """
        Detect faces in an image from URL
        Returns: (has_face, confidence_score)
        """
        try:
            if not self.face_cascade:
                logger.warning("Face cascade not loaded, returning False")
                return False, 0.0
            
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Convert to numpy array
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.warning(f"Could not decode image from URL: {image_url}")
                return False, 0.0
            
            return self.detect_faces_in_image(image)
            
        except Exception as e:
            logger.error(f"Error detecting faces in URL {image_url}: {str(e)}")
            return False, 0.0
    
    def detect_faces_in_image(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Detect faces in an image array
        Returns: (has_face, confidence_score)
        """
        try:
            if self.face_cascade is None:
                return False, 0.0
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            has_face = len(faces) > 0
            
            if has_face:
                # Calculate confidence based on face size relative to image
                image_area = gray.shape[0] * gray.shape[1]
                total_face_area = sum(w * h for (x, y, w, h) in faces)
                face_ratio = total_face_area / image_area
                
                # Confidence score based on face prominence
                confidence = min(1.0, face_ratio * 10)  # Scale to 0-1
            else:
                confidence = 0.0
            
            return has_face, confidence
            
        except Exception as e:
            logger.error(f"Error detecting faces in image: {str(e)}")
            return False, 0.0
    
    def analyze_channel_thumbnails(self, video_thumbnails: list) -> Tuple[float, int]:
        """
        Analyze multiple thumbnails to determine if channel is faceless
        Returns: (average_face_confidence, face_percentage)
        """
        try:
            if not video_thumbnails:
                return 0.0, 0
            
            total_confidence = 0.0
            face_count = 0
            analyzed_count = 0
            
            for thumbnail_url in video_thumbnails:
                if thumbnail_url:
                    has_face, confidence = self.detect_faces_in_url(thumbnail_url)
                    total_confidence += confidence
                    if has_face and confidence > Config.DEFAULT_PARAMS['face_detection_threshold']:
                        face_count += 1
                    analyzed_count += 1
            
            if analyzed_count == 0:
                return 0.0, 0
            
            avg_confidence = total_confidence / analyzed_count
            face_percentage = (face_count / analyzed_count) * 100
            
            logger.info(f"Analyzed {analyzed_count} thumbnails: {face_percentage:.1f}% contain faces")
            return avg_confidence, face_percentage
            
        except Exception as e:
            logger.error(f"Error analyzing channel thumbnails: {str(e)}")
            return 0.0, 0
