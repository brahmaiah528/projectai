import os
import sys

# Add project root and server directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(BASE_DIR, 'server')
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from datetime import datetime, timedelta
from app import create_app
from database import db
from models import User, Email, Prediction, ModelHistory, SystemLog

def init_database(drop_existing=False):
    """Initializes the SQLite database with all tables and seed data."""
    app = create_app()

    with app.app_context():
        # Ensure instance directory exists
        instance_dir = os.path.join(BASE_DIR, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, 'email_classifier.db')

        print("=" * 60)
        print("  AI EMAIL CLASSIFIER - DATABASE INITIALIZATION")
        print("=" * 60)
        print(f"Database Location: {db_path}")

        if drop_existing:
            print("\n[Action] Dropping existing database tables...")
            db.drop_all()
            print("  ✓ All existing tables dropped.")

        print("\n[Action] Creating database tables from models...")
        db.create_all()
        print("  ✓ Created table: 'users'")
        print("  ✓ Created table: 'emails'")
        print("  ✓ Created table: 'predictions'")
        print("  ✓ Created table: 'model_history'")
        print("  ✓ Created table: 'system_logs'")

        # ─── 1. Seed Default Users ───────────────────────────────────────────
        print("\n[Action] Seeding default user accounts...")
        admin = User.query.filter_by(email="admin@gmail.com").first()
        if not admin:
            admin = User(
                name="Admin Administrator",
                email="admin@gmail.com",
                role="admin",
                avatar_url="https://ui-avatars.com/api/?name=Admin+User&background=6366F1&color=fff",
                gmail_connected=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            print("  ✓ Created Admin: admin@gmail.com (Password: admin123)")
        else:
            print("  • Admin user already exists.")

        demo_user = User.query.filter_by(email="user@gmail.com").first()
        if not demo_user:
            demo_user = User(
                name="Demo User",
                email="user@gmail.com",
                role="user",
                avatar_url="https://ui-avatars.com/api/?name=Demo+User&background=10B981&color=fff",
                gmail_connected=True
            )
            demo_user.set_password("user123")
            db.session.add(demo_user)
            print("  ✓ Created Demo User: user@gmail.com (Password: user123)")
        else:
            print("  • Demo user already exists.")

        db.session.commit()

        # ─── 2. Seed Initial Categorized Emails ──────────────────────────────
        print("\n[Action] Seeding categorized emails...")
        sample_emails = [
            ("Chase Bank", "no-reply@chase.com", "Monthly Account Statement Ready", "Your July online banking statement is now ready to view and download.", "inbox", "Banking", 0.98, True, False),
            ("HackerRank", "jobs@hackerrank.com", "Technical Assessment Invitation: Frontend Engineer", "You have been invited to complete a 60-minute technical assessment for TechCorp.", "inbox", "Jobs", 0.96, False, True),
            ("National Exam Portal", "info@nbe.edu", "Admit Card Download Confirmation", "Your hall ticket for the national entrance exam is ready. Download from portal.", "inbox", "Examinations", 0.95, True, True),
            ("Amazon Logistics", "shipment@amazon.com", "Order #99821 Shipped & Out for Delivery", "Your package containing Mechanical Keyboard has shipped and will arrive today.", "inbox", "Purchases", 0.99, True, False),
            ("Crypto Rewards Inc", "claim@free-crypto.org", "CLAIM $10,000 FREE BITCOIN NOW!!", "You won $10,000 BTC. Send bank details immediately to claim your funds!", "spam", "Spam", 0.99, False, False),
            ("DevOps Team", "devops@company.com", "URGENT: Production Database Failover Alert", "Primary DB replica node failed. Engineering team active on war room call.", "inbox", "Important", 0.97, False, True),
            ("Spotify Premium", "promo@spotify.com", "Get 3 Months Premium Free - Special Summer Deal", "Upgrade your audio experience today with 3 months free ad-free music.", "inbox", "Promotions", 0.94, True, False),
            ("LinkedIn Notifications", "notifications@linkedin.com", "Sarah Johnson left a comment on your post", "Sarah Johnson commented: 'Congratulations on the new project!'", "inbox", "Social", 0.92, True, False),
            ("Mom", "mom@family.com", "Sunday Family Dinner Planning", "Hey sweetie, hope your week is going great. Are you coming over for dinner on Sunday?", "inbox", "Personal", 0.96, True, True),
            ("GitHub Security", "security@github.com", "Security Advisory: Update Dependencies", "We detected 2 security advisories in your repository dependencies.", "inbox", "Updates", 0.93, True, False),
            ("Google Accounts", "no-reply@accounts.google.com", "Your Google Verification Code: 492019", "Use 2FA code 492019 to verify your identity. This security code expires in 10 minutes. Do not share it with anyone.", "inbox", "Updates", 0.98, False, True),
            ("General Survey", "survey@insights.org", "Help Us Improve Community Tools", "Take 2 minutes to fill out our developer feedback survey.", "inbox", "Others", 0.88, True, False)
        ]

        for target in [demo_user, admin]:
            if target and Email.query.filter_by(user_id=target.id).count() == 0:
                for i, (snd, snd_em, sub, body, fld, cat, conf, r, st) in enumerate(sample_emails):
                    email = Email(
                        user_id=target.id,
                        message_id=f"msg_init_{target.id}_{i+100}",
                        sender=snd,
                        sender_email=snd_em,
                        recipient=target.email,
                        subject=sub,
                        body=body,
                        folder=fld,
                        category=cat,
                        confidence=conf,
                        is_read=r,
                        is_starred=st,
                        date=datetime.utcnow() - timedelta(hours=i*5)
                    )
                    db.session.add(email)
                print(f"  ✓ Seeded {len(sample_emails)} sample emails for {target.email}")

        # ─── 3. Seed Initial Model History Benchmark ─────────────────────────
        if ModelHistory.query.count() == 0:
            models_benchmark = [
                ("Linear SVM (Ensemble)", 0.9999, 0.9998, 0.9999, 0.9999, 1420),
                ("Logistic Regression", 0.9650, 0.9620, 0.9650, 0.9630, 1420),
                ("Random Forest", 0.9420, 0.9450, 0.9420, 0.9410, 1420),
                ("Multinomial Naive Bayes", 0.9380, 0.9390, 0.9380, 0.9370, 1420),
            ]
            for name, acc, prec, rec, f1, samples in models_benchmark:
                hist = ModelHistory(
                    model_name=name,
                    accuracy=acc,
                    precision=prec,
                    recall=rec,
                    f1_score=f1,
                    dataset_samples=samples,
                    trained_at=datetime.utcnow()
                )
                db.session.add(hist)
            print("  ✓ Seeded ML Model benchmark history metrics.")

        # ─── 4. Seed Initial System Log ──────────────────────────────────────
        log = SystemLog(
            user_id=admin.id if admin else None,
            user_email=admin.email if admin else "system",
            action="DATABASE_INIT",
            details="Database tables and initial seeds created successfully.",
            ip_address="127.0.0.1"
        )
        db.session.add(log)
        db.session.commit()

        # ─── 5. Print Summary ────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  DATABASE STATUS SUMMARY")
        print("=" * 60)
        print(f"  • Users Table:        {User.query.count()} accounts")
        print(f"  • Emails Table:       {Email.query.count()} emails")
        print(f"  • Model History:      {ModelHistory.query.count()} benchmark records")
        print(f"  • System Logs:        {SystemLog.query.count()} log records")
        print("=" * 60)
        print("  ✓ Database is ready and operational!\n")

if __name__ == '__main__':
    drop = '--reset' in sys.argv or '--drop' in sys.argv
    init_database(drop_existing=drop)
