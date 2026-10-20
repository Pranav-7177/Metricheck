from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_mrp_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_PRESENT"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
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
        message="Maximum Retail Price (MRP) declaration is clearly present on the packaging.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref,
        suggested_action="Verified compliant under Rule 6(1)(e)."
    )


def evaluate_mrp_value_valid(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_VALUE_VALID"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    extraction_st = (decl.get("extraction_status") or decl.get("status") or "NOT_FOUND") if decl else "NOT_FOUND"
    if (
        not decl
        or not decl.get("detected_value")
        or extraction_st in ("NOT_FOUND", "AMBIGUOUS", "LOW_CONFIDENCE", "UNABLE_TO_VERIFY")
        or decl.get("has_conflict")
    ):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Unable to verify numeric price value because declaration is absent, low-confidence, conflicting, or unreadable.",
            field_value=decl.get("detected_value") if decl else None,
            confidence=decl.get("confidence", 0.0) if decl else 0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    norm_val = decl.get("normalized_value")
    try:
        amt = float(norm_val) if norm_val else 0.0
        if amt > 0:
            return EvaluatedRuleResult(
                rule_id=rule_id,
                field_name=field_name,
                status="PASS",
                severity=severity,
                message=f"Valid statutory price value declared: ₹{amt:.2f}.",
                field_value=f"₹{amt:.2f}",
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
                message="Retail price amount is zero or negative, which is not legally permitted.",
                field_value=norm_val,
                confidence=decl.get("confidence", 0.90),
                evidence=decl.get("evidence", {}),
                rule_reference=ref,
                suggested_action="Verify physical packaging price declaration."
            )
    except (ValueError, TypeError):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Price could not be parsed as a valid numeric amount.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.5),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )


def evaluate_mrp_currency_valid(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_CURRENCY_VALID"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    extraction_st = (decl.get("extraction_status") or decl.get("status") or "NOT_FOUND") if decl else "NOT_FOUND"
    if (
        not decl
        or not decl.get("detected_value")
        or extraction_st in ("NOT_FOUND", "AMBIGUOUS", "LOW_CONFIDENCE", "UNABLE_TO_VERIFY")
        or decl.get("has_conflict")
    ):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Currency cannot be verified because MRP declaration is not available, unreadable, or conflicting.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    currency = decl.get("currency") or ("INR" if "₹" in (decl.get("detected_value") or "") or "rs" in (decl.get("raw_value") or "").lower() else None)
    if currency in ("INR", "₹"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="MRP is properly denominated in Indian Rupees (INR / ₹).",
            field_value=currency,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )
    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message="Currency indicator could not be definitively verified as Indian Rupee (INR).",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_mrp_conflict_check(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_CONFLICT_CHECK"
    field_name = "MRP"
    ref = "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    if not decl or decl.get("extraction_status") == "NOT_FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_APPLICABLE",
            severity="INFO",
            message="Conflict check not applicable as no MRP was detected.",
            field_value=None,
            confidence=1.0,
            evidence={},
            rule_reference=ref
        )

    if decl.get("has_conflict"):
        ev = dict(decl.get("evidence") or {})
        ev["has_conflict"] = True
        if decl.get("alternate_candidates"):
            ev["alternate_candidates"] = decl.get("alternate_candidates")
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Conflicting retail prices detected across packaging panels. Both candidates preserved in evidence.",
            field_value=decl.get("detected_value"),
            confidence=0.0,
            evidence=ev,
            rule_reference=ref,
            suggested_action="Review alternate candidates in evidence to check if dual pricing or over-stamping exists."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message="No conflicting retail price declarations detected across images.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_mrp_font_height(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MRP_FONT_HEIGHT"
    field_name = "MRP"
    ref = "Rule 9(1), Schedule II, Legal Metrology (PC) Rules 2011"
    severity = "WARNING"

    if not decl or decl.get("extraction_status") == "NOT_FOUND" or not decl.get("detected_value"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Physical font size could not be evaluated as MRP was not detected.",
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
                message=f"Calibrated MRP font height measured at {font_mm:.1f} mm (no statutory minimum threshold specified).",
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
            message=f"Calibrated MRP font height ({font_mm:.1f} mm) satisfies statutory minimum requirement ({req_mm:.1f} mm).",
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
            message=f"Calibrated MRP font height ({font_mm:.1f} mm) is below statutory minimum requirement ({req_mm:.1f} mm).",
            field_value=f"{font_mm:.1f} mm",
            confidence=vis_ev.get("calibration_confidence", 0.90),
            evidence=vis_ev,
            rule_reference=ref,
            suggested_action="Ensure numeral height on principal display panel meets Rule 9 Schedule II minimums."
        )



def register_mrp_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_PRESENT",
        field_name="MRP",
        description="Statutory declaration of Maximum Retail Price (MRP)",
        severity="CRITICAL",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_VALUE_VALID",
        field_name="MRP",
        description="Validation that declared price is a positive numerical amount",
        severity="ERROR",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_value_valid
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_CURRENCY_VALID",
        field_name="MRP",
        description="Validation of Indian Rupee (INR / ₹) currency symbol",
        severity="ERROR",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_currency_valid
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_CONFLICT_CHECK",
        field_name="MRP",
        description="Cross-image consistency check for retail price declarations",
        severity="CRITICAL",
        rule_source="Rule 6(1)(e), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_conflict_check
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MRP_FONT_HEIGHT",
        field_name="MRP",
        description="Visual verification of calibrated physical numeral font height",
        severity="WARNING",
        rule_source="Rule 9(1), Schedule II, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mrp_font_height
    ))
