from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_manufacturer_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MANUFACTURER_PRESENT"
    field_name = "MANUFACTURER"
    ref = "Rule 6(1)(a), Legal Metrology (PC) Rules 2011"
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
        message="Manufacturer name is clearly declared.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_manufacturer_address_evidence(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MANUFACTURER_ADDRESS_EVIDENCE"
    field_name = "MANUFACTURER"
    ref = "Rule 6(1)(a), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Manufacturer address cannot be verified because declaration was not found.",
            field_value=None,
            confidence=0.0,
            evidence=decl.get("evidence", {}) if decl else {},
            rule_reference=ref
        )

    val = decl.get("detected_value") or ""
    if len(val.strip()) >= 10:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="Manufacturer physical address evidence is substantive and preserved without truncation.",
            field_value=val,
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message="Manufacturer address appears abbreviated or brief. Full physical postal address advised.",
        field_value=val,
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_manufacturer_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="MANUFACTURER_PRESENT",
        field_name="MANUFACTURER",
        description="Statutory declaration of manufacturer name and legal identity",
        severity="CRITICAL",
        rule_source="Rule 6(1)(a), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_manufacturer_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="MANUFACTURER_ADDRESS_EVIDENCE",
        field_name="MANUFACTURER",
        description="Substantive physical premises address evidence for manufacturer",
        severity="ERROR",
        rule_source="Rule 6(1)(a), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_manufacturer_address_evidence
    ))
