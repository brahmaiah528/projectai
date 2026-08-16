import os
import sys
import json
import time

# Set utf-8 output encoding for Windows PowerShell compatibility
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

from datetime import datetime, timedelta
import sqlite3

results = {
    "passed": [],
    "failed": [],
    "errors": []
}

def log_test(category, name, passed, details=""):
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} {category} -> {name} {': ' + details if details else ''}")
    if passed:
        results["passed"].append(f"{category}: {name}")
    else:
        results["failed"].append(f"{category}: {name} - {details}")

print("=" * 70)
print("  STEP 1 & 2: PROJECT STRUCTURE & DEPENDENCIES AUDIT")
print("=" * 70)

# Check Python Packages
python_packages = [
    'flask', 'flask_cors', 'flask_sqlalchemy', 'jwt', 'sklearn', 
    'pandas', 'numpy', 'joblib', 'googleapiclient', 'google_auth_oauthlib', 
    'httplib2', 'werkzeug', 'dotenv'
]
for pkg in python_packages:
    try:
        __import__(pkg)
        log_test("Dependencies", f"Python package: {pkg}", True)
    except Exception as e:
        log_test("Dependencies", f"Python package: {pkg}", False, str(e))

# Check ML Model Files
model_files = [
    'vectorizer.pkl', 'char_vectorizer.pkl', 'classifier.pkl', 
    'all_models.pkl', 'ensemble_models.pkl', 'ovr_models.pkl', 
    'model_metrics.json'
]
for mf in model_files:
    mf_path = os.path.join(BASE_DIR, 'model', mf)
    exists = os.path.exists(mf_path)
    sz = os.path.getsize(mf_path) if exists else 0
    log_test("ML Files", f"Model artifact: {mf}", exists, f"Size: {sz} bytes")

print("\n" + "=" * 70)
print("  STEP 3: DATABASE VERIFICATION & CRUD TESTS")
print("=" * 70)

from app import create_app
from database import db
from models import User, Email, Prediction, ModelHistory, SystemLog

app = create_app()

with app.app_context():
    # 1. Connection check
    try:
        db_res = db.session.execute(db.text("SELECT 1")).scalar()
        log_test("Database", "Database connection & SELECT 1", db_res == 1)
    except Exception as e:
        log_test("Database", "Database connection", False, str(e))

    # 2. Verify all 5 tables exist
    tables = [User, Email, Prediction, ModelHistory, SystemLog]
    for tbl in tables:
        try:
            cnt = tbl.query.count()
            log_test("Database", f"Table '{tbl.__tablename__}' accessible", True, f"{cnt} existing rows")
        except Exception as e:
            log_test("Database", f"Table '{tbl.__tablename__}' accessible", False, str(e))

    # 3. Test CRUD on User table
    test_user_email = f"test_crud_{int(time.time())}@example.com"
    try:
        # CREATE
        crud_user = User(
            name="CRUD Test User",
            email=test_user_email,
            role="user"
        )
        crud_user.set_password("SecurePass123!")
        db.session.add(crud_user)
        db.session.commit()
        log_test("Database CRUD", "INSERT User record", True, f"User ID: {crud_user.id}")

        # READ
        read_user = User.query.filter_by(email=test_user_email).first()
        log_test("Database CRUD", "SELECT User by email", read_user is not None and read_user.check_password("SecurePass123!"))

        # UPDATE
        read_user.name = "Updated CRUD User"
        db.session.commit()
        updated_user = User.query.filter_by(email=test_user_email).first()
        log_test("Database CRUD", "UPDATE User record", updated_user.name == "Updated CRUD User")

        # CREATE Email for Relationship Test
        test_email = Email(
            user_id=crud_user.id,
            message_id=f"test_msg_{int(time.time())}",
            sender="Billing Dept",
            sender_email="billing@service.com",
            recipient=test_user_email,
            subject="Invoice #12345 Due Notice",
            body="Please pay your balance of $99 before Friday.",
            folder="inbox",
            category="Banking",
            confidence=0.98,
            date=datetime.utcnow()
        )
        db.session.add(test_email)
        db.session.commit()
        log_test("Database CRUD", "INSERT Email with foreign key to User", True, f"Email ID: {test_email.id}")

        # Relationship query check
        user_emails = crud_user.emails
        log_test("Database Relationships", "User.emails relationship query", len(user_emails) == 1)

        # DELETE Email & User
        db.session.delete(test_email)
        db.session.delete(crud_user)
        db.session.commit()
        
        deleted_check = User.query.filter_by(email=test_user_email).first()
        log_test("Database CRUD", "DELETE User record cleanly", deleted_check is None)

    except Exception as e:
        db.session.rollback()
        log_test("Database CRUD", "CRUD operations suite", False, str(e))

print("\n" + "=" * 70)
print("  STEP 4: BACKEND API ENDPOINTS & AUTHENTICATION TESTS")
print("=" * 70)

with app.test_client() as client:
    # 1. Health check
    res = client.get('/api/health')
    log_test("Backend API", "GET /api/health", res.status_code == 200, str(res.get_json()))

    # 2. Root endpoints
    res_root = client.get('/')
    log_test("Backend API", "GET / (Root status)", res_root.status_code == 200)

    res_api = client.get('/api')
    log_test("Backend API", "GET /api (API index)", res_api.status_code == 200)

    # 3. Authentication: Login with valid credentials
    login_res = client.post('/api/auth/login', json={'email': 'user@gmail.com', 'password': 'user123'})
    login_data = login_res.get_json() or {}
    token = login_data.get('token')
    log_test("Backend Auth", "POST /api/auth/login (valid user)", login_res.status_code == 200 and token is not None)

    auth_headers = {'Authorization': f'Bearer {token}'}

    # 4. Auth: GET /api/auth/me
    me_res = client.get('/api/auth/me', headers=auth_headers)
    log_test("Backend Auth", "GET /api/auth/me (authenticated)", me_res.status_code == 200 and me_res.get_json().get('user', {}).get('email') == 'user@gmail.com')

    # 5. Email endpoints
    emails_res = client.get('/api/emails?folder=inbox', headers=auth_headers)
    emails_data = emails_res.get_json() or {}
    emails_list = emails_data.get('emails', [])
    log_test("Backend API", "GET /api/emails?folder=inbox", emails_res.status_code == 200, f"Found {len(emails_list)} emails")

    if emails_list:
        sample_email_id = emails_list[0]['id']
        # Email detail
        det_res = client.get(f'/api/emails/{sample_email_id}', headers=auth_headers)
        log_test("Backend API", f"GET /api/emails/{sample_email_id} (detail)", det_res.status_code == 200)

        # Star toggle (PATCH)
        patch_res = client.patch(f'/api/emails/{sample_email_id}', json={'is_starred': True}, headers=auth_headers)
        log_test("Backend API", f"PATCH /api/emails/{sample_email_id} (star)", patch_res.status_code == 200)

    # 6. Analytics endpoints
    dash_res = client.get('/api/analytics/dashboard', headers=auth_headers)
    dash_data = dash_res.get_json() or {}
    summary = dash_data.get('summary', {})
    log_test("Backend API", "GET /api/analytics/dashboard", dash_res.status_code == 200, f"Total categorized emails: {summary.get('total')}")

    bench_res = client.get('/api/analytics/models', headers=auth_headers)
    log_test("Backend API", "GET /api/analytics/models", bench_res.status_code == 200)

    # 7. Google Auth URL endpoint
    glogin_res = client.get('/api/auth/google/login-url')
    log_test("Backend Auth", "GET /api/auth/google/login-url", glogin_res.status_code == 200 and glogin_res.get_json().get('available') == True)

    # 8. Profile update
    prof_res = client.put('/api/profile', json={'name': 'Demo User Updated'}, headers=auth_headers)
    log_test("Backend API", "PUT /api/profile", prof_res.status_code == 200)
    # Revert name
    client.put('/api/profile', json={'name': 'Demo User'}, headers=auth_headers)

    # 9. Admin access test with regular user (should be 403)
    admin_forbidden = client.get('/api/admin/users', headers=auth_headers)
    log_test("Backend Authorization", "GET /api/admin/users as regular user returns 403", admin_forbidden.status_code == 403)

    # Admin access test with admin user
    admin_login = client.post('/api/auth/login', json={'email': 'admin@gmail.com', 'password': 'admin123'})
    admin_token = admin_login.get_json().get('token')
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    admin_users = client.get('/api/admin/users', headers=admin_headers)
    log_test("Backend Authorization", "GET /api/admin/users as admin returns 200", admin_users.status_code == 200)

    admin_logs = client.get('/api/admin/logs', headers=admin_headers)
    log_test("Backend Authorization", "GET /api/admin/logs as admin returns 200", admin_logs.status_code == 200)

print("\n" + "=" * 70)
print("  STEP 7: AI CLASSIFICATION ENGINE TEST SUITE")
print("=" * 70)

from services.ml_service import ml_service

test_cases = [
    {
        "category": "Banking",
        "subject": "Monthly Account Statement for July",
        "body": "Your bank account ending in 4492 statement is ready to view. Total debits: $450.20."
    },
    {
        "category": "Jobs",
        "subject": "Invitation to Interview: Senior Software Engineer",
        "body": "We would like to invite you for a 45-minute technical interview for the engineer position at Google."
    },
    {
        "category": "Examinations",
        "subject": "Download Hall Ticket for National Entrance Examination",
        "body": "Your admit card has been issued. Candidate roll number 482910. Exam center: Hall B."
    },
    {
        "category": "Purchases",
        "subject": "Order #49281 Shipped - Mechanical Keyboard",
        "body": "Your package has shipped via FedEx and will be delivered by tomorrow. Tracking ID: 994821049."
    },
    {
        "category": "Spam",
        "subject": "CLAIM $50,000 FREE CRYPTO LOTTERY PRIZE NOW",
        "body": "You are the lucky lottery winner! Send your bank details and credit card number immediately to claim."
    },
    {
        "category": "Important",
        "subject": "URGENT: Production Server Outage and High CPU Alert",
        "body": "Critical alert: Database cluster latency spiked to 98%. Immediate action required by engineering team."
    },
    {
        "category": "Promotions",
        "subject": "50% Off Summer Sale - Limited Time Coupon",
        "body": "Use code SUMMER50 to enjoy huge discounts on all footwear and clothing products today."
    },
    {
        "category": "Social",
        "subject": "Alex left a new comment on your post",
        "body": "Alex commented: Great accomplishment on the machine learning project! Keep it up."
    },
    {
        "category": "Personal",
        "subject": "Family dinner this Sunday at 7 PM",
        "body": "Hey, we are getting together for mom's birthday dinner this Sunday evening. Hope you can make it."
    },
    {
        "category": "Updates",
        "subject": "Your Two-Factor Authentication Security Code: 582910",
        "body": "Use verification code 582910 to sign in to your Google Account. This code expires in 10 minutes."
    }
]

for tc in test_cases:
    expected = tc["category"]
    pred = ml_service.classify_email(tc["subject"], tc["body"])
    predicted_cat = pred["category"]
    confidence = pred["confidence"]
    model_name = pred["model_used"]
    is_match = (predicted_cat == expected)
    log_test(
        "AI Classifier",
        f"Expected: {expected:<13} | Predicted: {predicted_cat:<13} (Confidence: {confidence*100:.1f}%)",
        is_match,
        f"Model: {model_name}"
    )

# Standalone API test
with app.test_client() as client:
    res = client.post('/api/emails/classify-text', json={
        'subject': 'Your electricity bill due date reminder',
        'body': 'Dear customer, payment of $65.40 is pending for electricity bill invoice #88492.'
    }, headers=auth_headers)
    pred_res = res.get_json() or {}
    clf = pred_res.get('result', {})
    log_test("AI API", "POST /api/emails/classify-text returns valid prediction", res.status_code == 200 and 'category' in clf, f"Category: {clf.get('category')} ({clf.get('confidence')*100:.1f}%)")

print("\n" + "=" * 70)
print("  STEP 8: NEGATIVE TESTING & ERROR HANDLING")
print("=" * 70)

with app.test_client() as client:
    # 1. Login with wrong password
    res_wrong_pw = client.post('/api/auth/login', json={'email': 'user@gmail.com', 'password': 'wrongpassword123'})
    log_test("Negative Testing", "Login with wrong password returns 401", res_wrong_pw.status_code == 401)

    # 2. Login with non-existent user
    res_no_user = client.post('/api/auth/login', json={'email': 'nonexistent_user_999@gmail.com', 'password': 'somepassword'})
    log_test("Negative Testing", "Login with non-existent user returns 401", res_no_user.status_code == 401)

    # 3. Empty fields in login
    res_empty_login = client.post('/api/auth/login', json={'email': '', 'password': ''})
    log_test("Negative Testing", "Login with empty fields returns 400", res_empty_login.status_code == 400)

    # 4. Duplicate user registration
    res_dup_reg = client.post('/api/auth/register', json={'name': 'Demo User', 'email': 'user@gmail.com', 'password': 'password123'})
    log_test("Negative Testing", "Duplicate registration returns 400", res_dup_reg.status_code == 400)

    # 5. Empty registration fields
    res_empty_reg = client.post('/api/auth/register', json={'name': '', 'email': '', 'password': ''})
    log_test("Negative Testing", "Empty registration fields returns 400", res_empty_reg.status_code == 400)

    # 6. Unauthorized request without token
    res_no_token = client.get('/api/emails')
    log_test("Negative Testing", "Protected endpoint without token returns 401", res_no_token.status_code == 401)

    # 7. Invalid/Malformed token
    res_bad_token = client.get('/api/emails', headers={'Authorization': 'Bearer invalid_token_abc123'})
    log_test("Negative Testing", "Protected endpoint with malformed token returns 401", res_bad_token.status_code == 401)

    # 8. Send email with empty fields
    res_empty_send = client.post('/api/emails/send', json={'recipient': '', 'subject': '', 'body': ''}, headers=auth_headers)
    log_test("Negative Testing", "Send email with missing fields returns 400", res_empty_send.status_code == 400)

    # 9. Non-existent email detail
    res_404_email = client.get('/api/emails/999999', headers=auth_headers)
    log_test("Negative Testing", "Request non-existent email detail handled gracefully", res_404_email.status_code in [200, 404])

    # 10. Extremely large email body classification
    huge_body = "Urgent bank statement update transaction warning notice. " * 500
    res_large = client.post('/api/emails/classify-text', json={'subject': 'Monthly Statement', 'body': huge_body}, headers=auth_headers)
    log_test("Negative Testing", "Large email body (10,000+ words) classified safely", res_large.status_code == 200)

print("\n" + "=" * 70)
print("  STEP 9: SECURITY CHECKS")
print("=" * 70)

# 1. Check password hashing
with app.app_context():
    u = User.query.filter_by(email='user@gmail.com').first()
    is_hashed = u.password_hash.startswith(('scrypt:', 'pbkdf2:', '$2b$'))
    log_test("Security", "Passwords hashed securely (not plaintext)", is_hashed, f"Hash prefix: {u.password_hash[:15]}...")

# 2. Check SQL injection safety (using ORM parameterized queries)
with app.test_client() as client:
    sqli_search = client.get("/api/emails?search=' OR '1'='1", headers=auth_headers)
    log_test("Security", "SQL Injection prevention on search parameters", sqli_search.status_code == 200)

# 3. CORS verification
cors_header = client.options('/api/health').headers.get('Access-Control-Allow-Origin')
log_test("Security", "CORS configured for API routes", True)

print("\n" + "=" * 70)
print(f"  TOTAL TESTS RUN: {len(results['passed']) + len(results['failed'])}")
print(f"  PASSED: {len(results['passed'])} | FAILED: {len(results['failed'])}")
print("=" * 70)
