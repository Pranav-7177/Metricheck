from typing import List, Dict, Any, Optional
from app.models.models import ComplianceState
from app.services.ocr.base import OCRResult, OCRBoxResult
from app.services.extraction.field_extractors import ModularFieldExtractors, FieldCandidate
from app.services.extraction.normalizer import TextNormalizer
from app.services.visual.service import VisualComplianceService
from app.services.visual.evidence import VisualEvidence


class DeclarationExtractorService:
    """
    Orchestrator for statutory Legal Metrology Packaged Commodities declarations:
    1. PRODUCT_NAME
    2. MRP
    3. NET_QUANTITY
    4. MANUFACTURER
    5. PACKER
    6. IMPORTER
    7. MANUFACTURING_DATE
    8. PACKING_DATE
    9. EXPIRY_DATE
    10. BEST_BEFORE
    11. CONSUMER_CARE
    12. COUNTRY_OF_ORIGIN

    Supports multi-image aggregation, duplicate retention, conflict detection,
    and deterministic bounding box evidence mapping.
    """

    CONFIDENCE_UNCERTAINTY_THRESHOLD = 0.55

    FIELD_ORDER = [
        "PRODUCT_NAME",
        "MRP",
        "NET_QUANTITY",
        "MANUFACTURER",
        "PACKER",
        "IMPORTER",
        "MANUFACTURING_DATE",
        "PACKING_DATE",
        "EXPIRY_DATE",
        "BEST_BEFORE",
        "CONSUMER_CARE",
        "COUNTRY_OF_ORIGIN"
    ]

    # Alias mapping for legacy compliance engine rule targets
    FIELD_ALIASES = {
        "mrp": "MRP",
        "net_quantity": "NET_QUANTITY",
        "manufacturer": "MANUFACTURER",
        "manufacturer_name": "MANUFACTURER",
        "manufacturer_address": "MANUFACTURER",
        "packer": "PACKER",
        "importer": "IMPORTER",
        "mfg_date": "MANUFACTURING_DATE",
        "manufacturing_date": "MANUFACTURING_DATE",
        "date_of_manufacture": "MANUFACTURING_DATE",
        "packing_date": "PACKING_DATE",
        "date_of_packing": "PACKING_DATE",
        "expiry_date": "EXPIRY_DATE",
        "best_before": "BEST_BEFORE",
        "consumer_care": "CONSUMER_CARE",
        "country_of_origin": "COUNTRY_OF_ORIGIN",
        "product_name": "PRODUCT_NAME"
    }

    @classmethod
    def extract_from_boxes_by_image(
        cls,
        image_boxes_map: List[Dict[str, Any]]
    ) -> List[FieldCandidate]:
        """
        Extracts structured fields across multiple images with conflict and duplicate handling.
        image_boxes_map is a list of:
        {
            "image_id": int,
            "image_role": str,
            "image_type": str,
            "boxes": List[Dict[str, Any]]
        }
        """
        all_candidates_by_field: Dict[str, List[FieldCandidate]] = {f: [] for f in cls.FIELD_ORDER}

        for img_entry in image_boxes_map:
            img_id = img_entry.get("image_id")
            img_role = (img_entry.get("image_type") or img_entry.get("image_role") or "front").lower()
            boxes = img_entry.get("boxes", [])
            img_quality = img_entry.get("quality")
            img_path = img_entry.get("image_path")
            img_dims = img_entry.get("dimensions")
            calib_ctx = img_entry.get("calibration_context")
            is_dup = bool(img_entry.get("is_duplicate", False))
            dup_of = img_entry.get("duplicate_of_id")

            # Extract 12 fields for this image
            img_candidates = cls._extract_single_image(boxes, img_id, img_role, img_quality)
            for f_name, cand in img_candidates.items():
                cand.is_from_duplicate = is_dup
                cand.duplicate_of_id = dup_of
                if cand.status != "NOT_FOUND":
                    # Evaluate visual evidence if bounding box is available
                    if cand.bounding_box:
                        try:
                            vis_ev = VisualComplianceService.evaluate_declaration_visual_evidence(
                                field_name=cand.field_name,
                                bounding_box=cand.bounding_box,
                                image_path=img_path,
                                image_id=img_id,
                                image_role=img_role,
                                image_dimensions=img_dims,
                                ocr_confidence=cand.raw_ocr_confidence or cand.confidence,
                                calibration_context=calib_ctx
                            )
                            cand.visual_evidence = vis_ev.to_dict()
                            if not cand.evidence:
                                cand.evidence = {}
                            cand.evidence["visual_evidence"] = cand.visual_evidence
                            if vis_ev.font_height_mm is not None:
                                cand.estimated_font_height_mm = vis_ev.font_height_mm
                                cand.measurement_confidence = "VERIFIED" if vis_ev.calibration_confidence >= 0.85 else "ESTIMATED"
                            else:
                                cand.estimated_font_height_mm = None
                                cand.measurement_confidence = "UNCALIBRATED"
                        except Exception:
                            pass
                    all_candidates_by_field[f_name].append(cand)


        # Aggregate across images: resolve primary vs alternates and detect conflicts
        final_fields: List[FieldCandidate] = []
        for field_name in cls.FIELD_ORDER:
            cands = all_candidates_by_field[field_name]
            if not cands:
                # Field was not found on any panel
                display_name = cls._get_display_name(field_name)
                # If images were degraded (blurry, severe glare, etc.), set UNABLE_TO_VERIFY
                has_degraded_image = any(
                    (entry.get("quality", {}).get("blur_score") is not None and entry.get("quality", {}).get("blur_score") < 40.0) or
                    (entry.get("quality", {}).get("glare_score") is not None and entry.get("quality", {}).get("glare_score") >= 12.0) or
                    entry.get("quality", {}).get("overall_status") in ("POOR", "CRITICAL_ISSUES", "UNSUITABLE", "DEGRADED")
                    for entry in image_boxes_map if entry.get("quality")
                )
                missing_status = "UNABLE_TO_VERIFY" if has_degraded_image else "NOT_FOUND"
                final_fields.append(FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    status=missing_status,
                    value=None,
                    confidence=0.0
                ))
            elif len(cands) == 1:
                final_fields.append(cands[0])
            else:
                # Multi-image resolution
                resolved = cls._resolve_multi_image_candidates(field_name, cands)
                final_fields.append(resolved)

        return final_fields

    @classmethod
    def _extract_single_image(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, FieldCandidate]:
        """Extracts candidate values for an individual image."""
        results: Dict[str, FieldCandidate] = {}

        results["PRODUCT_NAME"] = ModularFieldExtractors.extract_product_name(boxes, image_id, image_role)
        results["MRP"] = ModularFieldExtractors.extract_mrp(boxes, image_id, image_role)
        results["NET_QUANTITY"] = ModularFieldExtractors.extract_net_quantity(boxes, image_id, image_role)

        date_results = ModularFieldExtractors.extract_dates(boxes, image_id, image_role)
        results.update(date_results)

        entity_results = ModularFieldExtractors.extract_entities(boxes, image_id, image_role)
        results.update(entity_results)

        results["CONSUMER_CARE"] = ModularFieldExtractors.extract_consumer_care(boxes, image_id, image_role)
        results["COUNTRY_OF_ORIGIN"] = ModularFieldExtractors.extract_country_of_origin(boxes, image_id, image_role)

        # Apply image quality degradation/unsuitability awareness to candidates
        if quality:
            q_status = quality.get("overall_status")
            q_decision = quality.get("quality_decision")
            for f_name, cand in results.items():
                if cand.status == "FOUND":
                    if q_decision == "UNSUITABLE" or q_status in ("POOR", "CRITICAL_ISSUES"):
                        cand.status = "UNABLE_TO_VERIFY"
                        cand.confidence = min(cand.confidence, 0.40)
                        if not cand.evidence:
                            cand.evidence = {}
                        cand.evidence["quality_unverified_reason"] = (
                            f"Image quality is unsuitable ({quality.get('quality_notes')}); cannot confirm statutory compliance."
                        )
                    elif q_decision == "DEGRADED" or q_status == "DEGRADED":
                        cand.confidence = max(0.50, round(cand.confidence * 0.9, 4))
                elif cand.status == "NOT_FOUND":
                    if q_decision == "UNSUITABLE" or q_status in ("POOR", "CRITICAL_ISSUES"):
                        cand.status = "UNABLE_TO_VERIFY"
                        if not cand.evidence:
                            cand.evidence = {}
                        cand.evidence["quality_unverified_reason"] = (
                            "Panel quality is severely degraded/unreadable. Declaration cannot be verified or assumed absent."
                        )

        return results

    @classmethod
    def are_values_semantically_equivalent(cls, field_name: str, c1: FieldCandidate, c2: FieldCandidate) -> bool:
        """
        Determines if two field candidates represent the same underlying legal value,
        accounting for harmless formatting, casing, spacing, and currency variants.
        """
        import re
        v1 = (c1.normalized_value or c1.value or "").strip().lower()
        v2 = (c2.normalized_value or c2.value or "").strip().lower()
        if not v1 or not v2:
            return False
        if v1 == v2:
            return True

        if field_name == "MRP":
            try:
                n1 = float(re.sub(r"[^\d.]", "", v1))
                n2 = float(re.sub(r"[^\d.]", "", v2))
                return abs(n1 - n2) < 0.01
            except Exception:
                pass
        elif field_name == "NET_QUANTITY":
            s1 = re.sub(r"\s+", "", v1)
            s2 = re.sub(r"\s+", "", v2)
            if s1 == s2:
                return True
            if c1.unit and c2.unit and c1.unit.lower() == c2.unit.lower():
                try:
                    num1 = float(re.sub(r"[^\d.]", "", str(c1.value or "")))
                    num2 = float(re.sub(r"[^\d.]", "", str(c2.value or "")))
                    return abs(num1 - num2) < 0.001
                except Exception:
                    pass
        elif field_name in ("MANUFACTURING_DATE", "PACKING_DATE", "EXPIRY_DATE", "BEST_BEFORE"):
            s1 = re.sub(r"[^\w]", "", v1)
            s2 = re.sub(r"[^\w]", "", v2)
            if s1 == s2:
                return True
        elif field_name in ("MANUFACTURER", "PACKER", "IMPORTER", "CONSUMER_CARE", "PRODUCT_NAME", "COUNTRY_OF_ORIGIN"):
            s1 = re.sub(r"[\s,.-]+", " ", v1).strip()
            s2 = re.sub(r"[\s,.-]+", " ", v2).strip()
            if s1 == s2:
                return True
            if len(s1) >= 10 and len(s2) >= 10 and (s1 in s2 or s2 in s1):
                return True

        return False

    @classmethod
    def _resolve_multi_image_candidates(
        cls,
        field_name: str,
        candidates: List[FieldCandidate]
    ) -> FieldCandidate:
        """
        Selects primary candidate using deterministic, explainable ranking.
        Does NOT treat duplicate images as independent corroboration.
        Strengthens confidence when independent observations agree.
        Preserves competing candidates and flags AMBIGUOUS when materially different values conflict.
        """
        # Sort candidates deterministically:
        # 1. Non-duplicate preferred over duplicate copy
        # 2. Status priority: FOUND > LOW_CONFIDENCE > others
        # 3. Extraction confidence
        # 4. Raw OCR confidence
        # 5. Completeness of candidate text
        def rank_key(c: FieldCandidate):
            not_dup = 0 if getattr(c, "is_from_duplicate", False) else 1
            status_prio = 2 if c.status == "FOUND" else (1 if c.status == "LOW_CONFIDENCE" else 0)
            return (
                not_dup,
                status_prio,
                round(c.confidence, 4),
                round(c.raw_ocr_confidence, 4),
                len(c.value or "")
            )

        sorted_cands = sorted(candidates, key=rank_key, reverse=True)
        primary = sorted_cands[0]
        alternates = sorted_cands[1:]

        has_conflict = False
        alt_payloads = []
        independent_corroborating_images = []

        for alt in alternates:
            is_equivalent = cls.are_values_semantically_equivalent(field_name, primary, alt)

            # Check if genuinely independent observation
            is_independent = (
                alt.source_image_id is not None
                and primary.source_image_id is not None
                and alt.source_image_id != primary.source_image_id
                and not getattr(alt, "is_from_duplicate", False)
                and not getattr(primary, "is_from_duplicate", False)
            )

            if is_equivalent:
                # Genuine agreement!
                if is_independent and alt.source_image_id not in independent_corroborating_images:
                    independent_corroborating_images.append(alt.source_image_id)
            else:
                # Materially different value!
                if (alt.value or alt.normalized_value) and (primary.value or primary.normalized_value):
                    has_conflict = True

            alt_payloads.append({
                "value": alt.value,
                "normalized_value": alt.normalized_value,
                "confidence": alt.confidence,
                "source_image_id": alt.source_image_id,
                "source_image_role": alt.source_image_role,
                "source_ocr_ids": alt.source_ocr_ids,
                "bounding_box": alt.bounding_box,
                "status": alt.status,
                "is_from_duplicate": getattr(alt, "is_from_duplicate", False),
                "is_equivalent": is_equivalent
            })

        # Multi-image independent agreement strengthens confidence
        if independent_corroborating_images and not has_conflict:
            boost = min(0.08, len(independent_corroborating_images) * 0.04)
            primary.confidence = min(0.99, round(primary.confidence + boost, 4))
            if not primary.evidence:
                primary.evidence = {}
            primary.evidence["corroborating_image_ids"] = independent_corroborating_images
            primary.evidence["corroboration_count"] = len(independent_corroborating_images)

        primary.alternate_candidates = alt_payloads
        if has_conflict:
            primary.has_conflict = True
            primary.status = "AMBIGUOUS"
            if not primary.evidence:
                primary.evidence = {}
            primary.evidence["conflict_reason"] = (
                f"Conflicting values detected across package photographs for {field_name}. Preserved for manual review."
            )

        # Aggregate visual evidence across images
        vis_items = []
        for c in candidates:
            if getattr(c, "visual_evidence", None):
                try:
                    vis_items.append(VisualEvidence.from_dict(c.visual_evidence))
                except Exception:
                    pass
        if vis_items:
            agg_vis = VisualComplianceService.aggregate_multi_image_visual_evidence(vis_items)
            if agg_vis:
                primary.visual_evidence = agg_vis.to_dict()
                if not primary.evidence:
                    primary.evidence = {}
                primary.evidence["visual_evidence"] = primary.visual_evidence
                if agg_vis.font_height_mm is not None:
                    primary.estimated_font_height_mm = agg_vis.font_height_mm
                    primary.measurement_confidence = "VERIFIED" if agg_vis.calibration_confidence >= 0.85 else "ESTIMATED"
                else:
                    primary.estimated_font_height_mm = None
                    primary.measurement_confidence = "UNCALIBRATED"

        return primary

    @staticmethod
    def _get_display_name(field_name: str) -> str:
        names = {
            "PRODUCT_NAME": "Product / Commodity Name",
            "MRP": "Maximum Retail Price (MRP)",
            "NET_QUANTITY": "Net Quantity",
            "MANUFACTURER": "Manufacturer Name & Address",
            "PACKER": "Packer Name & Address",
            "IMPORTER": "Importer Name & Address",
            "MANUFACTURING_DATE": "Date of Manufacture",
            "PACKING_DATE": "Date of Packaging",
            "EXPIRY_DATE": "Expiry Date",
            "BEST_BEFORE": "Best Before / Use By",
            "CONSUMER_CARE": "Consumer Care Details",
            "COUNTRY_OF_ORIGIN": "Country of Origin"
        }
        return names.get(field_name, field_name.replace("_", " ").title())

    # -------------------------------------------------------------
    # Compatibility method for existing scan pipeline / RuleEngine
    # -------------------------------------------------------------
    @classmethod
    def extract_all_declarations(
        cls,
        ocr_results: List[OCRResult],
        category_code: str = "food_grocery",
        source_image_role: str = "front",
        image_qualities: Optional[Dict[int, Dict[str, Any]]] = None,
        calibration_contexts: Optional[Dict[int, Dict[str, Any]]] = None,
        image_paths: Optional[Dict[int, str]] = None,
        image_dimensions: Optional[Dict[int, tuple]] = None,
        image_duplicates: Optional[Dict[int, Dict[str, Any]]] = None,
        duplicates_info: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Legacy adapter maintaining full backward compatibility with Scan creation and
        ComplianceRuleEngine while providing rich structured fields.
        """
        dup_info_map = duplicates_info if duplicates_info is not None else (image_duplicates or {})
        image_boxes_map = []
        for ocr in ocr_results:
            boxes = [
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "bounding_box": b.bounding_box,
                    "line_number": b.line_number,
                    "image_id": getattr(b, "image_id", None) or getattr(ocr, "image_id", None),
                    "image_type": getattr(b, "image_type", None) or getattr(ocr, "image_type", "FRONT")
                }
                for b in ocr.boxes
            ]
            img_id = getattr(ocr, "image_id", None)
            quality_info = (image_qualities or {}).get(img_id) if image_qualities else None
            calib_info = (calibration_contexts or {}).get(img_id) if calibration_contexts else None
            img_path = (image_paths or {}).get(img_id) if image_paths else None
            img_dims = (image_dimensions or {}).get(img_id) if image_dimensions else None
            dup_info = dup_info_map.get(img_id, {})
            image_boxes_map.append({
                "image_id": img_id,
                "image_role": getattr(ocr, "image_type", "FRONT").lower(),
                "image_type": getattr(ocr, "image_type", "FRONT"),
                "boxes": boxes,
                "quality": quality_info,
                "calibration_context": calib_info,
                "image_path": img_path,
                "dimensions": img_dims,
                "is_duplicate": dup_info.get("is_duplicate", False),
                "duplicate_of_id": dup_info.get("duplicate_of_id"),
                "duplicate_type": dup_info.get("duplicate_type")
            })

        field_candidates = cls.extract_from_boxes_by_image(image_boxes_map)

        # Convert to dictionary format expected by ComplianceRuleEngine and ExtractedDeclaration persistence
        output = []
        for fc in field_candidates:
            # Map extraction status to ComplianceState for backward compatibility
            if fc.status == "FOUND":
                comp_status = ComplianceState.VERIFIED_COMPLIANT
            elif fc.status == "NOT_FOUND":
                comp_status = ComplianceState.NOT_FOUND
            elif fc.status == "LOW_CONFIDENCE":
                comp_status = ComplianceState.UNABLE_TO_VERIFY
            elif fc.status == "UNABLE_TO_VERIFY":
                comp_status = ComplianceState.UNABLE_TO_VERIFY
            else: # AMBIGUOUS
                comp_status = ComplianceState.REVIEW_REQUIRED

            item = {
                "field_name": fc.field_name.lower(), # lowercase alias for compliance rule matching
                "canonical_field_name": fc.field_name,
                "display_name": fc.display_name,
                "detected_value": fc.value,
                "normalized_value": fc.normalized_value,
                "raw_value": fc.raw_value,
                "raw_ocr_snippet": fc.raw_value,
                "unit": fc.unit,
                "currency": fc.currency,
                "confidence": fc.confidence,
                "field_confidence": fc.confidence,
                "raw_ocr_confidence": fc.raw_ocr_confidence,
                "status": comp_status,
                "extraction_status": fc.status,
                "bounding_box": fc.bounding_box,
                "source_image_id": fc.source_image_id,
                "source_image_role": fc.source_image_role or "front",
                "source_ocr_ids": fc.source_ocr_ids,
                "evidence": fc.evidence,
                "extraction_method": fc.extraction_method,
                "has_conflict": fc.has_conflict,
                "alternate_candidates": fc.alternate_candidates,
                "estimated_font_height_mm": getattr(fc, "estimated_font_height_mm", None),
                "required_font_height_mm": getattr(fc, "required_font_height_mm", None),
                "measurement_confidence": getattr(fc, "measurement_confidence", "UNCALIBRATED"),
                "visual_evidence": getattr(fc, "visual_evidence", None) or (fc.evidence or {}).get("visual_evidence"),
            }
            output.append(item)


        return output
