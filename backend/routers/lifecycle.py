"""
Full lifecycle router — ties together blueprint, geolocation,
PDF generation, and Gmail into one complete flow.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import ADVISORY_DISCLAIMER
from database import get_db
from models.blueprint import BlueprintRecord, LifecycleRequest
from models.oauth_token import OAuthToken
from services import call_service, geolocation_service, gmail_service, pdf_generator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process-complete", tags=["Lifecycle"])
def process_complete(
    request: LifecycleRequest,
    db: Session = Depends(get_db),
):
    """
    Full lifecycle endpoint:
    1. Fetch blueprint data
    2. Fetch location data
    3. Generate PDF summary
    4. Send Gmail with PDF attached
    5. Generate compliance summary
    6. Return final structured response
    """
    # ── Step 1: Fetch blueprint ───────────────────────────────────
    blueprint = (
        db.query(BlueprintRecord)
        .filter(BlueprintRecord.id == request.blueprint_id)
        .first()
    )
    if not blueprint:
        raise HTTPException(
            status_code=404,
            detail=f"Blueprint {request.blueprint_id} not found.",
        )

    blueprint_data = {
        "total_area": blueprint.total_area,
        "overall_width": blueprint.overall_width,
        "overall_height": blueprint.overall_height,
        "floors": blueprint.floors,
        "floor_height": blueprint.floor_height,
        "seating_capacity": blueprint.seating_capacity,
        "number_of_exits": blueprint.number_of_exits,
        "number_of_staircases": blueprint.number_of_staircases,
        "kitchen_present": blueprint.kitchen_present,
    }

    # ── Step 2: Location data ─────────────────────────────────────
    location_data = {
        "formatted_address": blueprint.formatted_address or "Not available",
        "locality": blueprint.locality,
        "administrative_area": blueprint.administrative_area,
        "zone_detected": blueprint.zone_detected,
    }

    # If no location data, try to use default or skip
    if not blueprint.formatted_address:
        logger.warning(
            f"Blueprint {request.blueprint_id} has no location data. "
            "Run POST /check-location first."
        )

    # ── Step 3: Generate PDF ──────────────────────────────────────
    logger.info("Generating compliance PDF report...")
    try:
        pdf_path = pdf_generator.generate_compliance_report(
            blueprint_data=blueprint_data,
            location_data=location_data,
            blueprint_id=request.blueprint_id,
        )
        logger.info(f"PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        pdf_path = None

    # ── Step 4: Send Gmail ────────────────────────────────────────
    email_status = {"status": "skipped", "reason": "No OAuth token"}

    oauth_token = db.query(OAuthToken).filter(OAuthToken.provider == "google").first()
    if oauth_token:
        # Refresh token if expired
        access_token = oauth_token.access_token
        if oauth_token.expires_at and oauth_token.expires_at < datetime.utcnow():
            if oauth_token.refresh_token:
                try:
                    refreshed = gmail_service.refresh_access_token(oauth_token.refresh_token)
                    access_token = refreshed["access_token"]
                    oauth_token.access_token = access_token
                    oauth_token.expires_at = refreshed["expires_at"]
                    db.commit()
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    email_status = {"status": "failed", "reason": "Token refresh failed"}

        if email_status.get("status") != "failed":
            subject = f"CivicBuild Compliance Report — Blueprint #{request.blueprint_id}"
            body = (
                f"Dear Municipal Clerk,\n\n"
                f"Please find attached the compliance advisory report for "
                f"Blueprint #{request.blueprint_id}.\n\n"
                f"Building Details:\n"
                f"- Total Area: {blueprint_data.get('total_area', 'N/A')}\n"
                f"- Floors: {blueprint_data.get('floors', 'N/A')}\n"
                f"- Seating Capacity: {blueprint_data.get('seating_capacity', 'N/A')}\n"
                f"- Kitchen: {'Yes' if blueprint_data.get('kitchen_present') else 'No'}\n\n"
                f"Location: {location_data.get('formatted_address', 'N/A')}\n\n"
                f"{ADVISORY_DISCLAIMER}\n\n"
                f"Best regards,\n"
                f"CivicBuild AI System"
            )

            email_status = gmail_service.send_email(
                access_token=access_token,
                to_email=request.recipient_email,
                subject=subject,
                body=body,
                attachment_path=pdf_path,
            )
            logger.info(f"Email status: {email_status}")
    else:
        logger.warning("No OAuth token found. Skipping email. Visit /auth/login first.")

    # ── Step 5: Generate compliance summary ────────────────────────
    logger.info("Generating compliance summary...")
    summary_text = call_service.generate_summary(
        blueprint_data=blueprint_data,
        location_data=location_data,
        language=request.language,
    )
    logger.info(f"Summary generated ({len(summary_text)} chars)")

    # ── Step 6: Return response ───────────────────────────────────
    pdf_filename = None
    if pdf_path:
        import os
        pdf_filename = os.path.basename(pdf_path)

    return {
        "email_status": email_status,
        "summary_text": summary_text,
        "blueprint_data": blueprint_data,
        "location_data": location_data,
        "pdf_generated": pdf_path is not None,
        "pdf_filename": pdf_filename,
        "disclaimer": ADVISORY_DISCLAIMER,
    }
