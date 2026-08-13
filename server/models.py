from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin' or 'user'
    avatar_url = db.Column(db.String(255), nullable=True)
    gmail_connected = db.Column(db.Boolean, default=False)
    google_tokens = db.Column(db.Text, nullable=True) # JSON stored OAuth credentials
    # Last Gmail history ID — used for incremental/delta sync to avoid re-fetching all 500 emails
    gmail_history_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    emails = db.relationship('Email', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "gmail_connected": self.gmail_connected,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Email(db.Model):
    __tablename__ = 'emails'
    __table_args__ = (
        # Composite index for the most common query: user + folder + date sort
        db.Index('ix_emails_user_folder_date', 'user_id', 'folder', 'date'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message_id = db.Column(db.String(200), unique=True, nullable=True)
    # Stores the real Gmail message ID (separate from our local message_id for sent/draft emails)
    gmail_message_id = db.Column(db.String(200), nullable=True, index=True)
    sender = db.Column(db.String(150), nullable=False)
    sender_email = db.Column(db.String(150), nullable=False)
    recipient = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    snippet = db.Column(db.String(500), nullable=True)
    folder = db.Column(db.String(30), default='inbox', index=True) # inbox, sent, drafts, spam, trash, starred, snoozed
    category = db.Column(db.String(50), default='Others', index=True)
    confidence = db.Column(db.Float, default=0.0)
    is_read = db.Column(db.Boolean, default=False)
    is_starred = db.Column(db.Boolean, default=False)
    # Maps to Gmail IMPORTANT label (auto-set by Gmail based on user behavior)
    is_important = db.Column(db.Boolean, default=False)
    # When this email should resurface from snooze (NULL = not snoozed)
    snoozed_until = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def list_dict(self):
        """Fast serialization for email LIST view — skips ML priority_highlight computation.
        Use this for GET /api/emails to return 470 emails instantly instead of running 470 ML calls."""
        is_snoozed = bool(self.snoozed_until and self.snoozed_until > datetime.utcnow())
        body_text = self.body or ''
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "gmail_message_id": self.gmail_message_id,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": body_text,
            "snippet": self.snippet or (body_text[:120] + "..." if len(body_text) > 120 else body_text),
            "folder": self.folder,
            "category": self.category,
            "confidence": round(self.confidence * 100, 1) if self.confidence else 0.0,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
            "is_important": self.is_important,
            "is_snoozed": is_snoozed,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "priority_highlight": None,  # Computed on-demand in detail view only
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def to_dict(self):
        """Full serialization with ML priority highlight — use only for single email detail view."""
        from services.ml_service import MLService
        priority_highlight = MLService.extract_priority_highlight(self.subject, self.body, self.category)
        is_snoozed = bool(self.snoozed_until and self.snoozed_until > datetime.utcnow())
        body_text = self.body or ''
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message_id": self.message_id,
            "gmail_message_id": self.gmail_message_id,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": body_text,
            "snippet": self.snippet or (body_text[:120] + "..." if len(body_text) > 120 else body_text),
            "folder": self.folder,
            "category": self.category,
            "confidence": round(self.confidence * 100, 1) if self.confidence else 0.0,
            "is_read": self.is_read,
            "is_starred": self.is_starred,
            "is_important": self.is_important,
            "is_snoozed": is_snoozed,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "priority_highlight": priority_highlight,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Integer, db.ForeignKey('emails.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    model_used = db.Column(db.String(100), default='Logistic Regression')
    predicted_category = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    probabilities_json = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email_id": self.email_id,
            "user_id": self.user_id,
            "model_used": self.model_used,
            "predicted_category": self.predicted_category,
            "confidence": round(self.confidence * 100, 1),
            "probabilities": json.loads(self.probabilities_json) if self.probabilities_json else {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class ModelHistory(db.Model):
    __tablename__ = 'model_history'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    dataset_samples = db.Column(db.Integer, default=0)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "accuracy": round(self.accuracy * 100, 2),
            "precision": round(self.precision * 100, 2),
            "recall": round(self.recall * 100, 2),
            "f1_score": round(self.f1_score * 100, 2),
            "dataset_samples": self.dataset_samples,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None
        }

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    user_email = db.Column(db.String(120), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email or 'System',
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address or '127.0.0.1',
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
