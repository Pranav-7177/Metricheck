from typing import Dict, Any, Optional, Tuple
import re
from datetime import datetime
from app.services.compliance.rule_registry import RegisteredRule, RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult

def _parse_date_tuple(date_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Parses date strings into comparable (year, month, day) tuples.
    Supports YYYY-MM-DD, DD/MM/YYYY, MM/YYYY, DD-MM-YYYY, etc.
    """
    if not date_str:
        return None

    cleaned = date_str.strip()

    # YYYY-MM-DD or YYYY/MM/DD
    m_iso = re.match(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', cleaned)
    if m_iso:
        return (int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))

    # DD/MM/YYYY or DD-MM-YYYY
    m_dmy = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', cleaned)
    if m_dmy:
        return (int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))

    # MM/YYYY or MM-YYYY
    m_my = re.match(r'^(\d{1,2})[/-](\d{4})$', cleaned)
    if m_my:
        return (int(m_my.group(2)), int(m_my.group(1)), 1)

    # DD/MM/YY
    m_short = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$', cleaned)
    if m_short:
        yr = 2000 + int(m_short.group(3))
        return (yr, int(m_short.group(2)), int(m_short.group(1)))

    return None


def evaluate_mfg_or_packing_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "MANUFACTURING_OR_PACKING_DATE_PRESENT"
    field_name = "MANUFACTURING_DATE"
    ref = "Rule 6(1)(c), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    mfg = all_decls.get("MANUFACTURING_DATE") or all_decls.get("manufacturing_date") or all_decls.get("mfg_date")
    pkd = all_decls.get("PACKING_DATE") or all_decls.get("packing_date")

    # Check if either date is found
    if mfg and mfg.get("extraction_status") == "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Date of manufacture declared: {mfg.get('detected_value')}.",
            field_value=mfg.get("detected_value"),
            confidence=mfg.get("confidence", 0.95),
            evidence=mfg.get("evidence", {}),
            rule_reference=ref
        )

    if pkd and pkd.get("extraction_status") == "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Date of packaging declared: {pkd.get('detected_value')}.",
            field_value=pkd.get("detected_value"),
            confidence=pkd.get("confidence", 0.95),
            evidence=pkd.get("evidence", {}),
            rule_reference=ref
        )

    if (mfg and (mfg.get("extraction_status") == "UNABLE_TO_VERIFY" or mfg.get("status") == "UNABLE_TO_VERIFY")) or \
       (pkd and (pkd.get("extraction_status") == "UNABLE_TO_VERIFY" or pkd.get("status") == "UNABLE_TO_VERIFY")):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Relevant evidence appears to be present, but the declaration could not be reliably read or verified.",
            field_value=(mfg or pkd).get("detected_value"),
            confidence=0.0,
            evidence=(mfg or pkd).get("evidence", {}),
            rule_reference=ref,
            suggested_action="Capture a clearer close-up image of the declaration."
        )

    if (mfg and mfg.get("extraction_status") == "AMBIGUOUS") or (pkd and pkd.get("extraction_status") == "AMBIGUOUS") or \
       (mfg and mfg.get("has_conflict")) or (pkd and pkd.get("has_conflict")):
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Multiple conflicting or plausible values were detected. Manual review is required.",
            field_value=(mfg or pkd).get("detected_value"),
            confidence=0.5,
            evidence=(mfg or pkd).get("evidence", {}),
            rule_reference=ref,
            suggested_action="Review the conflicting values across the submitted images."
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_VERIFIABLE",
        severity=severity,
        message="No sufficiently reliable evidence for this declaration was detected in the submitted images.",
        field_value=None,
        confidence=0.0,
        evidence={},
        rule_reference=ref,
        suggested_action="Capture the package panel where this declaration is expected."
    )


def evaluate_expiry_or_best_before_present(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "EXPIRY_OR_BEST_BEFORE_PRESENT"
    field_name = "EXPIRY_DATE"
    ref = "Rule 6(1)(c) proviso, Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    exp = all_decls.get("EXPIRY_DATE") or all_decls.get("expiry_date")
    bb = all_decls.get("BEST_BEFORE") or all_decls.get("best_before")

    if exp and exp.get("extraction_status") == "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Expiry date declared: {exp.get('detected_value')}.",
            field_value=exp.get("detected_value"),
            confidence=exp.get("confidence", 0.95),
            evidence=exp.get("evidence", {}),
            rule_reference=ref
        )

    if bb and bb.get("extraction_status") == "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Best before declaration detected: {bb.get('detected_value')}.",
            field_value=bb.get("detected_value"),
            confidence=bb.get("confidence", 0.95),
            evidence=bb.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="NOT_VERIFIABLE",
        severity=severity,
        message="Expiry date / Best Before declaration not detected.",
        field_value=None,
        confidence=0.0,
        evidence={},
        rule_reference=ref,
        suggested_action="Verify if commodity is exempt from expiry declaration or locate expiry print."
    )


def evaluate_date_format_valid(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "DATE_FORMAT_VALID"
    field_name = "MANUFACTURING_DATE"
    ref = "Rule 6(1)(c), Legal Metrology (PC) Rules 2011"
    severity = "ERROR"

    mfg = all_decls.get("MANUFACTURING_DATE") or all_decls.get("manufacturing_date")
    pkd = all_decls.get("PACKING_DATE") or all_decls.get("packing_date")
    date_decl = mfg if (mfg and mfg.get("extraction_status") == "FOUND") else pkd

    if not date_decl or date_decl.get("extraction_status") != "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Date format cannot be evaluated as no manufacturing/packaging date was found.",
            field_value=None,
            confidence=0.0,
            evidence={},
            rule_reference=ref
        )

    date_str = date_decl.get("normalized_value") or date_decl.get("detected_value") or ""
    parsed = _parse_date_tuple(date_str)
    if parsed:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Date is declared in standard recognizable format ({date_str}).",
            field_value=date_str,
            confidence=date_decl.get("confidence", 0.95),
            evidence=date_decl.get("evidence", {}),
            rule_reference=ref
        )

    return EvaluatedRuleResult(
        rule_id=rule_id,
        field_name=field_name,
        status="WARNING",
        severity=severity,
        message=f"Declared date string '{date_str}' is non-standard or partially parsed.",
        field_value=date_str,
        confidence=0.5,
        evidence=date_decl.get("evidence", {}),
        rule_reference=ref
    )


def evaluate_date_consistency(decl: Optional[Dict[str, Any]], all_decls: Dict[str, Any]) -> EvaluatedRuleResult:
    rule_id = "DATE_CONSISTENCY_CHECK"
    field_name = "MANUFACTURING_DATE"
    ref = "Rule 6(1)(c), Legal Metrology (PC) Rules 2011"
    severity = "CRITICAL"

    mfg = all_decls.get("MANUFACTURING_DATE") or all_decls.get("manufacturing_date") or all_decls.get("PACKING_DATE") or all_decls.get("packing_date")
    exp = all_decls.get("EXPIRY_DATE") or all_decls.get("expiry_date")

    # Both dates must be reliably found
    if not mfg or mfg.get("extraction_status") != "FOUND" or not exp or exp.get("extraction_status") != "FOUND":
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="Cannot evaluate date chronology because both manufacturing and expiry dates were not simultaneously detected. Missing dates will not be fabricated.",
            field_value=None,
            confidence=0.0,
            evidence={},
            rule_reference=ref
        )

    mfg_str = mfg.get("normalized_value") or mfg.get("detected_value") or ""
    exp_str = exp.get("normalized_value") or exp.get("detected_value") or ""

    mfg_tuple = _parse_date_tuple(mfg_str)
    exp_tuple = _parse_date_tuple(exp_str)

    if not mfg_tuple or not exp_tuple:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="NOT_VERIFIABLE",
            severity=severity,
            message="One or both dates could not be parsed into calendar coordinates for comparison.",
            field_value=f"Mfg: {mfg_str} | Exp: {exp_str}",
            confidence=0.5,
            evidence={"mfg_evidence": mfg.get("evidence"), "exp_evidence": exp.get("evidence")},
            rule_reference=ref
        )

    if mfg_tuple <= exp_tuple:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="PASS",
            severity=severity,
            message=f"Date chronology valid: Manufacturing date ({mfg_str}) precedes Expiry date ({exp_str}).",
            field_value=f"{mfg_str} <= {exp_str}",
            confidence=min(mfg.get("confidence", 0.9), exp.get("confidence", 0.9)),
            evidence={"mfg_evidence": mfg.get("evidence"), "exp_evidence": exp.get("evidence")},
            rule_reference=ref
        )
    else:
        return EvaluatedRuleResult(
            rule_id=rule_id,
            field_name=field_name,
            status="FAIL",
            severity=severity,
            message=f"Chronological violation: Manufacturing date ({mfg_str}) occurs after Expiry date ({exp_str}).",
            field_value=f"{mfg_str} > {exp_str}",
            confidence=min(mfg.get("confidence", 0.9), exp.get("confidence", 0.9)),
            evidence={"mfg_evidence": mfg.get("evidence"), "exp_evidence": exp.get("evidence")},
            rule_reference=ref,
            suggested_action="Critical anomaly: Check packaging stamp coordinates for misread or misprinted dates."
        )


def register_date_rules():
    RuleRegistry.register(RegisteredRule(
        rule_id="MANUFACTURING_OR_PACKING_DATE_PRESENT",
        field_name="MANUFACTURING_DATE",
        description="Declaration of Month and Year of manufacture or packaging",
        severity="CRITICAL",
        rule_source="Rule 6(1)(c), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_mfg_or_packing_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="EXPIRY_OR_BEST_BEFORE_PRESENT",
        field_name="EXPIRY_DATE",
        description="Declaration of Best Before period or specific Expiry Date",
        severity="ERROR",
        rule_source="Rule 6(1)(c) proviso, Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_expiry_or_best_before_present
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="DATE_FORMAT_VALID",
        field_name="MANUFACTURING_DATE",
        description="Validation that date conforms to standard packaging representations",
        severity="ERROR",
        rule_source="Rule 6(1)(c), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_date_format_valid
    ))
    RuleRegistry.register(RegisteredRule(
        rule_id="DATE_CONSISTENCY_CHECK",
        field_name="MANUFACTURING_DATE",
        description="Chronological validation ensuring manufacture date precedes expiry date",
        severity="CRITICAL",
        rule_source="Rule 6(1)(c), Legal Metrology (PC) Rules 2011",
        evaluator=evaluate_date_consistency
    ))
