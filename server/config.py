import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-jwt-secret-key-987654321')
    
    # Ensure instance directory exists for SQLite database file
    _instance_dir = os.path.join(BASE_DIR, 'instance')
    os.makedirs(_instance_dir, exist_ok=True)
    _db_path = os.path.abspath(os.path.join(_instance_dir, 'email_classifier.db'))
    
    _custom_db = os.getenv('DATABASE_URL') or os.getenv('DATABASE_URI')
    if _custom_db and not _custom_db.startswith('sqlite'):
        if _custom_db.startswith('postgres://'):
            _custom_db = _custom_db.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _custom_db
    else:
        # Absolute Unix paths starting with '/' need 4 slashes in SQLAlchemy SQLite URI
        if _db_path.startswith('/'):
            SQLALCHEMY_DATABASE_URI = f"sqlite:////{_db_path.lstrip('/')}"
        else:
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 30
        }
    }
    
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    _render_url = os.getenv('RENDER_EXTERNAL_URL', 'https://ai-email-classification.onrender.com').rstrip('/')
    
    _frontend_env = os.getenv('FRONTEND_URL', '').rstrip('/')
    if not _frontend_env or 'localhost' in _frontend_env:
        FRONTEND_URL = 'https://projectai1.vercel.app'
    else:
        FRONTEND_URL = _frontend_env

    _g_redir = os.getenv('GOOGLE_REDIRECT_URI', '').rstrip('/')
    if not _g_redir or 'localhost' in _g_redir:
        GOOGLE_REDIRECT_URI = f"{_render_url}/api/auth/google/callback"
    else:
        GOOGLE_REDIRECT_URI = _g_redir

    _g_login_redir = os.getenv('GOOGLE_LOGIN_REDIRECT_URI', '').rstrip('/')
    if not _g_login_redir or 'localhost' in _g_login_redir:
        GOOGLE_LOGIN_REDIRECT_URI = f"{_render_url}/api/auth/google/login-callback"
    else:
        GOOGLE_LOGIN_REDIRECT_URI = _g_login_redir
    
    MODEL_DIR = os.path.join(BASE_DIR, 'model')

    # SMTP Email Sending
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_APP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '')
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465   # SSL (port 465) — more reliable than STARTTLS (587) behind firewalls
