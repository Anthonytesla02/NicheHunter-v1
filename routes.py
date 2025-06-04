import os
import csv
import json
import logging
from datetime import datetime
from flask import render_template, request, jsonify, send_file, flash, redirect, url_for
from app import app, db
from models import AnalysisSession, NicheResult, VideoData
from youtube_analyzer import YouTubeAnalyzer
from face_detector import FaceDetector
from niche_analyzer import NicheAnalyzer
from config import Config
import threading
import tempfile

logger = logging.getLogger(__name__)

# Global analysis state
analysis_state = {
    'running': False,
    'progress': 0,
    'status': 'idle',
    'current_session_id': None
}

@app.route('/')
def index():
    """Main dashboard page"""
    recent_sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).limit(5).all()
    return render_template('index.html', recent_sessions=recent_sessions)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    """Analysis configuration and execution page"""
    if request.method == 'GET':
        return render_template('analysis.html', 
                             default_params=Config.DEFAULT_PARAMS,
                             search_queries=Config.SEARCH_QUERIES)
    
    try:
        # Get parameters from form
        params = {}
        params['session_name'] = request.form.get('session_name', f'Analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        params['max_duration_seconds'] = int(request.form.get('max_duration_seconds', 60))
        params['min_views_per_day'] = int(request.form.get('min_views_per_day', 50000))
        params['min_monthly_views'] = int(request.form.get('min_monthly_views', 10000000))
        params['max_channel_videos'] = int(request.form.get('max_channel_videos', 20))
        params['max_channel_age_days'] = int(request.form.get('max_channel_age_days', 30))
        params['min_weekly_uploads'] = int(request.form.get('min_weekly_uploads', 4))
        params['min_video_views_7days'] = int(request.form.get('min_video_views_7days', 50000))
        params['days_back_to_search'] = int(request.form.get('days_back_to_search', 7))
        params['face_detection_threshold'] = float(request.form.get('face_detection_threshold', 0.7))
        params['max_face_percentage'] = int(request.form.get('max_face_percentage', 10))
        params['search_query'] = request.form.get('search_query', '')
        params['faceless_only'] = request.form.get('faceless_only') == 'on'
        params['max_results_per_query'] = int(request.form.get('max_results_per_query', 50))
        
        # Create new analysis session
        session = AnalysisSession(
            session_name=params['session_name'],
            status='pending'
        )
        session.set_parameters(params)
        db.session.add(session)
        db.session.commit()
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(
            target=run_analysis,
            args=(session.id, params)
        )
        analysis_thread.daemon = True
        analysis_thread.start()
        
        flash('Analysis started successfully!', 'success')
        return redirect(url_for('results', session_id=session.id))
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        flash(f'Error starting analysis: {str(e)}', 'error')
        return redirect(url_for('analyze'))

@app.route('/results/<int:session_id>')
def results(session_id):
    """Display analysis results"""
    session = AnalysisSession.query.get_or_404(session_id)
    niches = NicheResult.query.filter_by(session_id=session_id).order_by(NicheResult.viral_score.desc()).all()
    
    return render_template('results.html', 
                         session=session, 
                         niches=niches,
                         analysis_state=analysis_state)

@app.route('/api/analysis_status/<int:session_id>')
def analysis_status(session_id):
    """API endpoint to check analysis status"""
    session = AnalysisSession.query.get_or_404(session_id)
    
    return jsonify({
        'status': session.status,
        'progress': analysis_state.get('progress', 0),
        'total_videos_analyzed': session.total_videos_analyzed,
        'total_channels_found': session.total_channels_found,
        'total_niches_identified': session.total_niches_identified,
        'current_status': analysis_state.get('status', 'idle')
    })

@app.route('/export_csv/<int:session_id>')
def export_csv(session_id):
    """Export analysis results to CSV"""
    try:
        session = AnalysisSession.query.get_or_404(session_id)
        niches = NicheResult.query.filter_by(session_id=session_id).all()
        videos = VideoData.query.filter_by(session_id=session_id).all()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='')
        
        with open(temp_file.name, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write niches data
            writer.writerow(['=== NICHES ANALYSIS ==='])
            writer.writerow(['Niche Name', 'Total Videos', 'Avg Views/Day', 'Avg Engagement Ratio', 'Viral Score', 'Top Keywords'])
            
            for niche in niches:
                keywords = ', '.join(niche.get_keywords()[:5])
                writer.writerow([
                    niche.niche_name,
                    niche.total_videos,
                    f"{niche.avg_views_per_day:.0f}",
                    f"{niche.avg_engagement_ratio:.4f}",
                    f"{niche.viral_score:.2f}",
                    keywords
                ])
            
            writer.writerow([])  # Empty row
            
            # Write videos data
            writer.writerow(['=== VIDEOS ANALYSIS ==='])
            writer.writerow(['Video ID', 'Title', 'Channel', 'Views', 'Views/Day', 'Engagement Ratio', 'Viral Score', 'Has Face', 'Thumbnail URL'])
            
            for video in videos:
                writer.writerow([
                    video.video_id,
                    video.title,
                    video.channel_title,
                    video.view_count,
                    f"{video.views_per_day:.0f}",
                    f"{video.engagement_ratio:.4f}",
                    f"{video.viral_score:.2f}",
                    'Yes' if video.has_face else 'No',
                    video.thumbnail_url
                ])
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'{session.session_name}_results.csv',
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        flash(f'Error exporting CSV: {str(e)}', 'error')
        return redirect(url_for('results', session_id=session_id))

def run_analysis(session_id: int, params: dict):
    """Run the complete analysis in background"""
    global analysis_state
    
    try:
        analysis_state['running'] = True
        analysis_state['current_session_id'] = session_id
        analysis_state['progress'] = 0
        analysis_state['status'] = 'Initializing...'
        
        # Update session status
        with app.app_context():
            session = AnalysisSession.query.get(session_id)
            session.status = 'running'
            db.session.commit()
            
            # Initialize analyzers
            youtube_analyzer = YouTubeAnalyzer()
            face_detector = FaceDetector()
            niche_analyzer = NicheAnalyzer()
            
            analysis_state['status'] = 'Searching for videos...'
            analysis_state['progress'] = 10
            
            # Collect all videos
            all_videos = []
            search_queries = Config.SEARCH_QUERIES if not params.get('search_query') else [params['search_query']]
            
            for i, query in enumerate(search_queries):
                analysis_state['status'] = f'Searching: {query}'
                videos = youtube_analyzer.search_shorts(
                    query, 
                    params['days_back_to_search'], 
                    params['max_results_per_query']
                )
                all_videos.extend(videos)
                analysis_state['progress'] = 10 + (i + 1) * 20 // len(search_queries)
            
            logger.info(f"Found {len(all_videos)} videos total")
            
            # Get video details
            analysis_state['status'] = 'Analyzing video performance...'
            analysis_state['progress'] = 30
            
            video_ids = [v['video_id'] for v in all_videos]
            video_details = youtube_analyzer.get_video_details(video_ids)
            
            # Get channel details
            analysis_state['status'] = 'Analyzing channels...'
            analysis_state['progress'] = 40
            
            channel_ids = list(set(v['channel_id'] for v in all_videos))
            channel_details = youtube_analyzer.get_channel_details(channel_ids)
            
            # Filter and analyze videos
            analysis_state['status'] = 'Filtering viral content...'
            analysis_state['progress'] = 50
            
            qualified_videos = []
            
            for video in all_videos:
                video_id = video['video_id']
                channel_id = video['channel_id']
                
                if video_id not in video_details or channel_id not in channel_details:
                    continue
                
                video_stats = video_details[video_id]
                channel_stats = channel_details[channel_id]
                
                # Calculate metrics
                metrics = youtube_analyzer.calculate_viral_metrics(video_stats, channel_stats)
                
                # Apply filters
                if (video_stats['view_count'] > 0 and 
                    metrics['views_per_day'] >= params['min_views_per_day'] and
                    channel_stats['video_count'] <= params['max_channel_videos'] and
                    metrics['channel_age_days'] <= params['max_channel_age_days']):
                    
                    # Face detection if required
                    has_face = False
                    face_confidence = 0.0
                    
                    if params['faceless_only']:
                        analysis_state['status'] = f'Checking faces in video: {video["title"][:50]}...'
                        has_face, face_confidence = face_detector.detect_faces_in_url(video['thumbnail_url'])
                        
                        if has_face and face_confidence > params['face_detection_threshold']:
                            continue  # Skip videos with faces
                    
                    # Combine all data
                    combined_video = {
                        **video,
                        **video_stats,
                        **metrics,
                        'has_face': has_face,
                        'face_confidence': face_confidence,
                        'channel_stats': channel_stats
                    }
                    qualified_videos.append(combined_video)
            
            logger.info(f"Qualified {len(qualified_videos)} videos for analysis")
            
            # Save video data
            analysis_state['status'] = 'Saving video data...'
            analysis_state['progress'] = 60
            
            for video in qualified_videos:
                video_record = VideoData(
                    session_id=session_id,
                    video_id=video['video_id'],
                    title=video['title'],
                    channel_id=video['channel_id'],
                    channel_title=video['channel_title'],
                    published_at=datetime.fromisoformat(video['published_at'].replace('Z', '+00:00')),
                    duration_seconds=video['duration_seconds'],
                    view_count=video['view_count'],
                    like_count=video['like_count'],
                    comment_count=video['comment_count'],
                    thumbnail_url=video['thumbnail_url'],
                    has_face=video['has_face'],
                    face_confidence=video['face_confidence'],
                    viral_score=video['viral_score'],
                    views_per_day=video['views_per_day'],
                    engagement_ratio=video['engagement_ratio']
                )
                db.session.add(video_record)
            
            # Cluster videos into niches
            analysis_state['status'] = 'Identifying niches...'
            analysis_state['progress'] = 70
            
            niche_clusters = niche_analyzer.cluster_videos_by_content(qualified_videos)
            
            # Analyze each niche
            analysis_state['status'] = 'Analyzing niche performance...'
            analysis_state['progress'] = 80
            
            niche_analyses = {}
            for niche_name, niche_videos in niche_clusters.items():
                analysis = niche_analyzer.analyze_niche_performance(niche_videos)
                niche_analyses[niche_name] = analysis
            
            # Rank niches
            analysis_state['status'] = 'Ranking niches...'
            analysis_state['progress'] = 90
            
            ranked_niches = niche_analyzer.rank_niches(niche_analyses)
            
            # Save niche results
            for rank, niche_data in enumerate(ranked_niches[:10], 1):
                niche_name = niche_data['niche_name']
                analysis = niche_data['analysis']
                
                niche_result = NicheResult(
                    session_id=session_id,
                    niche_name=niche_name,
                    total_videos=analysis.get('total_videos', 0),
                    avg_views_per_day=analysis.get('avg_views_per_day', 0),
                    avg_engagement_ratio=analysis.get('avg_engagement_ratio', 0),
                    viral_score=niche_data['ranking_score']
                )
                
                niche_result.set_keywords(analysis.get('top_keywords', []))
                
                # Get top channels for this niche
                niche_videos = niche_clusters.get(niche_name, [])
                channel_data = []
                for video in niche_videos[:5]:  # Top 5 videos
                    channel_data.append({
                        'channel_title': video.get('channel_title', ''),
                        'channel_id': video.get('channel_id', ''),
                        'video_count': video.get('channel_stats', {}).get('video_count', 0),
                        'subscriber_count': video.get('channel_stats', {}).get('subscriber_count', 0)
                    })
                
                niche_result.set_top_channels(channel_data)
                niche_result.set_top_videos(analysis.get('top_videos', []))
                
                db.session.add(niche_result)
            
            # Update session with final results
            session.status = 'completed'
            session.total_videos_analyzed = len(qualified_videos)
            session.total_channels_found = len(set(v['channel_id'] for v in qualified_videos))
            session.total_niches_identified = len(ranked_niches)
            
            db.session.commit()
            
            analysis_state['status'] = 'Analysis completed!'
            analysis_state['progress'] = 100
            
            logger.info(f"Analysis completed for session {session_id}")
            
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        with app.app_context():
            session = AnalysisSession.query.get(session_id)
            session.status = 'failed'
            db.session.commit()
        
        analysis_state['status'] = f'Error: {str(e)}'
        analysis_state['running'] = False

@app.route('/sessions')
def sessions():
    """List all analysis sessions"""
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    return render_template('sessions.html', sessions=sessions)

@app.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    """Delete an analysis session and all related data"""
    try:
        session = AnalysisSession.query.get_or_404(session_id)
        
        # Delete related data
        VideoData.query.filter_by(session_id=session_id).delete()
        NicheResult.query.filter_by(session_id=session_id).delete()
        
        # Delete session
        db.session.delete(session)
        db.session.commit()
        
        flash(f'Session "{session.session_name}" deleted successfully!', 'success')
        
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        flash(f'Error deleting session: {str(e)}', 'error')
    
    return redirect(url_for('sessions'))
