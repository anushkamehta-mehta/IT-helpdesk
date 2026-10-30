"""Email notifications, sent through Brevo's HTTPS API (when BREVO_API_KEY is set) or over SMTP.
Sending runs as a background task after the response, so a slow or failing mail server never
blocks or breaks the request; failures are logged."""
import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.models import Ticket

log = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.brevo_api_key:
        _send_with_brevo(to, subject, body)
    elif settings.smtp_host:
        _send_with_smtp(to, subject, body)
    else:
        log.warning("No email provider configured (BREVO_API_KEY or SMTP_HOST); skipping email to %s (%s)", to, subject)


def _send_with_brevo(to: str, subject: str, body: str) -> None:
    """HTTPS instead of SMTP: works on hosts that block SMTP ports (e.g. Render's free plan)."""
    settings = get_settings()
    payload = {
        "sender": {"name": settings.mail_from_name, "email": settings.smtp_from or settings.smtp_user},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode(),
        headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20):
            pass
    except urllib.error.HTTPError as e:
        log.error("Could not send email to %s (%s): Brevo said %s %s", to, subject, e.code, e.read().decode(errors="replace"))
    except (urllib.error.URLError, OSError):
        log.exception("Could not send email to %s (%s)", to, subject)


def _send_with_smtp(to: str, subject: str, body: str) -> None:
    settings = get_settings()

    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if settings.smtp_security == "ssl":
            smtp = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        with smtp:
            if settings.smtp_security == "starttls":
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError):
        log.exception("Could not send email to %s (%s)", to, subject)


def send_later(background_tasks: BackgroundTasks, to: str, subject: str, body: str) -> None:
    """Send after the response. On Vercel (serverless) the function may be frozen once the response
    is sent, so there the email is sent before responding instead."""
    if os.environ.get("VERCEL"):
        send_email(to, subject, body)
    else:
        background_tasks.add_task(send_email, to, subject, body)


def ticket_resolved_email(ticket: Ticket) -> tuple[str, str, str]:
    """(to, subject, body) telling the requester their ticket is resolved."""
    link = f"{get_settings().app_base_url.rstrip('/')}/tickets/{ticket.id}"
    resolver = ticket.assignee.full_name if ticket.assignee else "The IT team"
    body = f"""Hi {ticket.creator.full_name},

Good news: your IT helpdesk ticket has been resolved.

Ticket:       #{ticket.id} {ticket.title}
Category:     {ticket.category.name}
Resolved by:  {resolver}

Your request:
{ticket.description}

How it was resolved:
{ticket.resolution_notes}

If everything works, please open the ticket and close it. If the issue is not fixed,
open the ticket and click "Request changes" to tell the IT team what still needs doing:
{link}

IT Helpdesk
"""
    return ticket.creator.email, f"Ticket #{ticket.id} resolved: {ticket.title}", body
