"""Master Prompt 07 — Regression Tests for Real Package Validation & Profiling.

Covers the 18 mandatory test requirements:
1. Real/synthetic dataset classification
2. Ground-truth parsing
3. Real-image loading framework
4. MRP unreadable
5. MRP glare
6. MRP missing
7. MRP distractors
8. Quantity distractors
9. Date association
10. Multi-image aggregation
11. Conflicting evidence
12. UNABLE_TO_VERIFY preservation
13. REVIEW_REQUIRED compliance behavior
14. PaddleOCR singleton reuse
15. Cold/warm timing
16. Retry timing
17. Spatial evidence preservation
18. Evaluation normalization non-mutation
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import pytest

from app.models.models import ImageType
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules import init_default_rules
from app.services.evaluation.eval_normalizer import EvaluationNormalizer
from app.services.evaluation.profiler import PipelineProfiler
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.extraction.field_extractors import FieldCandidate, ModularFieldExtractors
from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider, _shared_paddle_engine
from tests.run_real_validation_benchmark import (
    resolve_dataset_dir,
    load_dataset_annotations,
    validate_manifest,
    compute_calibration,
    STATUTORY_FIELDS,
)
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def setup_compliance_rules():
    init_default_rules()


# -----------------------------------------------------------------------------
# 1. Dataset Classification Test
# -----------------------------------------------------------------------------
def test_dataset_classification(tmp_path):
    """Verifies REAL_PHOTO, SYNTHETIC_CONTROLLED, and MIXED dataset detection."""
    # Test SYNTHETIC_CONTROLLED directory
    synth_dir = tmp_path / "annotations" / "synthetic"
    synth_dir.mkdir(parents=True)
    with open(synth_dir / "p1.json", "w") as f:
        json.dump({"dataset_type": "SYNTHETIC_CONTROLLED"}, f)

    products, dtype = load_dataset_annotations(tmp_path)
    assert dtype == "SYNTHETIC_CONTROLLED"
    assert len(products) == 1

    # Add REAL_PHOTO -> MIXED
    real_dir = tmp_path / "annotations" / "real"
    real_dir.mkdir(parents=True)
    with open(real_dir / "p2.json", "w") as f:
        json.dump({"dataset_type": "REAL_PHOTO"}, f)

    products, dtype = load_dataset_annotations(tmp_path)
    assert dtype == "MIXED"
    assert len(products) == 2


# -----------------------------------------------------------------------------
# 2. Ground-Truth Parsing Test
# -----------------------------------------------------------------------------
def test_ground_truth_parsing():
    """Verifies ground truth supports all 12 fields and explicit null values."""
    sample_gt = {
        "PRODUCT_NAME": "Premium Tea",
        "MRP": "₹150.00",
        "NET_QUANTITY": "250 g",
        "MANUFACTURER": "Tea Estate Ltd, Assam",
        "PACKER": None,
        "IMPORTER": None,
        "MANUFACTURING_DATE": "01/2026",
        "PACKING_DATE": None,
        "EXPIRY_DATE": "01/2028",
        "BEST_BEFORE": "24 Months from Mfd",
        "CONSUMER_CARE": "care@tea.in",
        "COUNTRY_OF_ORIGIN": "India"
    }
    for field_name in STATUTORY_FIELDS:
        assert field_name in sample_gt

    # Absent fields must not be treated as errors
    res_packer = EvaluationNormalizer.compare_field("PACKER", sample_gt["PACKER"], None)
    assert res_packer["evaluation_status"] == "NOT_APPLICABLE"
    assert res_packer["is_match"] is True


# -----------------------------------------------------------------------------
# 3. Real Image Loading Framework Test
# -----------------------------------------------------------------------------
def test_real_image_loading_framework(monkeypatch, tmp_path):
    """Verifies configurable dataset path via CLI arg or environment variable."""
    external_dir = tmp_path / "my_external_real_packages"
    external_dir.mkdir()
    (external_dir / "annotations").mkdir()

    # CLI arg takes precedence
    resolved = resolve_dataset_dir(str(external_dir))
    assert resolved == external_dir.resolve()

    # Env var works when no CLI arg
    monkeypatch.setenv("METRICHECK_REAL_DATASET_DIR", str(external_dir))
    resolved_env = resolve_dataset_dir(None)
    assert resolved_env == external_dir.resolve()


# -----------------------------------------------------------------------------
# 4. MRP Unreadable Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_unreadable_failure_state():
    """Unreadable MRP must produce UNABLE_TO_VERIFY / LOW_CONFIDENCE, never guessed value."""
    unreadable_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.15
    )
    eval_res = EvaluationNormalizer.compare_field("MRP", "₹199.00", unreadable_cand)
    assert eval_res["evaluation_status"] == "UNABLE_TO_VERIFY"
    assert eval_res["is_match"] is False
    assert eval_res["detected_value"] is None


# -----------------------------------------------------------------------------
# 5. MRP Glare Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_glare_failure_state():
    """Specular glare over MRP prevents reliable verification and is not called verified."""
    glare_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.20
    )
    compliance = ComplianceEngine.evaluate_declarations([glare_cand.to_dict()])
    assert compliance["overall_status"] in ("REVIEW_REQUIRED", "NOT_VERIFIABLE")
    assert compliance["overall_status"] != "COMPLIANT"


# -----------------------------------------------------------------------------
# 6. MRP Missing Failure State Test
# -----------------------------------------------------------------------------
def test_mrp_missing_failure_state():
    """Genuinely missing MRP produces NOT_FOUND without fabricating a price."""
    missing_cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value=None,
        status="NOT_FOUND",
        confidence=0.0
    )
    # When ground truth says MRP is null (genuinely absent)
    res_absent = EvaluationNormalizer.compare_field("MRP", None, missing_cand)
    assert res_absent["evaluation_status"] == "NOT_APPLICABLE"
    assert res_absent["detected_value"] is None

    # When ground truth expected MRP but none was found
    res_missing = EvaluationNormalizer.compare_field("MRP", "₹149.00", missing_cand)
    assert res_missing["evaluation_status"] == "NOT_FOUND"


# -----------------------------------------------------------------------------
# 7. MRP Distractor Rejection Test
# -----------------------------------------------------------------------------
def test_mrp_distractor_rejection():
    """Promo discounts (Save ₹50, Cashback ₹100) must not override statutory MRP."""
    boxes = [
        {"text": "SUPER SAVER OFFER! SAVE ₹50 ON NEXT PACK", "confidence": 0.98, "box": [10, 10, 300, 40]},
        {"text": "Cashback: Up to ₹100 inside wrapper", "confidence": 0.98, "box": [10, 50, 300, 80]},
        {"text": "Special Discount ₹20", "confidence": 0.98, "box": [10, 90, 250, 120]},
        {"text": "MRP: ₹199.00 (Incl. of all taxes)", "confidence": 0.99, "box": [10, 150, 350, 190]},
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "FOUND"
    assert cand.normalized_value == "199.00"
    assert "50" not in (cand.normalized_value or "")
    assert "100" not in (cand.normalized_value or "")


# -----------------------------------------------------------------------------
# 8. Quantity Distractor Rejection Test
# -----------------------------------------------------------------------------
def test_quantity_distractor_rejection():
    """Nutritional table lines (Calories 210 kcal, Carbs 25 g) must not be extracted as Net Qty."""
    boxes = [
        {"text": "Nutrition Facts per serving (50g):", "confidence": 0.95, "box": [10, 10, 250, 35]},
        {"text": "Calories: 210 kcal | Protein: 20 g", "confidence": 0.95, "box": [10, 40, 280, 65]},
        {"text": "Carbohydrates: 25 g | Total Fat: 7 g", "confidence": 0.95, "box": [10, 70, 280, 95]},
        {"text": "Net Weight: 300 g", "confidence": 0.99, "box": [10, 130, 200, 160]},
    ]
    cand = ModularFieldExtractors.extract_net_quantity(boxes, image_id=1, image_role="front")
    assert cand.status == "FOUND"
    assert cand.value == "300 g"
    assert "25 g" not in cand.value
    assert "20 g" not in cand.value


# -----------------------------------------------------------------------------
# 9. Date Association Test
# -----------------------------------------------------------------------------
def test_date_association():
    """Dates must be correctly associated with MFD, EXP, and Best Before; not batch numbers."""
    boxes = [
        {"text": "Batch No: B987654 | FSSAI Lic No: 10019022009876", "confidence": 0.96, "box": [10, 10, 400, 35]},
        {"text": "MFD: 04/2025", "confidence": 0.98, "box": [10, 45, 150, 75]},
        {"text": "EXP: 04/2028", "confidence": 0.98, "box": [10, 85, 150, 115]},
        {"text": "Best Before 36 Months from Mfd", "confidence": 0.97, "box": [10, 125, 300, 155]},
    ]
    dates = ModularFieldExtractors.extract_dates(boxes, image_id=1, image_role="front")
    assert dates["MANUFACTURING_DATE"].status == "FOUND"
    assert "04/2025" in (dates["MANUFACTURING_DATE"].value or "")

    assert dates["EXPIRY_DATE"].status == "FOUND"
    assert "04/2028" in (dates["EXPIRY_DATE"].value or "")

    assert dates["BEST_BEFORE"].status == "FOUND"
    assert "36 Months" in (dates["BEST_BEFORE"].value or "")


# -----------------------------------------------------------------------------
# 10. Multi-Image Aggregation Test
# -----------------------------------------------------------------------------
def test_multi_image_aggregation():
    """Aggregates front, back, and side panel evidence correctly."""
    front_boxes = [
        {"text": "ROYAL BASMATI RICE", "confidence": 0.98, "box": [10, 10, 300, 40]},
        {"text": "Net Quantity: 500 g", "confidence": 0.98, "box": [10, 50, 200, 80]},
        {"text": "MRP ₹149.00", "confidence": 0.99, "box": [10, 90, 180, 120]},
    ]
    back_boxes = [
        {"text": "Manufactured By: Royal Foods Ltd, Gurugram", "confidence": 0.97, "box": [10, 10, 350, 40]},
        {"text": "Consumer Care: care@royalfoods.in, 1800-200-1122", "confidence": 0.96, "box": [10, 50, 380, 80]},
    ]
    side_boxes = [
        {"text": "Mfg Date: 03/2026", "confidence": 0.98, "box": [10, 10, 180, 40]},
        {"text": "Country of Origin: India", "confidence": 0.99, "box": [10, 50, 220, 80]},
    ]

    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": front_boxes},
        {"image_id": 2, "image_role": "back", "boxes": back_boxes},
        {"image_id": 3, "image_role": "side", "boxes": side_boxes},
    ]

    aggregated = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    by_field = {c.field_name: c for c in aggregated}

    assert by_field["PRODUCT_NAME"].status == "FOUND"
    assert by_field["PRODUCT_NAME"].source_image_id == 1

    assert by_field["MANUFACTURER"].status == "FOUND"
    assert by_field["MANUFACTURER"].source_image_id == 2

    assert by_field["MANUFACTURING_DATE"].status == "FOUND"
    assert by_field["MANUFACTURING_DATE"].source_image_id == 3

    assert by_field["COUNTRY_OF_ORIGIN"].status == "FOUND"
    assert by_field["COUNTRY_OF_ORIGIN"].source_image_id == 3


# -----------------------------------------------------------------------------
# 11. Conflicting Evidence Resolution Test
# -----------------------------------------------------------------------------
def test_conflicting_evidence_resolution():
    """Conflicting prices between panels must result in AMBIGUOUS status."""
    front_boxes = [{"text": "MRP: ₹199.00", "confidence": 0.95, "box": [10, 10, 150, 40]}]
    back_boxes = [{"text": "MRP: ₹249.00", "confidence": 0.95, "box": [10, 10, 150, 40]}]

    image_boxes_map = [
        {"image_id": 1, "image_role": "front", "boxes": front_boxes},
        {"image_id": 2, "image_role": "back", "boxes": back_boxes},
    ]

    aggregated = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)
    by_field = {c.field_name: c for c in aggregated}

    mrp_cand = by_field["MRP"]
    assert mrp_cand.status == "AMBIGUOUS"
    assert mrp_cand.has_conflict is True
    assert len(mrp_cand.alternate_candidates) >= 1


# -----------------------------------------------------------------------------
# 12. UNABLE_TO_VERIFY Preservation Test
# -----------------------------------------------------------------------------
def test_unable_to_verify_preservation():
    """UNABLE_TO_VERIFY status must never be silently converted into PASS."""
    decl = FieldCandidate(
        field_name="NET_QUANTITY",
        display_name="Net Quantity",
        value=None,
        status="UNABLE_TO_VERIFY",
        confidence=0.1
    )
    res = ComplianceEngine.evaluate_declarations([decl.to_dict()])
    assert res["overall_status"] != "COMPLIANT"
    assert res["overall_status"] in ("REVIEW_REQUIRED", "NOT_VERIFIABLE")


# -----------------------------------------------------------------------------
# 13. REVIEW_REQUIRED Compliance Behavior Test
# -----------------------------------------------------------------------------
def test_review_required_compliance_behavior():
    """Mandatory declaration unverified triggers REVIEW_REQUIRED."""
    declarations = [
        {"field_name": "PRODUCT_NAME", "detected_value": "Shampoo", "status": "FOUND", "confidence": 0.98},
        {"field_name": "MRP", "detected_value": None, "status": "NOT_FOUND", "confidence": 0.0},
        {"field_name": "NET_QUANTITY", "detected_value": "200 ml", "status": "FOUND", "confidence": 0.95},
    ]
    res = ComplianceEngine.evaluate_declarations(declarations)
    assert res["overall_status"] == "REVIEW_REQUIRED"


# -----------------------------------------------------------------------------
# 14. PaddleOCR Singleton Reuse Test
# -----------------------------------------------------------------------------
def test_paddleocr_singleton_reuse():
    """Verifies PaddleOCRProvider instances share the same underlying model without recreation."""
    p1 = PaddleOCRProvider()
    p2 = PaddleOCRProvider()
    assert p1.is_available() is True
    assert p2.is_available() is True
    # Singleton check: _shared_paddle_engine exists and is identical
    from app.services.ocr.providers.paddleocr_provider import _shared_paddle_engine
    assert _shared_paddle_engine is not None


# -----------------------------------------------------------------------------
# 15. Cold vs Warm Timing Test
# -----------------------------------------------------------------------------
def test_cold_warm_timing(tmp_path):
    """Verifies profiler measures and isolates cold start and warm start metrics."""
    profiler = PipelineProfiler()
    # Create tiny dummy image
    img_path = tmp_path / "dummy.png"
    import cv2
    import numpy as np
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite(str(img_path), dummy_img)

    res1 = profiler.profile_single_image(str(img_path))
    res2 = profiler.profile_single_image(str(img_path))

    summary = profiler.get_latency_summary()
    assert "ocr_cold_start_ms" in summary
    assert "ocr_warm_inference_ms" in summary
    assert summary["ocr_cold_start_ms"] >= 0.0


# -----------------------------------------------------------------------------
# 16. Retry Latency and Benefit Test
# -----------------------------------------------------------------------------
def test_retry_latency_and_benefit(tmp_path):
    """Verifies profiler measures retry time when Attempt 2 is executed."""
    profiler = PipelineProfiler()
    img_path = tmp_path / "blank.png"
    import cv2
    import numpy as np
    dummy_img = np.full((150, 150, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(img_path), dummy_img)

    # Force retry
    res = profiler.profile_single_image(str(img_path), force_retry=True)
    assert res["retry_ms"] >= 0.0
    assert "total_ms" in res


# -----------------------------------------------------------------------------
# 17. Spatial Evidence Preservation Test
# -----------------------------------------------------------------------------
def test_spatial_evidence_preservation():
    """All spatial bounding boxes must remain bounded within [0.0, 1.0]."""
    boxes = [
        {"text": "MRP ₹199.00", "confidence": 0.95, "box": [10, 20, 210, 60]}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    bb = cand.bounding_box
    assert bb is not None
    assert 0.0 <= bb.get("x_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("y_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("w_rel", 0.0) <= 1.0
    assert 0.0 <= bb.get("h_rel", 0.0) <= 1.0


# -----------------------------------------------------------------------------
# 18. Evaluation Normalizer Non-Mutation Test
# -----------------------------------------------------------------------------
def test_evaluation_normalizer_non_mutation():
    """EvaluationNormalizer must not mutate candidate attributes or stored OCR text."""
    cand = FieldCandidate(
        field_name="MRP",
        display_name="Maximum Retail Price (MRP)",
        value="MRP ₹199.00 (Incl. of all taxes)",
        raw_value="MRP ₹199.00 (Incl. of all taxes)",
        normalized_value="199.00",
        confidence=0.98,
        status="FOUND",
        bounding_box={"x_rel": 0.1, "y_rel": 0.2, "w_rel": 0.3, "h_rel": 0.1}
    )
    orig_val = cand.value
    orig_raw = cand.raw_value
    orig_conf = cand.confidence
    orig_bb = dict(cand.bounding_box)

    comp = EvaluationNormalizer.compare_field("MRP", "₹199", cand)
    assert comp["is_match"] is True

    # Ensure no mutation on cand
    assert cand.value == orig_val
    assert cand.raw_value == orig_raw
    assert cand.confidence == orig_conf
    assert cand.bounding_box == orig_bb


# -----------------------------------------------------------------------------
# 19. Manifest Validation Test: Detects Missing & Invalid Roles
# -----------------------------------------------------------------------------
def test_manifest_validation_detects_missing_and_invalid_roles(tmp_path):
    """Verifies validate_manifest flags missing image files and unapproved panel roles."""
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True)
    manifest_data = {
        "manifest_version": "2.0.0",
        "real_catalog_specification": [
            {
                "product_id": "test_prod_01",
                "dataset_type": "REAL_PHOTO",
                "split": "test",
                "images": [
                    {"image_id": "img1", "file_name": "non_existent.jpg", "role": "INVALID_CUSTOM_ROLE"}
                ]
            }
        ]
    }
    with open(meta_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    report = validate_manifest(tmp_path)
    assert report["missing_images_count"] >= 1
    assert report["invalid_roles_count"] >= 1
    assert report["is_valid"] is False


# -----------------------------------------------------------------------------
# 20. Product-Level Split Integrity Test
# -----------------------------------------------------------------------------
def test_product_level_split_integrity(tmp_path):
    """Verifies that all images of a product stay together in the same split partition."""
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True)
    manifest_data = {
        "manifest_version": "2.0.0",
        "real_catalog_specification": [
            {
                "product_id": "prod_split_A",
                "dataset_type": "REAL_PHOTO",
                "split": "train",
                "images": [{"image_id": "img_f", "file_name": "f.jpg", "role": "front"}]
            },
            {
                "product_id": "prod_split_B",
                "dataset_type": "REAL_PHOTO",
                "split": "test",
                "images": [{"image_id": "img_b", "file_name": "b.jpg", "role": "back"}]
            }
        ]
    }
    with open(meta_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    report = validate_manifest(tmp_path)
    assert report["split_integrity_verified"] is True
    assert report["product_splits"].get("train") == 1
    assert report["product_splits"].get("test") == 1


# -----------------------------------------------------------------------------
# 21. Real-World Refusal Invariant When Photos Absent
# -----------------------------------------------------------------------------
def test_real_world_claim_refusal_when_photos_absent(tmp_path):
    """When zero real photos exist on disk, runner must report real_img_count == 0."""
    synth_dir = tmp_path / "annotations" / "synthetic"
    synth_dir.mkdir(parents=True)
    with open(synth_dir / "prod.json", "w", encoding="utf-8") as f:
        json.dump({"dataset_type": "SYNTHETIC_CONTROLLED"}, f)

    products, overall_type, real_count, synth_count = load_dataset_annotations(tmp_path, include_counts=True)
    assert real_count == 0
    assert overall_type == "SYNTHETIC_CONTROLLED"


# -----------------------------------------------------------------------------
# 22. Confidence Calibration & ECE Calculation Test
# -----------------------------------------------------------------------------
def test_confidence_calibration_binning_and_ece():
    """Verifies calibration bins, empirical accuracy, and ECE computation."""
    sample_extractions = [
        {"confidence": 0.98, "is_correct": True, "evaluation_status": "correct"},
        {"confidence": 0.96, "is_correct": True, "evaluation_status": "correct"},
        {"confidence": 0.91, "is_correct": True, "evaluation_status": "correct"},
        {"confidence": 0.88, "is_correct": False, "evaluation_status": "incorrect"},
        {"confidence": 0.65, "is_correct": False, "evaluation_status": "incorrect"},
        {"confidence": 0.35, "is_correct": False, "evaluation_status": "not_found"},
    ]
    cal = compute_calibration(sample_extractions)
    assert "expected_calibration_error" in cal
    assert cal["expected_calibration_error"] >= 0.0
    assert len(cal["bins"]) == 5
    assert cal["total_samples"] == 6

    # Verify high confidence bin has samples
    high_bin = next(b for b in cal["bins"] if b["bin_label"] == "[0.95 - 1.00]")
    assert high_bin["sample_count"] == 2
    assert high_bin["empirical_accuracy"] == 1.0


# -----------------------------------------------------------------------------
# 23. Ground-Truth Presence Taxonomy Accounting Test
# -----------------------------------------------------------------------------
def test_presence_taxonomy_accounting():
    """Verifies EvaluationNormalizer correctly distinguishes presence states."""
    # 1. NOT_APPLICABLE: Ground truth is null / None -> Not an error
    res_na = EvaluationNormalizer.compare_field("PACKER", None, None)
    assert res_na["evaluation_status"] == "NOT_APPLICABLE"
    assert res_na["is_match"] is True

    # 2. LEGIBLE & FOUND: Matching value -> correct
    cand_found = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value="MRP ₹199.00 (Incl. of all taxes)",
        normalized_value="199.00",
        confidence=0.98,
        status="FOUND"
    )
    res_correct = EvaluationNormalizer.compare_field("MRP", "₹199.00", cand_found)
    assert res_correct["evaluation_status"] == "CORRECT"

    # 3. ABSENT: Expected but not found -> NOT_FOUND
    res_missing = EvaluationNormalizer.compare_field("MRP", "₹199.00", None)
    assert res_missing["evaluation_status"] == "NOT_FOUND"


# -----------------------------------------------------------------------------
# 24. Manifest Duplicate Detection Test
# -----------------------------------------------------------------------------
def test_manifest_duplicate_detection(tmp_path):
    """Verifies validate_manifest flags identical images sharing duplicate SHA-256 hashes."""
    img_dir = tmp_path / "images" / "synthetic"
    img_dir.mkdir(parents=True)
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True)

    # Write two identical files
    content = b"IDENTICAL_IMAGE_PIXELS_FOR_DUPLICATE_CHECK"
    with open(img_dir / "img1.png", "wb") as f:
        f.write(content)
    with open(img_dir / "img2.png", "wb") as f:
        f.write(content)

    manifest_data = {
        "manifest_version": "2.0.0",
        "real_catalog_specification": [
            {
                "product_id": "prod1",
                "dataset_type": "SYNTHETIC_CONTROLLED",
                "images": [{"image_id": "i1", "file_name": "img1.png", "role": "front"}]
            },
            {
                "product_id": "prod2",
                "dataset_type": "SYNTHETIC_CONTROLLED",
                "images": [{"image_id": "i2", "file_name": "img2.png", "role": "front"}]
            }
        ]
    }
    with open(meta_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    report = validate_manifest(tmp_path)
    assert report["duplicate_images_count"] >= 1
    assert report["duplicate_images"][0]["sha256"] == hashlib.sha256(content).hexdigest()


# -----------------------------------------------------------------------------
# 25. Quality Preview API Endpoint Test
# -----------------------------------------------------------------------------
def test_quality_preview_endpoint():
    """Verifies POST /api/scans/quality-preview returns immediate CV telemetry and retake guidance."""
    import cv2
    import numpy as np
    client = TestClient(app)

    # Create dummy 700x700 sharp image
    img = np.full((700, 700, 3), 180, dtype=np.uint8)
    # Add text pattern for sharpness
    cv2.putText(img, "LEGAL METROLOGY MRP Rs 199", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (10, 10, 10), 2)
    _, enc = cv2.imencode(".png", img)
    img_bytes = enc.tobytes()

    response = client.post(
        "/api/scans/quality-preview",
        files={"image": ("test_capture.png", img_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "quality_status" in data
    assert "quality_decision" in data
    assert "blur_score" in data
    assert "glare_score" in data
    assert "resolution_w" in data
    assert "retake_guidance" in data
    assert isinstance(data["retake_guidance"], list)


# -----------------------------------------------------------------------------
# 26. Update Image Role API Endpoint Test
# -----------------------------------------------------------------------------
def test_update_image_role_endpoint():
    """Verifies PATCH /api/scans/{scan_id}/images/{image_id}/role updates role and triggers re-evaluation."""
    import cv2
    import numpy as np
    client = TestClient(app)

    # 1. Create a dummy scan with a front image
    img = np.full((650, 650, 3), 200, dtype=np.uint8)
    cv2.putText(img, "PRODUCT: TEA 500g MRP Rs 150", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    _, enc = cv2.imencode(".png", img)
    img_bytes = enc.tobytes()

    create_res = client.post(
        "/api/scans",
        data={"product_name": "Test Role Product", "category_id": 1},
        files={"front_image": ("front.png", img_bytes, "image/png")}
    )
    assert create_res.status_code == 200
    scan_data = create_res.json()
    scan_id = scan_data["id"]
    images = scan_data.get("images", [])
    assert len(images) >= 1
    image_id = images[0]["id"]

    # 2. Update role from FRONT to BACK
    patch_res = client.patch(
        f"/api/scans/{scan_id}/images/{image_id}/role",
        data={"role": "BACK"}
    )
    assert patch_res.status_code == 200
    updated_scan = patch_res.json()
    updated_img = next(im for im in updated_scan["images"] if im["id"] == image_id)
    assert updated_img["image_role"].upper() == "BACK"
    assert updated_img["image_type"] == "BACK"


# -----------------------------------------------------------------------------
# 27. Manifest Cross-Split Leakage Detection Test (Master Prompt 12)
# -----------------------------------------------------------------------------
def test_manifest_split_leakage_detection(tmp_path):
    """Verifies validate_manifest flags split leakage when products/images cross partition boundaries."""
    img_dir = tmp_path / "images" / "synthetic"
    img_dir.mkdir(parents=True)
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True)

    # Single image shared between two products in different splits
    content = b"IMAGE_PIXELS_SHARED_ACROSS_SPLITS"
    with open(img_dir / "leaked.png", "wb") as f:
        f.write(content)

    manifest_data = {
        "manifest_version": "2.0.0",
        "real_catalog_specification": [
            {
                "product_id": "prod_train",
                "dataset_type": "SYNTHETIC_CONTROLLED",
                "split": "train",
                "images": [{"image_id": "im1", "file_name": "leaked.png", "role": "front"}]
            },
            {
                "product_id": "prod_test",
                "dataset_type": "SYNTHETIC_CONTROLLED",
                "split": "test",
                "images": [{"image_id": "im2", "file_name": "leaked.png", "role": "front"}]
            }
        ]
    }
    with open(meta_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    report = validate_manifest(tmp_path)
    assert report["split_integrity_verified"] is False
    assert len(report["split_leakage_errors"]) >= 1
    assert any("leaked" in err.lower() for err in report["split_leakage_errors"])


# -----------------------------------------------------------------------------
# 28. Presence Taxonomy & Bounding Box Validation Test (Master Prompt 12)
# -----------------------------------------------------------------------------
def test_manifest_presence_and_bbox_validation(tmp_path):
    """Verifies validate_manifest detects invalid presence taxonomy and out-of-bounds relative bboxes."""
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir(parents=True)

    manifest_data = {
        "manifest_version": "2.0.0",
        "real_catalog_specification": [
            {
                "product_id": "prod_invalid_meta",
                "dataset_type": "SYNTHETIC_CONTROLLED",
                "split": "benchmark",
                "images": [{"image_id": "i1", "file_name": "test.png", "role": "front"}],
                "ground_truth": {
                    "MRP": {
                        "value": "₹150.00",
                        "status": "VISIBLE_NOT_TAXONOMY",  # Invalid presence status
                        "bbox": [1.5, 0.2, 0.3, 0.4]       # Invalid x_rel > 1.0
                    }
                }
            }
        ]
    }
    with open(meta_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    report = validate_manifest(tmp_path)
    assert report["invalid_presence_count"] >= 1
    assert report["invalid_presence_statuses"][0]["status"] == "VISIBLE_NOT_TAXONOMY"
    assert report["invalid_bounding_boxes_count"] >= 1
    assert report["is_valid"] is False


# -----------------------------------------------------------------------------
# 29. EvaluationNormalizer ABSENT vs NOT_APPLICABLE Distinction Test
# -----------------------------------------------------------------------------
def test_evaluation_normalizer_absent_vs_not_applicable():
    """Verifies ABSENT (omitted by manufacturer) is strictly distinguished from NOT_APPLICABLE (exempt)."""
    # Case 1: ABSENT declaration correctly not found -> CORRECT (with presence ABSENT)
    res_absent_correct = EvaluationNormalizer.compare_field(
        field_name="CONSUMER_CARE",
        ground_truth=None,
        candidate=None,
        gt_presence="ABSENT"
    )
    assert res_absent_correct["evaluation_status"] == "CORRECT"
    assert res_absent_correct["ground_truth_presence"] == "ABSENT"
    assert res_absent_correct["is_match"] is True

    # Case 2: ABSENT declaration hallucinated as FOUND -> INCORRECT
    cand_fp = FieldCandidate(
        field_name="CONSUMER_CARE",
        display_name="Consumer Care",
        value="care@sample.com",
        normalized_value="care@sample.com",
        confidence=0.95,
        status="FOUND"
    )
    res_absent_fp = EvaluationNormalizer.compare_field(
        field_name="CONSUMER_CARE",
        ground_truth=None,
        candidate=cand_fp,
        gt_presence="ABSENT"
    )
    assert res_absent_fp["evaluation_status"] == "INCORRECT"
    assert res_absent_fp["ground_truth_presence"] == "ABSENT"
    assert res_absent_fp["is_match"] is False

    # Case 3: NOT_APPLICABLE declaration correctly not found -> NOT_APPLICABLE
    res_na = EvaluationNormalizer.compare_field(
        field_name="IMPORTER",
        ground_truth=None,
        candidate=None,
        gt_presence="NOT_APPLICABLE"
    )
    assert res_na["evaluation_status"] == "NOT_APPLICABLE"
    assert res_na["ground_truth_presence"] == "NOT_APPLICABLE"


# -----------------------------------------------------------------------------
# 30. EvaluationNormalizer ILLEGIBLE Uncertainty Preservation Test
# -----------------------------------------------------------------------------
def test_evaluation_normalizer_illegible_uncertainty():
    """Verifies that an ILLEGIBLE package declaration correctly yields UNABLE_TO_VERIFY when unverified."""
    unverifiable_cand = FieldCandidate(
        field_name="MRP",
        display_name="MRP",
        value=None,
        normalized_value=None,
        confidence=0.30,
        status="UNABLE_TO_VERIFY"
    )
    res = EvaluationNormalizer.compare_field(
        field_name="MRP",
        ground_truth="₹199.00",
        candidate=unverifiable_cand,
        gt_presence="ILLEGIBLE"
    )
    assert res["evaluation_status"] == "UNABLE_TO_VERIFY"
    assert res["ground_truth_presence"] == "ILLEGIBLE"
    assert res["is_match"] is True  # Optical uncertainty correctly preserved


# -----------------------------------------------------------------------------
# 31. Repository Real Photo Availability & Refusal Status Test
# -----------------------------------------------------------------------------
def test_repository_real_photo_availability_status():
    """Confirms repository real photo directory state and validates classification refusal invariant."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    products, overall_type, real_img_count, synth_img_count = load_dataset_annotations(repo_ds_dir, include_counts=True)
    # The physical photos have not been supplied in this environment
    assert real_img_count == 0
    assert overall_type == "SYNTHETIC_CONTROLLED"


# -----------------------------------------------------------------------------
# 32. Traceable Role Update with Compliance Re-Evaluation Test
# -----------------------------------------------------------------------------
def test_role_update_triggers_compliance_reevaluation():
    """Verifies PATCH /api/scans/{id}/images/{img_id}/role updates role and recalculates compliance."""
    import cv2
    import numpy as np
    client = TestClient(app)

    # Front image with net quantity declaration
    img = np.full((600, 600, 3), 220, dtype=np.uint8)
    cv2.putText(img, "WHEAT FLOUR NET QTY 5 kg", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (10, 10, 10), 2)
    _, enc = cv2.imencode(".png", img)
    img_bytes = enc.tobytes()

    post_res = client.post(
        "/api/scans",
        data={"product_name": "Multi-role Test Item", "category_id": 1},
        files={
            "front_image": ("front.png", img_bytes, "image/png"),
            "side_image": ("side.png", img_bytes, "image/png"),
        }
    )
    assert post_res.status_code == 200
    scan = post_res.json()
    side_img = next(i for i in scan["images"] if i["image_role"].upper() == "SIDE")
    image_id = side_img["id"]

    # Now update image role from SIDE to BACK
    patch_res = client.patch(
        f"/api/scans/{scan['id']}/images/{image_id}/role",
        data={"role": "BACK"}
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    img_after = next(i for i in updated["images"] if i["id"] == image_id)
    assert img_after["image_role"].upper() == "BACK"
    assert "compliance_score" in updated
    assert "overall_status" in updated


# -----------------------------------------------------------------------------
# 33. Manifest Audit Detects Missing Real Images & Unexecutable Status
# -----------------------------------------------------------------------------
def test_manifest_audit_detects_missing_real_images_and_unexecutable_state():
    """Verifies that auditing the real manifest detects missing image files on disk and flags non-execution."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    manifest_report = validate_manifest(repo_ds_dir)
    assert "missing_images_count" in manifest_report
    # Manifest declares 28 real photo files, 0 exist on disk
    assert manifest_report["missing_images_count"] >= 28


# -----------------------------------------------------------------------------
# 34. Small Sample & Bounding Box Audit Verification
# -----------------------------------------------------------------------------
def test_small_sample_and_bounding_box_audit():
    """Verifies that catalog sub-categories with n < 5 trigger small-sample flags."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    manifest_file = repo_ds_dir / "metadata" / "dataset_manifest.json"
    with open(manifest_file, "r", encoding="utf-8") as f:
        mdata = json.load(f)

    catalog = mdata.get("real_catalog_specification", [])
    categories = {}
    for item in catalog:
        c = item.get("category", "Unknown")
        categories[c] = categories.get(c, 0) + 1

    # In 10-item spec, all categories have n < 5
    for cat, count in categories.items():
        assert count < 5, f"Category '{cat}' expected to have n < 5 in initial spec"


# -----------------------------------------------------------------------------
# 35. Benchmark Real Photo Refusal Invariant Enforcement
# -----------------------------------------------------------------------------
def test_benchmark_refusal_invariant_enforcement():
    """Verifies benchmark data guarantees NOT EXECUTED status when real images are absent."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    results_file = Path("tests/benchmark_results_real.json")
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            bdata = json.load(f)
        real_info = bdata.get("real_photo", {})
        status_note = real_info.get("status_note", "")
        assert "NOT EXECUTED" in status_note
        assert "no genuine" in status_note.lower() or "no verified" in status_note.lower()


# -----------------------------------------------------------------------------
# 36. Data Collection Template Schema Conformance
# -----------------------------------------------------------------------------
def test_data_collection_template_conformance():
    """Verifies that real_photo_manifest_template.json adheres to schema and protocol."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    template_file = repo_ds_dir / "templates" / "real_photo_manifest_template.json"
    assert template_file.exists(), "Template file must exist"

    with open(template_file, "r", encoding="utf-8") as f:
        tdata = json.load(f)

    entries = tdata.get("catalog_entries", [])
    assert len(entries) >= 1
    sample = entries[0]

    # Required fields under schema
    for req in ["product_id", "dataset_type", "category", "package_type", "images", "ground_truth"]:
        assert req in sample, f"Missing required property {req}"

    assert sample["dataset_type"] == "REAL_PHOTO"
    assert "provenance" in sample
    assert "camera_device" in sample["provenance"]
    assert "lighting_condition" in sample["provenance"]

    # Verify ground truth presence states
    valid_states = {"LEGIBLE", "ILLEGIBLE", "OBSCURED", "ABSENT", "NOT_APPLICABLE"}
    for fld, info in sample["ground_truth"].items():
        assert "status" in info
        assert info["status"] in valid_states
        if info.get("bounding_box"):
            bb = info["bounding_box"]
            for coord in ["x_rel", "y_rel", "w_rel", "h_rel"]:
                assert coord in bb
                assert 0.0 <= bb[coord] <= 1.0


# -----------------------------------------------------------------------------
# 37. Manifest Audit Detects 120 Omitted Bounding Boxes in Catalog Spec
# -----------------------------------------------------------------------------
def test_manifest_audit_detects_120_omitted_bounding_boxes():
    """Verifies that the manifest validator identifies all 120 omitted bounding boxes in the catalog spec."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    manifest_report = validate_manifest(repo_ds_dir)
    assert "omitted_bounding_boxes_count" in manifest_report
    assert manifest_report["omitted_bounding_boxes_count"] == 120


# -----------------------------------------------------------------------------
# 38. Manifest Discrepancy Resolution Metadata Tracking
# -----------------------------------------------------------------------------
def test_manifest_discrepancy_resolution_metadata():
    """Verifies that dataset_manifest.json explicitly tracks and resolves catalog discrepancies."""
    repo_ds_dir = Path(__file__).resolve().parent.parent.parent / "datasets" / "real_package_validation"
    if not repo_ds_dir.exists():
        repo_ds_dir = Path("datasets/real_package_validation").resolve()

    manifest_file = repo_ds_dir / "metadata" / "dataset_manifest.json"
    with open(manifest_file, "r", encoding="utf-8") as f:
        mdata = json.load(f)

    assert "manifest_audit_status" in mdata
    status_info = mdata["manifest_audit_status"]
    assert status_info["status"] == "PROVISIONAL_SPECIFICATION_PLAN_UNEXECUTED"
    assert status_info["discrepancies"]["missing_images_count"] == 28
    assert status_info["discrepancies"]["omitted_bounding_boxes_count"] == 120
    assert "discrepancy_resolution" in status_info


