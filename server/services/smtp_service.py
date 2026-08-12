import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


class SMTPService:
    """Handles real email delivery via Gmail SMTP using an App Password."""

    @staticmethod
    def send_email(to_address: str, subject: str, body: str, from_name: str = None) -> dict:
        """
        Send a real email via Gmail SMTP.
        Tries port 465 (SSL) first, then falls back to port 587 (STARTTLS).
        """
        smtp_email    = current_app.config.get('SMTP_EMAIL', '').strip()
        smtp_password = current_app.config.get('SMTP_APP_PASSWORD', '').replace(' ', '').strip()
        smtp_host     = current_app.config.get('SMTP_HOST', 'smtp.gmail.com')

        if not smtp_email or not smtp_password:
            return {
                'success': False,
                'message': 'SMTP credentials are not configured. Please set SMTP_EMAIL and SMTP_APP_PASSWORD in .env'
            }

        # Build the MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{from_name} <{smtp_email}>" if from_name else smtp_email
        msg['To']      = to_address

        # Plain text part
        plain_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(plain_part)

        # HTML part
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #f9f9f9; border-radius: 8px; padding: 24px; border: 1px solid #e0e0e0;">
              <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit;">{body}</pre>
              <hr style="border: none; border-top: 1px solid #ddd; margin-top: 24px;" />
              <p style="font-size: 11px; color: #888;">Sent via AI Email Classifier App</p>
            </div>
          </body>
        </html>
        """
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        # --- Try port 465 (SSL) first ---
        try:
            context = ssl.create_default_context()
            print(f"[SMTPService] Trying port 465 (SSL) → {smtp_host}")
            with smtplib.SMTP_SSL(smtp_host, 465, context=context, timeout=15) as server:
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, to_address, msg.as_string())
            print(f"[SMTPService] ✓ Email sent via port 465 to {to_address}")
            return {'success': True, 'message': f'Email delivered to {to_address}'}

        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': (
                    'Gmail authentication failed. '
                    'Make sure SMTP_APP_PASSWORD is a valid Gmail App Password '
                    'and that 2-Step Verification is enabled on your Google account.'
                )
            }

        except (smtplib.SMTPException, OSError, TimeoutError) as e465:
            print(f"[SMTPService] Port 465 failed: {e465}. Trying port 587 (STARTTLS)...")

        # --- Fallback: port 587 (STARTTLS) ---
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, 587, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, to_address, msg.as_string())
            print(f"[SMTPService] ✓ Email sent via port 587 to {to_address}")
            return {'success': True, 'message': f'Email delivered to {to_address}'}

        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': (
                    'Gmail authentication failed. '
                    'Ensure your App Password is correct and 2-Step Verification is enabled.'
                )
            }

        except smtplib.SMTPRecipientsRefused:
            return {
                'success': False,
                'message': f'Recipient address "{to_address}" was rejected by the mail server.'
            }

        except smtplib.SMTPException as e:
            return {'success': False, 'message': f'SMTP error: {str(e)}'}

        except Exception as e:
            return {
                'success': False,
                'message': (
                    f'Could not connect to Gmail SMTP on ports 465 or 587. '
                    f'Your firewall or ISP may be blocking outbound email. '
                    f'Detail: {str(e)}'
                )
            }


smtp_service = SMTPService()
