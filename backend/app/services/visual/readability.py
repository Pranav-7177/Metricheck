import os
import cv2
import numpy as np
from typing import Dict, Any, Optional
from app.services.visual.evidence import ReadabilityStatus

class ReadabilityService:
    """
    Evaluates visual readability, local contrast, blur, and glare/shadow overlap
    specifically within the declaration bounding box ROI.
    """

    @classmethod
    def analyze_readability(
        cls,
        parsed_box: Optional[Dict[str, float]],
        image_input: Any = None,
        ocr_confidence: float = 0.90
    ) -> Dict[str, Any]:
        """
        Calculates blur, contrast, glare percentage, and shadow percentage on text ROI.
        image_input can be a filepath (str) or a numpy array (cv2 image).
        """
        blur_score = 100.0
        contrast_score = 1.0
        glare_overlap_pct = 0.0
        shadow_overlap_pct = 0.0

        img = None
        if isinstance(image_input, str) and os.path.exists(image_input):
            try:
                img = cv2.imread(image_input)
            except Exception:
                img = None
        elif isinstance(image_input, np.ndarray):
            img = image_input

        if img is not None and parsed_box:
            try:
                img_h, img_w = img.shape[:2]
                x1 = max(0, int(parsed_box.get("x1", 0)))
                y1 = max(0, int(parsed_box.get("y1", 0)))
                x2 = min(img_w, int(parsed_box.get("x2", img_w)))
                y2 = min(img_h, int(parsed_box.get("y2", img_h)))

                if x2 > x1 + 5 and y2 > y1 + 5:
                    roi = img[y1:y2, x1:x2]
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    
                    # Local blur in text ROI
                    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                    
                    # Local contrast
                    min_val, max_val = float(np.min(gray)), float(np.max(gray))
                    contrast_score = round((max_val - min_val) / max(max_val + min_val, 1e-5), 2)
                    
                    # Glare and shadow overlap in text ROI
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    v_channel = hsv[:, :, 2]
                    total_roi_px = max(roi.shape[0] * roi.shape[1], 1)
                    glare_px = np.sum(v_channel >= 245)
                    shadow_px = np.sum(v_channel <= 30)
                    
                    glare_overlap_pct = round(float((glare_px / total_roi_px) * 100.0), 1)
                    shadow_overlap_pct = round(float((shadow_px / total_roi_px) * 100.0), 1)
            except Exception:
                pass

        # Determine categorical readability
        is_glare_obscured = (glare_overlap_pct >= 70.0) or (glare_overlap_pct >= 30.0 and (contrast_score < 0.60 or ocr_confidence < 0.80))
        if is_glare_obscured:
            status = ReadabilityStatus.UNABLE_TO_VERIFY.value
            explanation = "Glare overlaps the declaration region and prevents reliable visual verification. Capture the package with reduced reflections."
            recommendation = "Capture image with reduced reflections."
        elif blur_score < 30.0 or ocr_confidence < 0.40:
            status = ReadabilityStatus.UNREADABLE.value
            explanation = "Text region is blurred or character edge contrast is degraded."
            recommendation = "Capture a sharper, well-lit close-up photograph of this declaration."
        elif (glare_overlap_pct >= 25.0 and contrast_score < 0.50) or ocr_confidence < 0.65 or contrast_score < 0.35:
            status = ReadabilityStatus.MARGINAL.value
            explanation = "Text is discernible but has minor glare reflections or reduced contrast."
            recommendation = "Capture image with balanced lighting and reduced reflections."
        else:
            status = ReadabilityStatus.READABLE.value
            explanation = "Text declaration is visually clear, sharp, and free of obscuring glare."
            recommendation = None


        return {
            "readability": status,
            "blur_score": round(blur_score, 1),
            "contrast_score": contrast_score,
            "glare_overlap_percentage": glare_overlap_pct,
            "shadow_overlap_percentage": shadow_overlap_pct,
            "explanation": explanation,
            "recommendation": recommendation
        }
