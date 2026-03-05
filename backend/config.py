"""
Centralized configuration for the CivicBuild backend.
All environment variables and shared constants live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq LLM ─────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"

# ── Sarvam AI ─────────────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ── Google APIs ───────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback"
)
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# ── Reports directory ─────────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Advisory Disclaimer ──────────────────────────────────────────────
ADVISORY_DISCLAIMER = (
    "Preliminary advisory. Final approval subject to municipal authority verification."
)
