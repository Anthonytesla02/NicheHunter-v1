import spacy
import logging
from typing import List, Dict, Any
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from config import Config

logger = logging.getLogger(__name__)

class NicheAnalyzer:
    def __init__(self):
        self.nlp = None
        self._load_spacy_model()
        
    def _load_spacy_model(self):
        """Load spaCy model for NLP processing"""
        try:
            self.nlp = spacy.load(Config.SPACY_MODEL)
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading spaCy model: {str(e)}")
            logger.info("You may need to download the model: python -m spacy download en_core_web_sm")
    
    def extract_keywords_from_text(self, text: str) -> List[str]:
        """Extract meaningful keywords from text using NLP"""
        try:
            if not self.nlp:
                # Fallback to simple keyword extraction
                return self._simple_keyword_extraction(text)
            
            doc = self.nlp(text.lower())
            keywords = []
            
            # Extract entities, nouns, and adjectives
            for token in doc:
                if (token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and 
                    len(token.text) > 2 and 
                    not token.is_stop and 
                    not token.is_punct and
                    token.is_alpha):
                    keywords.append(token.lemma_)
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT']:
                    keywords.append(ent.text.lower())
            
            return list(set(keywords))
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return self._simple_keyword_extraction(text)
    
    def _simple_keyword_extraction(self, text: str) -> List[str]:
        """Simple fallback keyword extraction"""
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'youtube', 'shorts', 'video', 'subscribe', 'like', 'comment', 'share'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return list(set(keywords))
    
    def cluster_videos_by_content(self, videos_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Cluster videos by content similarity to identify niches"""
        try:
            if len(videos_data) < Config.MIN_CLUSTER_SIZE:
                logger.warning(f"Not enough videos ({len(videos_data)}) for clustering")
                return {"general": videos_data}
            
            # Prepare text data for clustering
            texts = []
            for video in videos_data:
                text = f"{video.get('title', '')} {video.get('description', '')}"
                texts.append(text)
            
            # Use TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            
            try:
                tfidf_matrix = vectorizer.fit_transform(texts)
            except ValueError as e:
                logger.warning(f"TF-IDF vectorization failed: {str(e)}")
                return {"general": videos_data}
            
            # Determine optimal number of clusters
            n_clusters = min(Config.MAX_CLUSTERS, max(2, len(videos_data) // Config.MIN_CLUSTER_SIZE))
            
            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            # Group videos by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(cluster_labels):
                clusters[f"cluster_{label}"].append(videos_data[i])
            
            # Generate meaningful cluster names
            named_clusters = {}
            feature_names = vectorizer.get_feature_names_out()
            
            for cluster_id, cluster_videos in clusters.items():
                if len(cluster_videos) >= Config.MIN_CLUSTER_SIZE:
                    # Get cluster center
                    cluster_idx = int(cluster_id.split('_')[1])
                    center = kmeans.cluster_centers_[cluster_idx]
                    
                    # Get top features for this cluster
                    top_indices = center.argsort()[-10:][::-1]
                    top_features = [feature_names[i] for i in top_indices]
                    
                    # Generate cluster name from top features and video titles
                    cluster_name = self._generate_cluster_name(cluster_videos, top_features)
                    named_clusters[cluster_name] = cluster_videos
                else:
                    # Merge small clusters into "general"
                    if "general" not in named_clusters:
                        named_clusters["general"] = []
                    named_clusters["general"].extend(cluster_videos)
            
            logger.info(f"Created {len(named_clusters)} content clusters")
            return named_clusters
            
        except Exception as e:
            logger.error(f"Error clustering videos: {str(e)}")
            return {"general": videos_data}
    
    def _generate_cluster_name(self, videos: List[Dict], top_features: List[str]) -> str:
        """Generate a meaningful name for a cluster"""
        try:
            # Extract common words from video titles
            all_titles = " ".join([video.get('title', '') for video in videos])
            title_keywords = self.extract_keywords_from_text(all_titles)
            
            # Combine with top TF-IDF features
            all_keywords = title_keywords + top_features
            keyword_counts = Counter(all_keywords)
            
            # Get most common meaningful keywords
            common_keywords = []
            for keyword, count in keyword_counts.most_common(5):
                if len(keyword) > 2 and keyword.isalpha():
                    common_keywords.append(keyword)
            
            if common_keywords:
                # Create cluster name from top 2-3 keywords
                name_parts = common_keywords[:3]
                cluster_name = " ".join(name_parts).title()
                
                # Clean up the name
                cluster_name = re.sub(r'\b(Shorts?|Video|Youtube)\b', '', cluster_name, flags=re.IGNORECASE)
                cluster_name = re.sub(r'\s+', ' ', cluster_name).strip()
                
                if cluster_name:
                    return cluster_name
            
            # Fallback: use most common word from titles
            title_words = []
            for video in videos:
                title = video.get('title', '')
                words = re.findall(r'\b\w{3,}\b', title.lower())
                title_words.extend(words)
            
            if title_words:
                most_common_word = Counter(title_words).most_common(1)[0][0]
                return most_common_word.title() + " Content"
            
            return "Unknown Niche"
            
        except Exception as e:
            logger.error(f"Error generating cluster name: {str(e)}")
            return "Content Cluster"
    
    def analyze_niche_performance(self, niche_videos: List[Dict]) -> Dict[str, Any]:
        """Analyze performance metrics for a niche"""
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
            avg_likes = total_likes / total_videos if total_videos > 0 else 0
            avg_comments = total_comments / total_videos if total_videos > 0 else 0
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
            keyword_counts = Counter(keywords)
            top_keywords = [keyword for keyword, count in keyword_counts.most_common(10)]
            
            return {
                'total_videos': total_videos,
                'unique_channels': len(unique_channels),
                'avg_views': avg_views,
                'avg_views_per_day': avg_views_per_day,
                'avg_engagement_ratio': avg_engagement,
                'avg_viral_score': avg_viral_score,
                'top_videos': top_videos,
                'top_keywords': top_keywords,
                'total_views': total_views,
                'total_engagement': total_likes + total_comments
            }
            
        except Exception as e:
            logger.error(f"Error analyzing niche performance: {str(e)}")
            return {}
    
    def rank_niches(self, niche_analyses: Dict[str, Dict]) -> List[Dict]:
        """Rank niches by their viral potential and performance"""
        try:
            ranked_niches = []
            
            for niche_name, analysis in niche_analyses.items():
                if not analysis:
                    continue
                
                # Calculate ranking score
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
                
                # Content volume component (10%)
                video_count = analysis.get('total_videos', 0)
                if video_count >= 10:
                    score += 10
                elif video_count >= 5:
                    score += 7
                elif video_count >= 3:
                    score += 5
                
                # Channel diversity component (5%)
                channel_count = analysis.get('unique_channels', 0)
                if channel_count >= 5:
                    score += 5
                elif channel_count >= 3:
                    score += 3
                elif channel_count >= 2:
                    score += 2
                
                ranked_niches.append({
                    'niche_name': niche_name,
                    'ranking_score': score,
                    'analysis': analysis
                })
            
            # Sort by ranking score
            ranked_niches.sort(key=lambda x: x['ranking_score'], reverse=True)
            
            logger.info(f"Ranked {len(ranked_niches)} niches")
            return ranked_niches
            
        except Exception as e:
            logger.error(f"Error ranking niches: {str(e)}")
            return []
