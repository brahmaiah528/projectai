import jwt
import time
import json
import secrets
import requests
import threading
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from database import db
from models import User, SystemLog
from middleware import token_required
from services.gmail_service import GmailService
from routes.email_routes import ensure_user_emails_exist, seed_emails_from_data

auth_bp = Blueprint('auth', __name__)

def _async_gmail_sync(app_obj, user_id, user_email, tokens_json):
    time.sleep(0.5)  # Brief pause to let main thread finalize its DB commit
    with app_obj.app_context():
        for attempt in range(3):
            try:
                print(f"[Async Gmail Sync] Starting background sync for {user_email} (max_results=500)...")
                live_emails = GmailService.fetch_live_gmail_messages(tokens_json, max_results=500)
                if live_emails:
                    # Clean up temporary simulation emails so real live Gmail messages replace them cleanly
                    try:
                        from models import Email
                        Email.query.filter(Email.user_id == user_id, Email.message_id.like('sim_%')).delete()
                        db.session.commit()
                    except Exception as del_err:
                        db.session.rollback()
                        print(f"[Async Gmail Sync] Warning clearing sim emails: {del_err}")

                    seeded = seed_emails_from_data(user_id, live_emails, source="live")
                    print(f"[Async Gmail Sync] Successfully synced {seeded} live emails for {user_email}")
                    # Save the current historyId so subsequent requests can use delta-sync
                    try:
                        profile = GmailService.fetch_gmail_profile(tokens_json)
                        if profile and profile.get('history_id'):
                            target_user = User.query.get(user_id)
                            if target_user:
                                target_user.gmail_history_id = str(profile['history_id'])
                                db.session.commit()
                                print(f"[Async Gmail Sync] Saved historyId={profile['history_id']} for {user_email}")
                    except Exception as hist_err:
                        print(f"[Async Gmail Sync] Could not save historyId: {hist_err}")
                else:
                    print(f"[Async Gmail Sync] No live messages returned, ensuring fallback emails for {user_email}...")
                    ensure_user_emails_exist(user_id)
                break
            except Exception as e:
                db.session.rollback()
                if "locked" in str(e).lower() and attempt < 2:
                    time.sleep(1.0)
                    continue
                print(f"[Async Gmail Sync Warning] {str(e)}")
                ensure_user_emails_exist(user_id)
                break


def _trigger_background_gmail_sync(user_id, user_email, tokens_json):
    app_obj = current_app._get_current_object()
    t = threading.Thread(
        target=_async_gmail_sync,
        args=(app_obj, user_id, user_email, tokens_json),
        daemon=True
    )
    t.start()

def create_jwt_token(user_id, email=None, remember_me=True):
    if not email:
        try:
            from models import User
            user = User.query.get(user_id)
            email = user.email if user else ""
        except Exception:
            email = ""
    now_ts = int(time.time())
    exp_seconds = 365 * 86400  # Permanent 1-year token for long long run
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': now_ts,
        'exp': now_ts + exp_seconds
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")

# ─── Standard Email/Password Auth ────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not name or not email or not password:
        return jsonify({'message': 'Name, email, and password are required.'}), 400
    email = email.lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'An account with this email already exists.'}), 400
    user = User(
        name=name.strip(), email=email, role='user',
        avatar_url=f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=0D8ABC&color=fff"
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    ensure_user_emails_exist(user.id)
    log = SystemLog(user_id=user.id, user_email=user.email, action="USER_REGISTERED", details=f"Registered: {email}")
    db.session.add(log)
    db.session.commit()
    token = create_jwt_token(user.id, email=user.email, remember_me=False)
    return jsonify({'message': 'Registration successful!', 'token': token, 'user': user.to_dict()}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    remember_me = data.get('remember_me', False)
    if not email or not password:
        return jsonify({'message': 'Email and password are required.'}), 400
    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid email or password.'}), 401
    ensure_user_emails_exist(user.id)
    token = create_jwt_token(user.id, email=user.email, remember_me=remember_me)
    log = SystemLog(user_id=user.id, user_email=user.email, action="USER_LOGIN", details=f"Login: {email}")
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': 'Login successful!', 'token': token, 'user': user.to_dict()}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Please provide your email address.'}), 400
    user = User.query.filter_by(email=email.lower().strip()).first()
    if not user:
        return jsonify({'message': 'If an account exists for this email, reset instructions have been sent.'}), 200
    log = SystemLog(user_id=user.id, user_email=user.email, action="FORGOT_PASSWORD_REQUEST", details=f"Reset for {email}")
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': 'Password reset link sent! Check your inbox.'}), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    ensure_user_emails_exist(current_user.id)
    return jsonify({'user': current_user.to_dict()}), 200

# ─── Google OAuth: Link Gmail to existing account (requires login) ─────────────

@auth_bp.route('/google/url', methods=['GET'])
@token_required
def get_google_auth_url(current_user):
    url, err = GmailService.get_google_auth_url()
    if err:
        return jsonify({'message': err, 'simulated': True}), 200
    return jsonify({'auth_url': url, 'simulated': False}), 200

@auth_bp.route('/google/callback', methods=['GET', 'POST'])
def google_callback():
    """Links Gmail tokens to user / logs in user after OAuth. Auto-syncs real emails."""
    code = request.args.get('code')
    jwt_token = None
    user_data = None
    error_msg = None

    if code:
        try:
            token_res = requests.post("https://oauth2.googleapis.com/token", data={
                'code': code,
                'client_id': current_app.config['GOOGLE_CLIENT_ID'],
                'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
                'redirect_uri': current_app.config['GOOGLE_REDIRECT_URI'],
                'grant_type': 'authorization_code'
            }, timeout=10)

            if token_res.status_code == 200:
                tokens = token_res.json()
                user_info = {}
                if tokens.get('access_token'):
                    info_res = requests.get(
                        'https://www.googleapis.com/oauth2/v2/userinfo',
                        headers={'Authorization': f"Bearer {tokens['access_token']}"},
                        timeout=10
                    )
                    if info_res.status_code == 200:
                        user_info = info_res.json()

                user_email = user_info.get('email', '').lower().strip()
                user_name = user_info.get('name') or (user_email.split('@')[0].title() if user_email else 'Gmail User')
                user_picture = user_info.get('picture', '')

                if user_email:
                    from models import Email as EmailModel
                    target_user = User.query.filter_by(email=user_email).first()
                    is_new_user = target_user is None

                    if is_new_user:
                        target_user = User(
                            name=user_name, email=user_email, role='user',
                            gmail_connected=True,
                            google_tokens=json.dumps(tokens),
                            avatar_url=user_picture or f"https://ui-avatars.com/api/?name={user_name.replace(' ', '+')}&background=0D8ABC&color=fff"
                        )
                        target_user.set_password(secrets.token_hex(32))
                        db.session.add(target_user)
                        db.session.commit()
                        log = SystemLog(user_id=target_user.id, user_email=target_user.email,
                                        action="GOOGLE_REGISTER", details=f"New Google user: {user_email}")
                    else:
                        target_user.gmail_connected = True
                        target_user.google_tokens = json.dumps(tokens)
                        if user_picture and not target_user.avatar_url:
                            target_user.avatar_url = user_picture
                        log = SystemLog(user_id=target_user.id, user_email=target_user.email,
                                        action="GOOGLE_LOGIN", details=f"Google login: {user_email}")
                    db.session.add(log)
                    db.session.commit()

                    # Ensure immediate emails exist for quick render, then sync live Gmail in background
                    ensure_user_emails_exist(target_user.id)
                    _trigger_background_gmail_sync(target_user.id, user_email, target_user.google_tokens)

                    jwt_token = create_jwt_token(target_user.id, email=target_user.email, remember_me=True)
                    user_data = target_user.to_dict()
                    print(f"[Google OAuth] Gmail connected & session issued for: {target_user.email}")
                else:
                    error_msg = "Could not fetch Google profile email."
            else:
                error_msg = f"Token exchange failed (status {token_res.status_code})."
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            print(f"[Google OAuth Error] {error_msg}")

    frontend_url = current_app.config.get('FRONTEND_URL', 'https://projectai-iota.vercel.app').rstrip('/')

    import urllib.parse
    if jwt_token and user_data:
        # Use query params (not fragment) — query params survive HTTP redirects reliably.
        # AuthCallbackPage immediately strips them from the URL bar with replaceState.
        params = urllib.parse.urlencode({'token': jwt_token, 'user': json.dumps(user_data)})
        redirect_url = f"{frontend_url}/auth/callback?{params}"
    else:
        err = urllib.parse.urlencode({'error': error_msg or 'OAuth failed'})
        redirect_url = f"{frontend_url}/auth/callback?{err}"

    from flask import redirect as flask_redirect
    return flask_redirect(redirect_url, 302)

# ─── Google Sign-In: Any Gmail user can log in / register ─────────────────────

@auth_bp.route('/google/login-url', methods=['GET'])
def get_google_login_url():
    """No auth required — returns Google OAuth URL for sign-in."""
    url, err = GmailService.get_google_login_url()
    if err:
        return jsonify({'message': err, 'available': False}), 200
    return jsonify({'auth_url': url, 'available': True}), 200

@auth_bp.route('/google/login-callback', methods=['GET'])
def google_login_callback():
    """Google OAuth callback for sign-in/registration. Any Gmail works."""
    code = request.args.get('code')
    jwt_token = None
    user_data = None
    error_msg = None

    if code:
        try:
            token_res = requests.post("https://oauth2.googleapis.com/token", data={
                'code': code,
                'client_id': current_app.config['GOOGLE_CLIENT_ID'],
                'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
                'redirect_uri': current_app.config['GOOGLE_LOGIN_REDIRECT_URI'],
                'grant_type': 'authorization_code'
            }, timeout=10)

            if token_res.status_code == 200:
                tokens = token_res.json()
                info_res = requests.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f"Bearer {tokens.get('access_token')}"},
                    timeout=10
                )
                if info_res.status_code == 200:
                    guser = info_res.json()
                    g_email = guser.get('email', '').lower().strip()
                    g_name = guser.get('name') or g_email.split('@')[0].title()
                    g_picture = guser.get('picture', '')

                    if g_email:
                        user = User.query.filter_by(email=g_email).first()
                        if not user:
                            # First time — create account automatically
                            user = User(
                                name=g_name, email=g_email, role='user',
                                gmail_connected=True,
                                google_tokens=json.dumps(tokens),
                                avatar_url=g_picture or f"https://ui-avatars.com/api/?name={g_name.replace(' ', '+')}&background=0D8ABC&color=fff"
                            )
                            user.set_password(secrets.token_hex(32))
                            db.session.add(user)
                            db.session.commit()
                            ensure_user_emails_exist(user.id)
                            log = SystemLog(user_id=user.id, user_email=user.email,
                                            action="GOOGLE_REGISTER", details=f"New Google user: {g_email}")
                        else:
                            # Existing user — update tokens and trigger async background Gmail sync
                            user.gmail_connected = True
                            user.google_tokens = json.dumps(tokens)
                            if g_picture and not user.avatar_url:
                                user.avatar_url = g_picture
                            log = SystemLog(user_id=user.id, user_email=user.email,
                                            action="GOOGLE_LOGIN", details=f"Google login: {g_email}")

                        db.session.add(log)
                        db.session.commit()

                        ensure_user_emails_exist(user.id)
                        _trigger_background_gmail_sync(user.id, g_email, user.google_tokens)

                        jwt_token = create_jwt_token(user.id, email=user.email, remember_me=True)
                        user_data = user.to_dict()
                    else:
                        error_msg = "Could not retrieve email from Google account."
                else:
                    error_msg = "Failed to fetch Google profile."
            else:
                error_msg = f"Token exchange failed (status {token_res.status_code})."
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            print(f"[Google Login Error] {error_msg}")

    frontend_url = current_app.config.get('FRONTEND_URL', 'https://projectai-iota.vercel.app').rstrip('/')

    import urllib.parse
    if jwt_token and user_data:
        # Use query params (not fragment) — query params survive HTTP redirects reliably.
        # AuthCallbackPage immediately strips them from the URL bar with replaceState.
        params = urllib.parse.urlencode({'token': jwt_token, 'user': json.dumps(user_data)})
        redirect_url = f"{frontend_url}/auth/callback?{params}"
    else:
        err = urllib.parse.urlencode({'error': error_msg or 'Sign-in failed'})
        redirect_url = f"{frontend_url}/auth/callback?{err}"

    from flask import redirect as flask_redirect
    return flask_redirect(redirect_url, 302)

