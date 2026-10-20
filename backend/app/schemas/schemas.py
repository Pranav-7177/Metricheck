from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.models import ComplianceState, ImageQualityStatus, ExtractionStatus

class CategoryBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class RuleBase(BaseModel):
    rule_id: str
    field_target: str
    requirement: str
    validation_type: str
    rule_reference: str
    version: str = "2024.1"
    effective_from: str = "2011-11-01"
    effective_to: Optional[str] = None
    is_mandatory: bool = True
    is_active: bool = True
    suggested_action: Optional[str] = None

class RuleResponse(RuleBase):
    id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class OCRBoxResponse(BaseModel):
    text: str
    confidence: float
    bounding_box: Dict[str, Any]
    line_number: Optional[int] = 1
    image_id: Optional[int] = None
    image_type: Optional[str] = "FRONT"

class OCRResultResponse(BaseModel):
    image_id: Optional[int] = None
    image_type: Optional[str] = "FRONT"
    full_text: str = ""
    boxes: List[OCRBoxResponse] = []
    total_detections: int = 0
    average_confidence: float = 0.0
    min_confidence: float = 0.0
    max_confidence: float = 0.0
    high_confidence_count: int = 0
    engine_name: str = "PaddleOCR-PP-OCRv6"
    processing_time_ms: float = 0.0
    attempt_count: int = 1
    preprocessed_used: bool = False
    status: str = "COMPLETED"
    error_message: Optional[str] = None

class ImageQualityResponse(BaseModel):
    image_id: int
    image_type: str
    file_path: str
    quality_status: ImageQualityStatus
    quality_score: float = 1.0
    blur_score: float
    brightness_score: float = 1.0
    glare_percentage: float = 0.0
    resolution_w: int
    resolution_h: int
    resolution_ok: bool = True
    preprocessing_applied: bool = False
    preprocessed_file_path: Optional[str] = None
    quality_notes: Optional[str] = None

class ImageQualityPreviewResponse(BaseModel):
    quality_status: ImageQualityStatus
    quality_decision: str = "ACCEPTABLE"
    quality_score: float = 1.0
    blur_score: float
    glare_score: float
    glare_percentage: float = 0.0
    lighting_score: float
    brightness_score: float = 1.0
    resolution_w: int
    resolution_h: int
    resolution_ok: bool = True
    perspective_skew: bool = False
    quality_notes: str
    retake_guidance: List[str] = []

class ScanQualityCheckResponse(BaseModel):
    scan_id: int
    overall_quality_status: ImageQualityStatus
    images: List[ImageQualityResponse]

class ScanOCRResponse(BaseModel):
    scan_id: int
    total_detections: int
    average_confidence: float
    ocr_engine: str
    results: List[OCRResultResponse]

class ScanImageResponse(BaseModel):
    id: int
    image_role: str
    image_type: Optional[str] = "FRONT"
    file_path: str
    preprocessed_file_path: Optional[str] = None
    original_filename: Optional[str] = None
    quality_status: ImageQualityStatus
    quality_score: Optional[float] = 1.0
    blur_score: float
    glare_score: float
    lighting_score: float
    resolution_w: int
    resolution_h: int
    quality_notes: Optional[str] = None
    preprocessing_status: Optional[str] = "NOT_REQUIRED"
    quality_decision: Optional[str] = "ACCEPTABLE"
    retake_guidance: Optional[List[str]] = None
    content_hash: Optional[str] = None
    perceptual_hash: Optional[str] = None
    is_duplicate: Optional[bool] = False
    duplicate_of_id: Optional[int] = None
    duplicate_type: Optional[str] = None
    duplicate_reason: Optional[str] = None
    ocr_status: Optional[str] = "PENDING"
    ocr_engine_used: Optional[str] = None
    ocr_confidence: Optional[float] = 0.0
    ocr_detections_count: Optional[int] = 0
    ocr_attempt_count: Optional[int] = 0
    ocr_raw_boxes: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)

class ExtractedFieldResponse(BaseModel):
    field_name: str
    display_name: str
    value: Optional[str] = None
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 0.0
    raw_ocr_confidence: float = 0.0
    status: str = "NOT_FOUND" # FOUND, NOT_FOUND, AMBIGUOUS, LOW_CONFIDENCE, UNABLE_TO_VERIFY
    source_image_id: Optional[int] = None
    source_image_role: Optional[str] = "front"
    source_ocr_ids: List[int] = []
    evidence: Dict[str, Any] = {}
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: str = "DETERMINISTIC_CONTEXT"
    has_conflict: bool = False
    alternate_candidates: List[Dict[str, Any]] = []
    estimated_font_height_mm: Optional[float] = None
    required_font_height_mm: Optional[float] = None
    measurement_confidence: Optional[str] = "UNCALIBRATED"
    visual_evidence: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class ScanExtractResponse(BaseModel):
    scan_id: int
    total_fields: int = 0
    fields: List[ExtractedFieldResponse] = []

class DeclarationResponse(BaseModel):
    id: int
    field_name: str
    display_name: str
    detected_value: Optional[str] = None
    normalized_value: Optional[str] = None
    raw_ocr_snippet: Optional[str] = None
    raw_value: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    extraction_method: Optional[str] = "DETERMINISTIC_CONTEXT"
    extraction_status: Optional[str] = "NOT_FOUND"
    field_confidence: Optional[float] = 0.0
    raw_ocr_confidence: Optional[float] = 0.0
    confidence: float # 0.0 to 1.0
    status: ComplianceState
    bounding_box: Optional[Dict[str, Any]] = None
    source_image_id: Optional[int] = None
    source_image_role: str
    source_ocr_ids: Optional[List[int]] = []
    evidence: Optional[Dict[str, Any]] = {}
    has_conflict: Optional[bool] = False
    alternate_candidates: Optional[List[Dict[str, Any]]] = []
    estimated_font_height_mm: Optional[float] = None
    required_font_height_mm: Optional[float] = None
    measurement_confidence: Optional[str] = "ESTIMATED"
    visual_evidence: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class RuleValidationResultResponse(BaseModel):
    id: int
    rule_id: int
    field_target: str
    expected_requirement: str
    detected_value: Optional[str] = None
    status: ComplianceState
    confidence: float
    reason: str
    suggested_action: Optional[str] = None
    rule_reference: str
    rule_version: str

    model_config = ConfigDict(from_attributes=True)

class ScanSummaryResponse(BaseModel):
    id: int
    product_name: str
    category_id: int
    category_name: Optional[str] = None
    created_at: datetime
    overall_status: ComplianceState
    compliance_score: float
    summary_verdict: Optional[str] = None
    is_calibrated: bool = False
    is_demo: bool = False
    images_count: int = 0
    scan_reliability: Optional[Dict[str, Any]] = None
    coverage_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class ScanDetailResponse(BaseModel):
    id: int
    product_name: str
    category_id: int
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    overall_status: ComplianceState
    compliance_score: float
    summary_verdict: Optional[str] = None
    is_calibrated: bool = False
    calibration_method: str = "uncalibrated_heuristic"
    pixels_per_mm: Optional[float] = None
    analysis_step: str = "COMPLETED"
    is_demo: bool = False
    scan_reliability: Optional[Dict[str, Any]] = None
    coverage_summary: Optional[Dict[str, Any]] = None
    
    images: List[ScanImageResponse] = []
    declarations: List[DeclarationResponse] = []
    rule_results: List[RuleValidationResultResponse] = []
    latest_evaluation: Optional["ScanEvaluationResponse"] = None

    model_config = ConfigDict(from_attributes=True)

class RuleResultResponse(BaseModel):
    id: Optional[int] = None
    rule_id: str
    field_name: str
    severity: str
    status: str
    reason: str
    suggested_action: Optional[str] = None
    rule_source: str
    declaration_id: Optional[int] = None
    detected_value: Optional[str] = None
    normalized_value: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class ComplianceSummaryResponse(BaseModel):
    overall_status: str
    total_rules: int
    passed_rules: int
    failed_rules: int
    warning_rules: int
    not_verifiable_rules: int
    not_applicable_rules: int
    critical_errors: int
    summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ScanEvaluationResponse(BaseModel):
    scan_id: int
    overall_status: str
    evaluated_at: datetime
    summary: ComplianceSummaryResponse
    results: List[RuleResultResponse] = []

    model_config = ConfigDict(from_attributes=True)

class DashboardStatsResponse(BaseModel):
    total_scans: int
    verified_compliant: int
    potential_non_compliance: int
    unable_to_verify: int
    review_required: int
    compliance_rate_percent: float
    recent_scans: List[ScanSummaryResponse]
