import enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

class VisualEvidenceStatus(str, enum.Enum):
    """
    Visual evidence verification states (strictly separated from extraction states).
    """
    MEASURABLE = "MEASURABLE"           # Physical dimensions can be estimated with calibrated reliability
    READABLE_ONLY = "READABLE_ONLY"     # Text is visually clear, but physical font size cannot be calibrated
    NOT_MEASURABLE = "NOT_MEASURABLE"   # Text exists, but no trustworthy calibration reference is available
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY" # Visual evidence inadequate due to blur, glare, perspective distortion
    AMBIGUOUS = "AMBIGUOUS"             # Conflicting visual measurements detected across panels

class ReadabilityStatus(str, enum.Enum):
    READABLE = "READABLE"               # Clear text with adequate contrast and sharp edges
    MARGINAL = "MARGINAL"               # Discernible but minor glare or reduced contrast
    UNREADABLE = "UNREADABLE"           # Heavy blur or low OCR confidence
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY" # Glare/shadow overlap > 30% obscuring characters

class VisibilityStatus(str, enum.Enum):
    FULLY_VISIBLE = "FULLY_VISIBLE"       # Entire bounding box cleanly within camera frame
    PARTIALLY_VISIBLE = "PARTIALLY_VISIBLE" # Bounding box clipped or touches image borders
    OBSCURED = "OBSCURED"                 # Occluded by glare, reflection, or obstruction
    OUT_OF_FRAME = "OUT_OF_FRAME"         # Completely cut off or out of camera view

class PlacementRegion(str, enum.Enum):
    TOP_LEFT = "TOP_LEFT"
    TOP_CENTER = "TOP_CENTER"
    TOP_RIGHT = "TOP_RIGHT"
    CENTER_LEFT = "CENTER_LEFT"
    CENTER = "CENTER"
    CENTER_RIGHT = "CENTER_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_CENTER = "BOTTOM_CENTER"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    UNKNOWN = "UNKNOWN"

class CalibrationMethod(str, enum.Enum):
    KNOWN_REFERENCE_OBJECT = "KNOWN_REFERENCE_OBJECT" # Coin, ID card, calibration target
    KNOWN_PACKAGE_DIMENSION = "KNOWN_PACKAGE_DIMENSION" # Known container height/width
    UNCALIBRATED = "UNCALIBRATED"                       # No valid calibration reference

@dataclass
class VisualEvidence:
    """
    Structured visual compliance and measurement evidence payload.
    Preserves raw pixel measurements alongside calibrated physical dimensions.
    """
    field: str
    image_id: Optional[int] = None
    source_image_role: str = "front"
    bbox: Optional[Dict[str, Any]] = None
    
    # Raw geometric measurements in image pixels
    text_height_px: float = 0.0
    text_width_px: float = 0.0
    orientation_deg: float = 0.0
    area_px: float = 0.0
    perspective_score: float = 1.0  # 1.0 = undistorted rectangle, < 0.65 = distorted
    is_curved_surface: bool = False
    
    # Calibrated physical measurements
    font_height_mm: Optional[float] = None
    pixels_per_mm: Optional[float] = None
    calibration_method: str = "UNCALIBRATED"
    calibration_confidence: float = 0.0
    
    # Visual quality and environment indicators
    blur_score: float = 100.0
    contrast_score: float = 1.0
    glare_overlap_percentage: float = 0.0
    shadow_overlap_percentage: float = 0.0
    
    # Categorical visual states
    readability: str = ReadabilityStatus.READABLE.value
    visibility: str = VisibilityStatus.FULLY_VISIBLE.value
    placement: str = PlacementRegion.CENTER.value
    normalized_x: float = 0.5
    normalized_y: float = 0.5
    
    # Overall visual classification
    visual_status: str = VisualEvidenceStatus.NOT_MEASURABLE.value
    
    # Inspector explainability & recommendations
    explanation: str = ""
    recommendation: Optional[str] = None
    alternate_visual_evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualEvidence":
        if not data:
            return cls(field="UNKNOWN")
        from dataclasses import fields
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

