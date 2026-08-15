import os
import sqlite3
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

    # For SQLite: use WAL journal mode and StaticPool so background threads
    # can write concurrently without hitting "database is locked".
    # WAL allows one writer + multiple readers simultaneously.
    # NullPool avoids cross-thread connection reuse issues in Flask dev server.
    if not (_custom_db and not _custom_db.startswith('sqlite')):
        db_file_path = _db_path
        def _sqlite_creator(path=db_file_path):
            conn = sqlite3.connect(
                path,
                timeout=60,           # wait up to 60s before raising OperationalError
                check_same_thread=False
            )
            # WAL mode: one writer + multiple readers simultaneously — eliminates most locks
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA foreign_keys=ON")
            # Slightly relax fsync for performance (safe: WAL already protects integrity)
            conn.execute("PRAGMA synchronous=NORMAL")
            # Bigger page cache = fewer disk reads
            conn.execute("PRAGMA cache_size=-32000")  # ~32MB cache
            conn.commit()
            return conn

        from sqlalchemy.pool import NullPool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'poolclass': NullPool,
            'creator': _sqlite_creator,
        }
    else:
        # For Postgres / other production DBs — use standard connection pool
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
    
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

    # Localhost-only URL configuration
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3001')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5001/api/auth/google/callback')
    GOOGLE_LOGIN_REDIRECT_URI = os.getenv('GOOGLE_LOGIN_REDIRECT_URI', 'http://localhost:5001/api/auth/google/login-callback')

    MODEL_DIR = os.path.join(BASE_DIR, 'model')

    # SMTP Email Sending
    SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')
    SMTP_APP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '')
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 465   # SSL port
