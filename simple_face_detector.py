import requests
import base64
from typing import Tuple, List
import logging
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

class SimpleFaceDetector:
    """
    Lightweight face detection without OpenCV/ML dependencies.
    Uses rule-based heuristics and optional external APIs.
    """
    
    def __init__(self):
        self.face_keywords = [
            'face', 'eyes', 'smile', 'person', 'man', 'woman', 'guy', 'girl',
            'selfie', 'portrait', 'headshot', 'closeup', 'talking', 'speaking'
        ]
        
        self.faceless_indicators = [
            'screen', 'text', 'animation', 'cartoon', 'logo', 'graphic',
            'chart', 'diagram', 'map', 'game', 'code', 'tutorial', 'how to',
            'facts', 'tips', 'ai generated', 'voiceover', 'narration'
        ]
    
    def detect_faces_in_url(self, image_url: str) -> Tuple[bool, float]:
        """
        Detect faces using multiple lightweight methods:
        1. URL pattern analysis
        2. Filename analysis
        3. Image metadata if available
        """
        try:
            # Method 1: URL and filename analysis
            has_face_url, confidence_url = self._analyze_url_patterns(image_url)
            
            # Method 2: Simple image analysis (no ML)
            has_face_simple, confidence_simple = self._simple_image_analysis(image_url)
            
            # Combine results with weighted average
            final_confidence = (confidence_url * 0.4 + confidence_simple * 0.6)
            has_face = final_confidence > 0.5
            
            return has_face, final_confidence
            
        except Exception as e:
            logger.error(f"Error in face detection: {str(e)}")
            return False, 0.0
    
    def _analyze_url_patterns(self, image_url: str) -> Tuple[bool, float]:
        """
        Analyze URL and filename for face-related patterns
        """
        try:
            url_lower = image_url.lower()
            
            # Check for faceless indicators in URL
            faceless_score = 0
            for indicator in self.faceless_indicators:
                if indicator in url_lower:
                    faceless_score += 1
            
            # Check for face indicators in URL
            face_score = 0
            for keyword in self.face_keywords:
                if keyword in url_lower:
                    face_score += 1
            
            # YouTube thumbnail analysis
            if 'ytimg.com' in url_lower or 'youtube.com' in url_lower:
                # Check thumbnail quality (higher quality often means faces)
                if 'maxresdefault' in url_lower or 'hqdefault' in url_lower:
                    face_score += 0.5  # Slight bias toward face content
            
            # Calculate confidence
            total_signals = face_score + faceless_score
            if total_signals == 0:
                return False, 0.3  # Neutral confidence
            
            face_confidence = face_score / total_signals
            return face_confidence > 0.5, face_confidence
            
        except Exception as e:
            logger.error(f"Error analyzing URL patterns: {str(e)}")
            return False, 0.3
    
    def _simple_image_analysis(self, image_url: str) -> Tuple[bool, float]:
        """
        Simple image analysis without heavy ML libraries
        """
        try:
            # Download and analyze image headers/metadata
            response = requests.head(image_url, timeout=5)
            
            # Check content type and size
            content_type = response.headers.get('content-type', '').lower()
            content_length = int(response.headers.get('content-length', 0))
            
            confidence = 0.3  # Base confidence
            
            # Larger images more likely to contain faces
            if content_length > 50000:  # > 50KB
                confidence += 0.2
            elif content_length > 20000:  # > 20KB
                confidence += 0.1
            
            # JPEG images more likely to contain faces than PNG graphics
            if 'jpeg' in content_type or 'jpg' in content_type:
                confidence += 0.1
            
            return confidence > 0.5, confidence
            
        except Exception as e:
            logger.error(f"Error in simple image analysis: {str(e)}")
            return False, 0.3
    
    def analyze_channel_thumbnails(self, video_thumbnails: List[str]) -> Tuple[float, int]:
        """
        Analyze multiple thumbnails to determine channel faceless percentage
        """
        try:
            if not video_thumbnails:
                return 0.0, 0
            
            total_confidence = 0
            face_count = 0
            
            for thumbnail_url in video_thumbnails[:10]:  # Analyze max 10 thumbnails
                has_face, confidence = self.detect_faces_in_url(thumbnail_url)
                total_confidence += confidence
                if has_face:
                    face_count += 1
            
            avg_confidence = total_confidence / len(video_thumbnails[:10])
            face_percentage = (face_count / len(video_thumbnails[:10])) * 100
            
            return avg_confidence, int(face_percentage)
            
        except Exception as e:
            logger.error(f"Error analyzing channel thumbnails: {str(e)}")
            return 0.0, 0
    
    def analyze_video_title_for_face_content(self, title: str, description: str = "") -> float:
        """
        Analyze video title and description for face-related content
        """
        try:
            text = f"{title} {description}".lower()
            
            # Look for face-related keywords
            face_indicators = 0
            for keyword in self.face_keywords:
                if keyword in text:
                    face_indicators += text.count(keyword)
            
            # Look for faceless content indicators
            faceless_indicators = 0
            for indicator in self.faceless_indicators:
                if indicator in text:
                    faceless_indicators += text.count(indicator)
            
            # Calculate face probability based on text analysis
            total_indicators = face_indicators + faceless_indicators
            if total_indicators == 0:
                return 0.3  # Neutral
            
            face_probability = face_indicators / total_indicators
            return min(face_probability, 1.0)
            
        except Exception as e:
            logger.error(f"Error analyzing video title: {str(e)}")
            return 0.3