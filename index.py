from app import app

# This is the entry point for Vercel
def handler(request):
    return app(request.environ, lambda *args: None)

# Export the Flask app for Vercel
application = app