from flask import render_template_string, current_app
from flask_mail import Mail, Message
from models import db, Notification
from flask_login import current_user
import smtplib
import time  # For retry

# Email template (unchanged)
EMAIL_TEMPLATE = '''
<html>
<body>
    <h2>Hello {{ user.username }}!</h2>
    <p>You have {{ unread_count }} unread notifications:</p>
    <ul>
    {% for notif in notifications %}
        <li>{{ notif.message }} - {{ notif.timestamp.strftime('%Y-%m-%d %H:%M') }}</li>
    {% endfor %}
    </ul>
    <p><a href="{{ url_for('notifications', _external=True) }}">View all</a> | <a href="{{ url_for('index', _external=True) }}">Back to Feed</a></p>
</body>
</html>
'''

def send_notification_digest(app):
    """Send email digest for current user's unread notifications."""
    if not current_user.is_authenticated or not current_user.email:
        return

    unread_notifs = db.session.query(Notification).filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.timestamp.desc()).all()

    if not unread_notifs:
        return

    with app.app_context():
        print(f"Debug: MAIL_USERNAME = {app.config.get('MAIL_USERNAME')}")  # Keep for now
        
        if 'mail' not in current_app.extensions:
            current_app.logger.warning("Flask-Mail not initialized—skipping email")
            return
        
        sender = app.config['MAIL_USERNAME']
        
        if not sender:
            current_app.logger.error("No MAIL_USERNAME configured—skipping email")
            return
        
        msg = Message(
            subject=f"You have {len(unread_notifs)} new notifications on Q&A App",
            sender=sender,
            recipients=[current_user.email],
            html=render_template_string(EMAIL_TEMPLATE, 
                                       user=current_user, 
                                       unread_count=len(unread_notifs),
                                       notifications=unread_notifs)
        )
        mail = current_app.extensions['mail']
        max_retries = 3
        for attempt in range(max_retries):
            try:
                mail.send(msg)
                print("Email sent successfully!")
                break
            except smtplib.SMTPServerDisconnected as e:
                current_app.logger.warning(f"SMTP connection closed on attempt {attempt+1}: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            except smtplib.SMTPSenderRefused as e:
                current_app.logger.error(f"SMTP auth failed: {e}. Check app password.")
                break
            except Exception as e:
                current_app.logger.error(f"Email send failed: {e}")
                if attempt == max_retries - 1:
                    current_app.logger.error("Max retries exceeded—email not sent.")
                else:
                    time.sleep(2 ** attempt)
        else:
            current_app.logger.error("Email send failed after retries.")