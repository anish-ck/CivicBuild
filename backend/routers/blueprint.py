"""
Blueprint upload and extraction router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import ADVISORY_DISCLAIMER
from database import get_db
from models.blueprint import BlueprintRecord, BlueprintResponse
from services import blueprint_scanner
from services import rag_service


class BlueprintUpdateRequest(BaseModel):
    total_area: Optional[str] = None
    floors: Optional[int] = None
    seating_capacity: Optional[int] = None
    number_of_exits: Optional[int] = None
    number_of_staircases: Optional[int] = None
    kitchen_present: Optional[bool] = None

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-blueprint", tags=["Blueprint"])
async def upload_blueprint(
    file: UploadFile = File(..., description="Blueprint PDF or image (JPG/PNG)"),
    db: Session = Depends(get_db),
):
    """
    Upload a building blueprint (PDF or image).
    Extracts text via OCR/PDF parsing, then uses Groq LLM to extract
    structured building details.
    """
    # Validate file type
    allowed_types = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/bmp",
    }
    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    if content_type not in allowed_types:
        # Try to infer from extension
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in ("pdf", "jpg", "jpeg", "png", "tiff", "bmp"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Accepted: PDF, JPG, PNG, TIFF, BMP.",
            )

    logger.info(f"Received blueprint: {filename} ({content_type})")

    # Read file bytes
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # Step 1: Extract text from file
    raw_text, ocr_status = blueprint_scanner.extract_text(file_bytes, content_type, filename)
    logger.info(f"Extracted {len(raw_text)} characters from blueprint (ocr_status={ocr_status})")

    # Step 2: Extract structured details via LLM
    details = blueprint_scanner.extract_blueprint_details(raw_text)
    logger.info(f"Extracted details: {details}")

    # Step 3: Save to database
    record = BlueprintRecord(
        filename=filename,
        raw_text=raw_text[:5000],  # Truncate for storage
        total_area=details.get("total_area"),
        overall_width=details.get("overall_width"),
        overall_height=details.get("overall_height"),
        floors=details.get("floors"),
        floor_height=details.get("floor_height"),
        seating_capacity=details.get("seating_capacity"),
        number_of_exits=details.get("number_of_exits"),
        number_of_staircases=details.get("number_of_staircases"),
        kitchen_present=details.get("kitchen_present"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Build helpful OCR message
    ocr_hint = None
    if ocr_status == "no_api_key":
        ocr_hint = (
            "Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY in .env "
            "and enable Cloud Vision API in Google Cloud Console. "
            "You can manually fill details via PATCH /blueprint/{id}."
        )
    elif ocr_status == "api_error":
        ocr_hint = (
            "Google Vision API returned an error. Ensure Cloud Vision API is enabled "
            "in your Google Cloud Console. You can manually fill details via PATCH /blueprint/{id}."
        )
    elif ocr_status == "empty":
        ocr_hint = (
            "OCR ran but found no text (image may be a photo without labels). "
            "Use PATCH /blueprint/{id} to enter details manually."
        )

    response = {
        "id": record.id,
        "filename": filename,
        "raw_text_length": len(raw_text),
        "ocr_status": ocr_status,
        "extracted_details": details,
        "profile": BlueprintResponse.model_validate(record).model_dump(),
        "disclaimer": ADVISORY_DISCLAIMER,
    }
    if ocr_hint:
        response["ocr_hint"] = ocr_hint
    return response


@router.get("/blueprint/{blueprint_id}", response_model=BlueprintResponse, tags=["Blueprint"])
def get_blueprint(blueprint_id: int, db: Session = Depends(get_db)):
    """Retrieve a stored blueprint record by ID."""
    record = db.query(BlueprintRecord).filter(BlueprintRecord.id == blueprint_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Blueprint {blueprint_id} not found.")
    return record


@router.patch("/blueprint/{blueprint_id}", tags=["Blueprint"])
def update_blueprint(
    blueprint_id: int,
    payload: BlueprintUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Manually update extracted blueprint details.
    Use this when OCR fails (e.g. Tesseract not installed or image has no text).
    Only fields provided in the request body will be updated.
    """
    record = db.query(BlueprintRecord).filter(BlueprintRecord.id == blueprint_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Blueprint {blueprint_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    logger.info(f"Blueprint {blueprint_id} manually updated: {update_data}")
    return {
        "message": f"Blueprint {blueprint_id} updated successfully.",
        "updated_fields": list(update_data.keys()),
        "profile": BlueprintResponse.model_validate(record).model_dump(),
        "disclaimer": ADVISORY_DISCLAIMER,
    }


@router.post("/check-blueprint-compliance", tags=["Blueprint"])
def check_blueprint_compliance(
    blueprint_id: int,
    city: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Check extracted blueprint details against city-specific licensing/building rules.
    Uses RAG retrieval + LLM to evaluate compliance.
    Returns compliant status, issues, and suggestions.
    """
    record = db.query(BlueprintRecord).filter(BlueprintRecord.id == blueprint_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Blueprint {blueprint_id} not found.")

    blueprint_details = {
        "total_area": record.total_area,
        "overall_width": record.overall_width,
        "overall_height": record.overall_height,
        "floors": record.floors,
        "floor_height": record.floor_height,
        "seating_capacity": record.seating_capacity,
        "number_of_exits": record.number_of_exits,
        "number_of_staircases": record.number_of_staircases,
        "kitchen_present": record.kitchen_present,
    }

    resolved_city = city or "chennai"
    logger.info(f"Running compliance check for blueprint {blueprint_id} in {resolved_city}: {blueprint_details}")
    result = rag_service.check_blueprint_compliance(blueprint_details, city=resolved_city)
    logger.info(f"Compliance result: compliant={result['compliant']}, issues={len(result['issues'])}")

    return {
        "blueprint_id": blueprint_id,
        "city": resolved_city,
        "compliant": result["compliant"],
        "issues": result["issues"],
        "suggestions": result["suggestions"],
        "summary": result["summary"],
        "disclaimer": ADVISORY_DISCLAIMER,
    }
