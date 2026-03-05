"""
Speech-to-Text service using Sarvam AI API.
Supports Hindi (hi-IN) and Tamil (ta-IN) with auto-detection.
"""

import os
import requests
from fastapi import HTTPException, UploadFile

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

SUPPORTED_LANGUAGES = {"hi-IN", "ta-IN"}


async def transcribe_audio(file: UploadFile) -> dict:
    """
    Send audio file to Sarvam AI STT API.
    Auto-detects language between Hindi and Tamil.
    Raises HTTPException if detected language is unsupported.
    """
    if not SARVAM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="SARVAM_API_KEY is not configured."
        )

    # Read file bytes
    audio_bytes = await file.read()
    filename = file.filename or "audio.wav"

    # Prepare multipart request — omit language_code for auto-detection
    files = {
        "file": (filename, audio_bytes, file.content_type or "audio/wav"),
    }
    data = {
        "model": "saaras:v3",
        "mode": "transcribe",
    }
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
    }

    try:
        response = requests.post(
            SARVAM_STT_URL,
            files=files,
            data=data,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Sarvam AI STT request failed: {str(e)}"
        )

    result = response.json()
    transcript = result.get("transcript", "")
    language_code = result.get("language_code", "unknown")
    language_probability = result.get("language_probability", 0.0)

    # Validate language
    if language_code not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Detected language '{language_code}' is not supported. "
                "Only Hindi (hi-IN) and Tamil (ta-IN) are accepted."
            ),
        )

    return {
        "transcript": transcript,
        "language_code": language_code,
        "language_probability": language_probability,
    }


async def translate_to_english(text: str, source_language: str) -> str:
    """
    Translate Hindi/Tamil text to English using Sarvam AI Translate API.
    Used internally by RAG service to bridge language gap.
    """
    if not SARVAM_API_KEY:
        return text  # Fallback: return original text

    url = "https://api.sarvam.ai/translate"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "input": text,
        "source_language_code": source_language,
        "target_language_code": "en-IN",
        "mode": "formal",
        "model": "mayura:v1",
        "enable_preprocessing": True,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()
        return result.get("translated_text", text)
    except Exception:
        return text  # Fallback: return original text on failure
