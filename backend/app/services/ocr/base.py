from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    """
    Standardized bounding box representation for package text detections.
    Supports both pixel coordinates (original image frame) and normalized
    relative coordinates (0.0 to 1.0) for responsive frontend overlays.
    """
    x1: int
    y1: int
    x2: int
    y2: int
    x: int
    y: int
    w: int
    h: int
    x_rel: Optional[float] = None
    y_rel: Optional[float] = None
    w_rel: Optional[float] = None
    h_rel: Optional[float] = None
    polygon: Optional[List[List[float]]] = None  # [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class OCRBoxResult(BaseModel):
    """
    Individual text detection with confidence and spatial coordinates.
    """
    text: str
    confidence: float  # 0.0 to 1.0
    bounding_box: Dict[str, Any]
    line_number: Optional[int] = 1
    image_id: Optional[int] = None
    image_type: Optional[str] = "FRONT"

class OCRResult(BaseModel):
    """
    Normalized multi-detection OCR result for a single packaged commodity image.
    Contains per-token detections, bounding boxes, aggregate confidence telemetry,
    and execution metadata without any fabricated text.
    """
    image_id: Optional[int] = None
    image_type: Optional[str] = "FRONT"
    full_text: str = ""
    boxes: List[OCRBoxResult] = Field(default_factory=list)
    total_detections: int = 0
    average_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0
    high_confidence_count: int = 0
    engine_name: str = "PaddleOCR-PP-OCRv6"
    processing_time_ms: float = 0.0
    attempt_count: int = 1
    preprocessed_used: bool = False
    retry_reason: Optional[str] = None
    status: str = "COMPLETED"  # COMPLETED, NO_TEXT_DETECTED, FAILED
    error_message: Optional[str] = None

class BaseOCREngine(ABC):
    """
    Abstract interface for pre-trained OCR engines.
    Allows local engines (RapidOCR, EasyOCR) or cloud vision models (Gemini)
    to be cleanly plugged in without altering downstream extraction or rule evaluation.
    """

    @abstractmethod
    def extract_text(
        self,
        image_path: str,
        image_id: Optional[int] = None,
        image_type: Optional[str] = "FRONT",
        **kwargs
    ) -> OCRResult:
        """
        Extracts real text detections, bounding boxes, and confidence scores from an image.
        Never fabricates mock text.
        """
        pass
