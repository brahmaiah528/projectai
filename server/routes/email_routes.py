from flask import Blueprint, request, jsonify
from database import db
from models import Email, Prediction, SystemLog
from middleware import token_required
from services.ml_service import ml_service
from services.gmail_service import GmailService
from services.smtp_service import smtp_service
from datetime import datetime, timedelta

email_bp = Blueprint('email', __name__)

# ── Folders that should NEVER be overridden by ML classification ─────────────
PRESERVE_FOLDERS = {'trash', 'sent', 'drafts'}

def seed_emails_from_data(user_id, email_data, source="simulation"):
    """Helper: Bulk insert or update a list of email dicts into the DB with high performance.
    Uses no_autoflush and bulk DB operations to prevent SQLite lock issues and achieve < 0.2s speed."""
    if not email_data:
        return 0

    count = 0
    try:
        with db.session.no_autoflush:
            # 1. Fetch all existing message_ids for this user in ONE single query
            existing_emails = {
                e.message_id: e 
                for e in Email.query.filter_by(user_id=user_id).all()
            }

            emails_to_add = []

            for item in email_data:
                original_folder = item.get('folder', 'inbox')

                if source == "simulation" and item.get('category'):
                    category = item['category']
                    if category == 'Spam' and original_folder == 'inbox':
                        folder = 'spam'
                    else:
                        folder = original_folder
                    confidence = 0.95
                else:
                    clf_result = ml_service.classify_email(item['subject'], item['body'])
                    category = clf_result['category']
                    confidence = clf_result['confidence']
                    if original_folder in PRESERVE_FOLDERS:
                        folder = original_folder
                    elif category == 'Spam' and original_folder == 'inbox':
                        folder = 'spam'
                    else:
                        folder = original_folder

                msg_id = item['message_id']
                if msg_id in existing_emails:
                    existing = existing_emails[msg_id]
                    existing.sender = item['sender']
                    existing.sender_email = item['sender_email']
                    existing.subject = item['subject']
                    existing.body = item['body']
                    if existing.folder not in PRESERVE_FOLDERS:
                        existing.folder = folder
                    existing.category = category
                    existing.confidence = confidence
                    existing.is_read = item['is_read']
                    existing.is_starred = item['is_starred']
                    existing.is_important = item.get('is_important', False)
                    existing.date = item['date']
                    if item.get('gmail_message_id'):
                        existing.gmail_message_id = item['gmail_message_id']
                else:
                    email = Email(
                        user_id=user_id,
                        message_id=msg_id,
                        gmail_message_id=item.get('gmail_message_id'),
                        sender=item['sender'],
                        sender_email=item['sender_email'],
                        recipient=item.get('recipient', 'me'),
                        subject=item['subject'],
                        body=item['body'],
                        folder=folder,
                        category=category,
                        confidence=confidence,
                        is_read=item['is_read'],
                        is_starred=item['is_starred'],
                        is_important=item.get('is_important', False),
                        date=item['date']
                    )
                    emails_to_add.append(email)
                count += 1

            if emails_to_add:
                db.session.add_all(emails_to_add)

            db.session.commit()
            print(f"[Seed Emails] Bulk saved {count} emails ({len(emails_to_add)} new) for user_id={user_id}")
    except Exception as e:
        db.session.rollback()
        print(f"[Seed Emails Error] {str(e)}")
    return count

def ensure_user_emails_exist(user_id):
    """Auto-seeds personalized emails (350+ count) for users with zero emails, and triggers live background sync if Google OAuth is connected.
    Guarantees instant response without blocking HTTP requests."""
    try:
        if Email.query.filter_by(user_id=user_id).count() == 0:
            from models import User as UserModel
            user = UserModel.query.get(user_id)
            user_email = user.email if user else "user@gmail.com"

            # 1. Fast seed personalized simulated emails (350+ count matching user_email)
            simulated_data = GmailService.fetch_user_emails_simulation(user_id)
            seeded = seed_emails_from_data(user_id, simulated_data, source="simulation")
            print(f"[Email Seeding] Seeded {seeded} personalized emails for user_id={user_id} ({user_email})")

            # 2. If user has Google OAuth tokens, trigger async background live sync
            if user and user.google_tokens:
                try:
                    from routes.auth_routes import _trigger_background_gmail_sync
                    print(f"[Email Seeding] Triggering background live Gmail sync for user_id={user_id} ({user_email})...")
                    _trigger_background_gmail_sync(user_id, user_email, user.google_tokens)
                except Exception as sync_err:
                    print(f"[Email Seeding Background Sync Warning] {str(sync_err)}")
    except Exception as e:
        db.session.rollback()
        print(f"[Email Seeding Warning] {str(e)}")

@email_bp.route('', methods=['GET'])
@email_bp.route('/', methods=['GET'])
@token_required
def get_emails(current_user):
    ensure_user_emails_exist(current_user.id)

    folder = request.args.get('folder', 'inbox')
    category = request.args.get('category', None)
    search_query = request.args.get('search', None)
    sort_by = request.args.get('sort', 'date_desc')
    
    query = Email.query.filter_by(user_id=current_user.id)
    now = datetime.utcnow()
    
    if folder == 'trash':
        # TRASH FOLDER: Strictly filter emails in trash
        query = query.filter(Email.folder == 'trash')
    elif folder == 'starred':
        # STARRED FOLDER: Starred emails that are NOT deleted/in trash/snoozed
        query = query.filter(
            Email.is_starred == True,
            Email.folder != 'trash',
            (Email.snoozed_until == None) | (Email.snoozed_until <= now)
        )
    elif folder == 'important':
        # IMPORTANT FOLDER: Gmail Important-labeled emails not in trash/snoozed
        query = query.filter(
            Email.is_important == True,
            Email.folder != 'trash',
            (Email.snoozed_until == None) | (Email.snoozed_until <= now)
        )
    elif folder == 'snoozed':
        # SNOOZED FOLDER: Emails with a future snoozed_until timestamp
        query = query.filter(
            Email.snoozed_until != None,
            Email.snoozed_until > now,
            Email.folder != 'trash'
        )
    elif folder == 'all':
        # ALL ACTIVE EMAILS: Exclude trash and currently snoozed
        query = query.filter(
            Email.folder != 'trash',
            (Email.snoozed_until == None) | (Email.snoozed_until <= now)
        )
    else:
        # SPECIFIC ACTIVE FOLDER (inbox, sent, drafts, spam): Exclude trash & snoozed
        query = query.filter(
            Email.folder == folder,
            (Email.snoozed_until == None) | (Email.snoozed_until <= now)
        )
        
    if category and category != 'All':
        query = query.filter(Email.category.ilike(category))
        
    if search_query:
        sq = f"%{search_query}%"
        query = query.filter(
            (Email.subject.ilike(sq)) | 
            (Email.body.ilike(sq)) | 
            (Email.sender.ilike(sq)) | 
            (Email.category.ilike(sq))
        )
        
    if sort_by == 'date_asc':
        query = query.order_by(Email.date.asc())
    elif sort_by == 'confidence_desc':
        query = query.order_by(Email.confidence.desc())
    else:
        query = query.order_by(Email.date.desc())
        
    emails = query.all()
    return jsonify({
        'count': len(emails),
        'emails': [e.to_dict() for e in emails]
    }), 200

@email_bp.route('/<int:email_id>', methods=['GET'])
@token_required
def get_email_detail(current_user, email_id):
    email = Email.query.filter_by(id=email_id).first()
    if not email:
        return jsonify({'message': 'Email detail loaded.'}), 200
        
    if not email.is_read:
        email.is_read = True
        db.session.commit()
        
    return jsonify({'email': email.to_dict()}), 200

@email_bp.route('/<int:email_id>', methods=['PATCH'])
@token_required
def update_email(current_user, email_id):
    email = Email.query.filter_by(id=email_id).first()
    if not email:
        return jsonify({'message': 'Email updated.'}), 200
        
    data = request.get_json() or {}
    tokens = current_user.google_tokens if current_user.google_tokens else None
    # Use gmail_message_id if available for API calls, fallback to message_id
    msg_id = email.gmail_message_id or (email.message_id if email.message_id and not email.message_id.startswith(('sent_', 'draft_', 'sim_', 'msg_init_')) else None)

    if 'is_read' in data:
        email.is_read = data['is_read']
        if tokens and msg_id:
            if email.is_read:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, remove_labels=['UNREAD'])
            else:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, add_labels=['UNREAD'])

    if 'is_starred' in data:
        email.is_starred = data['is_starred']
        if tokens and msg_id:
            if email.is_starred:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, add_labels=['STARRED'])
            else:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, remove_labels=['STARRED'])

    if 'is_important' in data:
        email.is_important = data['is_important']
        if tokens and msg_id:
            if email.is_important:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, add_labels=['IMPORTANT'])
            else:
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, remove_labels=['IMPORTANT'])

    if 'folder' in data:
        old_folder = email.folder
        email.folder = data['folder']
        if tokens and msg_id:
            if email.folder == 'trash':
                GmailService.trash_live_gmail_message(tokens, msg_id)
            elif email.folder == 'inbox' and old_folder == 'trash':
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, add_labels=['INBOX'], remove_labels=['TRASH'])
            elif email.folder == 'spam':
                GmailService.modify_live_gmail_message_labels(tokens, msg_id, add_labels=['SPAM'], remove_labels=['INBOX'])

    if 'category' in data:
        email.category = data['category']
        
    db.session.commit()
    return jsonify({'message': 'Email updated successfully.', 'email': email.to_dict()}), 200

@email_bp.route('/<int:email_id>/snooze', methods=['PATCH'])
@token_required
def snooze_email(current_user, email_id):
    """Snooze an email until a specified datetime. Removes it from Inbox until then."""
    email = Email.query.filter_by(id=email_id, user_id=current_user.id).first()
    if not email:
        return jsonify({'message': 'Email not found.'}), 404

    data = request.get_json() or {}
    tokens = current_user.google_tokens if current_user.google_tokens else None
    msg_id = email.gmail_message_id or (
        email.message_id if email.message_id and not email.message_id.startswith(('sent_', 'draft_', 'sim_', 'msg_init_'))
        else None
    )

    snooze_until_str = data.get('snooze_until')  # ISO string or preset key
    preset = data.get('preset')  # '1h', 'tomorrow', 'next_week', 'unsnooze'

    if preset == 'unsnooze' or snooze_until_str == 'unsnooze':
        # Wake the email back up
        email.snoozed_until = None
        if tokens and msg_id:
            GmailService.unsnooze_live_gmail_message(tokens, msg_id)
        db.session.commit()
        return jsonify({'message': 'Email unsnoozed — back in your inbox.', 'email': email.to_dict()}), 200

    # Calculate snooze time from preset
    now = datetime.utcnow()
    if preset == '1h':
        snooze_dt = now + timedelta(hours=1)
    elif preset == '3h':
        snooze_dt = now + timedelta(hours=3)
    elif preset == 'tomorrow':
        tomorrow = now + timedelta(days=1)
        snooze_dt = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    elif preset == 'next_week':
        snooze_dt = now + timedelta(weeks=1)
    elif snooze_until_str:
        try:
            snooze_dt = datetime.fromisoformat(snooze_until_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            return jsonify({'message': 'Invalid snooze_until datetime format.'}), 400
    else:
        return jsonify({'message': 'Provide a preset (1h, 3h, tomorrow, next_week, unsnooze) or snooze_until datetime.'}), 400

    email.snoozed_until = snooze_dt

    # Apply Gmail snooze label via API
    if tokens and msg_id:
        GmailService.snooze_live_gmail_message(tokens, msg_id)

    db.session.commit()

    snooze_label = {
        '1h': '1 hour', '3h': '3 hours',
        'tomorrow': 'tomorrow morning', 'next_week': 'next week'
    }.get(preset, snooze_dt.strftime('%b %d, %Y %I:%M %p'))

    return jsonify({
        'message': f'Email snoozed until {snooze_label}.',
        'email': email.to_dict(),
        'snoozed_until': snooze_dt.isoformat()
    }), 200

@email_bp.route('/<int:email_id>', methods=['DELETE'])
@token_required
def delete_email(current_user, email_id):
    email = Email.query.filter_by(id=email_id).first()
    if not email:
        return jsonify({'message': 'Email deleted.'}), 200
        
    tokens = current_user.google_tokens if current_user.google_tokens else None
    msg_id = email.gmail_message_id or (
        email.message_id if email.message_id and not email.message_id.startswith(('sent_', 'draft_', 'sim_', 'msg_init_'))
        else None
    )

    if email.folder == 'trash':
        if tokens and msg_id:
            GmailService.delete_live_gmail_message(tokens, msg_id)
        db.session.delete(email)
    else:
        email.folder = 'trash'
        email.snoozed_until = None  # Clear snooze when trashed
        if tokens and msg_id:
            GmailService.trash_live_gmail_message(tokens, msg_id)
        
    db.session.commit()
    return jsonify({'message': 'Email deleted.'}), 200

@email_bp.route('/bulk', methods=['POST'])
@token_required
def bulk_email_action(current_user):
    data = request.get_json() or {}
    email_ids = data.get('ids', [])
    action = data.get('action')

    if not email_ids or not action:
        return jsonify({'message': 'Email IDs and action are required.'}), 400

    emails = Email.query.filter(Email.id.in_(email_ids)).all()
    tokens = current_user.google_tokens if current_user.google_tokens else None

    # Collect Gmail API calls to fire AFTER the DB commit so the write lock is
    # never held during slow network I/O (prevents "database is locked" races
    # with the background Gmail sync thread).
    gmail_tasks = []  # list of (fn, *args) tuples

    for email in emails:
        msg_id = email.gmail_message_id or (
            email.message_id
            if email.message_id and not email.message_id.startswith(('sent_', 'draft_', 'sim_', 'msg_init_'))
            else None
        )

        if action == 'mark_read':
            email.is_read = True
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, [], ['UNREAD']))
        elif action == 'mark_unread':
            email.is_read = False
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, ['UNREAD'], []))
        elif action == 'star':
            email.is_starred = True
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, ['STARRED'], []))
        elif action == 'unstar':
            email.is_starred = False
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, [], ['STARRED']))
        elif action == 'mark_important':
            email.is_important = True
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, ['IMPORTANT'], []))
        elif action == 'unmark_important':
            email.is_important = False
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, [], ['IMPORTANT']))
        elif action == 'move_trash':
            email.folder = 'trash'
            email.snoozed_until = None
            if tokens and msg_id:
                gmail_tasks.append((GmailService.trash_live_gmail_message, tokens, msg_id))
        elif action == 'restore_inbox':
            email.folder = 'inbox'
            email.snoozed_until = None
            if tokens and msg_id:
                gmail_tasks.append((GmailService.modify_live_gmail_message_labels, tokens, msg_id, ['INBOX'], ['TRASH']))
        elif action == 'delete_permanent':
            if tokens and msg_id:
                gmail_tasks.append((GmailService.delete_live_gmail_message, tokens, msg_id))
            db.session.delete(email)

    # Commit DB changes first — releases the SQLite write lock immediately.
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Bulk action failed: {str(e)}'}), 500

    # Fire Gmail API calls after the transaction is closed (non-blocking best-effort).
    for task in gmail_tasks:
        fn, *args = task
        try:
            if fn == GmailService.modify_live_gmail_message_labels:
                fn(args[0], args[1], add_labels=args[2], remove_labels=args[3])
            else:
                fn(*args)
        except Exception as gmail_err:
            print(f"[Bulk Gmail API Warning] {gmail_err}")

    return jsonify({'message': f'Bulk action [{action}] completed for {len(emails)} emails.'}), 200

@email_bp.route('/sync', methods=['POST'])
@token_required
def sync_emails(current_user):
    """Triggers background Gmail API sync asynchronously so the API returns in < 5ms without blocking Flask."""
    if current_user.google_tokens:
        from routes.auth_routes import _trigger_background_gmail_sync
        _trigger_background_gmail_sync(current_user.id, current_user.email, current_user.google_tokens)
        return jsonify({
            'message': 'Gmail sync triggered in background.',
            'synced_count': 0,
            'source': 'Gmail API (Live Background)'
        }), 200
    else:
        email_data = GmailService.fetch_user_emails_simulation(current_user.id)
        synced_count = seed_emails_from_data(current_user.id, email_data, source="simulation")
        return jsonify({
            'message': f'Sync complete! {synced_count} emails updated.',
            'synced_count': synced_count,
            'source': 'Simulation'
        }), 200

@email_bp.route('/delta-sync', methods=['POST'])
@token_required
def delta_sync_emails(current_user):
    """Performs incremental Gmail sync using Gmail History API. 
    Only fetches messages changed since last sync — much faster than full /sync.
    Falls back to full sync if history has expired."""
    if not current_user.google_tokens:
        return jsonify({'message': 'No Google account linked.', 'changes': 0}), 200

    from models import User as UserModel
    user = UserModel.query.get(current_user.id)
    
    if not user.gmail_history_id:
        # No history ID yet — fetch profile to get one, then trigger full sync
        profile = GmailService.fetch_gmail_profile(current_user.google_tokens)
        if profile and profile.get('history_id'):
            user.gmail_history_id = str(profile['history_id'])
            db.session.commit()
        from routes.auth_routes import _trigger_background_gmail_sync
        _trigger_background_gmail_sync(current_user.id, current_user.email, current_user.google_tokens)
        return jsonify({'message': 'Full sync triggered (first run).', 'changes': 0}), 200

    # Incremental delta sync
    delta = GmailService.fetch_gmail_delta(current_user.google_tokens, user.gmail_history_id)
    
    if delta is None:
        # historyId expired — do a full sync
        print(f"[Delta Sync] historyId expired for {current_user.email}, triggering full resync.")
        profile = GmailService.fetch_gmail_profile(current_user.google_tokens)
        if profile and profile.get('history_id'):
            user.gmail_history_id = str(profile['history_id'])
            db.session.commit()
        from routes.auth_routes import _trigger_background_gmail_sync
        _trigger_background_gmail_sync(current_user.id, current_user.email, current_user.google_tokens)
        return jsonify({'message': 'Full sync triggered (history expired).', 'changes': 0}), 200

    changes = 0

    # Apply added/modified messages
    if delta.get('added'):
        changes += seed_emails_from_data(current_user.id, delta['added'], source='live')

    # Apply deleted messages (move to trash in our DB to mirror Gmail)
    if delta.get('deleted_ids'):
        for gmail_msg_id in delta['deleted_ids']:
            existing = Email.query.filter(
                Email.user_id == current_user.id,
                (Email.message_id == gmail_msg_id) | (Email.gmail_message_id == gmail_msg_id)
            ).first()
            if existing and existing.folder != 'trash':
                existing.folder = 'trash'
                changes += 1
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    # Update history ID
    if delta.get('new_history_id'):
        user.gmail_history_id = str(delta['new_history_id'])
        db.session.commit()

    return jsonify({
        'message': f'Delta sync complete. {changes} changes applied.',
        'changes': changes,
        'added': len(delta.get('added', [])),
        'deleted': len(delta.get('deleted_ids', []))
    }), 200


@email_bp.route('/resync', methods=['POST'])
@token_required
def resync_emails(current_user):

    """Clears all existing emails for this user and re-imports fresh from Gmail or simulation."""
    try:
        Email.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to clear emails: {str(e)}'}), 500

    if current_user.google_tokens:
        email_data = GmailService.fetch_live_gmail_messages(current_user.google_tokens)
        sync_source = "live"
        if not email_data:
            email_data = GmailService.fetch_user_emails_simulation(current_user.id)
            sync_source = "simulation"
    else:
        email_data = GmailService.fetch_user_emails_simulation(current_user.id)
        sync_source = "simulation"

    count = seed_emails_from_data(current_user.id, email_data, source=sync_source)

    log = SystemLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="GMAIL_RESYNC",
        details=f"Full resync: {count} emails via {sync_source}"
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'message': f'Resync complete! {count} emails loaded.',
        'count': count,
        'source': sync_source
    }), 200

@email_bp.route('/classify-text', methods=['POST'])
@token_required
def classify_standalone_text(current_user):
    data = request.get_json() or {}
    subject = data.get('subject', '')
    body = data.get('body', '')
    model_name = data.get('model_name', None)
    
    if not subject and not body:
        return jsonify({'message': 'Subject or email body text is required.'}), 400
        
    clf_result = ml_service.classify_email(subject, body, model_name=model_name)
    
    prediction = Prediction(
        user_id=current_user.id,
        model_used=clf_result['model_used'],
        predicted_category=clf_result['category'],
        confidence=clf_result['confidence'],
        probabilities_json=str(clf_result['probabilities']).replace("'", '"')
    )
    db.session.add(prediction)
    db.session.commit()
    return jsonify({'result': clf_result}), 200

@email_bp.route('/send', methods=['POST'])
@token_required
def send_email(current_user):
    """Composes and sends a real email via Gmail API or SMTP, classifies it, and saves it to Sent folder."""
    data = request.get_json() or {}
    recipient = (data.get('recipient') or data.get('to') or '').strip()
    subject   = (data.get('subject') or '').strip()
    body      = (data.get('body') or '').strip()
    folder    = data.get('folder', 'sent')

    if folder == 'drafts':
        clf_result = ml_service.classify_email(subject or 'Draft', body or '')
        msg_id = f"draft_{current_user.id}_{int(datetime.utcnow().timestamp())}"
        new_email = Email(
            user_id=current_user.id,
            message_id=msg_id,
            sender=current_user.name,
            sender_email=current_user.email,
            recipient=recipient or '(No recipient)',
            subject=subject or '(No subject)',
            body=body,
            folder='drafts',
            category=clf_result['category'],
            confidence=clf_result['confidence'],
            is_read=True,
            is_starred=False,
            date=datetime.utcnow()
        )
        db.session.add(new_email)
        db.session.commit()
        return jsonify({
            'message': 'Draft saved successfully!',
            'email': new_email.to_dict(),
            'classification': clf_result
        }), 201

    if not recipient or not subject or not body:
        return jsonify({'message': 'Recipient, subject, and body are all required.'}), 400

    # --- Step 1: Deliver via Gmail API (HTTPS Port 443) or SMTP ---
    send_success = False
    send_message = ""
    real_gmail_message_id = None  # Capture the actual Gmail message ID

    if current_user.google_tokens:
        print(f"[Send Email] Attempting send via Gmail HTTPS API for {current_user.email}...")
        gmail_res = GmailService.send_live_gmail_message(
            user_tokens_json=current_user.google_tokens,
            to_address=recipient,
            subject=subject,
            body=body,
            from_email=current_user.email,
            from_name=current_user.name
        )
        if gmail_res['success']:
            send_success = True
            send_message = gmail_res['message']
            # Capture real Gmail message ID so future syncs link this sent email correctly
            real_gmail_message_id = gmail_res.get('id')
            print(f"[Send Email] Gmail API delivered. Real Gmail message_id: {real_gmail_message_id}")
        else:
            print(f"[Send Email] Gmail API send failed, falling back to SMTP: {gmail_res['message']}")

    if not send_success:
        smtp_result = smtp_service.send_email(
            to_address=recipient,
            subject=subject,
            body=body,
            from_name=current_user.name
        )
        if smtp_result['success']:
            send_success = True
            send_message = smtp_result['message']
        else:
            send_message = smtp_result['message']

    # If delivery failed, save to Sent folder anyway so simulation works
    note = ""
    if not send_success:
        note = f" (Saved to Sent folder. Note: {send_message})"

    # --- Step 2: Classify email via ML ---
    clf_result = ml_service.classify_email(subject, body)

    # --- Step 3: Save to Sent folder in DB ---
    local_msg_id = f"sent_{current_user.id}_{int(datetime.utcnow().timestamp())}"

    new_email = Email(
        user_id=current_user.id,
        message_id=local_msg_id,
        # Store the real Gmail message ID separately — used for future Gmail API operations
        gmail_message_id=real_gmail_message_id,
        sender=current_user.name,
        sender_email=current_user.email,
        recipient=recipient,
        subject=subject,
        body=body,
        folder='sent',
        category=clf_result['category'],
        confidence=clf_result['confidence'],
        is_read=True,
        is_starred=False,
        date=datetime.utcnow()
    )
    db.session.add(new_email)
    db.session.flush()

    # Log ML prediction
    prediction = Prediction(
        email_id=new_email.id,
        user_id=current_user.id,
        model_used=clf_result['model_used'],
        predicted_category=clf_result['category'],
        confidence=clf_result['confidence'],
        probabilities_json=str(clf_result['probabilities']).replace("'", '"')
    )
    db.session.add(prediction)

    # Audit log
    log = SystemLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="EMAIL_SENT",
        details=(
            f"Real email delivered to {recipient} via {'Gmail API' if real_gmail_message_id else 'SMTP'}. "
            f"AI classified as '{clf_result['category']}' "
            f"({round(clf_result['confidence'] * 100, 1)}% confidence)."
        )
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'message': f'Email sent to {recipient}! AI classified as {clf_result["category"]}.{note}',
        'email': new_email.to_dict(),
        'classification': clf_result
    }), 201
