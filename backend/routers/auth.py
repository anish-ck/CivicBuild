"""
OAuth 2.0 authentication router for Gmail API.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models.oauth_token import OAuthToken, OAuthTokenResponse
from services import gmail_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/login", tags=["Auth"])
def auth_login():
    """
    Redirect user to Google OAuth 2.0 consent screen.
    After consent, Google redirects back to /auth/callback.
    """
    auth_url = gmail_service.get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback", tags=["Auth"])
def auth_callback(
    code: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    """
    Google OAuth 2.0 callback endpoint.
    Exchanges authorization code for access + refresh tokens.
    Stores tokens in database.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received.")

    logger.info("Exchanging OAuth authorization code for tokens...")

    try:
        tokens = gmail_service.exchange_code_for_tokens(code)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Store tokens in DB (upsert: replace existing google token)
    existing = db.query(OAuthToken).filter(OAuthToken.provider == "google").first()
    if existing:
        existing.access_token = tokens["access_token"]
        if tokens.get("refresh_token"):
            existing.refresh_token = tokens["refresh_token"]
        existing.expires_at = tokens["expires_at"]
    else:
        token_record = OAuthToken(
            provider="google",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_at=tokens["expires_at"],
        )
        db.add(token_record)

    db.commit()
    logger.info("OAuth tokens stored successfully.")

    return {
        "status": "success",
        "message": "Google OAuth connected. You can now send emails via Gmail API.",
        "expires_at": str(tokens["expires_at"]),
    }


@router.get("/token-status", tags=["Auth"])
def token_status(db: Session = Depends(get_db)):
    """Check current OAuth token status."""
    token = db.query(OAuthToken).filter(OAuthToken.provider == "google").first()
    if not token:
        return {"status": "not_configured", "message": "No OAuth token. Visit /auth/login first."}

    return {
        "status": "configured",
        "provider": token.provider,
        "expires_at": str(token.expires_at),
        "has_refresh_token": token.refresh_token is not None,
    }
