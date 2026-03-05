"""
Geolocation router — reverse geocoding via Google Maps API.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config import ADVISORY_DISCLAIMER
from database import get_db
from models.blueprint import BlueprintRecord, LocationRequest, LocationResponse
from models.profile import BusinessProfile
from services import geolocation_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/check-location", response_model=LocationResponse, tags=["Geolocation"])
def check_location(
    request: LocationRequest,
    db: Session = Depends(get_db),
):
    """
    Reverse geocode latitude/longitude using Google Maps Geocoding API.
    Optionally links the location to an existing blueprint record.
    """
    logger.info(f"Geocoding: lat={request.latitude}, lng={request.longitude}")

    # Reverse geocode
    geo_result = geolocation_service.reverse_geocode(
        request.latitude, request.longitude
    )

    # If blueprint_id provided, update the blueprint record
    if request.blueprint_id:
        record = (
            db.query(BlueprintRecord)
            .filter(BlueprintRecord.id == request.blueprint_id)
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Blueprint {request.blueprint_id} not found.",
            )

        record.latitude = request.latitude
        record.longitude = request.longitude
        record.formatted_address = geo_result["formatted_address"]
        record.locality = geo_result["locality"]
        record.administrative_area = geo_result["administrative_area"]
        record.zone_detected = geo_result["zone_detected"]
        db.commit()
        logger.info(f"Updated blueprint {request.blueprint_id} with location data")

    return LocationResponse(
        formatted_address=geo_result["formatted_address"],
        locality=geo_result.get("locality"),
        administrative_area=geo_result.get("administrative_area"),
        zone_detected=geo_result.get("zone_detected"),
        disclaimer=ADVISORY_DISCLAIMER,
    )


@router.post("/suggest-location", tags=["Geolocation"])
def suggest_location(
    blueprint_id: int = Query(None),
    profile_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    Suggest a suitable location for the business using LLM.
    Detects city from the user's business profile.
    """
    # Get business type and city from profile if available
    business_type = None
    city = None
    if profile_id:
        profile = db.query(BusinessProfile).filter(BusinessProfile.id == profile_id).first()
        if profile:
            business_type = profile.business_type
            city = profile.city

    # Get building details from blueprint if available
    building_details = {}
    blueprint = None
    if blueprint_id:
        blueprint = (
            db.query(BlueprintRecord)
            .filter(BlueprintRecord.id == blueprint_id)
            .first()
        )
        if blueprint:
            building_details = {
                "total_area": blueprint.total_area,
                "overall_width": blueprint.overall_width,
                "overall_height": blueprint.overall_height,
                "floors": blueprint.floors,
                "floor_height": blueprint.floor_height,
                "seating_capacity": blueprint.seating_capacity,
                "kitchen_present": blueprint.kitchen_present,
            }

    logger.info(f"Suggesting location for business_type={business_type}, city={city}")

    result = geolocation_service.suggest_city_location(
        business_type=business_type,
        building_details=building_details,
        city=city,
    )

    # Save to blueprint record if provided
    if blueprint:
        blueprint.formatted_address = result["formatted_address"]
        blueprint.locality = result["locality"]
        blueprint.administrative_area = result["administrative_area"]
        blueprint.zone_detected = result["zone_detected"]
        db.commit()
        logger.info(f"Updated blueprint {blueprint_id} with suggested location")

    return {
        "formatted_address": result["formatted_address"],
        "locality": result["locality"],
        "administrative_area": result["administrative_area"],
        "zone_detected": result["zone_detected"],
        "reason": result.get("reason", ""),
        "commercial_allowed": result.get("commercial_allowed", True),
        "disclaimer": ADVISORY_DISCLAIMER,
    }


from pydantic import BaseModel as _BaseModel


class SetLocationRequest(_BaseModel):
    address: str
    blueprint_id: int | None = None


@router.post("/set-location", tags=["Geolocation"])
def set_location(
    request: SetLocationRequest,
    db: Session = Depends(get_db),
):
    """
    User provides a specific Chennai address.
    We geocode it via Google Maps to get structured components, then save to blueprint.
    """
    logger.info(f"User-provided address: {request.address}")

    # Forward-geocode the user's address via Google Maps
    geo_result = geolocation_service.forward_geocode(request.address)

    # Save to blueprint record if provided
    if request.blueprint_id:
        blueprint = (
            db.query(BlueprintRecord)
            .filter(BlueprintRecord.id == request.blueprint_id)
            .first()
        )
        if blueprint:
            blueprint.latitude = geo_result.get("latitude")
            blueprint.longitude = geo_result.get("longitude")
            blueprint.formatted_address = geo_result["formatted_address"]
            blueprint.locality = geo_result["locality"]
            blueprint.administrative_area = geo_result["administrative_area"]
            blueprint.zone_detected = geo_result["zone_detected"]
            db.commit()
            logger.info(f"Updated blueprint {request.blueprint_id} with user address")

    return {
        "formatted_address": geo_result["formatted_address"],
        "locality": geo_result.get("locality"),
        "administrative_area": geo_result.get("administrative_area"),
        "zone_detected": geo_result.get("zone_detected"),
        "disclaimer": ADVISORY_DISCLAIMER,
    }
