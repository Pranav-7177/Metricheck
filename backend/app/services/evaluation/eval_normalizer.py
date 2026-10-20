"""Evaluation Normalizer for Ground-Truth Comparison.

Non-destructive comparison layer that evaluates MetriCheck extraction candidates
against ground-truth annotations without mutating original OCR text, coordinates,
confidences, or database records.

Evaluates field states:
- CORRECT
- INCORRECT
- NOT_FOUND
- LOW_CONFIDENCE
- AMBIGUOUS
- UNABLE_TO_VERIFY
- NOT_APPLICABLE
"""

import re
from typing import Any, Dict, Optional, Tuple


class EvaluationNormalizer:
    """Non-destructive ground-truth evaluation normalizer."""

    @staticmethod
    def normalize_mrp(val: Optional[str]) -> Optional[float]:
        """Extracts numeric price value from string representation."""
        if not val:
            return None
        # Remove currency symbols, commas, whitespace, and 'inclusive' clauses
        cleaned = re.sub(r'[₹Rs\.,\s\(\)]', '', str(val), flags=re.IGNORECASE)
        match = re.search(r'(\d+(?:\.\d{1,2})?)', str(val).replace(',', ''))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def normalize_quantity(val: Optional[str]) -> Optional[Tuple[float, str]]:
        """Normalizes quantity value to (base_amount, standard_unit)."""
        if not val:
            return None
        match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', str(val))
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2).lower().strip()

        # Standardize units: mass to grams, volume to milliliters, length to meters
        if unit in ("kg", "kgs", "kilogram", "kilograms"):
            return (amount * 1000.0, "g")
        elif unit in ("g", "gm", "gms", "gram", "grams"):
            return (amount, "g")
        elif unit in ("l", "ltr", "liter", "litres", "litre"):
            return (amount * 1000.0, "ml")
        elif unit in ("ml", "milliliter", "millilitre"):
            return (amount, "ml")
        elif unit in ("m", "meter", "metre"):
            return (amount, "m")
        return (amount, unit)

    @staticmethod
    def normalize_text_tokens(val: Optional[str]) -> set:
        """Extracts normalized alphanumeric tokens for fuzzy entity comparison."""
        if not val:
            return set()
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(val).lower())
        tokens = set(cleaned.split())
        # Filter generic legal metrology boilerplate words
        stop_words = {"pvt", "ltd", "limited", "private", "inc", "co", "and", "by", "plot", "sector", "road"}
        return tokens - stop_words

    @classmethod
    def compare_field(
        cls,
        field_name: str,
        ground_truth: Optional[str],
        candidate: Optional[Any],
        gt_presence: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compares system output candidate against ground truth.
        Accepts optional gt_presence from human-verified ground truth taxonomy:
        - LEGIBLE: text is clearly readable on physical package
        - ILLEGIBLE: text is faded/smeared/degraded on physical package
        - OBSCURED: text is physically covered by store sticker, tape, fold, etc.
        - ABSENT: legally required declaration is physically missing from package
        - NOT_APPLICABLE: declaration does not legally apply to this commodity category

        Returns evaluation dict with:
        - evaluation_status: CORRECT, INCORRECT, NOT_FOUND, LOW_CONFIDENCE, AMBIGUOUS, UNABLE_TO_VERIFY, NOT_APPLICABLE
        - is_match: bool
        - ground_truth: str or None
        - ground_truth_presence: str
        - detected_value: str or None
        - candidate_status: str
        """
        cand_val = getattr(candidate, "value", None) if candidate else None
        cand_status = getattr(candidate, "status", "NOT_FOUND") if candidate else "NOT_FOUND"
        cand_conf = getattr(candidate, "confidence", 0.0) if candidate else 0.0

        # Infer presence state if not explicitly supplied
        effective_presence = (gt_presence.upper() if gt_presence else None) or (
            "LEGIBLE" if ground_truth is not None and str(ground_truth).strip().lower() not in ("null", "none", "")
            else "NOT_APPLICABLE"
        )

        # Case 1: Ground truth presence is NOT_APPLICABLE (commodity exempt / field does not apply)
        if effective_presence == "NOT_APPLICABLE":
            if cand_status == "NOT_FOUND" or not cand_val:
                return {
                    "field_name": field_name,
                    "evaluation_status": "NOT_APPLICABLE",
                    "is_match": True,
                    "ground_truth": None,
                    "ground_truth_presence": "NOT_APPLICABLE",
                    "detected_value": None,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": "Declaration legally not applicable for this commodity and correctly not detected."
                }
            else:
                return {
                    "field_name": field_name,
                    "evaluation_status": "INCORRECT",
                    "is_match": False,
                    "ground_truth": None,
                    "ground_truth_presence": "NOT_APPLICABLE",
                    "detected_value": cand_val,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": f"False positive: field was extracted ({cand_val}) but is NOT_APPLICABLE for this commodity."
                }

        # Case 2: Ground truth presence is ABSENT (physically omitted by manufacturer)
        if effective_presence == "ABSENT":
            if cand_status == "NOT_FOUND" or not cand_val:
                return {
                    "field_name": field_name,
                    "evaluation_status": "CORRECT",
                    "is_match": True,
                    "ground_truth": None,
                    "ground_truth_presence": "ABSENT",
                    "detected_value": None,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": "Declaration physically absent on package and correctly identified as not found."
                }
            else:
                return {
                    "field_name": field_name,
                    "evaluation_status": "INCORRECT",
                    "is_match": False,
                    "ground_truth": None,
                    "ground_truth_presence": "ABSENT",
                    "detected_value": cand_val,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": f"False positive: field was extracted ({cand_val}) but is physically ABSENT on package."
                }

        # Case 3: Ground truth presence is ILLEGIBLE or OBSCURED (physical package defect/occlusion)
        if effective_presence in ("ILLEGIBLE", "OBSCURED"):
            if cand_status in ("UNABLE_TO_VERIFY", "LOW_CONFIDENCE", "NOT_FOUND"):
                return {
                    "field_name": field_name,
                    "evaluation_status": "UNABLE_TO_VERIFY",
                    "is_match": True,
                    "ground_truth": ground_truth,
                    "ground_truth_presence": effective_presence,
                    "detected_value": cand_val,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": f"Physical packaging is {effective_presence}; pipeline correctly indicated optical uncertainty ({cand_status})."
                }
            elif cand_val and ground_truth and str(ground_truth).strip().lower() in str(cand_val).strip().lower():
                return {
                    "field_name": field_name,
                    "evaluation_status": "CORRECT",
                    "is_match": True,
                    "ground_truth": ground_truth,
                    "ground_truth_presence": effective_presence,
                    "detected_value": cand_val,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": f"Declaration was read correctly despite packaging being {effective_presence}."
                }
            else:
                return {
                    "field_name": field_name,
                    "evaluation_status": "INCORRECT",
                    "is_match": False,
                    "ground_truth": ground_truth,
                    "ground_truth_presence": effective_presence,
                    "detected_value": cand_val,
                    "candidate_status": cand_status,
                    "confidence": cand_conf,
                    "reason": f"Erroneous extraction on {effective_presence} package: detected '{cand_val}'."
                }

        # Case 4: Ground truth exists and is LEGIBLE on package. Check candidate uncertainty states
        if cand_status == "UNABLE_TO_VERIFY":
            return {
                "field_name": field_name,
                "evaluation_status": "UNABLE_TO_VERIFY",
                "is_match": False,
                "ground_truth": ground_truth,
                "ground_truth_presence": "LEGIBLE",
                "detected_value": cand_val,
                "candidate_status": cand_status,
                "confidence": cand_conf,
                "reason": "Image quality or optical evidence was insufficient to verify declaration reliably."
            }

        if cand_status == "LOW_CONFIDENCE":
            return {
                "field_name": field_name,
                "evaluation_status": "LOW_CONFIDENCE",
                "is_match": False,
                "ground_truth": ground_truth,
                "ground_truth_presence": "LEGIBLE",
                "detected_value": cand_val,
                "candidate_status": cand_status,
                "confidence": cand_conf,
                "reason": f"Low OCR detection confidence ({cand_conf:.2f}); flagged for visual confirmation."
            }

        if cand_status == "AMBIGUOUS":
            return {
                "field_name": field_name,
                "evaluation_status": "AMBIGUOUS",
                "is_match": False,
                "ground_truth": ground_truth,
                "ground_truth_presence": "LEGIBLE",
                "detected_value": cand_val,
                "candidate_status": cand_status,
                "confidence": cand_conf,
                "reason": "Ambiguous or conflicting values detected across package panels."
            }

        if cand_status == "NOT_FOUND" or not cand_val:
            return {
                "field_name": field_name,
                "evaluation_status": "NOT_FOUND",
                "is_match": False,
                "ground_truth": ground_truth,
                "ground_truth_presence": "LEGIBLE",
                "detected_value": None,
                "candidate_status": cand_status,
                "confidence": cand_conf,
                "reason": "Declaration was present in ground truth but not detected by OCR/extractor."
            }

        # Case 3: Candidate has FOUND status; verify semantic equivalence
        is_match = False
        if field_name == "MRP":
            gt_num = cls.normalize_mrp(ground_truth)
            cand_num = cls.normalize_mrp(cand_val)
            if gt_num is not None and cand_num is not None:
                # Tolerant to decimal rounding (e.g. 149 vs 149.00)
                is_match = abs(gt_num - cand_num) < 0.01

        elif field_name == "NET_QUANTITY":
            gt_qty = cls.normalize_quantity(ground_truth)
            cand_qty = cls.normalize_quantity(cand_val)
            if gt_qty and cand_qty:
                amt_match = abs(gt_qty[0] - cand_qty[0]) < 0.01
                unit_match = gt_qty[1] == cand_qty[1]
                is_match = amt_match and unit_match

        elif field_name in ("MANUFACTURING_DATE", "PACKING_DATE", "EXPIRY_DATE", "BEST_BEFORE"):
            # Compare normalized digits and date words
            gt_clean = re.sub(r'[^a-zA-Z0-9]', '', str(ground_truth).lower())
            cand_clean = re.sub(r'[^a-zA-Z0-9]', '', str(cand_val).lower())
            is_match = (gt_clean in cand_clean) or (cand_clean in gt_clean) or (gt_clean == cand_clean)

        else:
            # Generic text entities (Product Name, Manufacturer, Packer, Importer, Consumer Care, Country)
            gt_tokens = cls.normalize_text_tokens(ground_truth)
            cand_tokens = cls.normalize_text_tokens(cand_val)
            if gt_tokens and cand_tokens:
                overlap = len(gt_tokens & cand_tokens)
                union = len(gt_tokens | cand_tokens)
                jaccard = overlap / union if union > 0 else 0.0
                recall = overlap / len(gt_tokens) if len(gt_tokens) > 0 else 0.0
                # Match passes if recall >= 0.5 or jaccard >= 0.4
                is_match = recall >= 0.5 or jaccard >= 0.4
            else:
                is_match = str(ground_truth).strip().lower() in str(cand_val).strip().lower()

        eval_status = "CORRECT" if is_match else "INCORRECT"
        return {
            "field_name": field_name,
            "evaluation_status": eval_status,
            "is_match": is_match,
            "ground_truth": ground_truth,
            "ground_truth_presence": "LEGIBLE",
            "detected_value": cand_val,
            "candidate_status": cand_status,
            "confidence": cand_conf,
            "reason": "Value matches ground truth declaration." if is_match else f"Value mismatch: expected '{ground_truth}', extracted '{cand_val}'."
        }
