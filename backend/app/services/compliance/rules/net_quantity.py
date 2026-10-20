from typing import Dict, Any, Optional
import re
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_net_quantity_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_PRESENT"
    field_name = "NET_QUANTITY"
    ref = "Rule 6(1)(d), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    if decl and (decl.get("extraction_status") == "UNABLE_TO_VERIFY" or decl.get("status") == "UNABLE_TO_VERIFY"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Relevant evidence appears to be present, but the declaration could not be reliably read or verified.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Capture a clearer close-up image of the declaration."
        )

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="No sufficiently reliable evidence for this declaration was detected in the submitted images.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref,
            suggested_action="Capture the package panel where this declaration is expected."
        )

    if decl.get("has_conflict") or decl.get("extraction_status") == "AMBIGUOUS":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Multiple conflicting or plausible values were detected. Manual review is required.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Review the conflicting values across the submitted images."
        )

    if decl.get("extraction_status") == "LOW_CONFIDENCE":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="WARNING",
            severity=severity,
            message="A candidate was detected, but confidence is below the configured verification threshold.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.0),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Submit a higher-resolution image with better lighting and reduced glare."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="Net quantity declaration is clearly present on packaging.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_numeric(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_NUMERIC"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Numeric net quantity cannot be verified due to missing or ambiguous declaration.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    val = decl.get("normalized_value") or decl.get("detected_value") or ""
    match = re.search(r'(\d+(?:\.\d+)?)', val)
    if match:
        try:
            num = float(match.group(1))
            if num > 0:
                return EvaluatedRuleResult(
                    rule_id=rule_id,
                    field_name=field_name,
                    status="PASS",
                    severity=severity,
                    message=f"Valid statutory positive quantity magnitude: {num}.",
                    field_value=str(num),
                    confidence=decl.get("confidence", 0.95),
                    evidence=decl.get("evidence", {}),
                    rule_reference=ref
                )
            else:
                return EvaluatedRuleResult(
                    rule_id=rule_id,
                    field_name=field_name,
                    status="FAIL",
                    severity=severity,
                    message="Net quantity amount is zero or negative.",
                    field_value=str(num),
                    confidence=decl.get("confidence", 0.90),
                    evidence=decl.get("evidence", {}),
                    rule_reference=ref
                )
        except ValueError:
            pass

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_VERIFIABLE",
        severity=severity,
        message="Could not parse numerical value for net quantity.",
        field_value=val,
        confidence=0.5,
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_unit_recognized(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_UNIT_RECOGNIZED"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Unit cannot be verified because quantity declaration was not found.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    recognized_units = {"g", "kg", "mg", "ml", "l", "cm", "m", "mm", "units"}
    unit = (decl.get("unit") or "").strip().lower()
    if not unit:
        # Fallback search from detected_value
        val = decl.get("detected_value") or ""
        match = re.search(r'\b(kg|g|mg|ml|l|cm|m|mm|units?)\b', val, re.IGNORECASE)
        unit = match.group(1).lower() if match else ""

    if unit in recognized_units:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Statutory standardized metric unit declared: '{unit}'.",
            field_value=unit,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message=f"Declared quantity unit '{unit}' could not be definitively validated against Rule 11 metric standards.",
        field_value=unit or "UNKNOWN",
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_qualifier(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_QUALIFIER_CHECK"
    field_name = "NET_QUANTITY"
    ref = "Rule 11, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") == "NOT_FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Qualifier check not applicable as net quantity is not present.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    raw_text = (decl.get("raw_value") or decl.get("detected_value") or "").lower()
    if "when packed" in raw_text:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="FAIL",
            severity=severity,
            message="Prohibited qualification: Rule 11 strictly prohibits qualifying net quantity with phrases such as 'when packed'.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Remove non-statutory 'when packed' qualification from the package label."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="Net quantity is declared without prohibited qualifiers.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_net_quantity_font_height(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "NET_QUANTITY_FONT_HEIGHT"
    field_name = "NET_QUANTITY"
    ref = "Rule 9(1), Schedule II, Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Physical font size could not be evaluated as Net Quantity was not detected.",
            field_value=None,
            confidence=0.0,
            evidence={},
            rule_reference=ref
        )

    vis_ev = decl.get("visual_evidence") or (decl.get("evidence", {}) or {}).get("visual_evidence") or {}
    vis_status = vis_ev.get("visual_status")

    font_mm = vis_ev.get("font_height_mm")
    req_mm = decl.get("required_font_height_mm")

    if not req_mm or req_mm <= 0:
        if font_mm is not None:
            return EvaluatedRuleResult(
                rule_id=rule_id,
                field_name=field_name,
                status="PASS",
                severity="INFO",
                message=f"Calibrated Net Quantity font height measured at {font_mm:.1f} mm (no statutory minimum threshold specified).",
                field_value=f"{font_mm:.1f} mm",
                confidence=vis_ev.get("calibration_confidence", 0.90),
                evidence=vis_ev,
                rule_reference=ref
            )
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="No verified legal font-size threshold is configured for this commodity category.",
            field_value=None,
            confidence=1.0,
            evidence=vis_ev,
            rule_reference=ref
        )

    if vis_status == "UNABLE_TO_VERIFY" or decl.get("extraction_status") == "UNABLE_TO_VERIFY":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Relevant visual evidence is present, but the declaration could not be reliably verified because of image quality, visibility, or distortion.",
            field_value=decl.get("detected_value"),
            confidence=0.0,
            evidence=vis_ev,
            rule_reference=ref,
            suggested_action="Capture a clearer close-up image of the declaration."
        )

    if vis_status in ("NOT_MEASURABLE", "READABLE_ONLY", None) or font_mm is None:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="The declaration is readable, but its physical size could not be measured reliably because no valid calibration reference was available.",
            field_value=decl.get("detected_value"),
            confidence=0.0,
            evidence=vis_ev,
            rule_reference=ref,
            suggested_action="Provide a known package dimension or calibrated reference."
        )

    if vis_status == "AMBIGUOUS":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Conflicting physical font measurements detected across photographs. Manual review is required.",
            field_value=decl.get("detected_value"),
            confidence=0.5,
            evidence=vis_ev,
            rule_reference=ref,
            suggested_action="Review the conflicting visual measurements across the submitted images."
        )

    if font_mm >= req_mm:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Calibrated Net Quantity font height ({font_mm:.1f} mm) satisfies statutory minimum requirement ({req_mm:.1f} mm).",
            field_value=f"{font_mm:.1f} mm",
            confidence=vis_ev.get("calibration_confidence", 0.90),
            evidence=vis_ev,
            rule_reference=ref
        )
    else:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="FAIL",
            severity="ERROR",
            message=f"Calibrated Net Quantity font height ({font_mm:.1f} mm) is below statutory minimum requirement ({req_mm:.1f} mm).",
            field_value=f"{font_mm:.1f} mm",
            confidence=vis_ev.get("calibration_confidence", 0.90),
            evidence=vis_ev,
            rule_reference=ref,
            suggested_action="Ensure numeral height on principal display panel meets Rule 9 Schedule II minimums."
        )



def register_net_quantity_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_PRESENT",
        field_name="NET_QUANTITY",
        description="Declaration of net quantity in terms of weight, measure, or number",
        severity="CRITICAL",
        rule_source="Rule 6(1)(d), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_NUMERIC",
        field_name="NET_QUANTITY",
        description="Validation of positive numeric quantity magnitude",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_numeric
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_UNIT_RECOGNIZED",
        field_name="NET_QUANTITY",
        description="Validation of recognized metric unit (g, kg, ml, L, etc.)",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_unit_recognized
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_QUALIFIER_CHECK",
        field_name="NET_QUANTITY",
        description="Prohibition of non-statutory qualifiers like 'when packed'",
        severity="ERROR",
        rule_source="Rule 11, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_qualifier
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="NET_QUANTITY_FONT_HEIGHT",
        field_name="NET_QUANTITY",
        description="Visual verification of calibrated physical numeral font height",
        severity="WARNING",
        rule_source="Rule 9(1), Schedule II, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_net_quantity_font_height
    ))

