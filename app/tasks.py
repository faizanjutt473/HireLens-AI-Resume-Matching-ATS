from celery import shared_task
from flask import current_app
from flask_mail import Message

from .extensions import mail


@shared_task(ignore_result=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_email(to, subject, body):
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.info(
            "EMAIL (mail not configured, not sent)\nTo: %s\nSubject: %s\n\n%s", to, subject, body
        )
        return
    mail.send(Message(subject=subject, recipients=[to], body=body))