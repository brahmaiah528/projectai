import sys
import os

# Set UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(BASE_DIR, 'server')
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import create_app
from database import db
from models import User, Email
from sqlalchemy.exc import IntegrityError
from datetime import datetime

print("=" * 60)
print("  TESTING ALL 3 APPLIED FIXES")
print("=" * 60)

app = create_app()

with app.test_client() as client:
    # ─── TEST FIX 3: Backend Email Validation ─────────────────────────────────
    print("\n--- FIX 3 TEST: Email Format Validation on Registration ---")
    
    # 1. Invalid email
    r_inv = client.post('/api/auth/register', json={'name': 'Bad', 'email': 'notanemail', 'password': 'pass'})
    p1 = (r_inv.status_code == 400)
    print(f"[{'PASS' if p1 else 'FAIL'}] Invalid email 'notanemail' -> Status: {r_inv.status_code} (Expected: 400)")

    # 2. Empty email
    r_empty = client.post('/api/auth/register', json={'name': 'Bad', 'email': '', 'password': 'pass'})
    p2 = (r_empty.status_code == 400)
    print(f"[{'PASS' if p2 else 'FAIL'}] Empty email '' -> Status: {r_empty.status_code} (Expected: 400)")

    # 3. Valid email
    v_email = 'test_valid_reg_2026@example.com'
    with app.app_context():
        u = User.query.filter_by(email=v_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()

    r_valid = client.post('/api/auth/register', json={'name': 'Valid User', 'email': v_email, 'password': 'SecurePass123!'})
    has_token = bool((r_valid.get_json() or {}).get('token'))
    p3 = (r_valid.status_code == 201 and has_token)
    print(f"[{'PASS' if p3 else 'FAIL'}] Valid email '{v_email}' -> Status: {r_valid.status_code} (Expected: 201, Token: {has_token})")

    # 4. Duplicate valid email
    r_dup = client.post('/api/auth/register', json={'name': 'Dup User', 'email': v_email, 'password': 'SecurePass123!'})
    p4 = (r_dup.status_code == 400)
    print(f"[{'PASS' if p4 else 'FAIL'}] Duplicate email '{v_email}' -> Status: {r_dup.status_code} (Expected: 400)")

    # Cleanup
    with app.app_context():
        u = User.query.filter_by(email=v_email).first()
        if u:
            db.session.delete(u)
            db.session.commit()

# ─── TEST FIX 2: SQLite Foreign Keys PRAGMA ──────────────────────────────
print("\n--- FIX 2 TEST: SQLite PRAGMA & Foreign Key Enforcement ---")
with app.app_context():
    conn = db.session.connection().connection
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys;')
    fk = cur.fetchone()[0]
    cur.execute('PRAGMA journal_mode;')
    jm = cur.fetchone()[0]
    cur.execute('PRAGMA busy_timeout;')
    bt = cur.fetchone()[0]

    p_fk = (fk == 1)
    p_jm = (jm == 'wal')
    p_bt = (bt >= 30000)

    print(f"[{'PASS' if p_fk else 'FAIL'}] PRAGMA foreign_keys = {fk} (Expected: 1)")
    print(f"[{'PASS' if p_jm else 'FAIL'}] PRAGMA journal_mode = {jm} (Expected: wal)")
    print(f"[{'PASS' if p_bt else 'FAIL'}] PRAGMA busy_timeout  = {bt} (Expected: >= 30000)")

    # Foreign Key Constraint Enforcement Check
    invalid_email = Email(
        user_id=99999999, message_id='invalid_fk_test_check',
        sender='Test', sender_email='test@example.com',
        recipient='me', subject='Invalid FK', body='Body',
        folder='inbox', category='Others', date=datetime.utcnow()
    )
    db.session.add(invalid_email)
    try:
        db.session.commit()
        print("[FAIL] Invalid FK was allowed by database!")
    except IntegrityError:
        db.session.rollback()
        print("[PASS] Invalid FK (user_id=99999999) was BLOCKED by SQLite IntegrityError!")

# ─── TEST REGRESSION: All Core Features ──────────────────────────────────
print("\n--- REGRESSION TESTS: Core User Features ---")
with app.test_client() as client:
    # Login
    r_login = client.post('/api/auth/login', json={'email': 'user@gmail.com', 'password': 'user123'})
    token = (r_login.get_json() or {}).get('token')
    auth_h = {'Authorization': f'Bearer {token}'} if token else {}
    print(f"[{'PASS' if r_login.status_code == 200 else 'FAIL'}] Login Demo User -> Status: {r_login.status_code}")

    # Inbox
    r_inbox = client.get('/api/emails?folder=inbox', headers=auth_h)
    print(f"[{'PASS' if r_inbox.status_code == 200 else 'FAIL'}] GET /api/emails -> Status: {r_inbox.status_code}")

    # AI Classification
    r_ai = client.post('/api/emails/classify-text', json={
        'subject': 'Your electricity bill due reminder',
        'body': 'Monthly invoice payment of $65.40 is due before Friday.'
    }, headers=auth_h)
    clf_res = (r_ai.get_json() or {}).get('result', {})
    print(f"[{'PASS' if r_ai.status_code == 200 else 'FAIL'}] AI Classify API -> Status: {r_ai.status_code} (Category: {clf_res.get('category')})")

    # Send Email
    r_send = client.post('/api/emails/send', json={
        'recipient': 'test@example.com',
        'subject': 'Regression test email',
        'body': 'Everything is verified and functioning.'
    }, headers=auth_h)
    print(f"[{'PASS' if r_send.status_code == 201 else 'FAIL'}] Send Email API -> Status: {r_send.status_code}")

    # Dashboard Stats
    r_dash = client.get('/api/analytics/dashboard', headers=auth_h)
    print(f"[{'PASS' if r_dash.status_code == 200 else 'FAIL'}] GET /api/analytics/dashboard -> Status: {r_dash.status_code}")

    # Admin RBAC
    r_adm_user = client.get('/api/admin/users', headers=auth_h)
    print(f"[{'PASS' if r_adm_user.status_code == 403 else 'FAIL'}] Admin Block Regular User -> Status: {r_adm_user.status_code} (Expected: 403)")

print("\n" + "=" * 60)
print("  ALL TESTS COMPLETED SUCCESSFULLY")
print("=" * 60)
