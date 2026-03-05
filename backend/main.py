"""
AI Business Setup Assistant — FastAPI Backend
Supports Hindi & Tamil voice input for business registration assistance.
Includes Blueprint Scanner, Geolocation, and Gmail integrations.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models.profile import (
    AskRequest,
    AskResponse,
    BusinessProfile,
    BusinessProfileResponse,
    LicenseSuggestion,
)
# Import new models so their tables get created
from models.blueprint import BlueprintRecord  # noqa: F401
from models.oauth_token import OAuthToken  # noqa: F401

from services import extraction_service, license_service, rag_service, speech_service
from services import blueprint_scanner

# Import routers
from routers import blueprint as blueprint_router
from routers import geolocation as geolocation_router
from routers import auth as auth_router
from routers import lifecycle as lifecycle_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ── Lifespan (startup / shutdown) ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables and initialize RAG knowledge base."""
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("[Startup] Database tables created.")

    # Initialize RAG vector store
    print("[Startup] Initializing RAG knowledge base...")
    rag_service.initialize()
    print("[Startup] RAG knowledge base ready.")

    # Google Vision API for blueprint OCR
    print("[Startup] Using Google Vision API for blueprint text extraction.")

    yield  # App is running

    print("[Shutdown] Cleaning up...")


# ── FastAPI App ───────────────────────────────────────────────────────

app = FastAPI(
    title="AI Business Setup Assistant — CivicBuild",
    description="Voice-powered business registration assistant with Blueprint Scanner, "
                "Geolocation & Gmail integrations. Supports Hindi & Tamil.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow all for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────────────────

app.include_router(blueprint_router.router, tags=["Blueprint"])
app.include_router(geolocation_router.router, tags=["Geolocation"])
app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(lifecycle_router.router, tags=["Lifecycle"])


# ── Health Check ──────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "running", "service": "CivicBuild AI Business Setup Assistant", "version": "2.0.0"}


# ── POST /voice-input ─────────────────────────────────────────────────

@app.post("/transcribe", tags=["Voice Input"])
async def transcribe_only(
    file: UploadFile = File(..., description="Audio file (WAV/MP3) in Hindi or Tamil"),
):
    """
    Transcribe audio and translate to English. Returns transcript only.
    Used for voice-to-text address input.
    """
    stt_result = await speech_service.transcribe_audio(file)
    transcript = stt_result["transcript"]
    language_code = stt_result["language_code"]

    english_transcript = transcript
    if language_code in ("hi-IN", "ta-IN"):
        english_transcript = await speech_service.translate_to_english(transcript, language_code)

    return {
        "transcript": transcript,
        "english_transcript": english_transcript,
        "detected_language": language_code,
    }


@app.post("/voice-input", tags=["Voice Input"])
async def voice_input(
    file: UploadFile = File(..., description="Audio file (WAV/MP3) in Hindi or Tamil"),
    db: Session = Depends(get_db),
):
    """
    Upload a voice recording in Hindi or Tamil.
    The system will:
    1. Transcribe the audio (Sarvam AI)
    2. Extract structured business details (Groq LLM)
    3. Save the business profile (SQLite)
    4. Suggest required licenses (rule-based)
    5. Return everything as structured JSON
    """
    # Step 1: Transcribe
    stt_result = await speech_service.transcribe_audio(file)
    transcript = stt_result["transcript"]
    language_code = stt_result["language_code"]

    # Step 1.5: Translate Hindi/Tamil to English for better LLM extraction
    english_transcript = transcript
    if language_code in ("hi-IN", "ta-IN"):
        english_transcript = await speech_service.translate_to_english(transcript, language_code)

    # Step 2: Extract structured data (using English text for accuracy)
    extracted = extraction_service.extract_business_details(english_transcript)

    # Step 3: Save to database
    profile = BusinessProfile(
        transcript=transcript,
        detected_language=language_code,
        business_type=extracted.get("business_type"),
        city=extracted.get("city"),
        seating_capacity=extracted.get("seating_capacity"),
        turnover=extracted.get("turnover"),
        serves_food=extracted.get("serves_food"),
        serves_alcohol=extracted.get("serves_alcohol"),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Step 4: Suggest licenses
    licenses = license_service.suggest_licenses(profile)

    # Step 5: Check for missing fields and generate follow-up question
    profile_data = {
        "business_type": extracted.get("business_type"),
        "city": extracted.get("city"),
        "seating_capacity": extracted.get("seating_capacity"),
        "turnover": extracted.get("turnover"),
        "serves_food": extracted.get("serves_food"),
        "serves_alcohol": extracted.get("serves_alcohol"),
    }
    missing = extraction_service.get_missing_fields(profile_data)
    followup = extraction_service.generate_followup_question(missing, language_code) if missing else ""

    # Step 6: Return response
    return {
        "id": profile.id,
        "transcript": transcript,
        "detected_language": language_code,
        "language_probability": stt_result.get("language_probability"),
        "profile": BusinessProfileResponse.model_validate(profile).model_dump(),
        "suggested_licenses": licenses,
        "missing_fields": missing,
        "followup_question": followup,
    }


# ── POST /voice-followup ───────────────────────────────────────────────

@app.post("/voice-followup", tags=["Voice Input"])
async def voice_followup(
    file: UploadFile = File(..., description="Follow-up audio file in Hindi or Tamil"),
    profile_id: int = 0,
    db: Session = Depends(get_db),
):
    """
    Follow-up voice input to fill in missing business details.
    Transcribes, extracts new info, merges into existing profile.
    """
    # Fetch existing profile
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found.")

    # Transcribe
    stt_result = await speech_service.transcribe_audio(file)
    transcript = stt_result["transcript"]
    language_code = stt_result["language_code"]

    # Translate to English for extraction
    english_transcript = transcript
    if language_code in ("hi-IN", "ta-IN"):
        english_transcript = await speech_service.translate_to_english(transcript, language_code)

    # Extract new data
    new_data = extraction_service.extract_business_details(english_transcript)

    # Build current profile data
    existing_data = {
        "business_type": profile.business_type,
        "city": profile.city,
        "seating_capacity": profile.seating_capacity,
        "turnover": profile.turnover,
        "serves_food": profile.serves_food,
        "serves_alcohol": profile.serves_alcohol,
    }

    # Merge — only fill in what was previously null
    merged = extraction_service.merge_profile_data(existing_data, new_data)

    # Update profile in DB
    profile.business_type = merged["business_type"]
    profile.city = merged["city"]
    profile.seating_capacity = merged["seating_capacity"]
    profile.turnover = merged["turnover"]
    profile.serves_food = merged["serves_food"]
    profile.serves_alcohol = merged["serves_alcohol"]
    # Append transcript
    profile.transcript = (profile.transcript or "") + "\n" + transcript
    db.commit()
    db.refresh(profile)

    # Check remaining missing fields
    missing = extraction_service.get_missing_fields(merged)
    followup = extraction_service.generate_followup_question(missing, language_code) if missing else ""

    # Re-suggest licenses with updated data
    licenses = license_service.suggest_licenses(profile)

    return {
        "id": profile.id,
        "transcript": transcript,
        "detected_language": language_code,
        "profile": BusinessProfileResponse.model_validate(profile).model_dump(),
        "suggested_licenses": licenses,
        "missing_fields": missing,
        "followup_question": followup,
    }


# ── GET /profile/{id} ─────────────────────────────────────────────────

@app.get("/profile/{profile_id}", response_model=BusinessProfileResponse, tags=["Profile"])
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    """Retrieve a stored business profile by ID."""
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile with id {profile_id} not found.")
    return profile


# ── GET /suggest-licenses/{id} ────────────────────────────────────────

@app.get("/suggest-licenses/{profile_id}", response_model=list[LicenseSuggestion], tags=["Licenses"])
def suggest_licenses(profile_id: int, db: Session = Depends(get_db)):
    """Get license suggestions for a business profile based on rule-based logic."""
    profile = db.query(BusinessProfile).filter(BusinessProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile with id {profile_id} not found.")
    return license_service.suggest_licenses(profile)


# ── POST /ask ──────────────────────────────────────────────────────────

@app.post("/ask", response_model=AskResponse, tags=["RAG Q&A"])
def ask_question(request: AskRequest):
    """
    Ask a regulatory/compliance question about restaurant licensing.
    Uses RAG (Retrieval-Augmented Generation) with city-specific documents.
    Supports questions in Hindi, Tamil, or English.
    """
    answer = rag_service.ask_question(
        question=request.question,
        language_code=request.language,
        city=request.city,
    )
    return AskResponse(answer=answer, language=request.language)


@app.get("/supported-cities", tags=["RAG Q&A"])
def supported_cities():
    """Return list of cities with licensing data in the RAG knowledge base."""
    return {"cities": rag_service.get_supported_cities()}


# ── GET /download-pdf/{filename} ──────────────────────────────────────

@app.get("/download-pdf/{filename}", tags=["PDF"])
def download_pdf(filename: str):
    """Download a generated compliance PDF report."""
    import os
    from config import REPORTS_DIR
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"PDF '{filename}' not found.")
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=filename,
    )


# ── Run with Uvicorn ──────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
