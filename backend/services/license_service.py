"""
Simple rule-based license suggestion engine.
No LLM involved — pure hardcoded business rules.
"""

from typing import Any


def suggest_licenses(profile: Any) -> list[dict]:
    """
    Given a BusinessProfile (ORM object or dict-like),
    return a list of suggested licenses with reasons.
    """
    suggestions = []

    # Trade License is always required
    suggestions.append({
        "license": "Trade License",
        "reason": "Mandatory for all businesses operating in India.",
    })

    # FSSAI if food is served
    if getattr(profile, "serves_food", None) is True:
        suggestions.append({
            "license": "FSSAI",
            "reason": "Food service requires FSSAI registration.",
        })

    # Fire NOC if seating > 50
    seating = getattr(profile, "seating_capacity", None)
    if seating is not None and seating > 50:
        suggestions.append({
            "license": "Fire NOC",
            "reason": "Seating capacity exceeds 50 — Fire NOC is required.",
        })

    # GST if turnover > 40 lakhs (4,000,000)
    turnover = getattr(profile, "turnover", None)
    if turnover is not None and turnover > 4_000_000:
        suggestions.append({
            "license": "GST Registration",
            "reason": "Annual turnover exceeds ₹40 lakhs — GST registration is mandatory.",
        })

    # Liquor License if alcohol is served
    if getattr(profile, "serves_alcohol", None) is True:
        suggestions.append({
            "license": "Liquor License",
            "reason": "Serving alcohol requires a valid liquor license from the state excise department.",
        })

    return suggestions
