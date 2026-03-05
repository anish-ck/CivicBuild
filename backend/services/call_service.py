"""
Advisory summary service using Groq LLM.
Generates compliance summaries for blueprint analysis.
(Twilio voice call removed — summary returned as text in API response.)
"""

import json
import logging

from openai import OpenAI

from config import (
    ADVISORY_DISCLAIMER,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
)

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are a municipal advisory assistant.
Generate a concise compliance summary (about 80-100 words) in the specified language.
Include:
1. Building details extracted from the blueprint
2. Location information
3. Key compliance requirements
4. End with this exact disclaimer: "{disclaimer}"

Keep it professional and clear.
Return the summary text only, no JSON or formatting."""


def _get_groq_client() -> OpenAI:
    return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)


def generate_summary(
    blueprint_data: dict,
    location_data: dict,
    language: str = "hi-IN",
) -> str:
    """
    Generate an advisory compliance summary using Groq LLM.
    """
    if not GROQ_API_KEY:
        return f"Blueprint analysis complete. {ADVISORY_DISCLAIMER}"

    lang_name = {"hi-IN": "Hindi", "ta-IN": "Tamil", "en": "English"}.get(
        language, "English"
    )

    prompt = SUMMARY_PROMPT.format(disclaimer=ADVISORY_DISCLAIMER)

    user_content = f"""Language: {lang_name}

Building Details:
{json.dumps(blueprint_data, indent=2, default=str)}

Location Details:
{json.dumps(location_data, indent=2, default=str)}"""

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return f"Blueprint analysis complete for your building. {ADVISORY_DISCLAIMER}"
