from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_country_of_origin_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "COUNTRY_OF_ORIGIN_PRESENT"
    field_name = "COUNTRY_OF_ORIGIN"
    ref = "Rule 6(10), Legal Metrology (PC) Amendment Rules"
    severity = "CRITICAL"

    if decl and (decl.get("extraction_status") == "UNABLE_TO_VERIFY" or decl.get("status") == "UNABLE_TO_VERIFY"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Relevant evidence appears to be present, but the declaration could not be reliably read or verified.",
            field_value=decl.get("detected_value"),
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
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
            confidence=0.0,
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
            confidence=0.0,
            evidence=decl.get("evidence", {}),
            rule_reference=ref,
            suggested_action="Submit a higher-resolution image with better lighting and reduced glare."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message=f"Country of Origin declared: {decl.get('detected_value')}.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_country_of_origin_explicit(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "COUNTRY_OF_ORIGIN_EXPLICIT"
    field_name = "COUNTRY_OF_ORIGIN"
    ref = "Rule 6(10), Legal Metrology (PC) Amendment Rules"
    severity = "CRITICAL"

    # Explicit origin declaration check
    if not decl or decl.get("extraction_status") != "FOUND" or not decl.get("detected_value"):
        # Even if manufacturer address has 'India', do NOT infer origin!
        mfg_decl = all_decls.get("MANUFACTURER") or all_decls.get("manufacturer")
        mfg_val = (mfg_decl.get("detected_value") or "").lower() if mfg_decl else ""
        has_addr_india = "india" in mfg_val

        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Statutory rule requires explicit country declaration ('Country of Origin' / 'Made in'). Country cannot be inferred from manufacturer address.",
            field_value=f"Manufacturer Address Context: {mfg_val[:30]}..." if has_addr_india else None,
            confidence=0.0,
            evidence={},
            rule_reference=ref,
            suggested_action="Ensure packaging includes an explicit 'Country of Origin: [Country]' declaration."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="PASS",
        severity=severity,
        message=f"Explicit Country of Origin declaration verified ('{decl.get('detected_value')}').",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_country_of_origin_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="COUNTRY_OF_ORIGIN_PRESENT",
        field_name="COUNTRY_OF_ORIGIN",
        description="Mandatory declaration of country of origin or manufacture",
        severity="CRITICAL",
        rule_source="Rule 6(10), Legal Metrology (PC) Amendment Rules",
        evaluator=evaluate_country_of_origin_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="COUNTRY_OF_ORIGIN_EXPLICIT",
        field_name="COUNTRY_OF_ORIGIN",
        description="Requirement that origin be explicitly stated and not inferred from address",
        severity="CRITICAL",
        rule_source="Rule 6(10), Legal Metrology (PC) Amendment Rules",
        evaluator=evaluate_country_of_origin_explicit
    ))
