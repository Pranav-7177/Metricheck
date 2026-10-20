from typing import Dict, Any, Optional
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def evaluate_product_name_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "PRODUCT_NAME_PRESENT"
    field_name = "PRODUCT_NAME"
    ref = "Rule 6(1)(b), Legal Metrology (PC) Rules 2011"
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
        message=f"Product / commodity name clearly declared ('{decl.get('detected_value')}').",
        field_value=decl.get("detected_value"),
        confidence=decl.get("confidence", 0.95),
        evidence=decl.get("evidence", {}),
        rule_reference=ref
    )


def register_product_name_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="PRODUCT_NAME_PRESENT",
        field_name="PRODUCT_NAME",
        description="Declaration of the common or generic names of the commodity",
        severity="CRITICAL",
        rule_source="Rule 6(1)(b), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_product_name_present
    ))
