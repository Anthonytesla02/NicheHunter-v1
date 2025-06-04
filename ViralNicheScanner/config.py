import os

class Config:
    # API Configuration
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'your-youtube-api-key')
    GOOGLE_VISION_API_KEY = os.environ.get('GOOGLE_VISION_API_KEY', 'your-vision-api-key')
    
    # Default Analysis Parameters
    DEFAULT_PARAMS = {
        'max_duration_seconds': 60,
        'min_views_per_day': 50000,
        'min_monthly_views': 10000000,
        'max_channel_videos': 20,
        'max_channel_age_days': 30,
        'min_weekly_uploads': 4,
        'min_video_views_7days': 50000,
        'days_back_to_search': 7,
        'face_detection_threshold': 0.7,
        'max_face_percentage': 10,
        'search_query': '',
        'faceless_only': True,
        'max_results_per_query': 50
    }
    
    # Search Queries for Different Niches
    SEARCH_QUERIES = [
        'youtube shorts viral',
        'shorts trending now',
        'viral shorts 2024',
        'ai facts shorts',
        'quick facts',
        'amazing facts',
        'did you know',
        'life hacks shorts',
        'psychology facts',
        'science facts',
        'technology shorts',
        'motivation shorts',
        'productivity tips',
        'money facts',
        'business shorts',
        'history facts',
        'space facts',
        'animal facts',
        'food facts',
        'travel shorts'
    ]
    
    # NLP Configuration
    SPACY_MODEL = 'en_core_web_sm'
    MIN_CLUSTER_SIZE = 3
    MAX_CLUSTERS = 10
    
    # Face Detection Configuration
    OPENCV_CASCADE_PATH = 'haarcascade_frontalface_default.xml'
    
    # File Paths
    RESULTS_DIR = 'results'
    TEMP_DIR = 'temp'
