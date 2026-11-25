from zoneinfo import ZoneInfo

from flask import current_app


def fmt_time(dt):
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    return dt.astimezone(tz).strftime("%A, %d %B %Y at %I:%M %p (%Z)")


def queue_email(to, subject, body):
    from .tasks import send_email

    try:
        send_email.delay(to, subject, body)
    except Exception:
        current_app.logger.exception("Could not queue email to %s", to)