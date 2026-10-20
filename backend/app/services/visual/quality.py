from typing import Dict, Any, Optional
from app.services.image_processing.quality import ImageQualityService

class VisualQualityService:
    """
    Quality bridge service providing image-level quality telemetry
    for visual compliance verification.
    """

    @classmethod
    def evaluate_image_quality(cls, file_path: Optional[str]) -> Dict[str, Any]:
        """Runs computer-vision quality checks on the target image."""
        if not file_path:
            return {
                "blur_score": 100.0,
                "glare_score": 0.0,
                "lighting_score": 100.0,
                "resolution_w": 1000,
                "resolution_h": 1000,
                "quality_status": "GOOD",
                "quality_notes": "Synthesized or missing image path; default quality metrics assigned."
            }

        return ImageQualityService.evaluate_image_file(file_path)
