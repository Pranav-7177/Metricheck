from typing import List, Dict, Any, Optional
from app.models.models import ComplianceState

class ReportGeneratorService:
    """
    Synthesizes rule evaluations, OCR confidences, visual quality assessments,
    and physical measurement checks into an explainable compliance assessment.
    """

    @classmethod
    def generate_overall_assessment(
        cls,
        rule_results: List[Dict[str, Any]],
        image_qualities: List[Dict[str, Any]],
        product_name: str,
        category_name: str,
        declarations: Optional[List[Any]] = None,
        images: Optional[List[Any]] = None,
        ocr_results: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Determines overall compliance state, score, summary verdict, and actionable advice.
        Synthesizes physical font measurements and visual evidence without fabricating claims.
        """
        if not rule_results:
            return {
                "overall_status": ComplianceState.REVIEW_REQUIRED,
                "compliance_score": 0.0,
                "summary_verdict": "No statutory rules evaluated for this scan.",
                "warnings": ["Evaluation pipeline produced 0 rule checks."],
                "recommended_actions": ["Upload packaging images and re-run compliance scan."]
            }

        counts = {
            ComplianceState.VERIFIED_COMPLIANT: 0,
            ComplianceState.POTENTIAL_NON_COMPLIANCE: 0,
            ComplianceState.UNABLE_TO_VERIFY: 0,
            ComplianceState.NOT_FOUND: 0,
            ComplianceState.NOT_APPLICABLE: 0,
            ComplianceState.REVIEW_REQUIRED: 0,
        }

        for r in rule_results:
            st = r["status"]
            counts[st] = counts.get(st, 0) + 1

        total_rules = len(rule_results)
        verified = counts[ComplianceState.VERIFIED_COMPLIANT]
        potential_issues = counts[ComplianceState.POTENTIAL_NON_COMPLIANCE] + counts[ComplianceState.NOT_FOUND]
        unable = counts[ComplianceState.UNABLE_TO_VERIFY]

        # Calculate weighted compliance score (0 - 100%)
        weighted_points = (
            verified * 1.0 +
            counts[ComplianceState.NOT_APPLICABLE] * 1.0 +
            unable * 0.4 +
            counts[ComplianceState.REVIEW_REQUIRED] * 0.5
        )
        score = min(100.0, max(0.0, (weighted_points / total_rules) * 100.0))

        # Overall Status Determination
        warnings = []
        recommended_actions = []

        if potential_issues > 0:
            overall_status = ComplianceState.POTENTIAL_NON_COMPLIANCE
            summary_verdict = f"{potential_issues} potential compliance discrepancies identified under Legal Metrology Rules 2011. Inspector review advised."
            warnings.append(f"Identified {potential_issues} field(s) with non-standard formatting or missing mandatory declarations.")
            recommended_actions.append("Perform physical verification on listed discrepancies before issuing official notice.")

        elif unable > 0:
            overall_status = ComplianceState.UNABLE_TO_VERIFY
            summary_verdict = f"{unable} declaration(s) could not be reliably verified due to image blur, glare, or low OCR confidence. Never classify as missing."
            warnings.append("Certain declaration panels had insufficient visual clarity or confidence below safety threshold.")
            recommended_actions.append("Upload higher-resolution or glare-free close-up photographs for the uncertain panels.")

        elif counts[ComplianceState.REVIEW_REQUIRED] > 0:
            overall_status = ComplianceState.REVIEW_REQUIRED
            summary_verdict = "Statutory declarations detected, but manual inspector confirmation is required for specific category schedules."
            recommended_actions.append("Review highlighted declaration nuances against category exemption list.")

        else:
            overall_status = ComplianceState.VERIFIED_COMPLIANT
            summary_verdict = "All evaluated mandatory packaged commodity declarations are verified compliant under Legal Metrology Rules 2011."
            recommended_actions.append("Scan record logged into inspection audit trail. No further action needed.")

        # Check for image quality alerts
        for img_q in image_qualities:
            if img_q.get("quality_status") in ["POOR", "CRITICAL_ISSUES"]:
                warnings.append(f"Image quality alert: {img_q.get('quality_notes')}")

        # Visual Compliance Synthesis & Operational Recommendations
        visual_summary = {
            "total_declarations": 0,
            "measurable_count": 0,
            "readable_only_count": 0,
            "not_measurable_count": 0,
            "unable_to_verify_count": 0,
            "calibrated_font_measurements": []
        }

        if declarations:
            for decl in declarations:
                visual_summary["total_declarations"] += 1
                vis_ev = (
                    decl.get("visual_evidence") if isinstance(decl, dict) else getattr(decl, "visual_evidence", None)
                ) or (
                    (decl.get("evidence", {}) or {}).get("visual_evidence") if isinstance(decl, dict) else (getattr(decl, "evidence", {}) or {}).get("visual_evidence")
                )
                if not vis_ev or not isinstance(vis_ev, dict):
                    continue

                v_status = vis_ev.get("visual_status")
                f_name = (decl.get("display_name") if isinstance(decl, dict) else getattr(decl, "display_name", None)) or (
                    decl.get("field_name") if isinstance(decl, dict) else getattr(decl, "field_name", "Declaration")
                )

                if v_status == "MEASURABLE":
                    visual_summary["measurable_count"] += 1
                    if vis_ev.get("font_height_mm") is not None:
                        visual_summary["calibrated_font_measurements"].append({
                            "field": f_name,
                            "font_height_mm": vis_ev.get("font_height_mm"),
                            "text_height_px": vis_ev.get("text_height_px"),
                            "calibration_method": vis_ev.get("calibration_method")
                        })
                elif v_status == "READABLE_ONLY":
                    visual_summary["readable_only_count"] += 1
                elif v_status == "UNABLE_TO_VERIFY":
                    visual_summary["unable_to_verify_count"] += 1
                else:
                    visual_summary["not_measurable_count"] += 1

                # Visual operational recommendations (Section 28)
                if vis_ev.get("recommendation") and vis_ev.get("recommendation") not in recommended_actions:
                    recommended_actions.append(f"{f_name}: {vis_ev['recommendation']}")

                if vis_ev.get("glare_overlap_percentage", 0) >= 25.0:
                    warnings.append(f"High glare on {f_name} ({vis_ev['glare_overlap_percentage']:.1f}% overlap).")

                if vis_ev.get("glare_overlap_percentage", 0) >= 25.0:
                    warnings.append(f"High glare on {f_name} ({vis_ev['glare_overlap_percentage']:.1f}% overlap).")

                if vis_ev.get("visibility") == "PARTIALLY_VISIBLE":
                    warnings.append(f"{f_name} is partially clipped by the frame boundary.")

        # Master Prompt 10 Scan Coverage & Reliability Synthesis
        coverage_summary = cls.generate_coverage_summary(
            images=images or [],
            declarations=declarations or []
        )
        scan_reliability = cls.generate_scan_reliability_report(
            images=images or [],
            declarations=declarations or [],
            quality_evaluations=image_qualities,
            ocr_results=ocr_results or []
        )

        return {
            "overall_status": overall_status,
            "compliance_score": round(score, 1),
            "summary_verdict": summary_verdict,
            "warnings": warnings,
            "recommended_actions": recommended_actions,
            "verified_count": verified,
            "issues_count": potential_issues,
            "uncertain_count": unable,
            "visual_compliance_summary": visual_summary,
            "coverage_summary": coverage_summary,
            "scan_reliability": scan_reliability
        }

    @classmethod
    def generate_coverage_summary(
        cls,
        images: List[Any],
        declarations: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Lightweight scan-coverage summary strictly grounded in available evidence.
        Never fabricates coverage percentages or equates missing coverage with legal failure.
        """
        total_images = len(images)
        usable_count = 0
        unusable_count = 0
        degraded_count = 0
        duplicate_count = 0
        known_roles = set()

        for img in images:
            q_status = getattr(img, "quality_status", None) or (img.get("quality_status") if isinstance(img, dict) else None)
            q_decision = getattr(img, "quality_decision", None) or (img.get("quality_decision") if isinstance(img, dict) else None)
            is_dup = getattr(img, "is_duplicate", False) or (img.get("is_duplicate") if isinstance(img, dict) else False)
            role = (getattr(img, "image_role", "") or (img.get("image_role") if isinstance(img, dict) else "")).lower()
            img_type = (getattr(img, "image_type", "") or (img.get("image_type") if isinstance(img, dict) else "")).upper()

            if is_dup:
                duplicate_count += 1

            if role and role not in ("unknown", "other"):
                known_roles.add(role.upper())
            elif img_type and img_type not in ("UNKNOWN", "OTHER"):
                known_roles.add(img_type)

            if q_decision == "UNSUITABLE" or q_status in ("POOR", "CRITICAL_ISSUES", "UNSUITABLE"):
                unusable_count += 1
            elif q_decision == "DEGRADED" or q_status == "DEGRADED":
                degraded_count += 1
                usable_count += 1
            else:
                usable_count += 1

        fields_with_usable_evidence = 0
        fields_requiring_review = 0
        unverified_fields = []
        conflicting_fields = []

        if declarations:
            for decl in declarations:
                st = getattr(decl, "extraction_status", None) or (decl.get("extraction_status") if isinstance(decl, dict) else None) or getattr(decl, "status", None)
                f_name = getattr(decl, "field_name", None) or (decl.get("field_name") if isinstance(decl, dict) else "unknown")
                disp_name = getattr(decl, "display_name", None) or (decl.get("display_name") if isinstance(decl, dict) else f_name)
                has_conf = getattr(decl, "has_conflict", False) or (decl.get("has_conflict") if isinstance(decl, dict) else False)

                if st == "FOUND":
                    fields_with_usable_evidence += 1
                elif st in ("AMBIGUOUS", "LOW_CONFIDENCE") or has_conf:
                    fields_requiring_review += 1
                    if has_conf or st == "AMBIGUOUS":
                        conflicting_fields.append(disp_name)
                elif st in ("UNABLE_TO_VERIFY", "NOT_FOUND"):
                    unverified_fields.append(disp_name)

        # Coverage status determination
        important_areas_missing = []
        if "FRONT" not in known_roles:
            important_areas_missing.append("Front / Principal Display Panel")
        if not ({"BACK", "SIDE", "LEFT_SIDE", "RIGHT_SIDE"} & known_roles):
            important_areas_missing.append("Back or Side Information Panel")

        if not important_areas_missing and usable_count >= 2:
            coverage_status = "ADEQUATE_MULTI_PANEL"
        elif usable_count >= 1:
            coverage_status = "PARTIAL_COVERAGE"
        else:
            coverage_status = "INSUFFICIENT_COVERAGE"

        return {
            "total_images_uploaded": total_images,
            "usable_images_count": usable_count,
            "unusable_images_count": unusable_count,
            "degraded_images_count": degraded_count,
            "duplicate_images_count": duplicate_count,
            "known_panel_roles": sorted(list(known_roles)),
            "coverage_status": coverage_status,
            "unverified_package_areas": important_areas_missing,
            "fields_with_usable_evidence_count": fields_with_usable_evidence,
            "fields_requiring_review_count": fields_requiring_review,
            "conflicting_fields": conflicting_fields,
            "unverified_fields": unverified_fields
        }

    @classmethod
    def generate_scan_reliability_report(
        cls,
        images: List[Any],
        declarations: Optional[List[Any]] = None,
        quality_evaluations: Optional[List[Dict[str, Any]]] = None,
        ocr_results: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes upload usability, known panel roles, quality warnings, retake guidance,
        duplicate relationships, OCR retries, and multi-image agreement/conflict into an
        explainable reliability assessment.
        """
        coverage = cls.generate_coverage_summary(images, declarations)

        quality_warnings = []
        retake_recommendations = []
        ocr_retries = []
        duplicate_details = []

        for img in images:
            # Duplicate handling
            is_dup = getattr(img, "is_duplicate", False) or (img.get("is_duplicate") if isinstance(img, dict) else False)
            if is_dup:
                dup_type = getattr(img, "duplicate_type", "DUPLICATE") or (img.get("duplicate_type") if isinstance(img, dict) else "DUPLICATE")
                dup_reason = getattr(img, "duplicate_reason", "") or (img.get("duplicate_reason") if isinstance(img, dict) else "")
                fn = getattr(img, "original_filename", "image") or (img.get("original_filename") if isinstance(img, dict) else "image")
                duplicate_details.append(f"{fn}: {dup_type} - {dup_reason}")

            # Retake guidance from image
            guidance = getattr(img, "retake_guidance", None) or (img.get("retake_guidance") if isinstance(img, dict) else None)
            if guidance and isinstance(guidance, list):
                for g in guidance:
                    if g not in retake_recommendations:
                        retake_recommendations.append(g)

            # Quality notes
            q_notes = getattr(img, "quality_notes", None) or (img.get("quality_notes") if isinstance(img, dict) else None)
            q_dec = getattr(img, "quality_decision", None) or (img.get("quality_decision") if isinstance(img, dict) else None)
            if q_dec in ("DEGRADED", "UNSUITABLE") and q_notes:
                if q_notes not in quality_warnings:
                    quality_warnings.append(q_notes)

            # OCR retry information
            ocr_attempts = getattr(img, "ocr_attempt_count", 1) or (img.get("ocr_attempt_count") if isinstance(img, dict) else 1)
            prep_stat = getattr(img, "preprocessing_status", "NOT_REQUIRED") or (img.get("preprocessing_status") if isinstance(img, dict) else "NOT_REQUIRED")
            if ocr_attempts > 1 or prep_stat == "APPLIED":
                fn = getattr(img, "original_filename", "image") or (img.get("original_filename") if isinstance(img, dict) else "image")
                ocr_retries.append(f"{fn}: Preprocessing applied, OCR retry executed ({ocr_attempts} attempts).")

        # Fallback to quality_evaluations if retake_recommendations is empty
        if not retake_recommendations and quality_evaluations:
            for qe in quality_evaluations:
                guidance_list = qe.get("retake_guidance", [])
                for g in guidance_list:
                    if g not in retake_recommendations:
                        retake_recommendations.append(g)
                if qe.get("quality_status") in ("POOR", "CRITICAL_ISSUES", "UNSUITABLE") and qe.get("quality_notes"):
                    if qe["quality_notes"] not in quality_warnings:
                        quality_warnings.append(qe["quality_notes"])

        # Multi-image agreement vs conflict summary
        conflicts = coverage.get("conflicting_fields", [])
        agreement_notes = []
        if declarations:
            for decl in declarations:
                alt = getattr(decl, "alternate_candidates", None) or (decl.get("alternate_candidates") if isinstance(decl, dict) else None) or []
                f_name = getattr(decl, "display_name", None) or (decl.get("display_name") if isinstance(decl, dict) else "Declaration")
                has_conf = getattr(decl, "has_conflict", False) or (decl.get("has_conflict") if isinstance(decl, dict) else False)
                if not has_conf and len(alt) > 0:
                    agreement_notes.append(f"{f_name} corroborated across multiple independent panels.")

        # Determine overall scan reliability level
        if coverage["usable_images_count"] >= 2 and not conflicts and not coverage["unverified_package_areas"]:
            reliability_level = "HIGH"
            reliability_message = "Multi-panel photographic coverage is sufficient and verified without conflicting declarations."
        elif coverage["usable_images_count"] >= 1 and not conflicts:
            reliability_level = "MODERATE"
            reliability_message = "Single or partial panel coverage available. Detected declarations are verified, but unverified panels should be checked if applicable."
        elif conflicts:
            reliability_level = "REVIEW_REQUIRED"
            reliability_message = f"Material declaration conflicts detected across photographs ({', '.join(conflicts)}). Inspector review required."
        else:
            reliability_level = "LOW"
            reliability_message = "Photographic evidence is degraded or insufficient to verify mandatory packaging panels."

        # Recommended next action
        if conflicts:
            next_action = f"Review conflicting declarations for {', '.join(conflicts)} on the physical commodity."
        elif coverage["unverified_package_areas"]:
            next_action = f"Upload clear photographs of missing package panels: {', '.join(coverage['unverified_package_areas'])}."
        elif retake_recommendations:
            next_action = retake_recommendations[0]
        else:
            next_action = "Package scan meets evidence reliability standards. No additional photographs required."

        return {
            "reliability_level": reliability_level,
            "reliability_message": reliability_message,
            "image_usability_summary": f"{coverage['usable_images_count']} of {coverage['total_images_uploaded']} images usable for statutory evaluation.",
            "known_panel_roles": coverage["known_panel_roles"],
            "duplicate_handling": {
                "duplicates_detected_count": coverage["duplicate_images_count"],
                "duplicate_details": duplicate_details,
                "policy_note": "Duplicates and near-duplicates are indexed for auditability but not counted as independent corroboration."
            },
            "ocr_recovery_attempts": ocr_retries,
            "quality_warnings": quality_warnings,
            "retake_recommendations": retake_recommendations,
            "multi_image_agreement": agreement_notes,
            "multi_image_conflicts": conflicts,
            "coverage_limitations": (
                f"Missing package panels ({', '.join(coverage['unverified_package_areas'])}). This limitation does not constitute a legal violation."
                if coverage["unverified_package_areas"] else "All standard panels provided."
            ),
            "recommended_next_action": next_action
        }

