"""
Gmail API service using OAuth 2.0.
Handles auth flow, token management, and sending emails with attachments.
"""

import base64
import logging
import os
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

import requests

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GMAIL_SCOPES,
)

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


# ── OAuth 2.0 Flow ───────────────────────────────────────────────────

def get_auth_url() -> str:
    """Build the Google OAuth 2.0 consent URL."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
    }

    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at,
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Token exchange failed: {e}")
        raise RuntimeError(f"Google token exchange failed: {str(e)}")


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access token."""
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
    }

    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return {
            "access_token": data["access_token"],
            "expires_at": expires_at,
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Token refresh failed: {e}")
        raise RuntimeError(f"Google token refresh failed: {str(e)}")


# ── Send Email ────────────────────────────────────────────────────────

def send_email(
    access_token: str,
    to_email: str,
    subject: str,
    body: str,
    attachment_path: str = None,
    cc: str = None,
) -> dict:
    """
    Send an email via Gmail API with optional PDF attachment.
    Returns the sent message metadata.
    """
    # Build MIME message
    if attachment_path:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain"))

        # Attach PDF
        if os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_filename = os.path.basename(attachment_path)
                pdf_attachment.add_header(
                    "Content-Disposition", "attachment", filename=pdf_filename
                )
                msg.attach(pdf_attachment)
        else:
            logger.warning(f"Attachment not found: {attachment_path}")
    else:
        msg = MIMEText(body, "plain")

    msg["To"] = to_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    # Base64url encode
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    # Send via Gmail API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"raw": raw_message}

    try:
        response = requests.post(
            GMAIL_SEND_URL, json=payload, headers=headers, timeout=15
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Email sent successfully. Message ID: {result.get('id')}")
        return {"status": "sent", "message_id": result.get("id")}
    except requests.exceptions.RequestException as e:
        logger.error(f"Email send failed: {e}")
        return {"status": "failed", "error": str(e)}
