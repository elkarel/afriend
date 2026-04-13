"""
Entry point for running the Flask development server directly.

For production use a WSGI server instead:
    gunicorn "app.factory:create_app()" --bind 0.0.0.0:5000 --workers 4
"""
from app.config import Config
from app.factory import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
