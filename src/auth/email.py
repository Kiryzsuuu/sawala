"""Sends the password-reset email over SMTP (Gmail App Password or any
other SMTP provider). No-ops with a log warning if SMTP isn't configured,
so the rest of the app still runs without email set up yet."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.utils.env import EMAIL_CONFIGURED, SMTP_APP_PASSWORD, SMTP_FROM_NAME, SMTP_HOST, SMTP_PORT, SMTP_USER
from src.utils.logger import get_logger

logger = get_logger(__name__)


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    if not EMAIL_CONFIGURED:
        logger.warning(
            "SMTP belum dikonfigurasi (.env) - link reset password untuk %s: %s",
            to_email, reset_link,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset Password SAWALA"
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email

    text = f"Klik link berikut untuk reset password kamu:\n{reset_link}\n\nLink berlaku 1 jam."
    html = f"""
    <p>Klik link berikut untuk reset password kamu:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>Link berlaku 1 jam. Kalau kamu tidak meminta ini, abaikan saja email ini.</p>
    """
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.error("Gagal mengirim email reset password ke %s: %s", to_email, exc)
        return False
