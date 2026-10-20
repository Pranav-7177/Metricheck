from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.compliance.rule_registry import RuleRegistry
from app.services.compliance.rule_result import EvaluatedRuleResult
from app.services.compliance.rules import init_default_rules

class ComplianceEngine:
    """
    Evaluates statutory compliance rules over structured declarations.
    Implements strict separation between Rule Severity and Compliance Status.
    Never invents missing information or prematurely claims legal non-compliance.
    """

    @classmethod
    def evaluate_declarations(cls, declarations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes all registered compliance rules against the provided declarations.
        """
        init_default_rules()

        # Build lookup map by field name (supporting both uppercase and lowercase)
        decl_map: Dict[str, Dict[str, Any]] = {}
        for d in declarations:
            # Handle both dictionary representations and ORM objects
            d_dict = d if isinstance(d, dict) else {
                "field_name": getattr(d, "field_name", ""),
                "display_name": getattr(d, "display_name", ""),
                "detected_value": getattr(d, "detected_value", None),
                "normalized_value": getattr(d, "normalized_value", None),
                "raw_value": getattr(d, "raw_value", None),
                "unit": getattr(d, "unit", None),
                "currency": getattr(d, "currency", None),
                "confidence": getattr(d, "confidence", 0.0),
                "field_confidence": getattr(d, "field_confidence", 0.0),
                "raw_ocr_confidence": getattr(d, "raw_ocr_confidence", 0.0),
                "extraction_status": getattr(d, "extraction_status", "NOT_FOUND"),
                "status": getattr(d, "status", None),
                "evidence": getattr(d, "evidence", {}) or {},
                "has_conflict": getattr(d, "has_conflict", False),
                "alternate_candidates": getattr(d, "alternate_candidates", []) or [],
                "source_image_id": getattr(d, "source_image_id", None),
                "source_ocr_ids": getattr(d, "source_ocr_ids", []) or [],
                "bounding_box": getattr(d, "bounding_box", None),
                "estimated_font_height_mm": getattr(d, "estimated_font_height_mm", None),
                "required_font_height_mm": getattr(d, "required_font_height_mm", None),
                "measurement_confidence": getattr(d, "measurement_confidence", "UNCALIBRATED"),
                "visual_evidence": (
                    getattr(d, "visual_evidence", None)
                    or ((getattr(d, "evidence", {}) or {}).get("visual_evidence") if hasattr(d, "evidence") else None)
                ),
            }
            if isinstance(d, dict):
                for k in ("estimated_font_height_mm", "required_font_height_mm", "measurement_confidence"):
                    if k in d:
                        d_dict[k] = d[k]
                d_dict["visual_evidence"] = d.get("visual_evidence") or (d.get("evidence", {}) or {}).get("visual_evidence")

            f_name = (d.get("field_name") if isinstance(d, dict) else getattr(d, "field_name", "")).upper()
            effective_status = (
                (d.get("extraction_status") if isinstance(d, dict) else getattr(d, "extraction_status", None))
                or (d.get("status") if isinstance(d, dict) else getattr(d, "status", None))
                or "NOT_FOUND"
            )
            d_dict["extraction_status"] = effective_status
            d_dict["status"] = effective_status
            if f_name:
                decl_map[f_name] = d_dict
                decl_map[f_name.lower()] = d_dict

        all_rules = RuleRegistry.get_all_rules()
        evaluated_results: List[EvaluatedRuleResult] = []

        passed_count = 0
        failed_count = 0
        warning_count = 0
        not_verifiable_count = 0
        not_applicable_count = 0

        for rule in all_rules:
            target_decl = decl_map.get(rule.field_name.upper())
            res = rule.evaluator(target_decl, decl_map)

            # Ensure evaluated rule preserves its configured severity and reference
            if not res.severity:
                res.severity = rule.severity
            if not res.rule_reference:
                res.rule_reference = rule.rule_source

            evaluated_results.append(res)

            if res.status == "PASS":
                passed_count += 1
            elif res.status == "FAIL":
                failed_count += 1
            elif res.status == "WARNING":
                warning_count += 1
            elif res.status == "NOT_VERIFIABLE":
                not_verifiable_count += 1
            elif res.status == "NOT_APPLICABLE":
                not_applicable_count += 1

        total_rules = len(evaluated_results)

        # Deterministic overall compliance status aggregation
        if failed_count > 0:
            overall_status = "NON_COMPLIANT"
        elif not_verifiable_count > 0 or warning_count > 0:
            overall_status = "REVIEW_REQUIRED"
        elif passed_count > 0:
            overall_status = "COMPLIANT"
        else:
            overall_status = "NOT_VERIFIABLE"

        applicable_count = total_rules - not_applicable_count
        if applicable_count > 0:
            score = round((passed_count / applicable_count) * 100.0, 1)
        else:
            score = 0.0

        return {
            "overall_status": overall_status,
            "compliance_score": score,
            "summary": {
                "total_rules": total_rules,
                "passed": passed_count,
                "failed": failed_count,
                "warnings": warning_count,
                "not_verifiable": not_verifiable_count,
                "not_applicable": not_applicable_count,
            },
            "results": [r.to_dict() for r in evaluated_results],
            "evaluated_at": datetime.utcnow().isoformat()
        }
