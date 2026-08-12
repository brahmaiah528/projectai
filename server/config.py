import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-jwt-secret-key-987654321')
    
    # Absolute path to primary SQLite database file
    _db_path = os.path.abspath(os.path.join(BASE_DIR, 'instance', 'email_classifier.db'))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 30
        }
    }
    
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5001/api/auth/google/callback')
    GOOGLE_LOGIN_REDIRECT_URI = os.getenv('GOOGLE_LOGIN_REDIRECT_URI', 'http://localhost:5001/api/auth/google/login-callback')
    
    MODEL_DIR = os.path.join(BASE_DIR, 'model')

    # SMTP Email Sending
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_APP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '')
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465   # SSL (port 465) — more reliable than STARTTLS (587) behind firewalls
