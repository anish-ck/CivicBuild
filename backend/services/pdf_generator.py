"""
PDF report generator using ReportLab.
Creates compliance advisory reports with blueprint and location data.
"""

import logging
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import ADVISORY_DISCLAIMER, REPORTS_DIR

logger = logging.getLogger(__name__)


def generate_compliance_report(
    blueprint_data: dict,
    location_data: dict,
    blueprint_id: int = None,
) -> str:
    """
    Generate a PDF compliance report.
    Returns the file path of the generated PDF.
    """
    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"compliance_report_{blueprint_id or 'unknown'}_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    # Create document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── Title ─────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=20,
        textColor=colors.HexColor("#1a365d"),
    )
    elements.append(Paragraph("CivicBuild — Compliance Advisory Report", title_style))
    elements.append(Spacer(1, 12))

    # ── Report metadata ───────────────────────────────────────────
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
    )
    elements.append(
        Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", meta_style)
    )
    if blueprint_id:
        elements.append(Paragraph(f"Blueprint ID: {blueprint_id}", meta_style))
    elements.append(Spacer(1, 20))

    # ── Blueprint Details Section ─────────────────────────────────
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#2d3748"),
        spaceAfter=10,
    )
    elements.append(Paragraph("Building Details", section_style))

    blueprint_table_data = [
        ["Parameter", "Value"],
        ["Total Area", str(blueprint_data.get("total_area", "N/A"))],
        ["Floors", str(blueprint_data.get("floors", "N/A"))],
        ["Seating Capacity", str(blueprint_data.get("seating_capacity", "N/A"))],
        ["Number of Exits", str(blueprint_data.get("number_of_exits", "N/A"))],
        ["Number of Staircases", str(blueprint_data.get("number_of_staircases", "N/A"))],
        ["Kitchen Present", str(blueprint_data.get("kitchen_present", "N/A"))],
    ]

    table = Table(blueprint_table_data, colWidths=[2.5 * inch, 3.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 20))

    # ── Location Details Section ──────────────────────────────────
    elements.append(Paragraph("Location Details", section_style))

    location_table_data = [
        ["Parameter", "Value"],
        ["Address", str(location_data.get("formatted_address", "N/A"))],
        ["Locality", str(location_data.get("locality", "N/A"))],
        ["Administrative Area", str(location_data.get("administrative_area", "N/A"))],
        ["Zone Detected", str(location_data.get("zone_detected", "N/A"))],
    ]

    loc_table = Table(location_table_data, colWidths=[2.5 * inch, 3.5 * inch])
    loc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ]
        )
    )
    elements.append(loc_table)
    elements.append(Spacer(1, 30))

    # ── Disclaimer ────────────────────────────────────────────────
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#e53e3e"),
        borderColor=colors.HexColor("#e53e3e"),
        borderWidth=1,
        borderPadding=10,
        backColor=colors.HexColor("#fff5f5"),
        spaceAfter=10,
    )
    elements.append(
        Paragraph(f"⚠ DISCLAIMER: {ADVISORY_DISCLAIMER}", disclaimer_style)
    )

    # ── Build PDF ─────────────────────────────────────────────────
    try:
        doc.build(elements)
        logger.info(f"PDF report generated: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise RuntimeError(f"PDF generation failed: {str(e)}")
