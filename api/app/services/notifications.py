"""Email notifications sent over SMTP. Sending runs as a background task after the response,
so a slow or failing mail server never blocks or breaks the request; failures are logged."""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from fastapi import BackgroundTasks

from app.core.config import get_settings
from app.models import Ticket

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        log.warning("SMTP_HOST is not set; skipping email to %s (%s)", to, subject)
        return

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
