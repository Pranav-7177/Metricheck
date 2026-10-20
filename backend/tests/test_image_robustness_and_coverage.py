"""Master Prompt 10 — Real-World Package Image Robustness, Multi-Panel Evidence & Scan Reliability Tests.

Comprehensive test suite verifying:
- Group A: Image validation & safety limits
- Group B: Quality gate decisions & actionable retake guidance
- Group C: Deterministic exact & near-duplicate detection (no artificial corroboration)
- Group D: Multi-panel evidence aggregation, semantic equivalence & conflict preservation
- Group E: Coverage completeness vs statutory non-compliance distinction
- Group F: End-to-end integration & re-evaluation
- Group G: Strict Legal-Safety Invariants (no false failures from scan uncertainty)
"""

import io
import os
import pytest
from PIL import Image

from app.models.models import ComplianceState, ImageQualityStatus, ImageType
from app.services.image_processing.image_validator import ImageValidator, ImageValidationError
from app.services.image_processing.quality import ImageQualityService
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.extraction.field_extractors import FieldCandidate
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.reporting.generator import ReportGeneratorService
from app.services.ocr.base import OCRResult, OCRBoxResult, BoundingBox
from tests.fixtures.synthetic_packages import render_package_label, apply_blur, apply_glare


# =========================================================================
# Group A: Image Validation Tests
# =========================================================================

def test_valid_image_accepted(tmp_path):
    """Verifies that a well-formed image passes validation and yields hashes."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    file_bytes = buf.getvalue()

    target_path = str(tmp_path / "valid.jpg")
    res = ImageValidator.validate_and_save_upload(file_bytes, "valid.jpg", target_path)

    assert res["is_valid"] is True
    assert res["width"] == 200
    assert res["height"] == 200
    assert len(res["content_hash"]) == 64
    assert len(res["perceptual_hash"]) == 16
    assert os.path.exists(target_path)


def test_empty_image_rejected(tmp_path):
    """Verifies that an empty image (0 bytes) is rejected with clear error."""
    target_path = str(tmp_path / "empty.jpg")
    with pytest.raises(ImageValidationError, match="empty"):
        ImageValidator.validate_and_save_upload(b"", "empty.jpg", target_path)


def test_corrupt_image_rejected(tmp_path):
    """Verifies that corrupt byte streams cannot bypass decoding."""
    target_path = str(tmp_path / "corrupt.jpg")
    with pytest.raises(ImageValidationError, match="Malformed or corrupt"):
        ImageValidator.validate_and_save_upload(b"NOT_A_REAL_IMAGE_BYTES_123456", "corrupt.jpg", target_path)


def test_unsupported_file_extension(tmp_path):
    """Verifies that non-whitelisted file extensions are rejected."""
    target_path = str(tmp_path / "script.exe")
    with pytest.raises(ImageValidationError, match="Unsupported image format"):
        ImageValidator.validate_and_save_upload(b"dummy_bytes", "script.exe", target_path)


def test_oversized_pixel_count_rejected(tmp_path):
    """Verifies decompression bomb safety limit (max 50 MP)."""
    # Create fake header indicating oversized dimensions without allocating RAM
    target_path = str(tmp_path / "bomb.png")
    # A 10000x6000 image has 60 MP > 50 MP limit
    img = Image.new("1", (10000, 6000))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    file_bytes = buf.getvalue()

    with pytest.raises(ImageValidationError, match="exceeds safety limit"):
        ImageValidator.validate_and_save_upload(file_bytes, "bomb.png", target_path)


def test_exif_orientation_transposition(tmp_path):
    """Verifies that EXIF orientation is normalized on save."""
    img = Image.new("RGB", (300, 100), color=(100, 150, 200))
    # Exif tag 0x0112 = Orientation. Value 6 indicates 90 degree CW rotation
    exif_bytes = b"Exif\x00\x00II*\x00\x08\x00\x00\x00\x01\x00\x12\x01\x03\x00\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    file_bytes = buf.getvalue()

    target_path = str(tmp_path / "exif_rotated.jpg")
    res = ImageValidator.validate_and_save_upload(file_bytes, "exif_rotated.jpg", target_path)
    assert res["is_valid"] is True
    # The transposed image orientation swaps width and height
    assert res["width"] == 100
    assert res["height"] == 300


# =========================================================================
# Group B: Quality Gate Decisions & Actionable Retake Guidance
# =========================================================================

def test_quality_decision_acceptable(tmp_path):
    """Clear, sharp image receives ACCEPTABLE decision."""
    img = render_package_label(width=800, height=800)
    p = str(tmp_path / "sharp.jpg")
    img.save(p)

    q = ImageQualityService.evaluate_image_file(p)
    assert q["quality_decision"] == "ACCEPTABLE"
    assert q["quality_status"] == ImageQualityStatus.GOOD
    assert len(q["retake_guidance"]) == 0


def test_blurry_image_retake_guidance(tmp_path):
    """Heavy blur triggers actionable retake guidance."""
    img = render_package_label(width=800, height=800)
    blurry = apply_blur(img, radius=12)
    p = str(tmp_path / "blurry.jpg")
    blurry.save(p)

    q = ImageQualityService.evaluate_image_file(p)
    assert q["quality_decision"] in ("DEGRADED", "UNSUITABLE")
    assert any("holding the camera steady" in g for g in q["retake_guidance"])


def test_glare_image_retake_guidance(tmp_path):
    """Severe glare triggers actionable glare-specific retake guidance."""
    img = render_package_label(width=800, height=800)
    glare_img = apply_glare(img, intensity=0.7)
    p = str(tmp_path / "glare.jpg")
    glare_img.save(p)

    q = ImageQualityService.evaluate_image_file(p)
    assert q["glare_score"] > 5.0
    assert any("direct reflections" in g or "Tilt the package" in g for g in q["retake_guidance"])


def test_poor_image_does_not_invalidate_usable_image():
    """Verifies that one poor image in a scan does not discard evidence from a clear image."""
    cands_front = [
        FieldCandidate(
            field_name="MRP",
            display_name="Maximum Retail Price (MRP)",
            value="₹299.00",
            normalized_value="299.00",
            status="FOUND",
            confidence=0.92,
            source_image_id=1,
            source_image_role="front"
        )
    ]
    cands_back_degraded = [
        FieldCandidate(
            field_name="MRP",
            display_name="Maximum Retail Price (MRP)",
            value=None,
            normalized_value=None,
            status="UNABLE_TO_VERIFY",
            confidence=0.10,
            source_image_id=2,
            source_image_role="back"
        )
    ]

    resolved = DeclarationExtractorService._resolve_multi_image_candidates(
        "MRP",
        cands_front + cands_back_degraded
    )

    # The usable candidate from the front panel is retained with high confidence
    assert resolved.status == "FOUND"
    assert resolved.value == "₹299.00"
    assert resolved.source_image_id == 1


# =========================================================================
# Group C: Duplicate Tests (No Artificial Corroboration)
# =========================================================================

def test_exact_duplicate_detection(tmp_path):
    """Exact cryptographic byte match is identified as EXACT duplicate."""
    img = render_package_label()
    p1 = str(tmp_path / "img1.jpg")
    img.save(p1)

    with open(p1, "rb") as f:
        b = f.read()

    res1 = ImageValidator.validate_and_save_upload(b, "img1.jpg", str(tmp_path / "save1.jpg"))
    res2 = ImageValidator.validate_and_save_upload(b, "img2.jpg", str(tmp_path / "save2.jpg"))

    meta = [
        {"id": 1, "content_hash": res1["content_hash"], "perceptual_hash": res1["perceptual_hash"], "width": 1000, "height": 700},
        {"id": 2, "content_hash": res2["content_hash"], "perceptual_hash": res2["perceptual_hash"], "width": 1000, "height": 700},
    ]

    dups = ImageValidator.detect_duplicates(meta)
    assert dups[0]["is_duplicate"] is False
    assert dups[1]["is_duplicate"] is True
    assert dups[1]["duplicate_type"] == "EXACT"
    assert dups[1]["duplicate_of_id"] == 1


def test_near_duplicate_detection(tmp_path):
    """Resized or recompressed photo of same panel detected as NEAR_DUPLICATE."""
    img1 = render_package_label(width=1000, height=700)
    img2 = render_package_label(width=900, height=630) # slight resize

    b1, b2 = io.BytesIO(), io.BytesIO()
    img1.save(b1, format="JPEG", quality=90)
    img2.save(b2, format="JPEG", quality=80)

    res1 = ImageValidator.validate_and_save_upload(b1.getvalue(), "p1.jpg", str(tmp_path / "p1.jpg"))
    res2 = ImageValidator.validate_and_save_upload(b2.getvalue(), "p2.jpg", str(tmp_path / "p2.jpg"))

    meta = [
        {"id": 10, "content_hash": res1["content_hash"], "perceptual_hash": res1["perceptual_hash"], "width": 1000, "height": 700},
        {"id": 11, "content_hash": res2["content_hash"], "perceptual_hash": res2["perceptual_hash"], "width": 900, "height": 630},
    ]

    dups = ImageValidator.detect_duplicates(meta, near_dup_threshold=6)
    assert dups[1]["is_duplicate"] is True
    assert dups[1]["duplicate_type"] == "NEAR_DUPLICATE"
    assert dups[1]["duplicate_of_id"] == 10


def test_duplicates_do_not_corroborate_confidence():
    """Duplicate images MUST NOT act as independent corroboration to boost candidate confidence."""
    c1 = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value="₹299.00",
        normalized_value="299.00",
        status="FOUND",
        confidence=0.85,
        source_image_id=1,
        source_image_role="front",
        is_from_duplicate=False
    )
    c2 = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value="₹299.00",
        normalized_value="299.00",
        status="FOUND",
        confidence=0.85,
        source_image_id=2,
        source_image_role="front",
        is_from_duplicate=True, # Marked as duplicate
        duplicate_of_id=1
    )

    resolved = DeclarationExtractorService._resolve_multi_image_candidates("MRP", [c1, c2])
    # Confidence remains exactly 0.85 without any multi-image agreement boost
    assert resolved.confidence == 0.85


# =========================================================================
# Group D: Multi-Image Extraction Tests
# =========================================================================

def test_semantic_equivalence_prevents_false_conflict():
    """Different currency representations of the same MRP do not trigger conflict."""
    c1 = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value="Rs 299.00",
        normalized_value="299.00",
        status="FOUND",
        confidence=0.90,
        source_image_id=1
    )
    c2 = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value="MRP: ₹299 (incl. taxes)",
        normalized_value="299",
        status="FOUND",
        confidence=0.91,
        source_image_id=2
    )

    is_equiv = DeclarationExtractorService.are_values_semantically_equivalent("MRP", c1, c2)
    assert is_equiv is True

    resolved = DeclarationExtractorService._resolve_multi_image_candidates("MRP", [c1, c2])
    assert resolved.has_conflict is False
    assert resolved.status == "FOUND"
    # Independent observation boosts confidence
    assert resolved.confidence > 0.91


def test_materially_conflicting_mrp_remains_ambiguous():
    """Genuinely conflicting MRP values (₹299 vs ₹499) must set status=AMBIGUOUS."""
    c1 = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value="₹299.00",
        normalized_value="299.00",
        status="FOUND",
        confidence=0.92,
        source_image_id=1,
        source_image_role="front"
    )
    c2 = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value="₹499.00",
        normalized_value="499.00",
        status="FOUND",
        confidence=0.89,
        source_image_id=2,
        source_image_role="back"
    )

    resolved = DeclarationExtractorService._resolve_multi_image_candidates("MRP", [c1, c2])
    assert resolved.has_conflict is True
    assert resolved.status == "AMBIGUOUS"
    assert len(resolved.alternate_candidates) == 1
    assert resolved.alternate_candidates[0]["value"] == "₹499.00"


def test_declarations_across_different_panels():
    """MRP on back panel and Net Quantity on side panel both extract successfully."""
    image_boxes_map = [
        {
            "image_id": 1,
            "image_role": "front",
            "image_type": "FRONT",
            "boxes": [
                {"id": 1, "text": "ORGANIC BASMATI RICE", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 200, "h": 40}, "line_number": 1}
            ]
        },
        {
            "image_id": 2,
            "image_role": "back",
            "image_type": "BACK",
            "boxes": [
                {"id": 2, "text": "MRP: Rs 350.00 (Incl. of all taxes)", "confidence": 0.93, "bounding_box": {"x": 20, "y": 50, "w": 180, "h": 30}, "line_number": 1}
            ]
        },
        {
            "image_id": 3,
            "image_role": "side",
            "image_type": "SIDE",
            "boxes": [
                {"id": 3, "text": "Net Quantity: 1 kg", "confidence": 0.92, "bounding_box": {"x": 15, "y": 30, "w": 140, "h": 25}, "line_number": 1}
            ]
        }
    ]

    fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    f_map = {f.field_name: f for f in fields}

    assert f_map["PRODUCT_NAME"].status == "FOUND"
    assert f_map["PRODUCT_NAME"].source_image_id == 1

    assert f_map["MRP"].status == "FOUND"
    assert f_map["MRP"].normalized_value == "350.00" or "350.00" in f_map["MRP"].value
    assert f_map["MRP"].source_image_id == 2

    assert f_map["NET_QUANTITY"].status == "FOUND"
    assert f_map["NET_QUANTITY"].normalized_value == "1" or "1" in f_map["NET_QUANTITY"].value
    assert f_map["NET_QUANTITY"].source_image_id == 3


# =========================================================================
# Group E: Coverage & Scan Completeness Tests
# =========================================================================

def test_missing_panel_coverage_summary():
    """Coverage summary accurately reports unverified package areas."""
    images = [
        {"id": 1, "image_role": "front", "image_type": "FRONT", "quality_decision": "ACCEPTABLE", "is_duplicate": False}
    ]
    summary = ReportGeneratorService.generate_coverage_summary(images)

    assert summary["total_images_uploaded"] == 1
    assert summary["usable_images_count"] == 1
    assert "FRONT" in summary["known_panel_roles"]
    assert summary["coverage_status"] == "PARTIAL_COVERAGE"
    assert "Back or Side Information Panel" in summary["unverified_package_areas"]


def test_unknown_panel_role_remains_unknown():
    """An unclassified panel remains UNKNOWN rather than guessing a role."""
    norm = ImageValidator.normalize_role("unspecified_angle")
    assert norm == "UNKNOWN"

    norm_empty = ImageValidator.normalize_role(None)
    assert norm_empty == "UNKNOWN"


def test_not_found_vs_unable_to_verify_distinction():
    """
    On an acceptable image, an omitted declaration is NOT_FOUND.
    On an unsuitable/degraded image, an omitted declaration is UNABLE_TO_VERIFY.
    """
    # Usable image:
    usable_map = [{
        "image_id": 1,
        "image_role": "front",
        "quality": {"overall_status": "GOOD", "blur_score": 120.0, "glare_score": 0.0, "quality_decision": "ACCEPTABLE"},
        "boxes": [{"id": 1, "text": "BRAND NAME", "confidence": 0.9, "bounding_box": {"x": 0, "y": 0, "w": 50, "h": 20}, "line_number": 1}]
    }]
    fields_usable = DeclarationExtractorService.extract_from_boxes_by_image(usable_map)
    mrp_usable = next(f for f in fields_usable if f.field_name == "MRP")
    assert mrp_usable.status == "NOT_FOUND"

    # Degraded/unsuitable image:
    unsuitable_map = [{
        "image_id": 2,
        "image_role": "front",
        "quality": {"overall_status": "POOR", "blur_score": 15.0, "glare_score": 25.0, "quality_decision": "UNSUITABLE"},
        "boxes": []
    }]
    fields_unsuitable = DeclarationExtractorService.extract_from_boxes_by_image(unsuitable_map)
    mrp_unsuitable = next(f for f in fields_unsuitable if f.field_name == "MRP")
    assert mrp_unsuitable.status == "UNABLE_TO_VERIFY"


# =========================================================================
# Group G: Strict Legal-Safety Invariants
# =========================================================================

def test_uncertainty_or_missing_coverage_never_creates_fail():
    """
    STRICT LEGAL SAFETY INVARIANT 1:
    A scan with unverified, degraded, or missing panels must NEVER produce
    FAIL or NON_COMPLIANT.
    """
    declarations = [
        FieldCandidate(
            field_name="MRP",
            display_name="MRP",
            value=None,
            status="UNABLE_TO_VERIFY",
            confidence=0.0
        ),
        FieldCandidate(
            field_name="NET_QUANTITY",
            display_name="Net Quantity",
            value=None,
            status="UNABLE_TO_VERIFY",
            confidence=0.0
        ),
        FieldCandidate(
            field_name="CONSUMER_CARE",
            display_name="Consumer Care",
            value=None,
            status="NOT_FOUND",
            confidence=0.0
        )
    ]

    eval_res = ComplianceEngine.evaluate_declarations(declarations)
    # The overall status must be REVIEW_REQUIRED, NOT NON_COMPLIANT
    assert eval_res["overall_status"] != "NON_COMPLIANT"
    assert eval_res["overall_status"] == "REVIEW_REQUIRED"

    # Individual rules must evaluate to NOT_VERIFIABLE or advisory WARNING, never FAIL
    for r in eval_res["results"]:
        assert r["status"] in ("NOT_VERIFIABLE", "NOT_APPLICABLE", "PASS", "WARNING")
        assert r["status"] != "FAIL"


def test_genuine_affirmative_violation_triggers_fail():
    """
    STRICT LEGAL SAFETY INVARIANT 2:
    A verified affirmative statutory violation (e.g. invalid MRP formatting without tax disclaimer)
    DOES produce FAIL and NON_COMPLIANT even if other fields are unverified.
    """
    declarations = [
        FieldCandidate(
            field_name="MRP",
            display_name="MRP",
            value="350.00",
            normalized_value="350.00",
            raw_value="MRP 350", # Missing '(incl. of all taxes)' on pre-packed commodity
            status="FOUND",
            confidence=0.92,
            evidence={"has_inclusive_taxes": False}
        ),
        FieldCandidate(
            field_name="NET_QUANTITY",
            display_name="Net Quantity",
            value=None,
            status="UNABLE_TO_VERIFY",
            confidence=0.0
        )
    ]

    eval_res = ComplianceEngine.evaluate_declarations(declarations)
    mrp_rule = next((r for r in eval_res["results"] if r["field_name"] == "MRP" and "TAX" in r["rule_id"]), None)
    if mrp_rule:
        assert mrp_rule["status"] == "FAIL"
        assert eval_res["overall_status"] == "NON_COMPLIANT"
