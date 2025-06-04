import re
import logging
from typing import List, Dict, Any
from collections import Counter, defaultdict
import json

logger = logging.getLogger(__name__)

class SimpleNicheAnalyzer:
    """
    Rule-based niche analyzer without machine learning dependencies.
    Uses keyword matching and content categorization rules.
    """
    
    def __init__(self):
        # Define niche categories with keywords
        self.niche_categories = {
            'AI & Technology': [
                'ai', 'artificial intelligence', 'tech', 'technology', 'robot', 'automation',
                'machine learning', 'coding', 'programming', 'software', 'app', 'digital'
            ],
            'Psychology & Mind': [
                'psychology', 'mind', 'brain', 'mental', 'mindset', 'behavior', 'cognitive',
                'emotional', 'memory', 'learning', 'habit', 'personality', 'psychology facts'
            ],
            'Science & Facts': [
                'science', 'facts', 'did you know', 'amazing facts', 'scientific', 'discovery',
                'research', 'study', 'experiment', 'physics', 'chemistry', 'biology'
            ],
            'Money & Finance': [
                'money', 'finance', 'investment', 'crypto', 'bitcoin', 'trading', 'business',
                'entrepreneur', 'wealth', 'rich', 'millionaire', 'passive income', 'stocks'
            ],
            'Life Hacks & Tips': [
                'life hack', 'tips', 'tricks', 'how to', 'productivity', 'efficiency',
                'time management', 'organization', 'useful', 'helpful', 'secret'
            ],
            'Motivation & Success': [
                'motivation', 'success', 'inspiration', 'mindset', 'goals', 'achievement',
                'self improvement', 'personal development', 'confidence', 'discipline'
            ],
            'History & Education': [
                'history', 'historical', 'ancient', 'war', 'civilization', 'education',
                'learning', 'knowledge', 'facts about', 'timeline', 'culture'
            ],
            'Health & Fitness': [
                'health', 'fitness', 'workout', 'exercise', 'diet', 'nutrition', 'wellness',
                'medical', 'doctor', 'symptoms', 'cure', 'treatment', 'body'
            ],
            'Space & Universe': [
                'space', 'universe', 'galaxy', 'planet', 'star', 'nasa', 'astronomy',
                'cosmos', 'solar system', 'astronaut', 'alien', 'black hole'
            ],
            'Animals & Nature': [
                'animal', 'nature', 'wildlife', 'pets', 'dogs', 'cats', 'ocean',
                'forest', 'environment', 'species', 'evolution', 'biology'
            ],
            'Food & Cooking': [
                'food', 'cooking', 'recipe', 'kitchen', 'chef', 'restaurant', 'meal',
                'ingredients', 'taste', 'cuisine', 'nutrition', 'eating'
            ],
            'Travel & Places': [
                'travel', 'country', 'city', 'destination', 'culture', 'geography',
                'adventure', 'vacation', 'explore', 'world', 'places', 'tourism'
            ]
        }
        
        # Stop words to ignore
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their', 'shorts', 'video', 'youtube', 'viral', 'trending'
        }
    
    def extract_keywords_from_text(self, text: str) -> List[str]:
        """
        Extract keywords from text using simple rules
        """
        try:
            if not text:
                return []
            
            # Clean and normalize text
            text = text.lower()
            text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            
            # Split into words
            words = text.split()
            
            # Filter out stop words and short words
            keywords = [
                word for word in words 
                if word not in self.stop_words and len(word) > 2
            ]
            
            # Extract phrases (2-3 words)
            phrases = []
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if self._is_meaningful_phrase(phrase):
                    phrases.append(phrase)
            
            # Combine keywords and phrases
            all_keywords = keywords + phrases
            
            # Count frequency and return top keywords
            keyword_counts = Counter(all_keywords)
            return [keyword for keyword, count in keyword_counts.most_common(20)]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    def _is_meaningful_phrase(self, phrase: str) -> bool:
        """
        Check if a phrase is meaningful (not just stop words)
        """
        words = phrase.split()
        return any(word not in self.stop_words for word in words)
    
    def cluster_videos_by_content(self, videos_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Cluster videos into niches using rule-based categorization
        """
        try:
            if not videos_data:
                return {}
            
            # Initialize clusters
            clusters = defaultdict(list)
            
            for video in videos_data:
                # Combine title and description for analysis
                title = video.get('title', '')
                description = video.get('description', '')
                text = f"{title} {description}".lower()
                
                # Find best matching niche
                best_niche = self._categorize_content(text)
                
                # Add video to appropriate cluster
                clusters[best_niche].append(video)
            
            # Filter out small clusters
            min_cluster_size = max(2, len(videos_data) // 10)  # Dynamic minimum
            filtered_clusters = {
                niche: videos for niche, videos in clusters.items()
                if len(videos) >= min_cluster_size
            }
            
            # If no clusters meet minimum size, create generic clusters
            if not filtered_clusters:
                filtered_clusters = self._create_generic_clusters(videos_data)
            
            return dict(filtered_clusters)
            
        except Exception as e:
            logger.error(f"Error clustering videos: {str(e)}")
            return {'General Content': videos_data}
    
    def _categorize_content(self, text: str) -> str:
        """
        Categorize content based on keyword matching
        """
        try:
            niche_scores = {}
            
            for niche, keywords in self.niche_categories.items():
                score = 0
                for keyword in keywords:
                    # Count keyword occurrences with weight for exact matches
                    if keyword in text:
                        score += text.count(keyword) * 2
                    
                    # Partial matches for compound keywords
                    words = keyword.split()
                    if len(words) > 1:
                        if all(word in text for word in words):
                            score += 1
                
                niche_scores[niche] = score
            
            # Return niche with highest score
            if niche_scores and max(niche_scores.values()) > 0:
                return max(niche_scores.keys(), key=lambda k: niche_scores[k])
            
            # Fallback categorization based on simple patterns
            return self._fallback_categorization(text)
            
        except Exception as e:
            logger.error(f"Error categorizing content: {str(e)}")
            return 'General Content'
    
    def _fallback_categorization(self, text: str) -> str:
        """
        Fallback categorization for uncategorized content
        """
        # Simple pattern matching
        if any(word in text for word in ['fact', 'know', 'amazing', 'secret']):
            return 'Facts & Knowledge'
        elif any(word in text for word in ['how', 'tutorial', 'guide', 'learn']):
            return 'Educational Content'
        elif any(word in text for word in ['quick', 'fast', 'easy', 'simple']):
            return 'Quick Tips'
        elif any(word in text for word in ['new', 'latest', 'update', 'news']):
            return 'Trending Topics'
        else:
            return 'General Content'
    
    def _create_generic_clusters(self, videos_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Create generic clusters when categorization fails
        """
        clusters = defaultdict(list)
        
        for i, video in enumerate(videos_data):
            cluster_name = f"Content Group {(i // 5) + 1}"
            clusters[cluster_name].append(video)
        
        return dict(clusters)
    
    def analyze_niche_performance(self, niche_videos: List[Dict]) -> Dict[str, Any]:
        """
        Analyze performance metrics for a niche
        """
        try:
            if not niche_videos:
                return {}
            
            # Calculate aggregate metrics
            total_videos = len(niche_videos)
            total_views = sum(video.get('view_count', 0) for video in niche_videos)
            total_likes = sum(video.get('like_count', 0) for video in niche_videos)
            total_comments = sum(video.get('comment_count', 0) for video in niche_videos)
            
            # Calculate averages
            avg_views = total_views / total_videos if total_videos > 0 else 0
            avg_engagement = (total_likes + total_comments) / max(total_views, 1)
            
            # Calculate views per day
            views_per_day_list = [video.get('views_per_day', 0) for video in niche_videos]
            avg_views_per_day = sum(views_per_day_list) / len(views_per_day_list) if views_per_day_list else 0
            
            # Calculate viral score
            viral_scores = [video.get('viral_score', 0) for video in niche_videos]
            avg_viral_score = sum(viral_scores) / len(viral_scores) if viral_scores else 0
            
            # Get unique channels
            unique_channels = set()
            for video in niche_videos:
                if video.get('channel_id'):
                    unique_channels.add(video['channel_id'])
            
            # Get top performing videos
            sorted_videos = sorted(niche_videos, key=lambda x: x.get('viral_score', 0), reverse=True)
            top_videos = sorted_videos[:3]
            
            # Extract common keywords
            all_titles = " ".join([video.get('title', '') for video in niche_videos])
            keywords = self.extract_keywords_from_text(all_titles)
            
            return {
                'total_videos': total_videos,
                'unique_channels': len(unique_channels),
                'avg_views': avg_views,
                'avg_views_per_day': avg_views_per_day,
                'avg_engagement_ratio': avg_engagement,
                'avg_viral_score': avg_viral_score,
                'top_videos': top_videos,
                'top_keywords': keywords[:10],
                'total_views': total_views,
                'total_engagement': total_likes + total_comments
            }
            
        except Exception as e:
            logger.error(f"Error analyzing niche performance: {str(e)}")
            return {}
    
    def rank_niches(self, niche_analyses: Dict[str, Dict]) -> List[Dict]:
        """
        Rank niches by their viral potential and performance
        """
        try:
            ranked_niches = []
            
            for niche_name, analysis in niche_analyses.items():
                if not analysis:
                    continue
                
                # Calculate ranking score (0-100)
                score = 0
                
                # Views per day component (40%)
                views_per_day = analysis.get('avg_views_per_day', 0)
                if views_per_day >= 100000:
                    score += 40
                elif views_per_day >= 50000:
                    score += 30
                elif views_per_day >= 20000:
                    score += 20
                elif views_per_day >= 5000:
                    score += 10
                
                # Engagement component (25%)
                engagement = analysis.get('avg_engagement_ratio', 0)
                if engagement >= 0.05:
                    score += 25
                elif engagement >= 0.03:
                    score += 20
                elif engagement >= 0.02:
                    score += 15
                elif engagement >= 0.01:
                    score += 10
                
                # Viral score component (20%)
                viral_score = analysis.get('avg_viral_score', 0)
                score += (viral_score / 100) * 20
                
                # Video count component (10%)
                video_count = analysis.get('total_videos', 0)
                if video_count >= 10:
                    score += 10
                elif video_count >= 5:
                    score += 5
                
                # Channel diversity component (5%)
                unique_channels = analysis.get('unique_channels', 0)
                if unique_channels >= 5:
                    score += 5
                elif unique_channels >= 3:
                    score += 2
                
                ranked_niches.append({
                    'niche_name': niche_name,
                    'ranking_score': min(100, score),
                    'analysis': analysis
                })
            
            # Sort by ranking score
            ranked_niches.sort(key=lambda x: x['ranking_score'], reverse=True)
            
            return ranked_niches
            
        except Exception as e:
            logger.error(f"Error ranking niches: {str(e)}")
            return []