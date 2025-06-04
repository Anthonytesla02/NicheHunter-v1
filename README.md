# YouTube Shorts Niche Analyzer

A powerful web application that analyzes YouTube Shorts to identify viral niches and trending content patterns.

## Features

- **Viral Content Analysis**: Scan YouTube Shorts for high-performing content
- **Niche Identification**: Use machine learning to cluster videos by content similarity
- **Face Detection**: Identify faceless content opportunities
- **Performance Metrics**: Calculate viral scores and engagement ratios
- **Export Results**: Download analysis results as CSV

## Deployment Options

### Option 1: Replit (Recommended)
This application is already configured and running on Replit. Simply use the current environment.

### Option 2: Railway
1. Connect your GitHub repository to Railway
2. Railway will automatically detect the Python application
3. Set environment variables for API keys

### Option 3: Render
1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - Build Command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
   - Start Command: `gunicorn app:app`

### Option 4: DigitalOcean App Platform
1. Create a new app from your GitHub repository
2. Configure as a Python app
3. Set build and run commands

## Required Environment Variables

- `YOUTUBE_API_KEY`: Your YouTube Data API v3 key
- `DATABASE_URL`: PostgreSQL database URL (optional, defaults to SQLite)

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Download spaCy model: `python -m spacy download en_core_web_sm`
3. Set environment variables
4. Run: `python main.py`

## Why Vercel Won't Work

Vercel's serverless functions have strict limits:
- 50MB deployment size limit
- Limited runtime for heavy computations
- No support for OpenCV and large ML libraries
- No persistent file system for model storage

The dependencies required (OpenCV, spaCy, scikit-learn) exceed these limits.