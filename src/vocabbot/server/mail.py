"""The one e-mail the server sends: the link of password recovery, to the address typed.

The server keeps no address (only its hash); the learner types it on the page
"nie pamiętam hasła", and the message goes to that address when its hash
matches the account's. Without SMTP settings the server offers no recovery by
mail, and the administrator sets a new password as before.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from vocabbot.server.config import Mail

TIMEOUT = 20


def message(mail: Mail, to: str, subject: str, body: str) -> EmailMessage:
    out = EmailMessage()
    out["From"] = mail.sender
    out["To"] = to
    out["Subject"] = subject
    out.set_content(body)
    return out


def send(mail: Mail, to: str, subject: str, body: str) -> None:
    """Send one message; a failure raises OSError or smtplib.SMTPException."""
    letter = message(mail, to, subject, body)
    context = ssl.create_default_context()
    if mail.security == "ssl":
        with smtplib.SMTP_SSL(mail.host, mail.port, timeout=TIMEOUT, context=context) as smtp:
            if mail.user:
                smtp.login(mail.user, mail.password)
            smtp.send_message(letter)
        return
    with smtplib.SMTP(mail.host, mail.port, timeout=TIMEOUT) as smtp:
        if mail.security == "starttls":
            smtp.starttls(context=context)
        if mail.user:
            smtp.login(mail.user, mail.password)
        smtp.send_message(letter)
