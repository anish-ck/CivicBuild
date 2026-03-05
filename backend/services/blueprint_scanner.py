"""
Blueprint Scanner service.
Extracts text from PDF or image files using Google Vision API,
then uses Groq LLM to extract structured building details.
"""

import base64
import json
import logging
from io import BytesIO

import requests
from openai import OpenAI
from pypdf import PdfReader

from config import GOOGLE_MAPS_API_KEY, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL

logger = logging.getLogger(__name__)

# Google Vision REST endpoint (uses the same API key as Google Maps)
VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

BLUEPRINT_EXTRACTION_PROMPT = """You are a building blueprint analysis assistant.
Extract structured building details from the following text extracted from a blueprint or building document.
Return strict JSON only.

Fields:
- total_area (string, e.g. "2500 sq ft" or null)
- overall_width (string, e.g. "45 ft" or null)
- overall_height (string, e.g. "30 ft" or null — this refers to the depth/length dimension of the building)
- floors (integer or null)
- floor_height (string, e.g. "10 ft" or null)
- seating_capacity (integer or null)
- number_of_exits (integer or null)
- number_of_staircases (integer or null)
- kitchen_present (boolean or null)

If a field is missing or unclear, return null for that field.
Return ONLY valid JSON, no extra text or explanation."""


def _get_groq_client() -> OpenAI:
    return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)


# ── Text Extraction ──────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file. Returns raw text string."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
        return full_text.strip()
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""


def extract_text_from_image(file_bytes: bytes) -> tuple[str, str]:
    """
    Extract text from an image using Google Vision API (TEXT_DETECTION).
    Returns (text, ocr_status) where ocr_status is one of:
      'success', 'empty', 'api_error', 'no_api_key', 'error'
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not configured — cannot use Vision API")
        return "", "no_api_key"

    try:
        # Encode image bytes to base64
        b64_image = base64.b64encode(file_bytes).decode("utf-8")

        payload = {
            "requests": [
                {
                    "image": {"content": b64_image},
                    "features": [
                        {"type": "TEXT_DETECTION", "maxResults": 50},
                        {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1},
                    ],
                }
            ]
        }

        resp = requests.post(
            VISION_API_URL,
            params={"key": GOOGLE_MAPS_API_KEY},
            json=payload,
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error(f"Google Vision API error {resp.status_code}: {resp.text[:500]}")
            return "", "api_error"

        result = resp.json()
        responses = result.get("responses", [])

        if not responses:
            return "", "empty"

        first = responses[0]

        # Check for errors in the response
        if "error" in first:
            logger.error(f"Vision API response error: {first['error']}")
            return "", "api_error"

        # Prefer DOCUMENT_TEXT_DETECTION (full text annotation)
        full_text_annotation = first.get("fullTextAnnotation", {})
        text = full_text_annotation.get("text", "")

        # Fallback to TEXT_DETECTION
        if not text:
            text_annotations = first.get("textAnnotations", [])
            if text_annotations:
                text = text_annotations[0].get("description", "")

        stripped = text.strip()
        status = "success" if stripped else "empty"
        logger.info(f"Google Vision extracted {len(stripped)} characters")
        return stripped, status

    except requests.exceptions.Timeout:
        logger.error("Google Vision API request timed out")
        return "", "api_error"
    except Exception as e:
        logger.error(f"Google Vision OCR failed: {e}")
        return "", "error"


def extract_text(file_bytes: bytes, content_type: str, filename: str) -> tuple[str, str]:
    """
    Route to the correct extraction method based on file type.
    Returns (text, ocr_status).
    """
    is_pdf = (
        content_type == "application/pdf"
        or (filename and filename.lower().endswith(".pdf"))
    )

    if is_pdf:
        text = extract_text_from_pdf(file_bytes)
        if len(text) < 50:
            logger.warning("PDF returned very little text (likely scanned).")
            status = "empty" if not text else "success"
        else:
            status = "success"
        return text, status
    else:
        # Image file (jpg, png, tiff, etc.) — use Google Vision API
        return extract_text_from_image(file_bytes)


# ── LLM Structured Extraction ────────────────────────────────────────

def extract_blueprint_details(raw_text: str) -> dict:
    """
    Send extracted text to Groq LLM and parse structured building details.
    Returns a dict with extracted fields (nulls for missing).
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not configured")
        return _empty_result()

    if not raw_text or len(raw_text.strip()) < 10:
        logger.warning("Extracted text too short for meaningful extraction")
        return _empty_result()

    client = _get_groq_client()

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": BLUEPRINT_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Blueprint text:\n{raw_text[:4000]}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=512,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        return {
            "total_area": parsed.get("total_area"),
            "overall_width": parsed.get("overall_width"),
            "overall_height": parsed.get("overall_height"),
            "floors": _safe_int(parsed.get("floors")),
            "floor_height": parsed.get("floor_height"),
            "seating_capacity": _safe_int(parsed.get("seating_capacity")),
            "number_of_exits": _safe_int(parsed.get("number_of_exits")),
            "number_of_staircases": _safe_int(parsed.get("number_of_staircases")),
            "kitchen_present": _safe_bool(parsed.get("kitchen_present")),
        }
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Blueprint extraction failed: {e}")
        return _empty_result()


def _empty_result() -> dict:
    return {
        "total_area": None,
        "overall_width": None,
        "overall_height": None,
        "floors": None,
        "floor_height": None,
        "seating_capacity": None,
        "number_of_exits": None,
        "number_of_staircases": None,
        "kitchen_present": None,
    }


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value)
