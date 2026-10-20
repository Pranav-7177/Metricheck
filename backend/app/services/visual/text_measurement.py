from typing import Dict, Any, Optional
from app.services.visual.evidence import VisualEvidenceStatus

class TextMeasurementService:
    """
    Computes text dimensions and determines physical font measurement status.
    Strictly prohibits fabricating physical millimeter measurements without valid calibration.
    """

    @classmethod
    def measure_declaration_text(
        cls,
        geometry: Dict[str, Any],
        calibration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes raw pixel geometry and calibration data.
        Returns font_height_mm, text_height_px, pixels_per_mm, and measurement_status.
        """
        raw_height_px = geometry.get("text_height_px", 0.0)
        raw_width_px = geometry.get("text_width_px", 0.0)
        perspective_score = geometry.get("perspective_score", 1.0)
        is_curved = geometry.get("is_curved_surface", False)

        is_calibrated = calibration.get("is_calibrated", False)
        pixels_per_mm = calibration.get("pixels_per_mm")
        calib_conf = calibration.get("calibration_confidence", 0.0)

        # Case 1: Surface or perspective distortion prevents reliable measurement
        if is_curved or perspective_score < 0.65:
            return {
                "text_height_px": raw_height_px,
                "text_width_px": raw_width_px,
                "font_height_mm": None,
                "pixels_per_mm": pixels_per_mm,
                "measurement_status": VisualEvidenceStatus.UNABLE_TO_VERIFY.value,
                "explanation": "The declaration region is significantly distorted by perspective. Capture the package more directly.",
                "recommendation": "Capture the package more directly."
            }

        # Case 2: Calibration is valid and sufficiently confident
        if is_calibrated and pixels_per_mm and pixels_per_mm > 0 and calib_conf >= 0.60:
            font_height_mm = round(raw_height_px / pixels_per_mm, 2)
            return {
                "text_height_px": raw_height_px,
                "text_width_px": raw_width_px,
                "font_height_mm": font_height_mm,
                "pixels_per_mm": pixels_per_mm,
                "measurement_status": VisualEvidenceStatus.MEASURABLE.value,
                "explanation": f"Calibrated font height measured at {font_height_mm:.1f} mm ({raw_height_px:.1f} px at {pixels_per_mm:.1f} px/mm).",
                "recommendation": None
            }

        # Case 3: No valid calibration reference
        return {
            "text_height_px": raw_height_px,
            "text_width_px": raw_width_px,
            "font_height_mm": None,
            "pixels_per_mm": None,
            "measurement_status": VisualEvidenceStatus.NOT_MEASURABLE.value,
            "explanation": "The declaration is readable, but its physical size could not be measured reliably because no valid calibration reference was available.",
            "recommendation": "Provide a known package dimension or calibrated reference."
        }
