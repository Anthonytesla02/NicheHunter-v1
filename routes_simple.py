import threading
import time
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, redirect, url_for, make_response
from app_simple import app, db
from models import AnalysisSession, VideoData, NicheResult
from youtube_analyzer import YouTubeAnalyzer
from simple_face_detector import SimpleFaceDetector
from simple_niche_analyzer import SimpleNicheAnalyzer
from config import Config
import json
import csv
import io

# Global state for analysis progress
analysis_states = {}

@app.route('/')
def index():
    """Main dashboard page"""
    recent_sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).limit(5).all()
    return render_template('index.html', recent_sessions=recent_sessions)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    """Analysis configuration and execution page"""
    if request.method == 'POST':
        # Get form data
        session_name = request.form.get('session_name', f'Analysis {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        
        # Get analysis parameters
        params = {}
        for key, default_value in Config.DEFAULT_PARAMS.items():
            form_value = request.form.get(key)
            if form_value:
                if isinstance(default_value, int):
                    params[key] = int(form_value)
                elif isinstance(default_value, float):
                    params[key] = float(form_value)
                elif isinstance(default_value, bool):
                    params[key] = form_value.lower() in ['true', '1', 'on']
                else:
                    params[key] = form_value
            else:
                params[key] = default_value
        
        # Create analysis session
        session = AnalysisSession(
            session_name=session_name,
            status='pending'
        )
        session.set_parameters(params)
        db.session.add(session)
        db.session.commit()
        
        # Start analysis in background thread
        thread = threading.Thread(target=run_analysis, args=(session.id, params))
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('results', session_id=session.id))
    
    return render_template('analysis.html', 
                         default_params=Config.DEFAULT_PARAMS,
                         search_queries=Config.SEARCH_QUERIES)

@app.route('/results/<int:session_id>')
def results(session_id):
    """Display analysis results"""
    session = AnalysisSession.query.get_or_404(session_id)
    niches = NicheResult.query.filter_by(session_id=session_id).order_by(NicheResult.viral_score.desc()).all()
    videos = VideoData.query.filter_by(session_id=session_id).order_by(VideoData.viral_score.desc()).limit(20).all()
    
    return render_template('results.html', 
                         session=session, 
                         niches=niches, 
                         videos=videos)

@app.route('/analysis-status/<int:session_id>')
def analysis_status(session_id):
    """API endpoint to check analysis status"""
    session = AnalysisSession.query.get_or_404(session_id)
    
    # Get current analysis state
    state = analysis_states.get(session_id, {
        'status': session.status,
        'progress': 0,
        'videos_processed': session.total_videos_analyzed,
        'channels_analyzed': 0,
        'niches_found': session.total_niches_identified
    })
    
    return jsonify(state)

@app.route('/export-csv/<int:session_id>')
def export_csv(session_id):
    """Export analysis results to CSV"""
    session = AnalysisSession.query.get_or_404(session_id)
    videos = VideoData.query.filter_by(session_id=session_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Video ID', 'Title', 'Channel', 'Views', 'Likes', 'Comments',
        'Duration (seconds)', 'Published Date', 'Viral Score', 'Views/Day',
        'Has Face', 'Face Confidence', 'Engagement Ratio'
    ])
    
    # Write data
    for video in videos:
        writer.writerow([
            video.video_id, video.title, video.channel_title,
            video.view_count, video.like_count, video.comment_count,
            video.duration_seconds, video.published_at.strftime('%Y-%m-%d') if video.published_at else '',
            video.viral_score, video.views_per_day,
            video.has_face, video.face_confidence, video.engagement_ratio
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=analysis_{session_id}.csv'
    
    return response

def run_analysis(session_id: int, params: dict):
    """Run the complete analysis in background"""
    try:
        # Initialize components
        youtube_analyzer = YouTubeAnalyzer()
        face_detector = SimpleFaceDetector()
        niche_analyzer = SimpleNicheAnalyzer()
        
        # Update session status
        session = AnalysisSession.query.get(session_id)
        session.status = 'running'
        db.session.commit()
        
        # Initialize analysis state
        analysis_states[session_id] = {
            'status': 'Starting analysis...',
            'progress': 0,
            'videos_processed': 0,
            'channels_analyzed': 0,
            'niches_found': 0
        }
        
        # Step 1: Search for videos
        analysis_states[session_id].update({
            'status': 'Searching for videos...',
            'progress': 10
        })
        
        search_queries = Config.SEARCH_QUERIES[:5]  # Limit for Vercel
        all_videos = []
        
        for i, query in enumerate(search_queries):
            analysis_states[session_id].update({
                'status': f'Searching: {query}',
                'progress': 10 + (i / len(search_queries)) * 20
            })
            
            videos = youtube_analyzer.search_shorts(
                query=query,
                days_back=params.get('days_back_to_search', 7),
                max_results=min(params.get('max_results_per_query', 20), 20)  # Limit for Vercel
            )
            all_videos.extend(videos)
            time.sleep(0.1)  # Rate limiting
        
        # Remove duplicates
        unique_videos = {v['video_id']: v for v in all_videos}.values()
        all_videos = list(unique_videos)
        
        # Step 2: Get detailed video information
        analysis_states[session_id].update({
            'status': 'Getting video details...',
            'progress': 30
        })
        
        video_ids = [v['video_id'] for v in all_videos]
        detailed_videos = youtube_analyzer.get_video_details(video_ids)
        
        # Step 3: Get channel information
        analysis_states[session_id].update({
            'status': 'Analyzing channels...',
            'progress': 45
        })
        
        channel_ids = list(set(v['channel_id'] for v in all_videos if v.get('channel_id')))
        channel_details = youtube_analyzer.get_channel_details(channel_ids)
        
        # Step 4: Face detection and viral scoring
        analysis_states[session_id].update({
            'status': 'Detecting faces and calculating scores...',
            'progress': 60
        })
        
        processed_videos = []
        for i, video in enumerate(all_videos):
            # Face detection
            thumbnail_url = video.get('thumbnail_url', '')
            has_face, face_confidence = face_detector.detect_faces_in_url(thumbnail_url)
            
            # Get detailed video data
            video_details = detailed_videos.get(video['video_id'], {})
            channel_data = channel_details.get(video.get('channel_id'), {})
            
            # Calculate viral metrics
            viral_metrics = youtube_analyzer.calculate_viral_metrics(video_details, channel_data)
            
            # Combine all data
            processed_video = {
                **video,
                **video_details,
                'has_face': has_face,
                'face_confidence': face_confidence,
                **viral_metrics
            }
            processed_videos.append(processed_video)
            
            # Update progress
            analysis_states[session_id].update({
                'videos_processed': i + 1,
                'progress': 60 + ((i + 1) / len(all_videos)) * 20
            })
        
        # Step 5: Cluster videos into niches
        analysis_states[session_id].update({
            'status': 'Identifying niches...',
            'progress': 80
        })
        
        niche_clusters = niche_analyzer.cluster_videos_by_content(processed_videos)
        
        # Step 6: Analyze niche performance
        analysis_states[session_id].update({
            'status': 'Analyzing niche performance...',
            'progress': 90
        })
        
        niche_analyses = {}
        for niche_name, niche_videos in niche_clusters.items():
            analysis = niche_analyzer.analyze_niche_performance(niche_videos)
            niche_analyses[niche_name] = analysis
        
        # Rank niches
        ranked_niches = niche_analyzer.rank_niches(niche_analyses)
        
        # Step 7: Save results to database
        analysis_states[session_id].update({
            'status': 'Saving results...',
            'progress': 95
        })
        
        # Save video data
        for video in processed_videos:
            video_data = VideoData(
                session_id=session_id,
                video_id=video.get('video_id', ''),
                title=video.get('title', ''),
                channel_id=video.get('channel_id', ''),
                channel_title=video.get('channel_title', ''),
                published_at=video.get('published_at'),
                duration_seconds=video.get('duration_seconds', 0),
                view_count=video.get('view_count', 0),
                like_count=video.get('like_count', 0),
                comment_count=video.get('comment_count', 0),
                thumbnail_url=video.get('thumbnail_url', ''),
                has_face=video.get('has_face', False),
                face_confidence=video.get('face_confidence', 0.0),
                viral_score=video.get('viral_score', 0.0),
                views_per_day=video.get('views_per_day', 0.0),
                engagement_ratio=video.get('engagement_ratio', 0.0)
            )
            db.session.add(video_data)
        
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
            db.session.add(niche_result)
        
        # Update session
        session.status = 'completed'
        session.total_videos_analyzed = len(processed_videos)
        session.total_niches_identified = len(ranked_niches)
        db.session.commit()
        
        # Final status update
        analysis_states[session_id].update({
            'status': 'completed',
            'progress': 100,
            'niches_found': len(ranked_niches)
        })
        
    except Exception as e:
        # Handle errors
        session = AnalysisSession.query.get(session_id)
        session.status = 'failed'
        db.session.commit()
        
        analysis_states[session_id] = {
            'status': 'failed',
            'progress': 0,
            'error': str(e)
        }

@app.route('/sessions')
def sessions():
    """List all analysis sessions"""
    sessions = AnalysisSession.query.order_by(AnalysisSession.created_at.desc()).all()
    return render_template('sessions.html', sessions=sessions)

@app.route('/delete-session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    """Delete an analysis session and all related data"""
    # Delete related data
    VideoData.query.filter_by(session_id=session_id).delete()
    NicheResult.query.filter_by(session_id=session_id).delete()
    
    # Delete session
    session = AnalysisSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    
    return redirect(url_for('sessions'))