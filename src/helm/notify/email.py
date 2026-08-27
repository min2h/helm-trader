from __future__ import annotations

import smtplib
from email.message import EmailMessage

from helm.db.models import User
from helm.settings import Settings


def send_email(settings: Settings, user: User, subject: str, body: str) -> bool:
    if not user.notify_email:
        return False
    to_addr = user.notify_address or user.email
    if not settings.smtp_host or not to_addr or "@users.helm" in to_addr:
        return False
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_addr
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
    return True
