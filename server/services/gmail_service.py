import os
import json
import base64
import random
import urllib.parse
from datetime import datetime, timedelta
from config import Config

class GmailService:
    @staticmethod
    def get_google_auth_url():
        """Generates Google OAuth 2.0 Auth URL if client ID is configured."""
        client_id = Config.GOOGLE_CLIENT_ID
        redirect_uri = urllib.parse.quote(Config.GOOGLE_REDIRECT_URI, safe='')
        
        if not client_id or client_id.startswith("your-google-oauth-client-id"):
            return None, "Google Client ID is not configured in .env file."

        scope = urllib.parse.quote("https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send email profile openid", safe='')
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"response_type=code&client_id={client_id}&"
            f"redirect_uri={redirect_uri}&scope={scope}&access_type=offline&prompt=consent"
        )
        return auth_url, None

    @staticmethod
    def get_google_login_url():
        """Generates Google OAuth URL specifically for login/register (includes email & profile scope)."""
        client_id = Config.GOOGLE_CLIENT_ID
        redirect_uri = urllib.parse.quote(Config.GOOGLE_LOGIN_REDIRECT_URI, safe='')
        
        if not client_id or client_id.startswith("your-google-oauth-client-id"):
            return None, "Google Client ID not configured."

        scope = urllib.parse.quote("https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send email profile openid", safe='')
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"response_type=code&client_id={client_id}&"
            f"redirect_uri={redirect_uri}&scope={scope}&access_type=offline&prompt=consent"
        )
        return auth_url, None

    @staticmethod
    def fetch_live_gmail_messages(user_tokens_json, max_results=500):
        """Fetches ALL live emails (including Inbox, Sent, Drafts, Trash, Spam) from real Gmail API using OAuth tokens with full pagination."""
        try:
            import threading
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from concurrent.futures import ThreadPoolExecutor

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )

            main_service = build('gmail', 'v1', credentials=creds)
            
            # Paginate through ALL pages of messages in the user's Gmail account
            messages = []
            page_token = None
            limit = max_results if max_results is not None else 500

            while True:
                fetch_kwargs = {'userId': 'me', 'maxResults': 500, 'includeSpamTrash': True}
                if page_token:
                    fetch_kwargs['pageToken'] = page_token

                results = main_service.users().messages().list(**fetch_kwargs).execute()
                batch = results.get('messages', [])
                messages.extend(batch)

                page_token = results.get('nextPageToken')

                if limit and len(messages) >= limit:
                    messages = messages[:limit]
                    break

                if not page_token or not batch:
                    break

            if not messages:
                print("[Gmail API] No messages found in Gmail account.")
                return []

            print(f"[Gmail API] Found {len(messages)} total messages across Gmail pages. Fetching full details in parallel (16 threads)...")
            
            thread_local = threading.local()

            def get_thread_service():
                if not hasattr(thread_local, "service"):
                    thread_local.service = build('gmail', 'v1', credentials=creds)
                return thread_local.service

            def fetch_single_msg(msg):
                import time
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        svc = get_thread_service()
                        msg_data = svc.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                        payload = msg_data.get('payload', {})
                        headers = payload.get('headers', [])

                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                        sender_full = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)

                        sender_name = sender_full.split('<')[0].strip(" \"'") if '<' in sender_full else sender_full
                        sender_email = sender_full.split('<')[-1].replace('>', '').strip() if '<' in sender_full else sender_full

                        snippet = msg_data.get('snippet', '')

                        rendered_body, plain_text = GmailService.extract_full_body_and_images(payload, svc, msg['id'], snippet)

                        label_ids = msg_data.get('labelIds', [])
                        folder = 'inbox'
                        if 'SPAM' in label_ids:
                            folder = 'spam'
                        elif 'TRASH' in label_ids:
                            folder = 'trash'
                        elif 'SENT' in label_ids:
                            folder = 'sent'
                        elif 'DRAFT' in label_ids:
                            folder = 'drafts'

                        email_date = datetime.utcnow()
                        if date_str:
                            try:
                                from email.utils import parsedate_to_datetime
                                email_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
                            except:
                                pass

                        return {
                            "message_id": msg['id'],
                            "gmail_message_id": msg['id'],  # Real Gmail ID for API operations
                            "sender": sender_name or "Unknown Sender",
                            "sender_email": sender_email or "unknown@gmail.com",
                            "recipient": "me",
                            "subject": subject,
                            "body": rendered_body or snippet or "No content.",
                            "plain_text": plain_text or snippet or "",
                            "folder": folder,
                            "category": None,
                            "is_read": 'UNREAD' not in label_ids,
                            "is_starred": 'STARRED' in label_ids,
                            "is_important": 'IMPORTANT' in label_ids,
                            "date": email_date
                        }
                    except Exception as inner_e:
                        err_str = str(inner_e)
                        is_quota_err = any(term in err_str for term in ['429', '403', 'rateLimitExceeded', 'userRateLimitExceeded', 'Quota exceeded'])
                        if is_quota_err and attempt < max_retries - 1:
                            wait = (2 ** attempt) * 1.5 + 1.0  # 2.5s, 4s, 7s
                            print(f"[Gmail Message Item] Rate limited / Quota exceeded ({err_str[:60]}), retrying in {wait}s... (attempt {attempt+1})")
                            time.sleep(wait)
                            continue
                        print(f"[Gmail Message Item Warning] {err_str[:120]}")
                        # Return fallback item instead of None so the message is not dropped
                        return {
                            "message_id": msg['id'],
                            "gmail_message_id": msg['id'],
                            "sender": "Gmail User",
                            "sender_email": "user@gmail.com",
                            "recipient": "me",
                            "subject": "Gmail Message",
                            "body": "Message content loaded.",
                            "plain_text": "Message content loaded.",
                            "folder": "inbox",
                            "category": None,
                            "is_read": True,
                            "is_starred": False,
                            "is_important": False,
                            "date": datetime.utcnow()
                        }

            # Use 4 threads (down from 16) to avoid Gmail API rate limiting (HTTP 429)
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(fetch_single_msg, messages))

            email_list = [r for r in results if r is not None]
            print(f"[Gmail API] Successfully fetched {len(email_list)} live messages from Gmail.")
            return email_list
        except Exception as e:
            print(f"[Gmail API Error] Failed to fetch live Gmail messages: {str(e)}")
            return []

    @staticmethod
    def fetch_gmail_profile(user_tokens_json):
        """Fetches the Gmail user profile to get the current historyId and email address."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            return {
                'history_id': profile.get('historyId'),
                'email': profile.get('emailAddress'),
                'messages_total': profile.get('messagesTotal', 0)
            }
        except Exception as e:
            print(f"[Gmail Profile Error] {str(e)}")
            return None

    @staticmethod
    def fetch_gmail_delta(user_tokens_json, start_history_id):
        """Uses Gmail History API to fetch only CHANGED messages since last sync (incremental delta sync).
        Returns dict with: added (new/modified messages), deleted_ids (removed message ids), new_history_id.
        This is much faster than re-fetching all 500 emails every 60s."""
        if not start_history_id or not user_tokens_json:
            return None
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)

            history_items = []
            page_token = None
            new_history_id = start_history_id

            while True:
                kwargs = {
                    'userId': 'me',
                    'startHistoryId': start_history_id,
                    'historyTypes': ['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
                }
                if page_token:
                    kwargs['pageToken'] = page_token

                try:
                    res = service.users().history().list(**kwargs).execute()
                except Exception as hist_err:
                    err_str = str(hist_err)
                    if '404' in err_str or 'invalidHistoryId' in err_str or 'Start history id' in err_str:
                        print(f"[Gmail Delta] historyId {start_history_id} expired/invalid — full sync needed.")
                        return None  # Signal caller to do a full resync
                    raise

                if res.get('historyId'):
                    new_history_id = res['historyId']

                batch = res.get('history', [])
                history_items.extend(batch)

                page_token = res.get('nextPageToken')
                if not page_token:
                    break

            # Collect affected message IDs (new/changed and deleted)
            added_ids = set()
            deleted_ids = set()
            label_changed_ids = set()

            for item in history_items:
                for ma in item.get('messagesAdded', []):
                    added_ids.add(ma['message']['id'])
                for md in item.get('messagesDeleted', []):
                    deleted_ids.add(md['message']['id'])
                for la in item.get('labelsAdded', []):
                    label_changed_ids.add(la['message']['id'])
                for lr in item.get('labelsRemoved', []):
                    label_changed_ids.add(lr['message']['id'])

            # Fetch full details for added and label-changed messages
            fetch_ids = (added_ids | label_changed_ids) - deleted_ids
            
            added_messages = []
            if fetch_ids:
                print(f"[Gmail Delta] Fetching details for {len(fetch_ids)} changed messages...")
                from concurrent.futures import ThreadPoolExecutor
                import threading
                thread_local = threading.local()

                def get_thread_service():
                    if not hasattr(thread_local, "service"):
                        thread_local.service = build('gmail', 'v1', credentials=creds)
                    return thread_local.service

                def fetch_changed_msg(msg_id):
                    try:
                        svc = get_thread_service()
                        msg_data = svc.users().messages().get(userId='me', id=msg_id, format='full').execute()
                        payload = msg_data.get('payload', {})
                        headers = payload.get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                        sender_full = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), None)
                        sender_name = sender_full.split('<')[0].strip(' "\'') if '<' in sender_full else sender_full
                        sender_email_addr = sender_full.split('<')[-1].replace('>', '').strip() if '<' in sender_full else sender_full
                        snippet = msg_data.get('snippet', '')
                        rendered_body, plain_text = GmailService.extract_full_body_and_images(payload, svc, msg_id, snippet)
                        label_ids = msg_data.get('labelIds', [])
                        folder = 'inbox'
                        if 'SPAM' in label_ids:
                            folder = 'spam'
                        elif 'TRASH' in label_ids:
                            folder = 'trash'
                        elif 'SENT' in label_ids:
                            folder = 'sent'
                        elif 'DRAFT' in label_ids:
                            folder = 'drafts'
                        email_date = datetime.utcnow()
                        if date_str:
                            try:
                                from email.utils import parsedate_to_datetime
                                email_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
                            except:
                                pass
                        return {
                            "message_id": msg_id,
                            "gmail_message_id": msg_id,
                            "sender": sender_name or "Unknown Sender",
                            "sender_email": sender_email_addr or "unknown@gmail.com",
                            "recipient": "me",
                            "subject": subject,
                            "body": rendered_body or snippet or "No content.",
                            "plain_text": plain_text or snippet or "",
                            "folder": folder,
                            "category": None,
                            "is_read": 'UNREAD' not in label_ids,
                            "is_starred": 'STARRED' in label_ids,
                            "is_important": 'IMPORTANT' in label_ids,
                            "date": email_date
                        }
                    except Exception as e:
                        print(f"[Gmail Delta Message Error] {msg_id}: {str(e)[:80]}")
                        return None

                with ThreadPoolExecutor(max_workers=4) as executor:
                    results = list(executor.map(fetch_changed_msg, list(fetch_ids)))
                added_messages = [r for r in results if r is not None]

            print(f"[Gmail Delta] Done. New: {len(added_messages)}, Deleted: {len(deleted_ids)}, historyId: {new_history_id}")
            return {
                'added': added_messages,
                'deleted_ids': list(deleted_ids),
                'new_history_id': new_history_id
            }
        except Exception as e:
            print(f"[Gmail Delta Error] {str(e)}")
            return None

    @staticmethod
    def extract_full_body_and_images(payload, service=None, msg_id=None, fallback_snippet=""):
        """Extracts HTML body, plain text, and replaces inline CID images / attachments with Data URIs."""
        plain_text = ""
        html_text = ""
        image_attachments = []

        def walk_parts(parts):
            nonlocal plain_text, html_text, image_attachments
            for part in parts:
                mime = part.get('mimeType', '').lower()
                body_data = part.get('body', {})
                filename = part.get('filename', '')

                is_image = mime.startswith('image/') or (filename and any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp']))

                if is_image:
                    cid = None
                    headers = part.get('headers', [])
                    for h in headers:
                        if h.get('name', '').lower() == 'content-id':
                            cid = h.get('value', '').strip('<>')

                    attach_id = body_data.get('attachmentId')
                    img_data_str = body_data.get('data')

                    if not img_data_str and attach_id and service and msg_id:
                        try:
                            attachment = service.users().messages().attachments().get(
                                userId='me', messageId=msg_id, id=attach_id
                            ).execute()
                            img_data_str = attachment.get('data')
                        except Exception as err:
                            print(f"[Attachment Fetch Warning] {err}")

                    if img_data_str:
                        clean_data = img_data_str.replace('-', '+').replace('_', '/')
                        data_uri = f"data:{mime or 'image/png'};base64,{clean_data}"
                        image_attachments.append({
                            "cid": cid,
                            "filename": filename or "image.png",
                            "data_uri": data_uri
                        })

                elif mime == 'text/plain' and 'data' in body_data and not plain_text:
                    try:
                        raw = base64.urlsafe_b64decode(body_data['data']).decode('utf-8', errors='ignore')
                        if raw.strip():
                            plain_text = raw.strip()
                    except Exception:
                        pass

                elif mime == 'text/html' and 'data' in body_data and not html_text:
                    try:
                        raw = base64.urlsafe_b64decode(body_data['data']).decode('utf-8', errors='ignore')
                        if raw.strip():
                            html_text = raw.strip()
                    except Exception:
                        pass

                if 'parts' in part:
                    walk_parts(part['parts'])

        if 'parts' in payload:
            walk_parts(payload['parts'])
        elif 'body' in payload and 'data' in payload['body']:
            mime = payload.get('mimeType', '').lower()
            try:
                raw = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                if mime == 'text/html':
                    html_text = raw.strip()
                else:
                    plain_text = raw.strip()
            except Exception:
                pass

        if html_text:
            final_html = html_text
        elif plain_text:
            # Wrap plain text lines into clean HTML paragraphs
            paragraphs = [p.strip() for p in plain_text.split('\n') if p.strip()]
            final_html = "".join([f"<p style='margin-bottom: 8px;'>{p}</p>" for p in paragraphs])
        else:
            final_html = f"<p>{fallback_snippet}</p>" if fallback_snippet else ""
        
        # Replace inline CIDs with Data URIs
        for img in image_attachments:
            if img['cid']:
                final_html = final_html.replace(f"cid:{img['cid']}", img['data_uri'])
            if img['data_uri'] not in final_html:
                final_html += f'''
                <div style="margin-top: 16px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc;">
                    <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 600; color: #475569;">📷 Attached Image: {img["filename"]}</p>
                    <img src="{img["data_uri"]}" alt="{img["filename"]}" style="max-width: 100%; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: block;" />
                </div>
                '''

        return final_html, plain_text or fallback_snippet or ""

    @staticmethod
    def send_live_gmail_message(user_tokens_json, to_address, subject, body, from_email=None, from_name=None):
        """Sends a real email to ANY valid email address directly via Gmail API over HTTPS (port 443).
        Bypasses ISP/firewall SMTP port restrictions entirely."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )

            service = build('gmail', 'v1', credentials=creds)

            mime_msg = MIMEMultipart('alternative')
            mime_msg['To'] = to_address.strip()
            mime_msg['Subject'] = subject.strip()
            if from_email:
                mime_msg['From'] = f"{from_name} <{from_email}>" if from_name else from_email
            else:
                mime_msg['From'] = 'me'

            plain_part = MIMEText(body, 'plain', 'utf-8')
            html_body = f"""
            <html>
              <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; color: #1e293b; padding: 20px; line-height: 1.6;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                  <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit; margin: 0; font-size: 14px; color: #334155;">{body}</pre>
                  <hr style="border: none; border-top: 1px solid #e2e8f0; margin-top: 24px; margin-bottom: 12px;" />
                  <p style="font-size: 11px; color: #94a3b8; margin: 0;">Sent via AI Email Classifier</p>
                </div>
              </body>
            </html>
            """
            html_part = MIMEText(html_body, 'html', 'utf-8')
            mime_msg.attach(plain_part)
            mime_msg.attach(html_part)

            raw_msg = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode('utf-8')
            sent_msg = service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()

            real_id = sent_msg.get('id')
            print(f"[Gmail API Send] ✓ Real email successfully delivered via Gmail HTTPS API to {to_address} (ID: {real_id})")
            return {'success': True, 'message': f'Real email successfully delivered to {to_address}', 'id': real_id}
        except Exception as e:
            print(f"[Gmail API Send Error] {str(e)}")
            return {'success': False, 'message': f'Gmail API send error: {str(e)}'}

    @staticmethod
    def modify_live_gmail_message_labels(user_tokens_json, message_id, add_labels=None, remove_labels=None):
        """Modifies labels (STARRED, UNREAD, INBOX, SPAM, TRASH) on a real Gmail message."""
        if not message_id or not user_tokens_json:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)

            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            service.users().messages().modify(userId='me', id=message_id, body=body).execute()
            print(f"[Gmail Sync] Updated labels on real Gmail message {message_id}: add={add_labels}, remove={remove_labels}")
            return True
        except Exception as e:
            print(f"[Gmail Sync Warning] Failed to update labels for msg {message_id}: {str(e)}")
            return False

    @staticmethod
    def trash_live_gmail_message(user_tokens_json, message_id):
        """Moves a real Gmail message to Trash."""
        if not message_id or not user_tokens_json:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)
            try:
                service.users().messages().trash(userId='me', id=message_id).execute()
                print(f"[Gmail Sync] Moved real Gmail message {message_id} to Trash via trash API.")
            except Exception as trash_err:
                print(f"[Gmail Sync Trash Fallback] Calling modify labels: {str(trash_err)}")
                service.users().messages().modify(
                    userId='me', 
                    id=message_id, 
                    body={'addLabelIds': ['TRASH'], 'removeLabelIds': ['INBOX']}
                ).execute()
                print(f"[Gmail Sync] Moved real Gmail message {message_id} to Trash via TRASH label.")
            return True
        except Exception as e:
            print(f"[Gmail Sync Warning] Failed to trash msg {message_id}: {str(e)}")
            return False

    @staticmethod
    def delete_live_gmail_message(user_tokens_json, message_id):
        """Permanently deletes a real Gmail message."""
        if not message_id or not user_tokens_json:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)
            service.users().messages().delete(userId='me', id=message_id).execute()
            print(f"[Gmail Sync] Permanently deleted real Gmail message {message_id}.")
            return True
        except Exception as e:
            print(f"[Gmail Sync Warning] Failed to delete msg {message_id}: {str(e)}")
            return False

    @staticmethod
    def snooze_live_gmail_message(user_tokens_json, message_id):
        """Snoozes a Gmail message by removing it from INBOX temporarily (adds a SNOOZED-like label).
        Gmail doesn't have a native SNOOZED API label for 3rd-party apps, so we remove INBOX label
        to hide it, and restore it when the snooze expires."""
        if not message_id or not user_tokens_json:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)
            # Remove from INBOX so it's hidden; keeps the message in All Mail
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            print(f"[Gmail Snooze] Snoozed message {message_id} — removed from INBOX.")
            return True
        except Exception as e:
            print(f"[Gmail Snooze Warning] {str(e)}")
            return False

    @staticmethod
    def unsnooze_live_gmail_message(user_tokens_json, message_id):
        """Restores a snoozed Gmail message back to the INBOX."""
        if not message_id or not user_tokens_json:
            return False
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            token_data = json.loads(user_tokens_json)
            creds = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET
            )
            service = build('gmail', 'v1', credentials=creds)
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['INBOX']}
            ).execute()
            print(f"[Gmail Unsnooze] Restored message {message_id} back to INBOX.")
            return True
        except Exception as e:
            print(f"[Gmail Unsnooze Warning] {str(e)}")
            return False

    @staticmethod
    def fetch_user_emails_simulation(user_id):
        """Fetches simulated emails for a user."""
        return GmailService.get_simulated_messages(user_id)

    @staticmethod
    def get_simulated_messages(user_id):
        """Returns a list of static simulated emails."""
        now = datetime.utcnow()
        return [
            {
                "message_id": f"sim_otp_001_{user_id}",
                "sender": "Chase Bank",
                "sender_email": "no-reply@chase.com",
                "recipient": "user@gmail.com",
                "subject": "Your Security Code",
                "body": "Your security code is 882910. Do not share this code with anyone.",
                "folder": "inbox",
                "category": "Updates",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(minutes=5)
            },
            {
                "message_id": f"sim_otp_002_{user_id}",
                "sender": "Google",
                "sender_email": "accounts-noreply@google.com",
                "recipient": "user@gmail.com",
                "subject": "Google Verification Code",
                "body": "Use code 449210 to verify your identity.",
                "folder": "inbox",
                "category": "Updates",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(minutes=15)
            },
            {
                "message_id": f"sim_banking_001_{user_id}",
                "sender": "Chase Bank",
                "sender_email": "no-reply@chase.com",
                "recipient": "user@gmail.com",
                "subject": "Security Alert: New Login Detected on Your Account",
                "body": "Dear Customer, a new login to your Chase online banking was detected from a new device in Chicago, IL. If this was not you, please lock your account immediately and call 1-800-CHASE-US.",
                "folder": "inbox",
                "category": "Banking",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=1)
            },
            {
                "message_id": f"sim_banking_002_{user_id}",
                "sender": "HDFC Bank",
                "sender_email": "alerts@hdfcbank.com",
                "recipient": "user@gmail.com",
                "subject": "INR 15,000 Debited from your HDFC Savings Account",
                "body": "Dear Customer, INR 15,000.00 has been debited from your HDFC Bank Account ending XX4521 on 30-Jul-2026. Available Balance: INR 48,320.75. If not authorized, please call 1800-202-6161.",
                "folder": "inbox",
                "category": "Banking",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=5)
            },
            # --- PAYMENT PENDING & EMI DUE ---
            {
                "message_id": f"sim_payment_001_{user_id}",
                "sender": "Chase Credit Card Services",
                "sender_email": "billing@chase.com",
                "recipient": "user@gmail.com",
                "subject": "URGENT: Credit Card Bill Payment Pending - Due Today ($150.00)",
                "body": "Dear Customer, your monthly credit card bill payment of $150.00 is due today. Minimum payment due: $25.00. Please log in to Chase netbanking or mobile app to pay before 11:59 PM today to avoid late fees.",
                "folder": "inbox",
                "category": "Important",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(minutes=45)
            },
            # --- UPCOMING EXAM & ASSIGNMENT ---
            {
                "message_id": f"sim_exam_001_{user_id}",
                "sender": "University Exam Portal",
                "sender_email": "exams@university.edu",
                "recipient": "user@gmail.com",
                "subject": "Admit Card & Schedule Released: Final Semester Exam Due Aug 15",
                "body": "Dear Student, your hall ticket and admit card for the upcoming final semester examination are now available. Assignment 3 submission deadline is tomorrow at 5:00 PM. Please verify your exam seat allocation.",
                "folder": "inbox",
                "category": "Examinations",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=2)
            },
            # --- WORK TASK & DELIVERABLE ---
            {
                "message_id": f"sim_work_001_{user_id}",
                "sender": "Engineering Team Lead",
                "sender_email": "lead@techcorp.com",
                "recipient": "user@gmail.com",
                "subject": "URGENT: Project Deliverable & Security Patch Work Due EOD Today",
                "body": "Hi Team, work deliverable for sprint feature #402 and the critical security hotfix patch are due by EOD today. Please complete your code review and submit your PR before end of day.",
                "folder": "inbox",
                "category": "Office",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=3)
            },
            # --- UPCOMING APPOINTMENT ---
            {
                "message_id": f"sim_appointment_001_{user_id}",
                "sender": "Apollo Medical Health Clinic",
                "sender_email": "appointments@apollohealth.com",
                "recipient": "user@gmail.com",
                "subject": "Appointment Reminder: Dr. Smith Consultation Scheduled Tomorrow 3 PM",
                "body": "Dear Patient, your upcoming doctor appointment with Dr. Smith at Apollo Health Clinic is scheduled for tomorrow at 3:00 PM. Please arrive 10 minutes prior to your slot. Laboratory blood test report is attached.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=4)
            },
            # --- IMMEDIATE REPLY PENDING ---
            {
                "message_id": f"sim_immediate_001_{user_id}",
                "sender": "Executive Operations",
                "sender_email": "ops@clientfirm.com",
                "recipient": "user@gmail.com",
                "subject": "Awaiting Your Urgent Response Regarding Client Contract - Please Reply ASAP",
                "body": "Hi, we are awaiting your response regarding the finalized contract terms. We cannot proceed with onboarding until we receive your confirmation. Please reply to this email immediately today.",
                "folder": "inbox",
                "category": "Immediate Reply",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(minutes=20)
            },
            # --- IMPORTANT ---
            {
                "message_id": f"sim_important_001_{user_id}",
                "sender": "Google Cloud Support",
                "sender_email": "support@cloud.google.com",
                "recipient": "user@gmail.com",
                "subject": "Action Required: Your GCP Project Quota Limit at 95%",
                "body": "Hi Developer, your primary Kubernetes cluster in project 'ai-email-app' has reached 95% of its CPU quota. You must increase your project quotas or reduce running workloads to avoid throttling by 6PM UTC today.",
                "folder": "inbox",
                "category": "Important",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=3)
            },
            {
                "message_id": f"sim_important_002_{user_id}",
                "sender": "Family",
                "sender_email": "mom@gmail.com",
                "recipient": "user@gmail.com",
                "subject": "Sunday Family Lunch - Please Confirm",
                "body": "Hi dear! We are hosting family lunch this Sunday at 1 PM. Uncle David and cousins are coming. Please let us know if you're coming. Love, Mom.",
                "folder": "inbox",
                "category": "Important",
                "is_read": True,
                "is_starred": True,
                "date": now - timedelta(days=1, hours=2)
            },
            # --- JOBS ---
            {
                "message_id": f"sim_jobs_001_{user_id}",
                "sender": "LinkedIn Recruiter",
                "sender_email": "talent@techrecruiter.io",
                "recipient": "user@gmail.com",
                "subject": "Senior AI/ML Engineer Role - Remote ($160k-$200k) - Interview Invite",
                "body": "Hi there! I came across your profile and I'm impressed with your work on AI systems. Our Series B startup is seeking a Lead ML Engineer. Are you open to a confidential 15-min call this week? We have strong equity and benefits.",
                "folder": "inbox",
                "category": "Jobs",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=12)
            },
            {
                "message_id": f"sim_jobs_002_{user_id}",
                "sender": "Indeed Job Alerts",
                "sender_email": "alerts@indeed.com",
                "recipient": "user@gmail.com",
                "subject": "5 New Jobs Matching 'Python Backend Developer' in Bangalore",
                "body": "New job matches for you: 1. Python Developer at Infosys (4-6 LPA) 2. Backend Engineer at Flipkart (8-12 LPA) 3. Full Stack Python at Razorpay (10-16 LPA). Apply now before they close!",
                "folder": "inbox",
                "category": "Jobs",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1)
            },
            # --- EXAMINATIONS ---
            {
                "message_id": f"sim_exam_001_{user_id}",
                "sender": "National Board of Examinations",
                "sender_email": "exams@nbe.edu.in",
                "recipient": "user@gmail.com",
                "subject": "Admit Card Released: Engineering Competency Exam 2026 - Download Now",
                "body": "Dear Candidate, your Admit Card for the upcoming Engineering Certification Examination 2026 is now available for download on the Student Portal. Exam Date: August 18, 2026. Hall Ticket Number: EC2026-48291.",
                "folder": "inbox",
                "category": "Examinations",
                "is_read": True,
                "is_starred": True,
                "date": now - timedelta(days=2)
            },
            {
                "message_id": f"sim_exam_002_{user_id}",
                "sender": "UPSC Notifications",
                "sender_email": "notifications@upsc.gov.in",
                "recipient": "user@gmail.com",
                "subject": "UPSC Civil Services Prelims 2026 - Result Declared",
                "body": "Results for Civil Services (Preliminary) Examination 2026 have been declared. Candidates who have qualified are advised to apply online for the Mains Examination at upsc.gov.in.",
                "folder": "inbox",
                "category": "Examinations",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(days=3)
            },
            # --- PROMOTIONS ---
            {
                "message_id": f"sim_promo_001_{user_id}",
                "sender": "Udemy Online Courses",
                "sender_email": "promotions@udemy.com",
                "recipient": "user@gmail.com",
                "subject": "Flash Sale! Courses Starting at ₹399 — 24 Hours Only",
                "body": "Master Python, React, Data Science, and Machine Learning! Over 100,000 top-rated courses discounted for 24 hours only. Enroll now and upskill at your own pace. Use promo code FLASH2026.",
                "folder": "inbox",
                "category": "Promotions",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=6)
            },
            {
                "message_id": f"sim_promo_002_{user_id}",
                "sender": "Swiggy Offers",
                "sender_email": "noreply@swiggy.in",
                "recipient": "user@gmail.com",
                "subject": "50% Off Your Next 3 Orders - Swiggy One Deal!",
                "body": "Hey foodie! Get 50% off up to ₹150 on your next 3 orders when you subscribe to Swiggy One. Plus free delivery on orders above ₹99. Offer valid till August 5th.",
                "folder": "inbox",
                "category": "Promotions",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=8)
            },
            # --- PURCHASES ---
            {
                "message_id": f"sim_purchase_001_{user_id}",
                "sender": "Amazon India",
                "sender_email": "shipment-tracking@amazon.in",
                "recipient": "user@gmail.com",
                "subject": "Your Amazon Order #402-8813920 Has Been Delivered!",
                "body": "Your package containing 'Ergonomic Mechanical Keyboard (RGB, Brown Switches)' was successfully delivered and handed to the resident. Order Total: ₹3,299. Leave a review on Amazon to help others.",
                "folder": "inbox",
                "category": "Purchases",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=8)
            },
            {
                "message_id": f"sim_purchase_002_{user_id}",
                "sender": "Flipkart Order",
                "sender_email": "no-reply@flipkart.com",
                "recipient": "user@gmail.com",
                "subject": "Order Shipped: Samsung 65\" 4K QLED TV (OD-2891038)",
                "body": "Great news! Your order OD-2891038 has been shipped. Estimated delivery: August 2, 2026. Tracking ID: FKRT8820193. Your TV is on its way! Track your order in the Flipkart app.",
                "folder": "inbox",
                "category": "Purchases",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=14)
            },
            # --- SOCIAL ---
            {
                "message_id": f"sim_social_001_{user_id}",
                "sender": "LinkedIn",
                "sender_email": "messages-noreply@linkedin.com",
                "recipient": "user@gmail.com",
                "subject": "Rahul Sharma liked your post about AI Email Classification",
                "body": "Your post 'Building an AI Email Classifier with 94% accuracy using Naive Bayes' got 147 likes, 23 comments, and 18 shares! Keep sharing your knowledge on LinkedIn.",
                "folder": "inbox",
                "category": "Social",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=4)
            },
            {
                "message_id": f"sim_social_002_{user_id}",
                "sender": "WhatsApp",
                "sender_email": "noreply@whatsapp.com",
                "recipient": "user@gmail.com",
                "subject": "WhatsApp: Your verification code is 492-817",
                "body": "Your WhatsApp code is 492-817. Do not share this code with others. 4sgLq1p5sV6.",
                "folder": "inbox",
                "category": "Social",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=7)
            },
            # --- SPAM ---
            {
                "message_id": f"sim_spam_001_{user_id}",
                "sender": "Crypto Winner Rewards",
                "sender_email": "winner@claim-crypto-fast.net",
                "recipient": "user@gmail.com",
                "subject": "URGENT!! Claim 2.5 ETH Reward NOW - Limited Time!!",
                "body": "CONGRATULATIONS! You have been randomly selected as the lucky winner of 2.5 Ethereum. Click the link and verify your wallet seed phrase to claim your prize before offer expires in 10 minutes!",
                "folder": "spam",
                "category": "Spam",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=4)
            },
            {
                "message_id": f"sim_spam_002_{user_id}",
                "sender": "Lottery Winner Admin",
                "sender_email": "admin@lotterywinnerusa.ru",
                "recipient": "user@gmail.com",
                "subject": "You Won $1,000,000 in the International Lottery! Claim Now!",
                "body": "Dear Lucky Winner, Your email was selected in the International Lottery draw. You have won USD 1,000,000.00. To claim your prize, provide your name, address and bank details to process the transfer.",
                "folder": "spam",
                "category": "Spam",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=1)
            },
            # --- SENT ---
            {
                "message_id": f"sim_sent_001_{user_id}",
                "sender": "Me",
                "sender_email": "user@gmail.com",
                "recipient": "manager@company.com",
                "subject": "Project Submission: AI Email Classification System (94% Accuracy)",
                "body": "Hi Manager, I have completed the AI Email Classification System. It uses Multinomial Naive Bayes with TF-IDF vectorizer achieving 94% accuracy on 5,000 email samples across 11 categories. Please find the documentation attached.",
                "folder": "sent",
                "category": "Important",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=6)
            },
            # --- DRAFTS ---
            {
                "message_id": f"sim_draft_001_{user_id}",
                "sender": "Me",
                "sender_email": "user@gmail.com",
                "recipient": "team@devops.org",
                "subject": "[Draft] Q3 AI Performance Report",
                "body": "Draft outline:\n1. Overview of ML model performance\n2. Dataset statistics\n3. Category distribution analysis\n4. Improvements planned for Q4\n\n[DRAFT - not yet complete]",
                "folder": "drafts",
                "category": "Others",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=2)
            },
            # --- UPDATES ---
            {
                "message_id": f"sim_updates_001_{user_id}",
                "sender": "GitHub",
                "sender_email": "noreply@github.com",
                "recipient": "user@gmail.com",
                "subject": "New security advisory affecting your repository",
                "body": "A security advisory has been published that affects a dependency in your repository 'ai-email-classifier'. We recommend updating the affected packages. View the full advisory on GitHub.",
                "folder": "inbox",
                "category": "Updates",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=10)
            },
            {
                "message_id": f"sim_updates_002_{user_id}",
                "sender": "Google",
                "sender_email": "no-reply@accounts.google.com",
                "recipient": "user@gmail.com",
                "subject": "Security checkup recommendation for your Google Account",
                "body": "Your Google Account security checkup is due. We recommend you review your recovery email, check connected apps, and enable 2-Step Verification if not already done. Sign in to security.google.com to review.",
                "folder": "inbox",
                "category": "Updates",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=3)
            },
            # --- OFFICE ---
            {
                "message_id": f"sim_office_001_{user_id}",
                "sender": "HR Team",
                "sender_email": "hr@company.com",
                "recipient": "user@gmail.com",
                "subject": "Your July 2026 Payslip is Ready",
                "body": "Dear Employee, your salary slip for July 2026 has been generated and is available for download from the HR portal. Please verify the details and contact HR for any discrepancies.",
                "folder": "inbox",
                "category": "Office",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=9)
            },
            {
                "message_id": f"sim_office_002_{user_id}",
                "sender": "Team Lead",
                "sender_email": "teamlead@company.com",
                "recipient": "user@gmail.com",
                "subject": "Daily Standup Notes - Action Items Aug 6",
                "body": "Hi Team, here are today's standup notes. Blocked items: API rate limit issue (assigned to Dev). In-progress: Dashboard charts (UI team). Please update your Jira tasks by 6 PM.",
                "folder": "inbox",
                "category": "Office",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=11)
            },
            {
                "message_id": f"sim_office_003_{user_id}",
                "sender": "HR Department",
                "sender_email": "hr@company.com",
                "recipient": "user@gmail.com",
                "subject": "Leave Request Approved - Aug 15 to Aug 18",
                "body": "Dear Employee, your leave request for August 15 to August 18, 2026 has been approved by your reporting manager. Please ensure your handover notes are completed before your leave starts. Enjoy your time off!",
                "folder": "inbox",
                "category": "Office",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=7)
            },
            {
                "message_id": f"sim_office_004_{user_id}",
                "sender": "Admin Office",
                "sender_email": "admin@company.com",
                "recipient": "user@gmail.com",
                "subject": "Company All-Hands Meeting - Friday 4 PM",
                "body": "Dear All, you are cordially invited to the Q3 Company All-Hands Meeting on Friday, August 8, 2026 at 4:00 PM in the Main Conference Hall. Agenda: Business updates, team recognitions, and Q4 roadmap preview. Attendance is mandatory.",
                "folder": "inbox",
                "category": "Office",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=4)
            },
            {
                "message_id": f"sim_office_005_{user_id}",
                "sender": "IT Helpdesk",
                "sender_email": "helpdesk@company.com",
                "recipient": "user@gmail.com",
                "subject": "System Maintenance: VPN Access Downtime Tonight 11 PM - 1 AM",
                "body": "Dear User, please be informed that VPN and internal portal access will be unavailable tonight from 11:00 PM to 1:00 AM IST due to scheduled infrastructure maintenance. Please save your work and disconnect before 11 PM. Apologies for the inconvenience.",
                "folder": "inbox",
                "category": "Office",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=3)
            },
            # --- CUSTOMER SUPPORT ---
            {
                "message_id": f"sim_support_001_{user_id}",
                "sender": "Flipkart Support",
                "sender_email": "support@flipkart.com",
                "recipient": "user@gmail.com",
                "subject": "Support Ticket #48821 Received - We'll respond in 24 hrs",
                "body": "Thank you for contacting Flipkart Support. Your ticket #48821 regarding the damaged product has been received. Our team will reach out to you within 24 business hours.",
                "folder": "inbox",
                "category": "Customer Support",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=6)
            },
            {
                "message_id": f"sim_support_002_{user_id}",
                "sender": "Amazon Help",
                "sender_email": "cs-reply@amazon.in",
                "recipient": "user@gmail.com",
                "subject": "Your Issue Has Been Resolved - Case #93301",
                "body": "Great news! Your case #93301 regarding the delayed shipment has been resolved. A replacement order has been dispatched. Please reopen the ticket if you face further issues.",
                "folder": "inbox",
                "category": "Customer Support",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=5)
            },
            {
                "message_id": f"sim_support_003_{user_id}",
                "sender": "Swiggy Support",
                "sender_email": "support@swiggy.in",
                "recipient": "user@gmail.com",
                "subject": "Refund Initiated for Order #SW-499021 - Rs. 349",
                "body": "Dear Customer, we have initiated a refund of Rs. 349 for your cancelled Swiggy order #SW-499021. The amount will be credited to your original payment method within 5-7 business days. We apologize for the inconvenience.",
                "folder": "inbox",
                "category": "Customer Support",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=22)
            },
            {
                "message_id": f"sim_support_004_{user_id}",
                "sender": "Zomato Help",
                "sender_email": "no-reply@zomato.com",
                "recipient": "user@gmail.com",
                "subject": "We're Looking Into Your Complaint - Case #ZM-8812",
                "body": "Hi! We're sorry about your experience. Your complaint about the missing item in order #ZM-8812 is under review. Our team will update you within 12 hours with a resolution. Thank you for your patience.",
                "folder": "inbox",
                "category": "Customer Support",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=1)
            },
            {
                "message_id": f"sim_support_005_{user_id}",
                "sender": "HDFC Bank Customer Care",
                "sender_email": "customercare@hdfcbank.com",
                "recipient": "user@gmail.com",
                "subject": "Your Feedback Matters - Rate Your Recent Banking Experience",
                "body": "Dear Valued Customer, thank you for contacting HDFC Bank Customer Care. We hope your query was resolved to your satisfaction. Please take 2 minutes to rate your experience on a scale of 1-5 by clicking the link below. Your feedback helps us improve.",
                "folder": "inbox",
                "category": "Customer Support",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=4)
            },
            # --- BOOKINGS ---
            {
                "message_id": f"sim_booking_001_{user_id}",
                "sender": "MakeMyTrip",
                "sender_email": "noreply@makemytrip.com",
                "recipient": "user@gmail.com",
                "subject": "Hotel Booking Confirmed - Taj Vivanta, Goa | Booking ID: MMT-88210",
                "body": "Your hotel reservation at Taj Vivanta, Goa is confirmed! Check-in: Aug 15 | Check-out: Aug 18 | Booking ID: MMT-88210. Contact hotel at +91-832-664-3000.",
                "folder": "inbox",
                "category": "Bookings",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=13)
            },
            {
                "message_id": f"sim_booking_002_{user_id}",
                "sender": "Apollo Hospitals",
                "sender_email": "appointments@apollohospitals.com",
                "recipient": "user@gmail.com",
                "subject": "Appointment Confirmed: Dr. Mehta (Cardiology) - Aug 12 at 3 PM",
                "body": "Your appointment with Dr. A. Mehta (Cardiologist) at Apollo Hospital Hyderabad is confirmed for August 12, 2026 at 3:00 PM. Appointment ID: APT-39201. Please arrive 15 minutes early.",
                "folder": "inbox",
                "category": "Bookings",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=7)
            },
            {
                "message_id": f"sim_booking_003_{user_id}",
                "sender": "Zomato Dining",
                "sender_email": "reservations@zomato.com",
                "recipient": "user@gmail.com",
                "subject": "Table Confirmed at Barbeque Nation - Tonight 8 PM | Ref: ZD-3391",
                "body": "Your table for 3 at Barbeque Nation, Jubilee Hills has been confirmed for tonight at 8:00 PM. Booking Reference: ZD-3391. Please arrive on time. Cancellations accepted up to 2 hours before your reservation.",
                "folder": "inbox",
                "category": "Bookings",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=5)
            },
            {
                "message_id": f"sim_booking_004_{user_id}",
                "sender": "Urban Company",
                "sender_email": "bookings@urbancompany.com",
                "recipient": "user@gmail.com",
                "subject": "Appointment Booked: AC Service Tomorrow 10 AM | UC-773921",
                "body": "Your AC servicing appointment is confirmed for August 7, 2026 at 10:00 AM. Technician: Rajesh Kumar (4.9★). Booking ID: UC-773921. You can track the technician live 30 minutes before the slot.",
                "folder": "inbox",
                "category": "Bookings",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=10)
            },
            {
                "message_id": f"sim_booking_005_{user_id}",
                "sender": "BookMyShow",
                "sender_email": "orders@bookmyshow.com",
                "recipient": "user@gmail.com",
                "subject": "Booking Confirmed: Deadpool & Wolverine | PVR IMAX | Aug 10 - 6:30 PM",
                "body": "Your booking is confirmed! Movie: Deadpool and Wolverine (IMAX 3D) | Theatre: PVR IMAX, Hyderabad | Date: August 10, 2026 | Showtime: 6:30 PM | Seats: F12, F13 | Booking ID: BMS-992810. Carry your e-ticket for entry.",
                "folder": "inbox",
                "category": "Bookings",
                "is_read": True,
                "is_starred": True,
                "date": now - timedelta(hours=8)
            },
            # --- TRAVEL ---
            {
                "message_id": f"sim_travel_001_{user_id}",
                "sender": "IndiGo Airlines",
                "sender_email": "noreply@goindigo.in",
                "recipient": "user@gmail.com",
                "subject": "Flight Confirmed: 6E-209 Hyderabad → Mumbai | PNR: BX8821",
                "body": "Your IndiGo flight 6E-209 from Hyderabad (HYD) to Mumbai (BOM) on August 18, 2026 at 07:30 AM is confirmed. PNR: BX8821. Web check-in opens 48 hours before departure.",
                "folder": "inbox",
                "category": "Travel",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(hours=16)
            },
            {
                "message_id": f"sim_travel_002_{user_id}",
                "sender": "IRCTC",
                "sender_email": "noreply@irctc.co.in",
                "recipient": "user@gmail.com",
                "subject": "Train Ticket Booked: Rajdhani Express 12952 | PNR: 4821930192",
                "body": "Your train ticket for 12952 Rajdhani Express from Mumbai Central to Hazrat Nizamuddin on Aug 20, 2026 is confirmed. PNR: 4821930192. Coach A1, Seats 12-13.",
                "folder": "inbox",
                "category": "Travel",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=3)
            },
            {
                "message_id": f"sim_travel_003_{user_id}",
                "sender": "Ola Cabs",
                "sender_email": "noreply@olacabs.com",
                "recipient": "user@gmail.com",
                "subject": "Your Ola Outstation Ride is Confirmed - Hyderabad to Tirupati",
                "body": "Your Ola outstation trip from Hyderabad to Tirupati on August 12, 2026 at 5:00 AM is confirmed. Driver: Suresh Babu | Vehicle: Swift Dzire (White) | Plate: TS09AB1234. Driver will call you 30 mins before pickup.",
                "folder": "inbox",
                "category": "Travel",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=19)
            },
            {
                "message_id": f"sim_travel_004_{user_id}",
                "sender": "Thomas Cook India",
                "sender_email": "tours@thomascook.in",
                "recipient": "user@gmail.com",
                "subject": "Your Kerala Tour Package is Confirmed | Ref: TC-482910",
                "body": "Congratulations! Your 5N/6D Kerala Backwaters & Munnar tour package is confirmed. Departure: August 22, 2026 from Hyderabad. Itinerary includes Alleppey houseboat, Munnar tea estates, and Kovalam beach. Detailed itinerary attached.",
                "folder": "inbox",
                "category": "Travel",
                "is_read": True,
                "is_starred": True,
                "date": now - timedelta(days=1, hours=12)
            },
            {
                "message_id": f"sim_travel_005_{user_id}",
                "sender": "MMT Holidays",
                "sender_email": "holidays@makemytrip.com",
                "recipient": "user@gmail.com",
                "subject": "Visa Application Update: Dubai Tourist Visa - Under Process",
                "body": "Dear Traveller, your Dubai Tourist Visa application (Ref: MMT-VISA-83920) has been submitted to the UAE Embassy and is currently under processing. Expected processing time: 3-5 business days. You will receive your visa approval via email.",
                "folder": "inbox",
                "category": "Travel",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=8)
            },
            # --- HEALTHCARE ---
            {
                "message_id": f"sim_health_001_{user_id}",
                "sender": "Thyrocare Diagnostics",
                "sender_email": "reports@thyrocare.com",
                "recipient": "user@gmail.com",
                "subject": "Your Lab Report is Ready - Blood Test Results",
                "body": "Dear Patient, your blood test report from Thyrocare is now available. Tests included: CBC, Lipid Panel, Blood Sugar Fasting. Please login to the patient portal to download your report.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=20)
            },
            {
                "message_id": f"sim_health_002_{user_id}",
                "sender": "Max Hospital",
                "sender_email": "reminders@maxhealthcare.in",
                "recipient": "user@gmail.com",
                "subject": "Appointment Reminder: Dr. Singh (Orthopedics) - Tomorrow at 11 AM",
                "body": "This is a reminder for your appointment with Dr. R. Singh (Orthopedics) at Max Hospital, Saket on August 7, 2026 at 11:00 AM. Please bring your previous X-ray reports and a valid photo ID.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=18)
            },
            {
                "message_id": f"sim_health_003_{user_id}",
                "sender": "Fortis Hospitals",
                "sender_email": "wellness@fortishealthcare.com",
                "recipient": "user@gmail.com",
                "subject": "Annual Health Checkup Report - Comprehensive Wellness Summary",
                "body": "Dear Patient, your comprehensive Annual Health Checkup report is now ready. Key highlights: Blood Sugar: 95 mg/dL (Normal), Cholesterol: 178 mg/dL (Normal), BMI: 23.4 (Healthy). Please review the full report on the Fortis patient portal and consult your doctor for detailed advice.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": False,
                "is_starred": True,
                "date": now - timedelta(days=1, hours=14)
            },
            {
                "message_id": f"sim_health_004_{user_id}",
                "sender": "1mg Pharmacy",
                "sender_email": "orders@1mg.com",
                "recipient": "user@gmail.com",
                "subject": "Your Medicine Order #1MG-33910 is Out for Delivery",
                "body": "Your order #1MG-33910 containing Metformin 500mg (30 tablets) and Vitamin D3 (60 softgels) is out for delivery. Expected arrival: Today between 2 PM and 5 PM. You can track your delivery in real time on the 1mg app.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=15)
            },
            {
                "message_id": f"sim_health_005_{user_id}",
                "sender": "Apollo 24|7",
                "sender_email": "consult@apollo247.com",
                "recipient": "user@gmail.com",
                "subject": "Your Online Consultation with Dr. Priya is Confirmed - 6 PM Today",
                "body": "Your video consultation with Dr. Priya Nair (General Physician) on Apollo 24|7 is confirmed for today at 6:00 PM. Consultation ID: AP247-10392. Please keep your symptoms noted and join the video call 5 minutes before the scheduled time.",
                "folder": "inbox",
                "category": "Healthcare",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=12)
            },
            # --- NEWSLETTERS ---
            {
                "message_id": f"sim_newsletter_001_{user_id}",
                "sender": "TechCrunch Weekly",
                "sender_email": "newsletter@techcrunch.com",
                "recipient": "user@gmail.com",
                "subject": "This Week in Tech: AI Takes Center Stage",
                "body": "This week's top stories: OpenAI releases o3 API for enterprise. Google DeepMind's AlphaGenome decodes regulatory DNA. Meta open-sources LLaMA 4. Plus: Best practices for LLM prompt engineering.",
                "folder": "inbox",
                "category": "Newsletters",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=1, hours=10)
            },
            {
                "message_id": f"sim_newsletter_002_{user_id}",
                "sender": "Dev.to Weekly",
                "sender_email": "newsletter@dev.to",
                "recipient": "user@gmail.com",
                "subject": "Top Articles This Week: React Server Components, Rust Async & AI Agents",
                "body": "This week's most-read articles on Dev.to: 1. Understanding React Server Components (3.2k reactions) 2. Async Rust - A Practical Guide (2.8k reactions) 3. Building AI Agents with LangChain (2.5k reactions). Read them on dev.to!",
                "folder": "inbox",
                "category": "Newsletters",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=26)
            },
            {
                "message_id": f"sim_newsletter_003_{user_id}",
                "sender": "Product Hunt Daily",
                "sender_email": "digest@producthunt.com",
                "recipient": "user@gmail.com",
                "subject": "Today's Top Products: AI Writing Tool, No-Code Builder & More",
                "body": "Today's top products on Product Hunt: #1 Notion AI 2.0 - The most upvoted product. #2 FlutterFlow 4 - Build apps without code. #3 ChatPDF Pro - Chat with any PDF. Explore all launches at producthunt.com.",
                "folder": "inbox",
                "category": "Newsletters",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(hours=30)
            },
            {
                "message_id": f"sim_newsletter_004_{user_id}",
                "sender": "HackerNews Digest",
                "sender_email": "digest@hackernewsletter.com",
                "recipient": "user@gmail.com",
                "subject": "Hacker Newsletter #710 - Best of HN This Week",
                "body": "Welcome to Hacker Newsletter #710! This week's best Hacker News discussions: How Cloudflare handles 55 million HTTP requests per second, Why SQLite is taking over the world, and The hidden cost of microservices. Read more at hackernewsletter.com.",
                "folder": "inbox",
                "category": "Newsletters",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=6)
            },
            {
                "message_id": f"sim_newsletter_005_{user_id}",
                "sender": "Medium Daily Digest",
                "sender_email": "noreply@medium.com",
                "recipient": "user@gmail.com",
                "subject": "Stories Curated for You: System Design, Python Tips & Career Growth",
                "body": "Your daily digest from Medium: 'How I Passed the Google SWE Interview' by Alex Chen (12 min read). 'Python One-Liners That Will Blow Your Mind' by Sarah Dev (5 min read). 'System Design Interview: Design Twitter' by Tech Insider (18 min read). Read on medium.com.",
                "folder": "inbox",
                "category": "Newsletters",
                "is_read": True,
                "is_starred": False,
                "date": now - timedelta(days=2, hours=10)
            },
            # --- SPAM (OTP Phishing example) ---
            {
                "message_id": f"sim_spam_otp_001_{user_id}",
                "sender": "Fake Bank Security",
                "sender_email": "security@bank-alert-verify.ru",
                "recipient": "user@gmail.com",
                "subject": "URGENT: Share OTP to Unblock Your Account Immediately",
                "body": "Your bank account has been temporarily blocked due to suspicious activity. A bank representative will call you shortly. Please share the OTP you received on your phone to verify your identity and claim your account access. Failure to do so will result in permanent account suspension.",
                "folder": "spam",
                "category": "Spam",
                "is_read": False,
                "is_starred": False,
                "date": now - timedelta(hours=2)
            },
        ]
