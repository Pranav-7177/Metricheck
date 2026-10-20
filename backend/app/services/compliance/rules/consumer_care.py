from typing import Dict, Any, Optional
import re
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_consumer_care_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "CONSUMER_CARE_PRESENT"
    field_name = "CONSUMER_CARE"
    ref = "Rule 6(1)(g), Legal Metrology (PC) Rules 2011"
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
        message="Consumer grievance contact details are clearly declared on the package.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_consumer_care_contact_evidence(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "CONSUMER_CARE_CONTACT_EVIDENCE"
    field_name = "CONSUMER_CARE"
    ref = "Rule 6(1)(g), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    if not decl or decl.get("extraction_status") in ("NOT_FOUND", "AMBIGUOUS"):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Cannot evaluate contact channels because consumer care declaration was not detected.",
            field_value=None,
            confidence=0.0,
            evidence={},
            rule_reference=ref
        )

    text = (decl.get("detected_value") or "").lower()
    has_phone = bool(re.search(r'(?:1800|1860|\b\d{7,10}\b|phone|tel|helpline)', text))
    has_email = bool(re.search(r'(@|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|email)', text))

    if has_phone or has_email:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message="Consumer care declaration contains verifiable telephonic or electronic contact channel.",
            field_value=decl.get("detected_value"),
            confidence=decl.get("confidence", 0.95),
            evidence=decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message="Consumer care declaration does not explicitly identify a telephone number or email address.",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.6),
        evidence=decl.get("evidence", {}),
        rule_reference=ref,
        suggested_action="Check packaging to confirm telephone/email grievance contact presence."
    )


def register_consumer_care_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="CONSUMER_CARE_PRESENT",
        field_name="CONSUMER_CARE",
        description="Mandatory declaration of consumer care / grievance cell details",
        severity="CRITICAL",
        rule_source="Rule 6(1)(g), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_consumer_care_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="CONSUMER_CARE_CONTACT_EVIDENCE",
        field_name="CONSUMER_CARE",
        description="Verifiable telephone, toll-free, or email grievance channels",
        severity="ERROR",
        rule_source="Rule 6(1)(g), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_consumer_care_contact_evidence
    ))
