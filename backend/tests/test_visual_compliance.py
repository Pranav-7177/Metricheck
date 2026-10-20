import pytest
import numpy as np
import cv2
from typing import Dict, Any

from app.services.visual.evidence import (
    VisualEvidence, VisualEvidenceStatus, ReadabilityStatus,
    VisibilityStatus, PlacementRegion, CalibrationMethod
)
from app.services.visual.geometry import GeometryService
from app.services.visual.calibration import CalibrationService
from app.services.visual.text_measurement import TextMeasurementService
from app.services.visual.readability import ReadabilityService
from app.services.visual.placement import PlacementService
from app.services.visual.service import VisualComplianceService
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules.mrp import evaluate_mrp_font_height
from app.services.compliance.rules.net_quantity import evaluate_net_quantity_font_height
from app.services.reporting.generator import ReportGeneratorService


# ============================================================================
# 1. GEOMETRY TESTS
# ============================================================================

def test_bbox_text_height():
    """Validates deterministic text height calculation from axis-aligned bounding box."""
    bbox = {"x1": 50, "y1": 100, "x2": 250, "y2": 140}
    geo = GeometryService.analyze_box_geometry(bbox)
    assert geo["text_height_px"] == 40.0
    assert geo["text_width_px"] == 200.0
    assert geo["area_px"] == 8000.0
    assert geo["orientation_deg"] == 0.0
    assert geo["perspective_score"] == 1.0
    assert not geo["is_curved_surface"]


def test_rotated_bbox_measurement():
    """Validates text height extraction from rotated 4-point polygon coordinates."""
    # Rotated box roughly 45 degrees
    poly = [[100, 100], [170.71, 170.71], [142.42, 199.0], [71.71, 128.28]]
    geo = GeometryService.analyze_box_geometry(poly)
    # The height (shorter side) should be close to 40 px, longer side close to 100 px
    assert 35.0 <= geo["text_height_px"] <= 45.0
    assert 90.0 <= geo["text_width_px"] <= 110.0
    assert geo["orientation_deg"] != 0.0


def test_perspective_detection():
    """Validates trapezoidal / non-parallel quadrilateral detection."""
    # Strongly trapezoidal box (narrow top, wide bottom)
    trapezoid = [[120, 100], [180, 100], [250, 180], [50, 180]]
    geo = GeometryService.analyze_box_geometry(trapezoid)
    assert geo["perspective_score"] < 0.85
    assert geo["is_curved_surface"] or geo["perspective_score"] < 0.70


# ============================================================================
# 2. CALIBRATION TESTS
# ============================================================================

def test_known_reference_calibration():
    """Validates Method A: Known physical reference (e.g. 5 Rupee coin: 23mm)."""
    # 5 Rupee coin detected with diameter 92 px -> 92 / 23 = 4.0 px/mm
    res = CalibrationService.calibrate_from_reference(
        reference_type="coin_rupee_5",
        detected_pixel_dimension=92.0,
        detection_confidence=0.95
    )
    assert res["is_calibrated"] is True
    assert res["calibration_method"] == CalibrationMethod.KNOWN_REFERENCE_OBJECT.value
    assert res["pixels_per_mm"] == 4.0
    assert res["calibration_confidence"] == 0.95


def test_package_dimension_calibration():
    """Validates Method B: User-supplied known package dimension metadata."""
    # Package height declared as 200 mm, detected at 800 px -> 4.0 px/mm
    res = CalibrationService.calibrate_from_package_dimension(
        known_dimension_mm=200.0,
        detected_pixel_dimension=800.0,
        dimension_axis="height",
        confidence=0.90
    )
    assert res["is_calibrated"] is True
    assert res["calibration_method"] == CalibrationMethod.KNOWN_PACKAGE_DIMENSION.value
    assert res["pixels_per_mm"] == 4.0
    assert res["calibration_confidence"] == 0.90


def test_missing_calibration_returns_not_measurable():
    """Validates Method C: Missing calibration strictly returns uncalibrated result."""
    res = CalibrationService.get_uncalibrated_result()
    assert res["is_calibrated"] is False
    assert res["pixels_per_mm"] is None
    assert res["calibration_confidence"] == 0.0

    geo = {"text_height_px": 40.0, "perspective_score": 1.0, "is_curved_surface": False}
    meas = TextMeasurementService.measure_declaration_text(geo, res)
    assert meas["measurement_status"] == VisualEvidenceStatus.NOT_MEASURABLE.value
    assert meas["font_height_mm"] is None


def test_low_confidence_calibration_returns_not_measurable():
    """Low confidence calibration (< 0.60) must be rejected to prevent fabricated measurements."""
    res = CalibrationService.calibrate_from_reference(
        reference_type="coin_rupee_5",
        detected_pixel_dimension=92.0,
        detection_confidence=0.45  # Below threshold
    )
    assert res["is_calibrated"] is False
    assert res["pixels_per_mm"] is None


# ============================================================================
# 3. READABILITY TESTS
# ============================================================================

def test_readable_text_region():
    """Validates clean high-contrast text ROI results in READABLE status."""
    # Generate a sharp black text on light off-white background patch (typical packaging label)
    img = np.ones((100, 200, 3), dtype=np.uint8) * 230
    cv2.putText(img, "MRP Rs 199", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    box = {"x": 5, "y": 5, "w": 190, "h": 90}

    res = ReadabilityService.analyze_readability(box, image_input=img, ocr_confidence=0.95)
    assert res["readability"] == ReadabilityStatus.READABLE.value
    assert res["glare_overlap_percentage"] < 5.0


def test_blurred_text_region():
    """Validates heavily blurred text ROI lowers blur score and triggers MARGINAL/UNREADABLE."""
    # Create smooth, blurred patch
    img = np.ones((100, 200, 3), dtype=np.uint8) * 200
    blurred = cv2.GaussianBlur(img, (25, 25), 0)
    box = {"x": 10, "y": 10, "w": 180, "h": 80}

    res = ReadabilityService.analyze_readability(box, image_input=blurred, ocr_confidence=0.45)
    assert res["readability"] in (ReadabilityStatus.UNREADABLE.value, ReadabilityStatus.MARGINAL.value)


def test_glare_overlaps_text():
    """Validates glare > 30% overlap triggers UNABLE_TO_VERIFY status."""
    # 50% white patch (value 255)
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    img[:, :100] = 255  # Left half is pure blown-out glare
    box = {"x": 0, "y": 0, "w": 200, "h": 100}

    res = ReadabilityService.analyze_readability(box, image_input=img, ocr_confidence=0.70)
    assert res["glare_overlap_percentage"] >= 30.0
    assert res["readability"] == ReadabilityStatus.UNABLE_TO_VERIFY.value


def test_low_resolution_text():
    """Validates very small text ROI is marked MARGINAL or UNREADABLE."""
    box = {"x": 0, "y": 0, "w": 12, "h": 6}  # 6 px height is too low for physical inspection
    res = ReadabilityService.analyze_readability(box, image_input=None, ocr_confidence=0.50)
    assert res["readability"] in (ReadabilityStatus.MARGINAL.value, ReadabilityStatus.UNREADABLE.value)


# ============================================================================
# 4. VISIBILITY & PLACEMENT TESTS
# ============================================================================

def test_fully_visible_declaration():
    """Validates centered box well inside margins is FULLY_VISIBLE."""
    box = {"x": 200, "y": 300, "w": 150, "h": 50}
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000)
    assert res["visibility"] == VisibilityStatus.FULLY_VISIBLE.value


def test_partially_visible_declaration():
    """Validates box touching or crossing edge boundary is PARTIALLY_VISIBLE."""
    box = {"x": 2, "y": 300, "w": 150, "h": 50} # x=2 touches left border (< 4px margin)
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000)
    assert res["visibility"] == VisibilityStatus.PARTIALLY_VISIBLE.value


def test_declaration_out_of_frame():
    """Validates coordinates outside frame are marked OUT_OF_FRAME."""
    box = {"x": -60, "y": 300, "w": 50, "h": 50} # completely outside frame (x2 = -10 <= 0)
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000)
    assert res["visibility"] == VisibilityStatus.OUT_OF_FRAME.value



def test_normalized_declaration_position():
    """Validates normalized coordinate calculation and quadrant placement."""
    box = {"x": 800, "y": 800, "w": 100, "h": 100} # center at (850, 850)
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000)
    assert res["normalized_x"] == 0.85
    assert res["normalized_y"] == 0.85
    assert res["placement"] == PlacementRegion.BOTTOM_RIGHT.value


def test_front_panel_position():
    """Validates panel role integration with quadrant placement."""
    box = {"x": 100, "y": 100, "w": 100, "h": 50}
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000, image_role="front")
    assert res["placement"] == PlacementRegion.TOP_LEFT.value


def test_side_panel_position():
    """Validates side panel quadrant placement."""
    box = {"x": 500, "y": 500, "w": 100, "h": 50}
    res = PlacementService.analyze_placement_and_visibility(box, image_width=1000, image_height=1000, image_role="side")
    assert res["placement"] == PlacementRegion.CENTER.value


# ============================================================================
# 5. COMPLIANCE SAFETY TESTS (NO FALSE FAILS)
# ============================================================================

def test_visual_uncertainty_not_false_fail():
    """Uncertain visual evidence MUST NOT produce a legal violation FAIL."""
    decl = {
        "field_name": "MRP",
        "detected_value": "₹199",
        "extraction_status": "FOUND",
        "required_font_height_mm": 3.0,
        "visual_evidence": {
            "visual_status": "UNABLE_TO_VERIFY",
            "font_height_mm": None
        }
    }
    res = evaluate_mrp_font_height(decl, {})
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


def test_unmeasurable_font_not_false_fail():
    """Uncalibrated font MUST NOT produce a legal violation FAIL."""
    decl = {
        "field_name": "MRP",
        "detected_value": "₹199",
        "extraction_status": "FOUND",
        "required_font_height_mm": 3.0,
        "visual_evidence": {
            "visual_status": "NOT_MEASURABLE",
            "font_height_mm": None
        }
    }
    res = evaluate_mrp_font_height(decl, {})
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


def test_missing_calibration_not_false_fail():
    """Net quantity font check without calibration returns NOT_VERIFIABLE, not FAIL."""
    decl = {
        "field_name": "NET_QUANTITY",
        "detected_value": "500 g",
        "extraction_status": "FOUND",
        "required_font_height_mm": 4.0,
        "visual_evidence": {
            "visual_status": "READABLE_ONLY",
            "font_height_mm": None
        }
    }
    res = evaluate_net_quantity_font_height(decl, {})
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


def test_glare_not_false_fail():
    """Severe glare overlapping text returns NOT_VERIFIABLE, not FAIL."""
    decl = {
        "field_name": "MRP",
        "detected_value": "₹199",
        "extraction_status": "FOUND",
        "required_font_height_mm": 3.0,
        "visual_evidence": {
            "visual_status": "UNABLE_TO_VERIFY",
            "glare_overlap_percentage": 42.0,
            "font_height_mm": None
        }
    }
    res = evaluate_mrp_font_height(decl, {})
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


def test_partial_visibility_not_false_fail():
    """Partially clipped declaration returns NOT_VERIFIABLE, not FAIL."""
    decl = {
        "field_name": "NET_QUANTITY",
        "detected_value": "100 g",
        "extraction_status": "FOUND",
        "required_font_height_mm": 2.0,
        "visual_evidence": {
            "visual_status": "UNABLE_TO_VERIFY",
            "visibility": "PARTIALLY_VISIBLE",
            "font_height_mm": None
        }
    }
    res = evaluate_net_quantity_font_height(decl, {})
    assert res.status == "NOT_VERIFIABLE"
    assert res.status != "FAIL"


# ============================================================================
# 6. INTEGRATION TESTS
# ============================================================================

def test_visual_evidence_reaches_compliance_engine():
    """Validates that calibrated font evidence properly reaches ComplianceEngine."""
    declarations = [
        {
            "field_name": "MRP",
            "detected_value": "₹ 199.00",
            "normalized_value": "199.00",
            "currency": "INR",
            "extraction_status": "FOUND",
            "required_font_height_mm": 3.0,
            "visual_evidence": {
                "visual_status": "MEASURABLE",
                "font_height_mm": 4.2,
                "text_height_px": 42.0,
                "calibration_confidence": 0.95
            }
        }
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    mrp_font_rule = next((r for r in res["results"] if r["rule_id"] == "MRP_FONT_HEIGHT"), None)
    assert mrp_font_rule is not None
    assert mrp_font_rule["status"] == "PASS"
    assert "4.2 mm" in mrp_font_rule["message"]


def test_visual_evidence_reaches_report():
    """Validates ReportGeneratorService synthesizes visual metrics and recommendations."""
    rule_results = [
        {"status": "PASS", "rule_id": "TEST_1"},
        {"status": "NOT_VERIFIABLE", "rule_id": "TEST_2"}
    ]
    declarations = [
        {
            "field_name": "MRP",
            "display_name": "Maximum Retail Price (MRP)",
            "visual_evidence": {
                "visual_status": "MEASURABLE",
                "font_height_mm": 5.0,
                "text_height_px": 50.0,
                "calibration_method": "KNOWN_REFERENCE_OBJECT",
                "recommendation": "Maintain calibrated scale for audit trail."
            }
        },
        {
            "field_name": "NET_QUANTITY",
            "display_name": "Net Quantity",
            "visual_evidence": {
                "visual_status": "NOT_MEASURABLE",
                "glare_overlap_percentage": 28.0,
                "recommendation": "Provide a known package dimension or calibrated reference."
            }
        }
    ]
    rep = ReportGeneratorService.generate_overall_assessment(
        rule_results=rule_results,
        image_qualities=[],
        product_name="Sample Biscuit",
        category_name="Food & Grocery",
        declarations=declarations
    )
    v_sum = rep["visual_compliance_summary"]
    assert v_sum["measurable_count"] == 1
    assert v_sum["not_measurable_count"] == 1
    assert len(v_sum["calibrated_font_measurements"]) == 1
    assert any("glare" in w.lower() for w in rep["warnings"])
    assert any("Provide a known package dimension" in rec for rec in rep["recommended_actions"])


def test_multi_image_visual_aggregation_and_conflict():
    """Validates multi-image visual evidence aggregation and material conflict detection."""
    ev1 = VisualEvidence(
        field="MRP",
        image_id=1,
        source_image_role="front",
        font_height_mm=10.0,
        text_height_px=40.0,
        calibration_confidence=0.90,
        visual_status=VisualEvidenceStatus.MEASURABLE.value
    )
    # Second photo gives 15.0 mm (> 35% difference -> material conflict)
    ev2 = VisualEvidence(
        field="MRP",
        image_id=2,
        source_image_role="close_up",
        font_height_mm=15.0,
        text_height_px=60.0,
        calibration_confidence=0.92,
        visual_status=VisualEvidenceStatus.MEASURABLE.value
    )

    agg = VisualComplianceService.aggregate_multi_image_visual_evidence([ev1, ev2])
    assert agg is not None
    assert agg.visual_status == VisualEvidenceStatus.AMBIGUOUS.value
    assert "conflicting" in agg.explanation.lower()
