import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
from config import Config

logger = logging.getLogger(__name__)

class YouTubeAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    def search_shorts(self, query: str, days_back: int = 7, max_results: int = 50) -> List[Dict]:
        """Search for YouTube Shorts based on query and date range"""
        try:
            # Calculate date range
            published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            
            # Search parameters
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'videoDuration': 'short',  # Videos under 4 minutes
                'publishedAfter': published_after,
                'order': 'viewCount',
                'maxResults': max_results,
                'key': self.api_key
            }
            
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            for item in data.get('items', []):
                video_data = {
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                    'description': item['snippet'].get('description', '')
                }
                videos.append(video_data)
            
            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos
            
        except Exception as e:
            logger.error(f"Error searching videos for query '{query}': {str(e)}")
            return []
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get detailed statistics for videos"""
        try:
            # Split into chunks of 50 (API limit)
            video_details = {}
            
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i:i+50]
                
                params = {
                    'part': 'statistics,contentDetails,snippet',
                    'id': ','.join(chunk),
                    'key': self.api_key
                }
                
                response = requests.get(f"{self.base_url}/videos", params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get('items', []):
                    video_id = item['id']
                    
                    # Parse duration
                    duration_str = item['contentDetails']['duration']
                    duration_seconds = self._parse_duration(duration_str)
                    
                    # Only include shorts (< 60 seconds)
                    if duration_seconds <= 60:
                        stats = item['statistics']
                        video_details[video_id] = {
                            'duration_seconds': duration_seconds,
                            'view_count': int(stats.get('viewCount', 0)),
                            'like_count': int(stats.get('likeCount', 0)),
                            'comment_count': int(stats.get('commentCount', 0)),
                            'published_at': item['snippet']['publishedAt']
                        }
            
            logger.info(f"Retrieved details for {len(video_details)} valid shorts")
            return video_details
            
        except Exception as e:
            logger.error(f"Error getting video details: {str(e)}")
            return {}
    
    def get_channel_details(self, channel_ids: List[str]) -> Dict[str, Dict]:
        """Get channel statistics and details"""
        try:
            channel_details = {}
            
            for i in range(0, len(channel_ids), 50):
                chunk = channel_ids[i:i+50]
                
                params = {
                    'part': 'statistics,snippet',
                    'id': ','.join(chunk),
                    'key': self.api_key
                }
                
                response = requests.get(f"{self.base_url}/channels", params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get('items', []):
                    channel_id = item['id']
                    stats = item['statistics']
                    snippet = item['snippet']
                    
                    channel_details[channel_id] = {
                        'title': snippet['title'],
                        'subscriber_count': int(stats.get('subscriberCount', 0)),
                        'video_count': int(stats.get('videoCount', 0)),
                        'view_count': int(stats.get('viewCount', 0)),
                        'created_at': snippet.get('publishedAt'),
                        'thumbnail_url': snippet['thumbnails'].get('default', {}).get('url', '')
                    }
            
            logger.info(f"Retrieved details for {len(channel_details)} channels")
            return channel_details
            
        except Exception as e:
            logger.error(f"Error getting channel details: {str(e)}")
            return {}
    
    def calculate_viral_metrics(self, video_data: Dict, channel_data: Dict) -> Dict:
        """Calculate viral score and metrics for a video"""
        try:
            # Parse published date
            published_at = datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00'))
            days_since_published = (datetime.now(published_at.tzinfo) - published_at).days
            days_since_published = max(1, days_since_published)  # Avoid division by zero
            
            # Calculate metrics
            views_per_day = video_data['view_count'] / days_since_published
            engagement_ratio = (video_data['like_count'] + video_data['comment_count']) / max(video_data['view_count'], 1)
            
            # Channel age factor
            if channel_data.get('created_at'):
                channel_created = datetime.fromisoformat(channel_data['created_at'].replace('Z', '+00:00'))
                channel_age_days = (datetime.now(channel_created.tzinfo) - channel_created).days
            else:
                channel_age_days = 365  # Default if unknown
            
            # Calculate viral score (0-100)
            viral_score = 0
            
            # Views per day component (40% of score)
            if views_per_day >= 100000:
                viral_score += 40
            elif views_per_day >= 50000:
                viral_score += 30
            elif views_per_day >= 10000:
                viral_score += 20
            elif views_per_day >= 1000:
                viral_score += 10
            
            # Engagement component (30% of score)
            if engagement_ratio >= 0.1:
                viral_score += 30
            elif engagement_ratio >= 0.05:
                viral_score += 20
            elif engagement_ratio >= 0.02:
                viral_score += 15
            elif engagement_ratio >= 0.01:
                viral_score += 10
            
            # Channel newness component (20% of score)
            if channel_age_days <= 30:
                viral_score += 20
            elif channel_age_days <= 90:
                viral_score += 15
            elif channel_age_days <= 180:
                viral_score += 10
            elif channel_age_days <= 365:
                viral_score += 5
            
            # Video performance consistency (10% of score)
            if channel_data.get('video_count', 0) > 0:
                avg_views_per_video = channel_data.get('view_count', 0) / channel_data['video_count']
                if avg_views_per_video >= 100000:
                    viral_score += 10
                elif avg_views_per_video >= 50000:
                    viral_score += 7
                elif avg_views_per_video >= 10000:
                    viral_score += 5
            
            return {
                'viral_score': min(100, viral_score),
                'views_per_day': views_per_day,
                'engagement_ratio': engagement_ratio,
                'channel_age_days': channel_age_days,
                'days_since_published': days_since_published
            }
            
        except Exception as e:
            logger.error(f"Error calculating viral metrics: {str(e)}")
            return {
                'viral_score': 0,
                'views_per_day': 0,
                'engagement_ratio': 0,
                'channel_age_days': 365,
                'days_since_published': 1
            }
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        try:
            # Remove 'PT' prefix
            duration_str = duration_str[2:]
            
            hours = 0
            minutes = 0
            seconds = 0
            
            if 'H' in duration_str:
                hours_str, duration_str = duration_str.split('H')
                hours = int(hours_str)
            
            if 'M' in duration_str:
                minutes_str, duration_str = duration_str.split('M')
                minutes = int(minutes_str)
            
            if 'S' in duration_str:
                seconds_str = duration_str.replace('S', '')
                seconds = int(seconds_str)
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.error(f"Error parsing duration '{duration_str}': {str(e)}")
            return 0
