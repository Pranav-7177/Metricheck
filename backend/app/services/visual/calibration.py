from typing import Dict, Any, Optional
from app.services.visual.evidence import CalibrationMethod

class CalibrationService:
    """
    Deterministic camera calibration and scale determination service.
    CRITICAL RULE: Pixels never equal physical millimeters without verified calibration.
    """

    REFERENCE_STANDARDS: Dict[str, float] = {
        "coin_rupee_5": 23.0,       # Standard 5 INR coin diameter = 23.0 mm
        "coin_rupee_10": 27.0,      # Standard 10 INR coin diameter = 27.0 mm
        "coin_rupee_1": 19.0,       # Standard 1 INR coin diameter = 19.0 mm
        "coin_rupee_2": 25.0,       # Standard 2 INR coin diameter = 25.0 mm
        "id_card_width": 85.6,      # ISO/IEC 7810 ID-1 standard width = 85.6 mm
        "id_card_height": 53.98,    # ISO/IEC 7810 ID-1 standard height = 53.98 mm
        "credit_card_width": 85.6,  # Credit/Debit card width = 85.6 mm
        "standard_ruler_10mm": 10.0 # 10 mm calibration ruler marker
    }

    MIN_ACCEPTABLE_CONFIDENCE: float = 0.60

    @classmethod
    def calibrate_from_reference(
        cls,
        reference_type: str,
        detected_pixel_dimension: float,
        detection_confidence: float = 0.90
    ) -> Dict[str, Any]:
        """
        Method A: Known physical reference object in the photograph.
        """
        ref_standard = cls.REFERENCE_STANDARDS.get(reference_type.lower())
        if not ref_standard or detected_pixel_dimension <= 0 or detection_confidence < cls.MIN_ACCEPTABLE_CONFIDENCE:
            return cls.get_uncalibrated_result(
                notes="Reference standard invalid, unread, or confidence below required threshold."
            )

        pixels_per_mm = round(detected_pixel_dimension / ref_standard, 4)
        return {
            "is_calibrated": True,
            "calibration_method": CalibrationMethod.KNOWN_REFERENCE_OBJECT.value,
            "pixels_per_mm": pixels_per_mm,
            "calibration_confidence": round(min(1.0, detection_confidence), 2),
            "source": f"Reference standard '{reference_type}' ({ref_standard} mm)",
            "notes": f"Calibrated via known reference object ({ref_standard} mm -> {detected_pixel_dimension:.1f} px)."
        }

    @classmethod
    def calibrate_from_package_dimension(
        cls,
        known_dimension_mm: float,
        detected_pixel_dimension: float,
        dimension_axis: str = "height",
        confidence: float = 0.85
    ) -> Dict[str, Any]:
        """
        Method B: User-supplied known package physical dimension metadata.
        """
        if known_dimension_mm <= 0 or detected_pixel_dimension <= 0 or confidence < cls.MIN_ACCEPTABLE_CONFIDENCE:
            return cls.get_uncalibrated_result(
                notes="Known package dimension or detected container boundary is invalid."
            )

        pixels_per_mm = round(detected_pixel_dimension / known_dimension_mm, 4)
        return {
            "is_calibrated": True,
            "calibration_method": CalibrationMethod.KNOWN_PACKAGE_DIMENSION.value,
            "pixels_per_mm": pixels_per_mm,
            "calibration_confidence": round(min(1.0, confidence), 2),
            "source": f"Declared container {dimension_axis} ({known_dimension_mm} mm)",
            "notes": f"Calibrated via package dimension metadata ({known_dimension_mm} mm -> {detected_pixel_dimension:.1f} px)."
        }

    @classmethod
    def calibrate_from_pixels_per_mm(
        cls,
        pixels_per_mm: float,
        calibration_method: str = CalibrationMethod.KNOWN_REFERENCE_OBJECT.value,
        confidence: float = 0.90,
        source: str = "Pre-calibrated camera scale"
    ) -> Dict[str, Any]:
        """
        Direct calibrated scale input.
        """
        if pixels_per_mm <= 0 or confidence < cls.MIN_ACCEPTABLE_CONFIDENCE:
            return cls.get_uncalibrated_result(notes="Supplied pixels_per_mm is invalid or confidence below threshold.")
        return {
            "is_calibrated": True,
            "calibration_method": calibration_method,
            "pixels_per_mm": round(pixels_per_mm, 4),
            "calibration_confidence": round(min(1.0, confidence), 2),
            "source": source,
            "notes": f"Calibrated via scale ({pixels_per_mm:.2f} px/mm)."
        }

    @classmethod
    def get_uncalibrated_result(cls, notes: str = "No valid calibration reference available.") -> Dict[str, Any]:
        """
        Method C: No calibration available.
        Ensures physical font size is marked NOT_MEASURABLE and never fabricated.
        """
        return {
            "is_calibrated": False,
            "calibration_method": CalibrationMethod.UNCALIBRATED.value,
            "pixels_per_mm": None,
            "calibration_confidence": 0.0,
            "source": "None",
            "notes": notes
        }

