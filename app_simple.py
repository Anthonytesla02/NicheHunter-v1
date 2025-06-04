import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.INFO)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    
    # Use SQLite for Vercel compatibility
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///youtube_analyzer.db"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize the app with the extension
    db.init_app(app)
    
    # Import routes after app initialization
    from routes_simple import *
    
    with app.app_context():
        # Import models to ensure tables are created
        import models
        db.create_all()
    
    return app

# Create app instance
app = create_app()

# Export for Vercel
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)