"""
Structured extraction service using Groq LLM (llama-3.1-8b-instant).
Extracts business details from transcripts into structured JSON.
"""

import json
import os

from openai import OpenAI

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = "llama-3.1-8b-instant"

EXTRACTION_PROMPT = """You are an information extraction assistant.
Extract structured business details from this transcript.
Return strict JSON only.

Fields:
- business_type (string or null) — e.g. "restaurant", "hotel", "shop", "bar", "cafe", "bakery", etc.
- city (string or null) — in English
- seating_capacity (integer or null)
- turnover (number or null)
- serves_food (boolean or null) — true if restaurant, cafe, food business, or food is mentioned
- serves_alcohol (boolean or null) — true if bar, pub, alcohol, or liquor is mentioned

If a field is missing or unclear, return null for that field.
Return ONLY valid JSON, no extra text or explanation."""


def get_groq_client() -> OpenAI:
    """Create an OpenAI client pointed at Groq's API."""
    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL,
    )


def extract_business_details(transcript: str) -> dict:
    """
    Send transcript to Groq LLM and extract structured business information.
    Returns a dict with the extracted fields (nulls for missing data).
    """
    if not GROQ_API_KEY:
        return _empty_result()

    client = get_groq_client()

    # Few-shot examples to guide extraction from questions/statements
    few_shot = [
        {
            "role": "user",
            "content": "Transcript:\nI want to buy a shop in Chennai. What documents are needed? Is it possible to open a shop for a restaurant in my area?"
        },
        {
            "role": "assistant",
            "content": '{"business_type": "restaurant", "city": "Chennai", "seating_capacity": null, "turnover": null, "serves_food": true, "serves_alcohol": null}'
        },
        {
            "role": "user",
            "content": "Transcript:\nI want to open a bar in Mumbai with 100 seats and annual turnover of 50 lakhs. We will serve food and alcohol."
        },
        {
            "role": "assistant",
            "content": '{"business_type": "bar", "city": "Mumbai", "seating_capacity": 100, "turnover": 5000000, "serves_food": true, "serves_alcohol": true}'
        },
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                *few_shot,
                {"role": "user", "content": f"Transcript:\n{transcript}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=512,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        # Normalize field names and types
        return {
            "business_type": parsed.get("business_type"),
            "city": parsed.get("city"),
            "seating_capacity": _safe_int(parsed.get("seating_capacity")),
            "turnover": _safe_float(parsed.get("turnover")),
            "serves_food": _safe_bool(parsed.get("serves_food")),
            "serves_alcohol": _safe_bool(parsed.get("serves_alcohol")),
        }

    except (json.JSONDecodeError, Exception):
        return _empty_result()


def _empty_result() -> dict:
    return {
        "business_type": None,
        "city": None,
        "seating_capacity": None,
        "turnover": None,
        "serves_food": None,
        "serves_alcohol": None,
    }


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
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


# ── Missing-field detection & follow-up question generation ──────────

# The fields we require a user to provide
REQUIRED_FIELDS = [
    "business_type",
    "city",
    "seating_capacity",
    "turnover",
    "serves_food",
    "serves_alcohol",
]

# Human-readable English question for each field
_FIELD_QUESTIONS: dict[str, str] = {
    "business_type": "What type of business do you want to open? For example: restaurant, hotel, shop, cafe, bar, bakery.",
    "city": "In which city do you want to open your business?",
    "seating_capacity": "How many seats or customers will your business accommodate?",
    "turnover": "What is your expected annual turnover or revenue?",
    "serves_food": "Will your business serve food? Please say yes or no.",
    "serves_alcohol": "Will your business serve alcohol? Please say yes or no.",
}


def get_missing_fields(profile_data: dict) -> list[str]:
    """Return a list of field names that are still None / missing."""
    missing = []
    for field in REQUIRED_FIELDS:
        if profile_data.get(field) is None:
            missing.append(field)
    return missing


def generate_followup_question(
    missing_fields: list[str],
    language: str = "en",
) -> str:
    """
    Build a single follow-up question that asks for all missing fields.
    Uses Groq LLM to produce a natural question in the target language.
    If LLM fails, falls back to an English template.
    """
    if not missing_fields:
        return ""

    # Build English bullet list of what we need
    items = [_FIELD_QUESTIONS[f] for f in missing_fields if f in _FIELD_QUESTIONS]
    english_text = (
        "I still need a few more details from you:\n"
        + "\n".join(f"• {q}" for q in items)
        + "\n\nPlease tell me."
    )

    lang_map = {"hi-IN": "Hindi", "ta-IN": "Tamil", "en": "English"}
    target_lang = lang_map.get(language, "English")

    if target_lang == "English" or not GROQ_API_KEY:
        return english_text

    # Use Groq to produce a natural question in Hindi / Tamil
    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a friendly business registration assistant. "
                        f"Translate the following request into {target_lang}. "
                        f"Keep it natural and conversational. Return ONLY the translated text."
                    ),
                },
                {"role": "user", "content": english_text},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        translated = resp.choices[0].message.content.strip()
        return translated if translated else english_text
    except Exception:
        return english_text


def merge_profile_data(existing: dict, new_data: dict) -> dict:
    """Merge new extracted data into existing profile, filling only nulls."""
    merged = dict(existing)
    for key in REQUIRED_FIELDS:
        if merged.get(key) is None and new_data.get(key) is not None:
            merged[key] = new_data[key]
    return merged
