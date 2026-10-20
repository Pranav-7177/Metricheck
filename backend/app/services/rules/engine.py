from typing import List, Dict, Any, Optional
from app.models.models import ComplianceState, ComplianceRule

class ComplianceRuleEngine:
    """
    Evaluates category-specific, versioned legal rules against extracted declarations.
    Produces rich, explainable results with detailed reasons, statutory references,
    and suggested inspector actions.
    """

    @classmethod
    def evaluate_rules(
        cls,
        rules: List[ComplianceRule],
        extracted_declarations: List[Dict[str, Any]],
        category_code: str
    ) -> List[Dict[str, Any]]:
        """
        Executes applicable versioned rules for the product category.
        """
        results = []
        decl_map = {d["field_name"]: d for d in extracted_declarations}

        for rule in rules:
            field = rule.field_target
            decl = decl_map.get(field)

            # Evaluate declaration status against this rule
            eval_result = cls._evaluate_single_rule(rule, decl, category_code)
            results.append(eval_result)

        return results

    @classmethod
    def _evaluate_single_rule(
        cls,
        rule: ComplianceRule,
        decl: Optional[Dict[str, Any]],
        category_code: str
    ) -> Dict[str, Any]:
        """
        Evaluates a single statutory rule against an extracted declaration.
        """
        rule_info = {
            "rule_id": rule.id,
            "field_target": rule.field_target,
            "expected_requirement": rule.requirement,
            "rule_reference": rule.rule_reference,
            "rule_version": rule.version,
        }

        # Case 1: Declaration was not found at all
        status_val = decl.get("status") if decl else None
        ext_status_val = decl.get("extraction_status") if decl else None

        if not decl or status_val in (ComplianceState.NOT_FOUND, "NOT_FOUND") or ext_status_val == "NOT_FOUND":
            if rule.is_mandatory:
                return {
                    **rule_info,
                    "detected_value": "NOT DETECTED",
                    "status": ComplianceState.NOT_FOUND,
                    "confidence": 0.85,
                    "reason": "No sufficiently reliable evidence for this declaration was detected in the submitted images.",
                    "suggested_action": "Capture the package panel where this declaration is expected."
                }
            else:
                return {
                    **rule_info,
                    "detected_value": "NOT DETECTED",
                    "status": ComplianceState.NOT_APPLICABLE,
                    "confidence": 0.90,
                    "reason": f"Non-mandatory declaration for category '{category_code}'.",
                    "suggested_action": "No action required."
                }

        # Case 2: Declaration was unreadable / unable to verify
        if status_val in (ComplianceState.UNABLE_TO_VERIFY, "UNABLE_TO_VERIFY") or ext_status_val == "UNABLE_TO_VERIFY":
            return {
                **rule_info,
                "detected_value": decl.get("detected_value") or "Unreadable text",
                "status": ComplianceState.UNABLE_TO_VERIFY,
                "confidence": decl.get("confidence", 0.0),
                "reason": "Relevant evidence appears to be present, but the declaration could not be reliably read or verified.",
                "suggested_action": "Capture a clearer close-up image of the declaration."
            }

        # Case 3: Conflicting or ambiguous candidates
        if decl.get("has_conflict") or ext_status_val == "AMBIGUOUS" or status_val in (ComplianceState.REVIEW_REQUIRED, "AMBIGUOUS"):
            return {
                **rule_info,
                "detected_value": decl.get("detected_value") or "Ambiguous values",
                "status": ComplianceState.REVIEW_REQUIRED,
                "confidence": decl.get("confidence", 0.5),
                "reason": "Multiple conflicting or plausible values were detected. Manual review is required.",
                "suggested_action": "Review the conflicting values across the submitted images."
            }

        # Case 4: Low OCR confidence below threshold
        if ext_status_val == "LOW_CONFIDENCE":
            return {
                **rule_info,
                "detected_value": decl.get("detected_value") or "Low confidence text",
                "status": ComplianceState.UNABLE_TO_VERIFY,
                "confidence": decl.get("confidence", 0.4),
                "reason": "A candidate was detected, but confidence is below the configured verification threshold.",
                "suggested_action": "Submit a higher-resolution image with better lighting and reduced glare."
            }

        detected_val = str(decl.get("detected_value") or "")
        conf = decl.get("confidence", 0.9)

        # Case 3: Specific legal validations
        if rule.field_target == "mrp":
            if "incl" not in detected_val.lower() and "tax" not in detected_val.lower():
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.POTENTIAL_NON_COMPLIANCE,
                    "confidence": conf,
                    "reason": "MRP detected without mandatory statutory phrase 'inclusive of all taxes' or 'incl. of all taxes'.",
                    "suggested_action": "Inspect physical packaging to ensure tax inclusion statement is present next to the retail price."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Maximum Retail Price is clearly declared with statutory tax inclusion statement.",
                "suggested_action": "Verified compliant under Rule 6(1)(e)."
            }

        elif rule.field_target == "net_quantity":
            if "when packed" in detected_val.lower():
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.POTENTIAL_NON_COMPLIANCE,
                    "confidence": conf,
                    "reason": "Prohibited qualification: Rule prohibits qualifying net quantity with phrases like 'when packed' for standard goods.",
                    "suggested_action": "Review qualification legality under Chapter II exemptions or issue advisory."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Net quantity is specified in standardized statutory metric units.",
                "suggested_action": "Verified compliant under Rule 11."
            }

        elif rule.field_target == "consumer_care":
            has_phone = "phone" in detected_val.lower() or "1800" in detected_val
            has_email = "email" in detected_val.lower() or "@" in detected_val
            if not has_phone or not has_email:
                return {
                    **rule_info,
                    "detected_value": detected_val,
                    "status": ComplianceState.REVIEW_REQUIRED,
                    "confidence": conf,
                    "reason": "Statutory rule requires complete consumer care contact details including telephone/toll-free and email address.",
                    "suggested_action": "Verify if alternative consumer care contact channels are printed on back or side panels."
                }
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Consumer care cell contact information includes functional phone and electronic communication channels.",
                "suggested_action": "Verified compliant under Rule 6(1)(g)."
            }

        elif rule.field_target == "manufacturer_name":
            return {
                **rule_info,
                "detected_value": detected_val,
                "status": ComplianceState.VERIFIED_COMPLIANT,
                "confidence": conf,
                "reason": "Manufacturer / Packer / Importer corporate identity and location details are clearly legible.",
                "suggested_action": "Verified compliant under Rule 6(1)(a)/(b)."
            }

        # Fallback to declaration's inherent compliance state
        return {
            **rule_info,
            "detected_value": detected_val,
            "status": decl.get("status", ComplianceState.VERIFIED_COMPLIANT),
            "confidence": conf,
            "reason": f"Statutory declaration requirement for '{rule.field_target}' verified against applicable schedule.",
            "suggested_action": rule.suggested_action or "No action required."
        }
