import pytest
from app.services.extraction.field_extractors import ModularFieldExtractors, FieldCandidate
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.compliance.rules import init_default_rules
from app.models.models import ComplianceState

def setup_module():
    init_default_rules()

# ============================================================================
# MASTER PROMPT 08: REGRESSION & HARDENING TEST SUITE
# ============================================================================

def test_mrp_not_found():
    """
    When no MRP evidence exists, extraction must be NOT_FOUND,
    and compliance rule must evaluate to NOT_VERIFIABLE (never FAIL).
    """
    boxes = [
        {"id": 1, "text": "Chocolate Chip Biscuits", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 200, "h": 20}, "line_number": 1},
        {"id": 2, "text": "Net Weight 100 g", "confidence": 0.94, "bounding_box": {"x": 10, "y": 40, "w": 150, "h": 20}, "line_number": 2},
        {"id": 3, "text": "Ingredients: Wheat Flour, Sugar, Cocoa", "confidence": 0.92, "bounding_box": {"x": 10, "y": 70, "w": 300, "h": 20}, "line_number": 3},
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "NOT_FOUND"
    assert cand.value is None

    # Test compliance mapping
    decl = {
        "field_name": "MRP",
        "detected_value": None,
        "extraction_status": "NOT_FOUND",
        "status": "NOT_FOUND",
        "confidence": 0.0
    }
    res = ComplianceEngine.evaluate_declarations([decl])
    mrp_present = next(r for r in res["results"] if r["rule_id"] == "MRP_PRESENT")
    assert mrp_present["status"] == "NOT_VERIFIABLE"
    assert mrp_present["status"] != "FAIL"
    assert "No sufficiently reliable evidence" in mrp_present["message"]
    assert "Capture the package panel" in mrp_present["suggested_action"]


def test_mrp_unable_to_verify():
    """
    When MRP evidence exists but value is unreadable, corrupted, or fragmented,
    status must be UNABLE_TO_VERIFY, and compliance must be NOT_VERIFIABLE (never FAIL).
    """
    unreadable_cases = [
        [{"id": 1, "text": "MRP ₹1?9", "confidence": 0.50, "bounding_box": {"x": 10, "y": 10, "w": 120, "h": 20}, "line_number": 1}],
        [{"id": 2, "text": "MRP ₹", "confidence": 0.85, "bounding_box": {"x": 10, "y": 10, "w": 80, "h": 20}, "line_number": 1}],
        [{"id": 3, "text": "MRP ???", "confidence": 0.60, "bounding_box": {"x": 10, "y": 10, "w": 90, "h": 20}, "line_number": 1}],
        [{"id": 4, "text": "MRP", "confidence": 0.90, "bounding_box": {"x": 10, "y": 10, "w": 50, "h": 20}, "line_number": 1}],
    ]
    for boxes in unreadable_cases:
        cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="back")
        assert cand.status == "UNABLE_TO_VERIFY", f"Failed for {boxes[0]['text']}"
        assert cand.value is None

    # Test compliance mapping
    decl = {
        "field_name": "MRP",
        "detected_value": None,
        "extraction_status": "UNABLE_TO_VERIFY",
        "status": "UNABLE_TO_VERIFY",
        "confidence": 0.0
    }
    res = ComplianceEngine.evaluate_declarations([decl])
    mrp_present = next(r for r in res["results"] if r["rule_id"] == "MRP_PRESENT")
    assert mrp_present["status"] == "NOT_VERIFIABLE"
    assert mrp_present["status"] != "FAIL"
    assert "Relevant evidence appears to be present" in mrp_present["message"]
    assert "Capture a clearer close-up image" in mrp_present["suggested_action"]


def test_mrp_low_confidence():
    """
    When MRP is detected but confidence is below threshold, status must be LOW_CONFIDENCE,
    and compliance rule must evaluate to WARNING or NOT_VERIFIABLE (never FAIL).
    """
    boxes = [
        {"id": 1, "text": "MRP ₹199 (Incl. of all taxes)", "confidence": 0.43, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 20}, "line_number": 1}
    ]
    cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
    assert cand.status == "LOW_CONFIDENCE"
    assert cand.normalized_value == "199.00"

    decl = {
        "field_name": "MRP",
        "detected_value": cand.value,
        "normalized_value": cand.normalized_value,
        "extraction_status": "LOW_CONFIDENCE",
        "status": "UNABLE_TO_VERIFY",
        "confidence": cand.confidence
    }
    res = ComplianceEngine.evaluate_declarations([decl])
    mrp_present = next(r for r in res["results"] if r["rule_id"] == "MRP_PRESENT")
    assert mrp_present["status"] in ("WARNING", "NOT_VERIFIABLE")
    assert mrp_present["status"] != "FAIL"


def test_mrp_conflicting_values():
    """
    When different images declare conflicting MRP values, DeclarationExtractorService
    must set status=AMBIGUOUS and has_conflict=True without discarding either candidate.
    """
    img1 = {
        "image_id": 1,
        "image_role": "front",
        "boxes": [
            {"id": 101, "text": "MRP ₹199 (Incl. of all taxes)", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 200, "h": 20}, "line_number": 1}
        ]
    }
    img2 = {
        "image_id": 2,
        "image_role": "back",
        "boxes": [
            {"id": 201, "text": "MRP ₹249 (Incl. of all taxes)", "confidence": 0.94, "bounding_box": {"x": 10, "y": 10, "w": 200, "h": 20}, "line_number": 1}
        ]
    }
    fields = DeclarationExtractorService.extract_from_boxes_by_image([img1, img2])
    mrp_field = next(f for f in fields if f.field_name == "MRP")

    assert mrp_field.status == "AMBIGUOUS"
    assert mrp_field.has_conflict is True
    assert len(mrp_field.alternate_candidates) >= 1
    assert any("249" in alt["value"] or "199" in alt["value"] for alt in mrp_field.alternate_candidates)

    # Compliance evaluation check
    decl = {
        "field_name": "MRP",
        "detected_value": mrp_field.value,
        "extraction_status": "AMBIGUOUS",
        "has_conflict": True,
        "alternate_candidates": mrp_field.alternate_candidates,
        "confidence": mrp_field.confidence
    }
    res = ComplianceEngine.evaluate_declarations([decl])
    conflict_rule = next(r for r in res["results"] if r["rule_id"] == "MRP_CONFLICT_CHECK")
    assert conflict_rule["status"] == "NOT_VERIFIABLE"
    assert conflict_rule["status"] != "FAIL"


def test_promotional_price_not_mrp():
    """
    Promotional prices like 'Save ₹50', '₹50 OFF', 'Cashback ₹50' must NEVER be extracted as statutory MRP.
    """
    promo_cases = [
        [{"id": 1, "text": "Save ₹50 on this pack!", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1}],
        [{"id": 2, "text": "₹50 OFF Special Offer", "confidence": 0.93, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1}],
        [{"id": 3, "text": "Cashback ₹50 on UPI", "confidence": 0.94, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1}],
        [{"id": 4, "text": "₹50", "confidence": 0.91, "bounding_box": {"x": 10, "y": 10, "w": 50, "h": 20}, "line_number": 1}], # Standalone price without statutory cue
    ]
    for boxes in promo_cases:
        cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
        assert cand.status == "NOT_FOUND", f"Promotional text mistakenly extracted as MRP: {boxes[0]['text']}"
        assert cand.value is None


def test_discount_price_not_mrp():
    """
    Discounts, offer prices, and introductory prices must not become statutory MRP.
    """
    discount_cases = [
        [{"id": 1, "text": "Discount ₹100", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 150, "h": 20}, "line_number": 1}],
        [{"id": 2, "text": "Offer Price ₹199", "confidence": 0.92, "bounding_box": {"x": 10, "y": 10, "w": 160, "h": 20}, "line_number": 1}],
        [{"id": 3, "text": "Special Price ₹249", "confidence": 0.94, "bounding_box": {"x": 10, "y": 10, "w": 170, "h": 20}, "line_number": 1}],
        [{"id": 4, "text": "Starting ₹49", "confidence": 0.91, "bounding_box": {"x": 10, "y": 10, "w": 120, "h": 20}, "line_number": 1}],
    ]
    for boxes in discount_cases:
        cand = ModularFieldExtractors.extract_mrp(boxes, image_id=1, image_role="front")
        assert cand.status == "NOT_FOUND"


def test_product_name_excludes_statutory_labels():
    """
    Statutory labels (MRP, Net Wt, Mfg by, Expiry, Ingredients, etc.) must NEVER become the product name.
    """
    statutory_boxes = [
        {"id": 1, "text": "MRP ₹199 (Incl. of all taxes)", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 40}, "line_number": 1},
        {"id": 2, "text": "Net Weight: 500 g", "confidence": 0.94, "bounding_box": {"x": 10, "y": 60, "w": 200, "h": 35}, "line_number": 2},
        {"id": 3, "text": "Manufactured by: Sunrise Biscuits Pvt Ltd", "confidence": 0.93, "bounding_box": {"x": 10, "y": 100, "w": 350, "h": 30}, "line_number": 3},
        {"id": 4, "text": "Best Before 12 Months", "confidence": 0.91, "bounding_box": {"x": 10, "y": 140, "w": 220, "h": 25}, "line_number": 4},
        {"id": 5, "text": "Customer Care: 1800-200-1234", "confidence": 0.92, "bounding_box": {"x": 10, "y": 170, "w": 250, "h": 25}, "line_number": 5},
    ]
    cand = ModularFieldExtractors.extract_product_name(statutory_boxes, image_id=1, image_role="front")
    assert cand.status == "NOT_FOUND", f"Statutory declaration misclassified as product name: {cand.value}"


def test_product_name_excludes_promotional_text():
    """
    Promotional slogans and marketing badges must NEVER be classified as the product name.
    """
    promotional_boxes = [
        {"id": 1, "text": "BUY 1 GET 1 FREE", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 45}, "line_number": 1},
        {"id": 2, "text": "NEW & IMPROVED FORMULA", "confidence": 0.94, "bounding_box": {"x": 10, "y": 60, "w": 300, "h": 40}, "line_number": 2},
        {"id": 3, "text": "100% NATURAL & ORGANIC", "confidence": 0.92, "bounding_box": {"x": 10, "y": 110, "w": 280, "h": 35}, "line_number": 3},
        {"id": 4, "text": "EXTRA 20% MORE", "confidence": 0.91, "bounding_box": {"x": 10, "y": 150, "w": 200, "h": 30}, "line_number": 4},
    ]
    cand = ModularFieldExtractors.extract_product_name(promotional_boxes, image_id=1, image_role="front")
    assert cand.status == "NOT_FOUND", f"Promotional text misclassified as product name: {cand.value}"


def test_product_name_scoring():
    """
    Deterministic scoring must select the genuine product commodity name over
    promotional banners and statutory declarations based on position and scoring criteria.
    """
    boxes = [
        {"id": 1, "text": "LIMITED EDITION OFFER", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 30}, "line_number": 1},
        {"id": 2, "text": "ALMOND CRUNCH CHOCOLATE COOKIES", "confidence": 0.94, "bounding_box": {"x": 10, "y": 50, "w": 400, "h": 50}, "line_number": 2},
        {"id": 3, "text": "Net Weight 200 g", "confidence": 0.92, "bounding_box": {"x": 10, "y": 110, "w": 180, "h": 25}, "line_number": 3},
        {"id": 4, "text": "MRP ₹120.00", "confidence": 0.93, "bounding_box": {"x": 10, "y": 140, "w": 150, "h": 25}, "line_number": 4},
    ]
    cand = ModularFieldExtractors.extract_product_name(boxes, image_id=1, image_role="front")
    assert cand.status == "FOUND"
    assert cand.value == "ALMOND CRUNCH CHOCOLATE COOKIES"


def test_net_quantity_rejects_promotional_percentage():
    """
    Percentages like '20% EXTRA', '50% OFF', 'SAVE 50%' must NOT be extracted as net quantity.
    """
    promo_boxes = [
        {"id": 1, "text": "20% EXTRA VALUE PACK", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 20}, "line_number": 1},
        {"id": 2, "text": "50% OFF ON SECOND PACK", "confidence": 0.93, "bounding_box": {"x": 10, "y": 40, "w": 260, "h": 20}, "line_number": 2},
    ]
    cand = ModularFieldExtractors.extract_net_quantity(promo_boxes, image_id=1, image_role="front")
    assert cand.status == "NOT_FOUND"
    assert cand.value is None

    # Valid metric quantities must succeed
    valid_boxes = [
        {"id": 1, "text": "Net Weight: 500 g", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1}
    ]
    valid_cand = ModularFieldExtractors.extract_net_quantity(valid_boxes, image_id=1, image_role="front")
    assert valid_cand.status == "FOUND"
    assert valid_cand.normalized_value == "500 g"
    assert valid_cand.unit == "g"


def test_net_quantity_unable_to_verify():
    """
    When NET WT label exists but numeric value is unreadable, status must be UNABLE_TO_VERIFY.
    """
    boxes = [
        {"id": 1, "text": "NET WT. ???", "confidence": 0.50, "bounding_box": {"x": 10, "y": 10, "w": 120, "h": 20}, "line_number": 1}
    ]
    cand = ModularFieldExtractors.extract_net_quantity(boxes, image_id=1, image_role="front")
    assert cand.status == "UNABLE_TO_VERIFY"
    assert cand.value is None


def test_date_requires_context():
    """
    Bare numbers (120, 2026, 12.5) must not be fabricated into manufacturing or packaging dates.
    Contextual indicator (MFD, PKD, EXP, BEST BEFORE) is required.
    """
    bare_number_boxes = [
        {"id": 1, "text": "120", "confidence": 0.90, "bounding_box": {"x": 10, "y": 10, "w": 50, "h": 20}, "line_number": 1},
        {"id": 2, "text": "2026", "confidence": 0.92, "bounding_box": {"x": 10, "y": 40, "w": 60, "h": 20}, "line_number": 2},
        {"id": 3, "text": "12.5", "confidence": 0.89, "bounding_box": {"x": 10, "y": 70, "w": 50, "h": 20}, "line_number": 3},
    ]
    dates = ModularFieldExtractors.extract_dates(bare_number_boxes, image_id=1, image_role="back")
    assert dates["MANUFACTURING_DATE"].status == "NOT_FOUND"
    assert dates["EXPIRY_DATE"].status == "NOT_FOUND"

    # Contextual dates must be extracted properly
    context_boxes = [
        {"id": 10, "text": "MFD 12/09/2026", "confidence": 0.95, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1},
        {"id": 11, "text": "BEST BEFORE 12 MONTHS FROM MFD", "confidence": 0.93, "bounding_box": {"x": 10, "y": 40, "w": 300, "h": 20}, "line_number": 2},
    ]
    ctx_dates = ModularFieldExtractors.extract_dates(context_boxes, image_id=1, image_role="back")
    assert ctx_dates["MANUFACTURING_DATE"].status == "FOUND"
    assert ctx_dates["MANUFACTURING_DATE"].normalized_value == "12/09/2026"
    assert ctx_dates["BEST_BEFORE"].status == "FOUND"


def test_manufacturer_requires_context():
    """
    A company address without an explicit role label (Manufactured by, Packed by, etc.)
    must not automatically be classified as the statutory manufacturer.
    """
    unlabeled_entity_boxes = [
        {"id": 1, "text": "Apex Distribution & Supply Co", "confidence": 0.92, "bounding_box": {"x": 10, "y": 10, "w": 250, "h": 20}, "line_number": 1},
        {"id": 2, "text": "Plot 45, Sector 18, Gurugram 122001", "confidence": 0.90, "bounding_box": {"x": 10, "y": 35, "w": 280, "h": 20}, "line_number": 2},
    ]
    entities = ModularFieldExtractors.extract_entities(unlabeled_entity_boxes, image_id=1, image_role="back")
    assert entities["MANUFACTURER"].status in ("AMBIGUOUS", "NOT_FOUND")

    # Explicit statutory prefix must succeed
    labeled_entity_boxes = [
        {"id": 10, "text": "Manufactured by: Apex Foods India Pvt Ltd", "confidence": 0.94, "bounding_box": {"x": 10, "y": 10, "w": 320, "h": 20}, "line_number": 1},
        {"id": 11, "text": "Plot 45, Sector 18, Gurugram 122001, Haryana", "confidence": 0.92, "bounding_box": {"x": 10, "y": 35, "w": 340, "h": 20}, "line_number": 2},
    ]
    labeled_entities = ModularFieldExtractors.extract_entities(labeled_entity_boxes, image_id=1, image_role="back")
    assert labeled_entities["MANUFACTURER"].status == "FOUND"
    assert "Apex Foods" in labeled_entities["MANUFACTURER"].value


def test_consumer_care_requires_context():
    """
    Generic phone numbers or emails without Consumer Care context must NOT become statutory Consumer Care.
    """
    generic_contact_boxes = [
        {"id": 1, "text": "Office: 011-23456789", "confidence": 0.91, "bounding_box": {"x": 10, "y": 10, "w": 180, "h": 20}, "line_number": 1},
        {"id": 2, "text": "Website: www.apexcompany.com", "confidence": 0.93, "bounding_box": {"x": 10, "y": 35, "w": 220, "h": 20}, "line_number": 2},
    ]
    cand = ModularFieldExtractors.extract_consumer_care(generic_contact_boxes, image_id=1, image_role="back")
    assert cand.status in ("NOT_FOUND", "AMBIGUOUS")

    # Statutory consumer care cues must succeed
    statutory_care_boxes = [
        {"id": 10, "text": "For consumer complaints contact Customer Care:", "confidence": 0.94, "bounding_box": {"x": 10, "y": 10, "w": 350, "h": 20}, "line_number": 1},
        {"id": 11, "text": "Toll Free: 1800-200-9999, Email: care@apex.in", "confidence": 0.95, "bounding_box": {"x": 10, "y": 35, "w": 340, "h": 20}, "line_number": 2},
    ]
    statutory_cand = ModularFieldExtractors.extract_consumer_care(statutory_care_boxes, image_id=1, image_role="back")
    assert statutory_cand.status == "FOUND"
    assert "1800-200-9999" in statutory_cand.value


def test_country_of_origin_not_inferred():
    """
    Country of Origin MUST NOT be inferred from manufacturer address or city names.
    Explicit 'Country of Origin' or 'Made in' is strictly required.
    """
    mfg_address_boxes = [
        {"id": 1, "text": "Manufactured by: Royal Biscuits Ltd, Andheri East, Mumbai, Maharashtra, India", "confidence": 0.93, "bounding_box": {"x": 10, "y": 10, "w": 450, "h": 20}, "line_number": 1}
    ]
    origin_cand = ModularFieldExtractors.extract_country_of_origin(mfg_address_boxes, image_id=1, image_role="back")
    assert origin_cand.status == "NOT_FOUND"
    assert origin_cand.value is None

    # Explicit statutory origin statement must be extracted
    explicit_origin_boxes = [
        {"id": 10, "text": "Country of Origin: India", "confidence": 0.96, "bounding_box": {"x": 10, "y": 10, "w": 200, "h": 20}, "line_number": 1}
    ]
    explicit_cand = ModularFieldExtractors.extract_country_of_origin(explicit_origin_boxes, image_id=1, image_role="back")
    assert explicit_cand.status == "FOUND"
    assert "India" in explicit_cand.value


def test_not_found_not_false_fail():
    """
    Absence of reliable evidence (NOT_FOUND) must NOT evaluate to FAIL or NON_COMPLIANT.
    """
    empty_decls = [
        {"field_name": "MRP", "detected_value": None, "extraction_status": "NOT_FOUND", "status": "NOT_FOUND", "confidence": 0.0},
        {"field_name": "NET_QUANTITY", "detected_value": None, "extraction_status": "NOT_FOUND", "status": "NOT_FOUND", "confidence": 0.0},
        {"field_name": "PRODUCT_NAME", "detected_value": None, "extraction_status": "NOT_FOUND", "status": "NOT_FOUND", "confidence": 0.0},
    ]
    res = ComplianceEngine.evaluate_declarations(empty_decls)
    assert res["summary"]["failed"] == 0
    assert res["overall_status"] in ("REVIEW_REQUIRED", "NOT_VERIFIABLE")
    assert res["overall_status"] != "NON_COMPLIANT"


def test_unable_to_verify_not_false_fail():
    """
    Unreadable evidence (UNABLE_TO_VERIFY) must NOT evaluate to FAIL or NON_COMPLIANT.
    """
    unreadable_decls = [
        {"field_name": "MRP", "detected_value": None, "extraction_status": "UNABLE_TO_VERIFY", "status": "UNABLE_TO_VERIFY", "confidence": 0.0},
        {"field_name": "NET_QUANTITY", "detected_value": None, "extraction_status": "UNABLE_TO_VERIFY", "status": "UNABLE_TO_VERIFY", "confidence": 0.0},
        {"field_name": "MANUFACTURING_DATE", "detected_value": None, "extraction_status": "UNABLE_TO_VERIFY", "status": "UNABLE_TO_VERIFY", "confidence": 0.0},
    ]
    res = ComplianceEngine.evaluate_declarations(unreadable_decls)
    assert res["summary"]["failed"] == 0
    assert res["overall_status"] in ("REVIEW_REQUIRED", "UNABLE_TO_VERIFY", "NOT_VERIFIABLE")
    assert res["overall_status"] != "NON_COMPLIANT"
