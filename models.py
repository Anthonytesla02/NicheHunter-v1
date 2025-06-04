from app import db
from datetime import datetime
import json

class AnalysisSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parameters = db.Column(db.Text)  # JSON string of search parameters
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    total_videos_analyzed = db.Column(db.Integer, default=0)
    total_channels_found = db.Column(db.Integer, default=0)
    total_niches_identified = db.Column(db.Integer, default=0)
    
    def set_parameters(self, params_dict):
        self.parameters = json.dumps(params_dict)
    
    def get_parameters(self):
        if self.parameters:
            return json.loads(self.parameters)
        return {}

class NicheResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_session.id'), nullable=False)
    niche_name = db.Column(db.String(200), nullable=False)
    total_videos = db.Column(db.Integer, default=0)
    avg_views_per_day = db.Column(db.Float, default=0.0)
    avg_engagement_ratio = db.Column(db.Float, default=0.0)
    viral_score = db.Column(db.Float, default=0.0)
    keywords = db.Column(db.Text)  # JSON array of keywords
    top_channels = db.Column(db.Text)  # JSON array of channel data
    top_videos = db.Column(db.Text)  # JSON array of video data
    
    session = db.relationship('AnalysisSession', backref=db.backref('niches', lazy=True))
    
    def set_keywords(self, keywords_list):
        self.keywords = json.dumps(keywords_list)
    
    def get_keywords(self):
        if self.keywords:
            return json.loads(self.keywords)
        return []
    
    def set_top_channels(self, channels_list):
        self.top_channels = json.dumps(channels_list)
    
    def get_top_channels(self):
        if self.top_channels:
            return json.loads(self.top_channels)
        return []
    
    def set_top_videos(self, videos_list):
        self.top_videos = json.dumps(videos_list)
    
    def get_top_videos(self):
        if self.top_videos:
            return json.loads(self.top_videos)
        return []

class VideoData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('analysis_session.id'), nullable=False)
    video_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.Text)
    channel_id = db.Column(db.String(100))
    channel_title = db.Column(db.String(200))
    published_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.Text)
    has_face = db.Column(db.Boolean, default=False)
    face_confidence = db.Column(db.Float, default=0.0)
    viral_score = db.Column(db.Float, default=0.0)
    views_per_day = db.Column(db.Float, default=0.0)
    engagement_ratio = db.Column(db.Float, default=0.0)
    
    session = db.relationship('AnalysisSession', backref=db.backref('videos', lazy=True))
