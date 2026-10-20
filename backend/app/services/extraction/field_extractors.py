import re
import statistics
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from app.services.extraction.normalizer import TextNormalizer
from app.services.extraction.evidence_matcher import EvidenceMatcher

@dataclass
class FieldCandidate:
    field_name: str
    display_name: str
    value: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 0.0
    raw_ocr_confidence: float = 0.0
    status: str = "NOT_FOUND"  # FOUND, NOT_FOUND, AMBIGUOUS, LOW_CONFIDENCE, UNABLE_TO_VERIFY
    source_image_id: Optional[int] = None
    source_image_role: Optional[str] = "front"
    source_ocr_ids: List[int] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: str = "DETERMINISTIC_CONTEXT"
    has_conflict: bool = False
    alternate_candidates: List[Dict[str, Any]] = field(default_factory=list)
    estimated_font_height_mm: Optional[float] = None
    required_font_height_mm: Optional[float] = None
    measurement_confidence: Optional[str] = "UNCALIBRATED"
    visual_evidence: Optional[Dict[str, Any]] = None
    is_from_duplicate: bool = False
    duplicate_of_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "display_name": self.display_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "currency": self.currency,
            "unit": self.unit,
            "confidence": self.confidence,
            "raw_ocr_confidence": self.raw_ocr_confidence,
            "status": self.status,
            "source_image_id": self.source_image_id,
            "source_image_role": self.source_image_role,
            "source_ocr_ids": self.source_ocr_ids,
            "evidence": self.evidence,
            "bounding_box": self.bounding_box,
            "extraction_method": self.extraction_method,
            "has_conflict": self.has_conflict,
            "alternate_candidates": self.alternate_candidates,
            "estimated_font_height_mm": self.estimated_font_height_mm,
            "required_font_height_mm": self.required_font_height_mm,
            "measurement_confidence": self.measurement_confidence,
            "visual_evidence": self.visual_evidence,
            "is_from_duplicate": self.is_from_duplicate,
            "duplicate_of_id": self.duplicate_of_id,
        }



class ModularFieldExtractors:
    """
    Modular deterministic extractors for the 12 statutory package declaration fields.
    Each extractor locates evidence boxes, parses values, and calculates explainable confidence.
    """

    DATE_PATTERN = r'(?:\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+\d{2,4}\b|\b\d{1,2}[\s,.-]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+\d{2,4}\b)'

    @classmethod
    def _determine_missing_field_status(
        cls,
        image_quality: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Determines whether a missing field declaration is genuinely NOT_FOUND
        or UNABLE_TO_VERIFY due to image degradation (severe blur, glare, poor quality).
        Returns (status, reason).
        """
        if image_quality:
            q_status = str(image_quality.get("quality_status", "")).upper()
            blur_score = float(image_quality.get("blur_score", 100.0))
            glare_score = float(image_quality.get("glare_score") or image_quality.get("glare_percentage") or 0.0)
            quality_score = float(image_quality.get("quality_score", 1.0))

            if blur_score < 40.0:
                return "UNABLE_TO_VERIFY", f"Severe defocus blur (sharpness score {blur_score:.1f} < 40.0) prevents reliable verification."

            if glare_score >= 12.0:
                return "UNABLE_TO_VERIFY", f"Severe specular reflection/glare ({glare_score:.1f}% washed out) prevents reliable verification."

            if "POOR" in q_status or "CRITICAL" in q_status or quality_score < 0.40:
                return "UNABLE_TO_VERIFY", f"Image quality gate failed ({q_status}, score {quality_score:.2f}); cannot verify statutory declaration reliably."

        return "NOT_FOUND", None

    @classmethod
    def _should_exclude_from_product_name(cls, text: str) -> bool:
        """
        Determines whether an OCR text box must be excluded from being considered
        as a product name candidate (Section 13).
        """
        lower = text.lower()
        # 1. Statutory labels
        if any(re.search(pat, text, re.IGNORECASE) for pat in [
            r'\bMRP\b', r'\bMAX(?:IMUM)?\s+RETAIL\s+PRICE\b', r'\bNET\s*(?:QTY|WT|WEIGHT|VOL)\b',
            r'\bMANUFACTURED\b', r'\bPACKED\b', r'\bIMPORTED\b', r'\bMFG\b', r'\bPKD\b', r'\bEXP\b',
            r'\bBEST\s+BEFORE\b', r'\bCONSUMER\s+CARE\b', r'\bCUSTOMER\s+CARE\b', r'\bINGREDIENTS?\b',
            r'\bDIRECTIONS?\b', r'\bWARNING\b', r'\bUSAGE\b', r'\bBATCH\b', r'\bLOT\b', r'\bFSSAI\b',
            r'\bLIC\s*NO\b', r'\bNUTRITION\b', r'\bNUTRITIONAL\b', r'\bSTORAGE\b', r'\bCONTAINS\b'
        ]):
            return True

        # 2. Contact info (Phone numbers, emails, websites)
        if re.search(r'\b(?:1800|1860|\d{10}|\d{3}[-\s]\d{3}[-\s]\d{4})\b', text):
            return True
        if "@" in text or re.search(r'\b(?:www\.|\.com|\.in|\.org)\b', lower):
            return True

        # 3. Addresses & Geography
        if any(re.search(pat, text, re.IGNORECASE) for pat in [
            r'\bPLOT\b', r'\bROAD\b', r'\bSTREET\b', r'\bNAGAR\b', r'\bSECTOR\b', r'\bPHASE\b',
            r'\bINDUSTRIAL\s+AREA\b', r'\bDIST(?:RICT)?\b', r'\bSTATE\b', r'\bPIN\b', r'\b\d{6}\b',
            r'\bDELHI\b', r'\bMUMBAI\b', r'\bBANGALORE\b', r'\bBENGALURU\b', r'\bCHENNAI\b', r'\bKOLKATA\b',
            r'\bHYDERABAD\b', r'\bHARYANA\b', r'\bKARNATAKA\b', r'\bMAHARASHTRA\b', r'\bTAMIL\s*NADU\b'
        ]):
            return True

        # 4. Pure dates or pure numbers or pure prices
        if re.search(cls.DATE_PATTERN, text, re.IGNORECASE) and len(text.split()) <= 3:
            return True
        if re.search(r'^[₹Rs\s.:/-]*\d+(?:\.\d+)?$', text, re.IGNORECASE):
            return True
        if re.search(r'^\d+\s*(?:g|kg|ml|l|ltr|gm|gms|units?|pcs?)$', text, re.IGNORECASE):
            return True

        return False

    @classmethod
    def _has_promotional_keyword(cls, text: str) -> bool:
        """Checks if text contains promotional discount or marketing slogan phrasing."""
        return bool(re.search(
            r'\b(?:new|best\s+value|buy\s*1\s*get\s*1|free|special\s+offer|premium\s+quality|'
            r'100%\s+natural|extra|limited\s+edition|save|discount|cash\s*back|deal|win|bonus|'
            r'coupon|special\s+price|offer\s+price|starting\s+(?:at|from)?|up\s+to\s+\d+%\s+off|'
            r'\d+%\s+off|pack\s+free|wrapper|promo)\b',
            text,
            re.IGNORECASE
        ))

    @classmethod
    def _is_pure_promotional_or_statutory(cls, text: str) -> bool:
        if cls._should_exclude_from_product_name(text):
            return True
        if cls._has_promotional_keyword(text) and len(text.split()) <= 4:
            return True
        return False

    # -------------------------------------------------------------
    # 1. MRP EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_mrp(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> FieldCandidate:
        field_name = "MRP"
        display_name = "Maximum Retail Price (MRP)"

        # Search for explicit statutory MRP indicators
        mrp_regex = re.compile(r'(?:MRP|M\.?R\.?P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)[\s.:₹Rs/-]*([0-9,]+(?:\.[0-9]{1,2})?)', re.IGNORECASE)
        tax_regex = re.compile(r'(?:incl|inclusive)\.?\s*(?:of)?\s*(?:all)?\s*taxes', re.IGNORECASE)
        promo_distractor_regex = re.compile(
            r'\b(?:save|discount|off|offer|special|cashback|cash\s*back|starting|from|win|deal|coupon|buy|get|free)\b',
            re.IGNORECASE
        )

        # Check for unreadable/corrupted MRP indicator in single box (e.g. "MRP ₹1?9", "MRP ₹", "MRP ???")
        corrupt_mrp_regex = re.compile(
            r'\b(?:MRP|M\.?R\.?P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)\b[\s.:]*(?:[₹Rs\s.:/-]*\?+|[₹Rs\s.:/-]*\d+[\d,]*\?+[0-9?]*|[₹Rs]\s*$)',
            re.IGNORECASE
        )

        unreadable_box = None
        for box in boxes:
            text = box.get("text", "").strip()
            if corrupt_mrp_regex.search(text):
                unreadable_box = box
                break

        # 1. First search within single box
        for box in boxes:
            text = box.get("text", "")
            if corrupt_mrp_regex.search(text):
                continue
            match = mrp_regex.search(text)
            if match and match.group(1):
                raw_amt = match.group(1).replace(",", "")
                # Skip if text is primarily a promotional discount like "Save ₹50 on MRP"
                match_start = match.start()
                prefix_text = text[:match_start]
                if promo_distractor_regex.search(prefix_text) and not any(k in prefix_text.upper() for k in ["MRP", "RETAIL PRICE"]):
                    continue

                tax_match = tax_regex.search(text)
                tax_text = " (Incl. of all taxes)" if tax_match else ""
                val_formatted = f"{float(raw_amt):.2f}"
                currency = "INR"
                raw_ocr_conf = float(box.get("confidence", 0.0))

                # Look for adjacent tax box if not in same box
                matched_boxes = [box]
                if not tax_match:
                    adj = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=40)
                    for ab in adj:
                        if tax_regex.search(ab.get("text", "")):
                            matched_boxes.append(ab)
                            tax_text = " (Incl. of all taxes)"
                            break

                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=len(matched_boxes))

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=f"₹{val_formatted}{tax_text}",
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    currency=currency,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_PRICE_PATTERN"
                )

        # 2. Multi-box search: MRP label in one box, price in adjacent box
        label_only_regex = re.compile(r'^(?:MRP|M\.?R\.?P\.?|MAX(?:IMUM)?\s+RETAIL\s+PRICE)[\s.:₹Rs/-]*$', re.IGNORECASE)
        price_num_regex = re.compile(r'^[₹Rs\s.:/-]*([0-9,]+(?:\.[0-9]{1,2})?)$', re.IGNORECASE)

        mrp_anchor_found = None
        for box in boxes:
            text = box.get("text", "").strip()
            if label_only_regex.search(text):
                mrp_anchor_found = box
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=150, max_y_gap=35)
                for cand_box in adj_boxes:
                    c_text = cand_box.get("text", "").strip()
                    # Check if adjacent box is unreadable/corrupted
                    if "?" in c_text:
                        unreadable_box = cand_box
                        break
                    # Skip promotional text in adjacent box
                    if promo_distractor_regex.search(c_text):
                        continue
                    p_match = price_num_regex.search(c_text)
                    if p_match:
                        raw_amt = p_match.group(1).replace(",", "")
                        try:
                            num_val = float(raw_amt)
                            if num_val > 0:
                                matched_boxes = [box, cand_box]
                                raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand_box.get("confidence", 0.0))) / 2.0
                                val_formatted = f"{num_val:.2f}"
                                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)

                                return FieldCandidate(
                                    field_name=field_name,
                                    display_name=display_name,
                                    value=f"₹{val_formatted}",
                                    raw_value=f"{box.get('text')} {cand_box.get('text')}",
                                    normalized_value=val_formatted,
                                    currency="INR",
                                    confidence=conf,
                                    raw_ocr_confidence=raw_ocr_conf,
                                    status=status,
                                    source_image_id=image_id,
                                    source_image_role=image_role,
                                    source_ocr_ids=evidence["source_ocr_ids"],
                                    evidence=evidence,
                                    bounding_box=evidence["enclosing_box"],
                                    extraction_method="SPATIAL_PROXIMITY_MERGE"
                                )
                        except ValueError:
                            continue

        # If an unreadable MRP pattern or orphaned anchor was found:
        target_unreadable = unreadable_box or mrp_anchor_found
        if target_unreadable:
            raw_conf = float(target_unreadable.get("confidence", 0.0))
            evidence = EvidenceMatcher.build_evidence([target_unreadable], source_image_id=image_id, source_image_role=image_role)
            evidence["reason"] = "Relevant MRP indicator detected, but numeric price value could not be reliably established."
            return FieldCandidate(
                field_name=field_name,
                display_name=display_name,
                value=None,
                raw_value=target_unreadable.get("text"),
                normalized_value=None,
                confidence=round(raw_conf * 0.5, 4),
                raw_ocr_confidence=raw_conf,
                status="UNABLE_TO_VERIFY",
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="UNREADABLE_MRP_FLAG"
            )

        missing_status, reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": reason} if reason else {}
        return FieldCandidate(
            field_name=field_name,
            display_name=display_name,
            status=missing_status,
            source_image_id=image_id,
            source_image_role=image_role,
            evidence=missing_evidence
        )

    # -------------------------------------------------------------
    # 2. NET QUANTITY EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_net_quantity(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> FieldCandidate:
        field_name = "NET_QUANTITY"
        display_name = "Net Quantity"

        qty_units = r'(?:kg|kgs|kilogram|kilograms|g|gm|gms|gram|grams|mg|ml|m\.l\.|millilitre|l|ltr|litre|litres|cm|m|mm|units?|pcs?|n)'
        label_only_regex = re.compile(r'\b(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\b', re.IGNORECASE)
        val_unit_regex = re.compile(rf'(\d+(?:\.\d+)?)\s*({qty_units})\b', re.IGNORECASE)
        combined_regex = re.compile(
            rf'\b(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\s*[:.-]?\s*(\d+(?:\.\d+)?)\s*({qty_units})\b',
            re.IGNORECASE
        )
        promo_qty_regex = re.compile(r'(?:\b\d+%\s*(?:extra|off|more|discount|free)\b|\bsave\s+\d+%\b)', re.IGNORECASE)

        # Check for unreadable net quantity (e.g. "NET WT. ???" or "NET QTY: [unreadable]")
        corrupt_net_regex = re.compile(
            r'\b(?:NET\s*(?:QTY|QUANTITY|WT\.?|WEIGHT|VOL\.?|VOLUME|CONTENTS?)|N\.?\s*W\.?)\b[\s.:]*(?:\?+|[^\w\s]*\?+)',
            re.IGNORECASE
        )

        unreadable_box = None
        for box in boxes:
            text = box.get("text", "").strip()
            if corrupt_net_regex.search(text):
                unreadable_box = box
                break

        # 1. Look for combined label + quantity in a single box
        for box in boxes:
            text = box.get("text", "")
            # Skip promotional percentage
            if promo_qty_regex.search(text):
                continue
            match = combined_regex.search(text)
            if match:
                num_str, raw_unit = match.group(1), match.group(2)
                canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                val_formatted = f"{num_str} {canonical_unit}"
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=val_formatted,
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    unit=canonical_unit,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_LABEL_VALUE"
                )

        # 2. Multi-box: Label in one box, value in adjacent box
        net_anchor_found = None
        for box in boxes:
            text = box.get("text", "")
            if promo_qty_regex.search(text):
                continue
            if label_only_regex.search(text):
                net_anchor_found = box
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=50)
                for cand_box in adj_boxes:
                    c_text = cand_box.get("text", "")
                    if promo_qty_regex.search(c_text):
                        continue
                    if "?" in c_text:
                        unreadable_box = cand_box
                        break
                    c_match = val_unit_regex.search(c_text)
                    if c_match:
                        num_str, raw_unit = c_match.group(1), c_match.group(2)
                        canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                        val_formatted = f"{num_str} {canonical_unit}"
                        matched_boxes = [box, cand_box]
                        raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand_box.get("confidence", 0.0))) / 2.0
                        evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)

                        return FieldCandidate(
                            field_name=field_name,
                            display_name=display_name,
                            value=val_formatted,
                            raw_value=f"{box.get('text')} {cand_box.get('text')}",
                            normalized_value=val_formatted,
                            unit=canonical_unit,
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="SPATIAL_PROXIMITY_MERGE"
                        )

        # 3. Fallback: bare quantity in single box when no label exists
        nutritional_distractor_regex = re.compile(
            r'\b(?:carb(?:ohydrate)?s?|protein|fat|sugar|serving|energy|cholesterol|sodium|nutrient|nutrition|per\s+\d+)\b',
            re.IGNORECASE
        )
        for box in boxes:
            text = box.get("text", "")
            if promo_qty_regex.search(text) or nutritional_distractor_regex.search(text):
                continue
            match = val_unit_regex.search(text)
            if match:
                num_str, raw_unit = match.group(1), match.group(2)
                canonical_unit = TextNormalizer.canonicalize_unit(raw_unit)
                val_formatted = f"{num_str} {canonical_unit}"
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=val_formatted,
                    raw_value=box.get("text"),
                    normalized_value=val_formatted,
                    unit=canonical_unit,
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="REGEX_UNIT_PATTERN"
                )

        target_unreadable = unreadable_box or net_anchor_found
        if target_unreadable:
            raw_conf = float(target_unreadable.get("confidence", 0.0))
            evidence = EvidenceMatcher.build_evidence([target_unreadable], source_image_id=image_id, source_image_role=image_role)
            evidence["reason"] = "Relevant Net Quantity indicator detected, but numeric value could not be reliably established."
            return FieldCandidate(
                field_name=field_name,
                display_name=display_name,
                value=None,
                raw_value=target_unreadable.get("text"),
                normalized_value=None,
                confidence=round(raw_conf * 0.5, 4),
                raw_ocr_confidence=raw_conf,
                status="UNABLE_TO_VERIFY",
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="UNREADABLE_NET_QTY_FLAG"
            )

        missing_status, reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": reason} if reason else {}
        return FieldCandidate(
            field_name=field_name,
            display_name=display_name,
            status=missing_status,
            source_image_id=image_id,
            source_image_role=image_role,
            evidence=missing_evidence
        )

    # -------------------------------------------------------------
    # 3-6. DATES EXTRACTION (MANUFACTURING, PACKING, EXPIRY, BEST_BEFORE)
    # -------------------------------------------------------------
    @classmethod
    def extract_dates(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, FieldCandidate]:
        missing_status, missing_reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": missing_reason} if missing_reason else {}

        results = {
            "MANUFACTURING_DATE": FieldCandidate(field_name="MANUFACTURING_DATE", display_name="Date of Manufacture", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
            "PACKING_DATE": FieldCandidate(field_name="PACKING_DATE", display_name="Date of Packaging", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
            "EXPIRY_DATE": FieldCandidate(field_name="EXPIRY_DATE", display_name="Expiry Date", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
            "BEST_BEFORE": FieldCandidate(field_name="BEST_BEFORE", display_name="Best Before / Use By", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
        }

        date_regex = re.compile(cls.DATE_PATTERN, re.IGNORECASE)

        # Contextual label patterns
        label_configs = [
            ("MANUFACTURING_DATE", re.compile(r'\b(?:MFD|MFG|DATE\s+OF\s+MFG|MANUFACTURED\s+ON|MFG\.?\s*DATE)\b', re.IGNORECASE)),
            ("PACKING_DATE", re.compile(r'\b(?:PKD|PKG|DATE\s+OF\s+P(?:AC)?K(?:IN)?G|PACKED\s+ON|PKD\.?\s*DATE)\b', re.IGNORECASE)),
            ("EXPIRY_DATE", re.compile(r'\b(?:EXP|EXPIRY|DATE\s+OF\s+EXPIRY|EXP\.?\s*DATE|USE\s+BEFORE)\b', re.IGNORECASE)),
            ("BEST_BEFORE", re.compile(r'\b(?:BEST\s+BEFORE|BB)\b', re.IGNORECASE)),
        ]

        # Scan for explicit contextual dates
        matched_box_indices = set()
        duration_regex = re.compile(r'\b(\d+\s*(?:months?|days?|years?)(?:\s+from\s+[\w\s]+)?)\b', re.IGNORECASE)

        for target_field, label_re in label_configs:
            for idx, box in enumerate(boxes):
                text = box.get("text", "")
                if label_re.search(text):
                    # Check for unreadable date (e.g. "MFD: ??/??/????" or "EXP: ???")
                    if "?" in text or re.search(r'[:.-]\s*$', text):
                        # check if adjacent has date
                        adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=40)
                        has_adj_date = any(date_regex.search(ab.get("text", "")) for ab in adj_boxes)
                        if not has_adj_date:
                            raw_ocr_conf = float(box.get("confidence", 0.0))
                            ev = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                            ev["reason"] = f"Relevant {results[target_field].display_name} label detected, but date value could not be reliably verified."
                            results[target_field] = FieldCandidate(
                                field_name=target_field,
                                display_name=results[target_field].display_name,
                                value=None,
                                raw_value=text,
                                status="UNABLE_TO_VERIFY",
                                confidence=round(raw_ocr_conf * 0.5, 4),
                                raw_ocr_confidence=raw_ocr_conf,
                                source_image_id=image_id,
                                source_image_role=image_role,
                                source_ocr_ids=ev["source_ocr_ids"],
                                evidence=ev,
                                bounding_box=ev["enclosing_box"],
                                extraction_method="UNREADABLE_DATE_FLAG"
                            )
                            matched_box_indices.add(idx)
                            break

                    # 1. Date or duration in same box
                    d_match = date_regex.search(text)
                    if not d_match and target_field == "BEST_BEFORE":
                        d_match = duration_regex.search(text)
                    if d_match:
                        date_val = d_match.group(0)
                        raw_ocr_conf = float(box.get("confidence", 0.0))
                        evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)
                        results[target_field] = FieldCandidate(
                            field_name=target_field,
                            display_name=results[target_field].display_name,
                            value=date_val,
                            raw_value=text,
                            normalized_value=date_val,
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="REGEX_LABEL_VALUE"
                        )
                        matched_box_indices.add(idx)
                        break

                    # 2. Date in adjacent box
                    adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=200, max_y_gap=40)
                    found_adj = False
                    for ab in adj_boxes:
                        ab_text = ab.get("text", "")
                        ad_match = date_regex.search(ab_text)
                        if not ad_match and target_field == "BEST_BEFORE":
                            ad_match = duration_regex.search(ab_text)
                        if ad_match:
                            date_val = ad_match.group(0)
                            matched_boxes = [box, ab]
                            raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(ab.get("confidence", 0.0))) / 2.0
                            evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                            status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True, supporting_tokens_count=2)
                            results[target_field] = FieldCandidate(
                                field_name=target_field,
                                display_name=results[target_field].display_name,
                                value=date_val,
                                raw_value=f"{text} {ab_text}",
                                normalized_value=date_val,
                                confidence=conf,
                                raw_ocr_confidence=raw_ocr_conf,
                                status=status,
                                source_image_id=image_id,
                                source_image_role=image_role,
                                source_ocr_ids=evidence["source_ocr_ids"],
                                evidence=evidence,
                                bounding_box=evidence["enclosing_box"],
                                extraction_method="SPATIAL_PROXIMITY_MERGE"
                            )
                            matched_box_indices.add(idx)
                            found_adj = True
                            break
                    if found_adj:
                        break

        # Check for unassigned/ambiguous dates:
        # If there's a valid date token in the image without label context:
        unmatched_dates = []
        for idx, box in enumerate(boxes):
            if idx in matched_box_indices:
                continue
            text = box.get("text", "")
            if any(label_re.search(text) for _, label_re in label_configs):
                continue
            d_match = date_regex.search(text)
            if d_match:
                unmatched_dates.append((box, d_match.group(0)))

        # If all date fields are NOT_FOUND and an ambiguous date is present:
        if unmatched_dates and all(f.status == "NOT_FOUND" for f in results.values()):
            box, date_val = unmatched_dates[0]
            raw_ocr_conf = float(box.get("confidence", 0.0))
            evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, is_ambiguous=True)
            results["MANUFACTURING_DATE"] = FieldCandidate(
                field_name="MANUFACTURING_DATE",
                display_name="Date of Manufacture",
                value=date_val,
                raw_value=box.get("text"),
                normalized_value=date_val,
                confidence=conf,
                raw_ocr_confidence=raw_ocr_conf,
                status="AMBIGUOUS",
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="UNLABELLED_DATE_AMBIGUOUS"
            )

        return results

    # -------------------------------------------------------------
    # 7-9. ENTITY EXTRACTION (MANUFACTURER, PACKER, IMPORTER)
    # -------------------------------------------------------------
    @classmethod
    def extract_entities(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, FieldCandidate]:
        missing_status, missing_reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": missing_reason} if missing_reason else {}

        results = {
            "MANUFACTURER": FieldCandidate(field_name="MANUFACTURER", display_name="Manufacturer Name & Address", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
            "PACKER": FieldCandidate(field_name="PACKER", display_name="Packer Name & Address", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
            "IMPORTER": FieldCandidate(field_name="IMPORTER", display_name="Importer Name & Address", status=missing_status, source_image_id=image_id, source_image_role=image_role, evidence=dict(missing_evidence)),
        }

        entity_configs = [
            ("MANUFACTURER", re.compile(r'\b(?:MANUFACTURED\s+&\s+MARKETED\s+BY|MANUFACTURED\s+(?:BY|AT)|MFD\.?\s+BY|MFG\.?\s+BY)\b', re.IGNORECASE)),
            ("PACKER", re.compile(r'\b(?:PACKED\s+(?:BY|AT)|PKD\.?\s+BY)\b', re.IGNORECASE)),
            ("IMPORTER", re.compile(r'\b(?:IMPORTED\s+(?:&\s+MARKETED\s+)?BY|IMPORTER\s*:?)\b', re.IGNORECASE)),
        ]

        for target_field, label_re in entity_configs:
            for box in boxes:
                text = box.get("text", "")
                if label_re.search(text):
                    # Multi-line address accumulation
                    matched_boxes = [box]
                    label_sub = label_re.sub("", text).strip().lstrip(":").strip()
                    accumulated_text = [label_sub] if label_sub else []

                    # Find vertically adjacent lines (multi-line address)
                    adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=300, max_y_gap=90)
                    for ab in adj_boxes:
                        ab_text = ab.get("text", "").strip()
                        # Stop if another major statutory label starts
                        if any(re.search(pat, ab_text, re.IGNORECASE) for pat in [r'\bMRP\b', r'\bNET\s+QTY\b', r'\bPKD\b', r'\bEXP\b', r'\bCONSUMER\s+CARE\b']):
                            break
                        accumulated_text.append(ab_text)
                        matched_boxes.append(ab)
                        if len(accumulated_text) >= 4:
                            break

                    combined_address = " ".join([t for t in accumulated_text if t]).strip()
                    if not combined_address and label_sub:
                        combined_address = label_sub
                    if not combined_address:
                        combined_address = text.strip()

                    raw_ocr_conf = sum(float(b.get("confidence", 0.0)) for b in matched_boxes) / max(len(matched_boxes), 1)
                    evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=len(matched_boxes))

                    results[target_field] = FieldCandidate(
                        field_name=target_field,
                        display_name=results[target_field].display_name,
                        value=combined_address,
                        raw_value=" \n ".join([b.get("text", "") for b in matched_boxes]),
                        normalized_value=combined_address,
                        confidence=conf,
                        raw_ocr_confidence=round(raw_ocr_conf, 4),
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="MULTI_LINE_ADDRESS_EXPANSION"
                    )
                    break

        return results

    # -------------------------------------------------------------
    # 10. CONSUMER CARE EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_consumer_care(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> FieldCandidate:
        field_name = "CONSUMER_CARE"
        display_name = "Consumer Care Details"

        label_re = re.compile(r'\b(?:CONSUMER\s+(?:CARE|CELL|HELPLINE)|CUSTOMER\s+(?:CARE|SUPPORT|SERVICE)|TOLL\s*FREE|HELP\s*LINE|FOR\s+COMPLAINTS\s+CONTACT)\b', re.IGNORECASE)
        phone_re = re.compile(r'(?:(?:1800|1860)[\s-]?\d{3}[\s-]?\d{3,4}|\b(?:0\d{2,4}[-\s]?)?\d{6,10}\b)')
        email_re = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

        matched_boxes = []
        extracted_parts = []

        # Find consumer care anchor
        anchor_box = None
        for box in boxes:
            text = box.get("text", "")
            if label_re.search(text):
                anchor_box = box
                matched_boxes.append(box)
                extracted_parts.append(text.strip())
                break

        # If anchor box exists, aggregate adjacent contact info
        if anchor_box:
            adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(anchor_box, boxes, max_x_gap=300, max_y_gap=100)
            for ab in adj_boxes:
                ab_text = ab.get("text", "").strip()
                if phone_re.search(ab_text) or email_re.search(ab_text) or "address" in ab_text.lower() or "care" in ab_text.lower():
                    matched_boxes.append(ab)
                    extracted_parts.append(ab_text)
                    if len(extracted_parts) >= 3:
                        break

            combined_val = " | ".join(dict.fromkeys(extracted_parts))
            raw_ocr_conf = sum(float(b.get("confidence", 0.0)) for b in matched_boxes) / max(len(matched_boxes), 1)
            evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
            status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
            conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=len(matched_boxes))

            return FieldCandidate(
                field_name=field_name,
                display_name=display_name,
                value=combined_val,
                raw_value=" \n ".join([b.get("text", "") for b in matched_boxes]),
                normalized_value=combined_val,
                confidence=conf,
                raw_ocr_confidence=round(raw_ocr_conf, 4),
                status=status,
                source_image_id=image_id,
                source_image_role=image_role,
                source_ocr_ids=evidence["source_ocr_ids"],
                evidence=evidence,
                bounding_box=evidence["enclosing_box"],
                extraction_method="CONTEXTUAL_CONTACT_GROUPING"
            )

        # Standalone toll-free or feedback email with contextual prefix
        for box in boxes:
            text = box.get("text", "")
            if re.search(r'\b(?:1800[-\s]?\d{3}[-\s]?\d{3,4}|feedback@|customercare@)\b', text, re.IGNORECASE):
                matched_boxes = [box]
                raw_ocr_conf = float(box.get("confidence", 0.0))
                evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, is_canonical_format=True)

                return FieldCandidate(
                    field_name=field_name,
                    display_name=display_name,
                    value=text.strip(),
                    raw_value=text,
                    normalized_value=text.strip(),
                    confidence=conf,
                    raw_ocr_confidence=raw_ocr_conf,
                    status=status,
                    source_image_id=image_id,
                    source_image_role=image_role,
                    source_ocr_ids=evidence["source_ocr_ids"],
                    evidence=evidence,
                    bounding_box=evidence["enclosing_box"],
                    extraction_method="TOLLFREE_OR_EMAIL_PATTERN"
                )

        missing_status, reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": reason} if reason else {}
        return FieldCandidate(
            field_name=field_name,
            display_name=display_name,
            status=missing_status,
            source_image_id=image_id,
            source_image_role=image_role,
            evidence=missing_evidence
        )

    # -------------------------------------------------------------
    # 11. COUNTRY OF ORIGIN EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_country_of_origin(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> FieldCandidate:
        field_name = "COUNTRY_OF_ORIGIN"
        display_name = "Country of Origin"

        country_re = re.compile(
            r'\b(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN|PRODUCT\s+OF|MANUFACTURED\s+IN)\s*[:.-]?\s*([A-Za-z\s]+)',
            re.IGNORECASE
        )

        for box in boxes:
            text = box.get("text", "")
            match = country_re.search(text)
            if match:
                country_str = match.group(1).strip()
                # Clean extraneous words if any
                country_clean = re.split(r'[,.\n\r]', country_str)[0].strip()
                if country_clean and len(country_clean) >= 3:
                    raw_ocr_conf = float(box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, is_canonical_format=True)

                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=country_clean.title(),
                        raw_value=box.get("text"),
                        normalized_value=country_clean.title(),
                        confidence=conf,
                        raw_ocr_confidence=raw_ocr_conf,
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="REGEX_COUNTRY_CONTEXT"
                    )

        # Multi-box: "Country of Origin:" on one line, "India" on adjacent line
        anchor_re = re.compile(r'\b(?:COUNTRY\s+OF\s+ORIGIN|MADE\s+IN)\b', re.IGNORECASE)
        for box in boxes:
            text = box.get("text", "")
            if anchor_re.search(text):
                adj_boxes = EvidenceMatcher.find_spatially_adjacent_boxes(box, boxes, max_x_gap=150, max_y_gap=40)
                if adj_boxes:
                    cand = adj_boxes[0]
                    c_clean = cand.get("text", "").strip()
                    if c_clean and len(c_clean) >= 3:
                        matched_boxes = [box, cand]
                        raw_ocr_conf = (float(box.get("confidence", 0.0)) + float(cand.get("confidence", 0.0))) / 2.0
                        evidence = EvidenceMatcher.build_evidence(matched_boxes, source_image_id=image_id, source_image_role=image_role)
                        status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                        conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True, supporting_tokens_count=2)

                        return FieldCandidate(
                            field_name=field_name,
                            display_name=display_name,
                            value=c_clean.title(),
                            raw_value=f"{text} {c_clean}",
                            normalized_value=c_clean.title(),
                            confidence=conf,
                            raw_ocr_confidence=raw_ocr_conf,
                            status=status,
                            source_image_id=image_id,
                            source_image_role=image_role,
                            source_ocr_ids=evidence["source_ocr_ids"],
                            evidence=evidence,
                            bounding_box=evidence["enclosing_box"],
                            extraction_method="SPATIAL_PROXIMITY_MERGE"
                        )

        missing_status, reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": reason} if reason else {}
        return FieldCandidate(
            field_name=field_name,
            display_name=display_name,
            status=missing_status,
            source_image_id=image_id,
            source_image_role=image_role,
            evidence=missing_evidence
        )

    # -------------------------------------------------------------
    # 12. PRODUCT NAME EXTRACTION
    # -------------------------------------------------------------
    @classmethod
    def extract_product_name(
        cls,
        boxes: List[Dict[str, Any]],
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_quality: Optional[Dict[str, Any]] = None
    ) -> FieldCandidate:
        field_name = "PRODUCT_NAME"
        display_name = "Product / Commodity Name"

        # 1. Explicit label cues: highest priority
        explicit_label_re = re.compile(
            r'\b(?:PRODUCT\s+NAME|NAME\s+OF\s+COMMODITY|COMMODITY|ITEM\s+NAME|BRAND\s+NAME|PRODUCT\s+TITLE)\s*[:.-]?\s*(.+)',
            re.IGNORECASE
        )
        for box in boxes:
            text = box.get("text", "").strip()
            match = explicit_label_re.search(text)
            if match:
                val = match.group(1).strip()
                if len(val) >= 2 and not cls._is_pure_promotional_or_statutory(val):
                    raw_ocr_conf = float(box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([box], source_image_id=image_id, source_image_role=image_role)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=True)
                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=val,
                        raw_value=text,
                        normalized_value=val,
                        confidence=conf,
                        raw_ocr_confidence=raw_ocr_conf,
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="EXPLICIT_PRODUCT_LABEL"
                    )

        # 2. Multi-signal candidate scoring (Front panel only)
        if image_role.lower() == "front" and boxes:
            scored_candidates = []
            heights = [b.get("bounding_box", {}).get("h", 0) for b in boxes if b.get("bounding_box", {}).get("h", 0) > 0]
            median_h = statistics.median(heights) if heights else 20.0

            for box in boxes:
                text = box.get("text", "").strip()
                if not text or len(text) < 3:
                    continue

                if cls._should_exclude_from_product_name(text):
                    continue

                score = 0
                bbox = box.get("bounding_box", {})
                y_pos = bbox.get("y", 0)
                box_h = bbox.get("h", 0)

                # Positive Signal: Position (top 40% of panel)
                if y_pos < 180:
                    score += 35
                elif y_pos < 300:
                    score += 20
                elif y_pos > 500:
                    score -= 25

                # Positive Signal: Prominent Size
                if box_h >= median_h * 1.5:
                    score += 30
                elif box_h >= median_h * 1.2:
                    score += 15

                # Positive Signal: Capitalization
                words = text.split()
                if text.isupper():
                    score += 20
                elif text.istitle():
                    score += 15

                # Positive Signal: Concise product title (1 to 5 words)
                if 1 <= len(words) <= 4:
                    score += 15
                elif len(words) > 7:
                    score -= 25

                # Positive Signal: Character length
                if 4 <= len(text) <= 35:
                    score += 10
                elif len(text) > 50:
                    score -= 30

                # Negative Signals: Promotional keywords
                if cls._has_promotional_keyword(text):
                    score -= 70

                # Negative Signals: Subtitle / category descriptors
                if re.search(r'\b(?:beverage|juice|pouch|carton|packaged|instant|ready\s+to\s+eat|snack|pure)\b', text, re.IGNORECASE):
                    score -= 35

                # Negative Signals: Percentage or digits
                if "%" in text or re.search(r'\b\d+\b', text):
                    score -= 35

                # Negative Signals: Trailing exclamation marks
                if text.endswith("!"):
                    score -= 25

                scored_candidates.append((score, box))

            if scored_candidates:
                scored_candidates.sort(key=lambda item: (-item[0], -float(item[1].get("confidence", 0.0))))
                best_score, best_box = scored_candidates[0]

                # Threshold requirement (Section 15):
                if best_score >= 35:
                    best_text = best_box.get("text", "").strip()
                    raw_ocr_conf = float(best_box.get("confidence", 0.0))
                    evidence = EvidenceMatcher.build_evidence([best_box], source_image_id=image_id, source_image_role=image_role)
                    conf = EvidenceMatcher.calculate_confidence(raw_ocr_conf, has_explicit_label=False, supporting_tokens_count=1)
                    status = "LOW_CONFIDENCE" if raw_ocr_conf < 0.55 else "FOUND"

                    return FieldCandidate(
                        field_name=field_name,
                        display_name=display_name,
                        value=best_text,
                        raw_value=best_text,
                        normalized_value=best_text,
                        confidence=round(conf * 0.90, 4),
                        raw_ocr_confidence=raw_ocr_conf,
                        status=status,
                        source_image_id=image_id,
                        source_image_role=image_role,
                        source_ocr_ids=evidence["source_ocr_ids"],
                        evidence=evidence,
                        bounding_box=evidence["enclosing_box"],
                        extraction_method="DETERMINISTIC_SCORING_PROMINENCE"
                    )

        # Fallback to missing status
        missing_status, reason = cls._determine_missing_field_status(image_quality)
        missing_evidence = {"reason": reason} if reason else {}
        return FieldCandidate(
            field_name=field_name,
            display_name=display_name,
            status=missing_status,
            source_image_id=image_id,
            source_image_role=image_role,
            evidence=missing_evidence
        )
