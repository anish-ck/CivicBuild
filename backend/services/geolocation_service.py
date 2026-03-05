"""
Google Maps Geocoding service.
Reverse geocoding: lat/lng → structured address.
Chennai location suggestion via Groq LLM.
"""

import json
import logging

import requests
from openai import OpenAI

from config import GOOGLE_MAPS_API_KEY, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def reverse_geocode(latitude: float, longitude: float) -> dict:
    """
    Reverse geocode a lat/lng pair using Google Maps Geocoding API.
    Returns structured address components.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not configured")
        return {
            "formatted_address": "API key not configured",
            "locality": None,
            "administrative_area": None,
            "zone_detected": None,
        }

    params = {
        "latlng": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            logger.warning(f"Geocoding API returned status: {data.get('status')}")
            return {
                "formatted_address": f"Geocoding failed: {data.get('status')}",
                "locality": None,
                "administrative_area": None,
                "zone_detected": None,
            }

        result = data["results"][0]
        formatted_address = result.get("formatted_address", "")

        # Parse address components
        locality = None
        administrative_area = None
        zone_detected = None

        for component in result.get("address_components", []):
            types = component.get("types", [])

            if "locality" in types:
                locality = component.get("long_name")
            elif "sublocality_level_1" in types and not locality:
                locality = component.get("long_name")

            if "administrative_area_level_1" in types:
                administrative_area = component.get("long_name")

            if "administrative_area_level_2" in types:
                zone_detected = component.get("long_name")
            elif "sublocality" in types and not zone_detected:
                zone_detected = component.get("long_name")

        # Try to detect zone from place types
        if not zone_detected:
            all_types = result.get("types", [])
            for t in all_types:
                if t not in ("street_address", "route", "political"):
                    zone_detected = t.replace("_", " ").title()
                    break

        return {
            "formatted_address": formatted_address,
            "locality": locality,
            "administrative_area": administrative_area,
            "zone_detected": zone_detected,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request failed: {e}")
        return {
            "formatted_address": f"Request failed: {str(e)}",
            "locality": None,
            "administrative_area": None,
            "zone_detected": None,
        }


# ── Chennai Location Suggestion via LLM ──────────────────────────────

LOCATION_PROMPT_TEMPLATE = """You are an expert urban planner and zoning advisor for {city}, {state}, India.
Based on the business type and building details provided, suggest ONE specific real area/locality in {city} where this business is allowed and suitable to operate.

You MUST return strict JSON only with these fields:
- suggested_address (string) — a realistic full address in {city} (include area name, road if possible, {city}, {state}, PIN code)
- locality (string) — the area/neighborhood name
- zone_type (string) — the zoning category (e.g. "Commercial Zone", "Mixed-Use Zone")
- reason (string) — 1-2 sentences explaining why this area is suitable for this business type
- commercial_allowed (boolean) — true if commercial activity is allowed in this zone

Return ONLY valid JSON, no extra text."""

# City → State mapping
CITY_STATE_MAP = {
    "chennai": "Tamil Nadu",
    "mumbai": "Maharashtra",
    "bangalore": "Karnataka",
    "delhi": "Delhi",
    "hyderabad": "Telangana",
    "kolkata": "West Bengal",
}


def suggest_city_location(
    business_type: str | None = None,
    building_details: dict | None = None,
    city: str | None = None,
) -> dict:
    """
    Use Groq LLM to suggest a specific address in the given city suitable for
    the given business type and building characteristics.
    """
    city_name = (city or "Chennai").strip().title()
    state = CITY_STATE_MAP.get(city_name.lower(), "")
    if not state:
        state = "India"

    if not GROQ_API_KEY:
        return _default_location(city_name, state)

    btype = business_type or "restaurant"
    details_str = ""
    if building_details:
        details_str = "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}"
            for k, v in building_details.items()
            if v is not None
        )

    system_prompt = LOCATION_PROMPT_TEMPLATE.format(city=city_name, state=state)

    user_msg = f"""Business Type: {btype}
City: {city_name}, {state}

Building Details:
{details_str or 'Not available'}

Suggest a suitable {city_name} location where this {btype} is allowed to operate."""

    try:
        client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        logger.info(f"LLM suggested {city_name} location: {parsed}")
        return {
            "formatted_address": parsed.get("suggested_address", f"{city_name}, {state}"),
            "locality": parsed.get("locality", city_name),
            "administrative_area": state,
            "zone_detected": parsed.get("zone_type", "Commercial Zone"),
            "reason": parsed.get("reason", ""),
            "commercial_allowed": parsed.get("commercial_allowed", True),
        }
    except Exception as e:
        logger.error(f"{city_name} location suggestion failed: {e}")
        return _default_location(city_name, state)


# Keep backward-compat alias
def suggest_chennai_location(
    business_type: str | None = None,
    building_details: dict | None = None,
) -> dict:
    return suggest_city_location(business_type, building_details, city="Chennai")


def _default_location(city: str = "Chennai", state: str = "Tamil Nadu") -> dict:
    """Fallback default location for any city."""
    return {
        "formatted_address": f"Main Commercial Road, {city}, {state}",
        "locality": city,
        "administrative_area": state,
        "zone_detected": "Commercial Zone",
        "reason": f"A major commercial area in {city} suitable for various business types.",
        "commercial_allowed": True,
    }


# ── Forward Geocoding (address string → lat/lng + components) ──────

def forward_geocode(address: str) -> dict:
    """
    Forward geocode an address string using Google Maps Geocoding API.
    Appends ', Chennai, Tamil Nadu' if not already present to keep results local.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("GOOGLE_MAPS_API_KEY not configured")
        return {
            "formatted_address": address,
            "locality": None,
            "administrative_area": None,
            "zone_detected": None,
            "latitude": None,
            "longitude": None,
        }

    # Ensure the query is scoped to India
    query = address.strip()
    lower = query.lower()
    if "india" not in lower:
        query += ", India"

    params = {
        "address": query,
        "key": GOOGLE_MAPS_API_KEY,
    }

    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            logger.warning(f"Forward geocoding returned status: {data.get('status')}")
            return {
                "formatted_address": address,
                "locality": None,
                "administrative_area": None,
                "zone_detected": None,
                "latitude": None,
                "longitude": None,
            }

        result = data["results"][0]
        formatted_address = result.get("formatted_address", address)

        locality = None
        administrative_area = None
        zone_detected = None
        lat = result.get("geometry", {}).get("location", {}).get("lat")
        lng = result.get("geometry", {}).get("location", {}).get("lng")

        for component in result.get("address_components", []):
            types = component.get("types", [])
            if "locality" in types:
                locality = component.get("long_name")
            elif "sublocality_level_1" in types and not locality:
                locality = component.get("long_name")
            if "administrative_area_level_1" in types:
                administrative_area = component.get("long_name")
            if "administrative_area_level_2" in types:
                zone_detected = component.get("long_name")
            elif "sublocality" in types and not zone_detected:
                zone_detected = component.get("long_name")

        return {
            "formatted_address": formatted_address,
            "locality": locality,
            "administrative_area": administrative_area,
            "zone_detected": zone_detected,
            "latitude": lat,
            "longitude": lng,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Forward geocoding request failed: {e}")
        return {
            "formatted_address": address,
            "locality": None,
            "administrative_area": None,
            "zone_detected": None,
            "latitude": None,
            "longitude": None,
        }
