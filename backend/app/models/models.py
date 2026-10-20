import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.database.session import Base

class ComplianceState(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    VERIFIED_COMPLIANT = "VERIFIED_COMPLIANT"
    POTENTIAL_NON_COMPLIANCE = "POTENTIAL_NON_COMPLIANCE"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"
    NOT_FOUND = "NOT_FOUND"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

class RuleSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

class ImageType(str, enum.Enum):
    FRONT = "FRONT"
    BACK = "BACK"
    SIDE = "SIDE"
    LEFT_SIDE = "LEFT_SIDE"
    RIGHT_SIDE = "RIGHT_SIDE"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    CLOSE_UP = "CLOSE_UP"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

class ImageQualityStatus(str, enum.Enum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    DEGRADED = "DEGRADED"
    POOR = "POOR"
    UNSUITABLE = "UNSUITABLE"
    CRITICAL_ISSUES = "CRITICAL_ISSUES"

class ExtractionStatus(str, enum.Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True) # e.g. 'food_grocery', 'cosmetics'
    name = Column(String(100), nullable=False) # e.g. 'Food / Grocery'
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    rules = relationship("ComplianceRule", back_populates="category_rel")
    scans = relationship("Scan", back_populates="category_rel")

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(50), unique=True, nullable=False, index=True) # e.g. "LMR-2011-R6-MRP"
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True) # None means all/general
    field_target = Column(String(50), nullable=False) # "mrp", "net_quantity", "manufacturer", etc.
    requirement = Column(Text, nullable=False)
    validation_type = Column(String(50), nullable=False) # "presence", "format", "physical_measurement", "unit_sale_price"
    rule_reference = Column(String(100), nullable=False) # e.g. "Rule 6(1)(e), Legal Metrology (PC) Rules 2011"
    version = Column(String(20), default="2024.1")
    effective_from = Column(String(30), default="2011-11-01")
    effective_to = Column(String(30), nullable=True)
    is_mandatory = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    suggested_action = Column(Text, nullable=True)

    category_rel = relationship("ProductCategory", back_populates="rules")
    validation_results = relationship("RuleValidationResult", back_populates="rule_rel")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    overall_status = Column(Enum(ComplianceState), default=ComplianceState.REVIEW_REQUIRED)
    compliance_score = Column(Float, default=0.0) # 0 to 100%
    summary_verdict = Column(Text, nullable=True)
    
    # Calibration details
    is_calibrated = Column(Boolean, default=False)
    calibration_method = Column(String(50), default="uncalibrated_heuristic") # coin, credit_card, manual_dpi, heuristic
    pixels_per_mm = Column(Float, nullable=True)
    
    # Multi-step analysis status
    analysis_step = Column(String(50), default="COMPLETED") # UPLOADING, QUALITY_CHECK, PREPROCESSING, OCR, EXTRACTION, RULES, VISUAL_CHECKS, REPORT_GENERATION, COMPLETED
    is_demo = Column(Boolean, default=False)

    # Master Prompt 10 Reliability & Coverage summaries
    scan_reliability = Column(JSON, nullable=True)
    coverage_summary = Column(JSON, nullable=True)

    category_rel = relationship("ProductCategory", back_populates="scans")
    images = relationship("ScanImage", back_populates="scan_rel", cascade="all, delete-orphan")
    declarations = relationship("ExtractedDeclaration", back_populates="scan_rel", cascade="all, delete-orphan")
    rule_results = relationship("RuleValidationResult", back_populates="scan_rel", cascade="all, delete-orphan")
    ocr_records = relationship("OCRRecord", back_populates="scan_rel", cascade="all, delete-orphan")
    evaluations = relationship("ComplianceEvaluation", back_populates="scan_rel", cascade="all, delete-orphan")

class ScanImage(Base):
    __tablename__ = "scan_images"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    image_role = Column(String(20), default="front") # front, back, side, close_up, left_side, right_side, top, bottom, unknown
    image_type = Column(String(30), default="FRONT") # FRONT, BACK, SIDE, LEFT_SIDE, RIGHT_SIDE, TOP, BOTTOM, CLOSE_UP, OTHER, UNKNOWN
    file_path = Column(String(500), nullable=False)
    preprocessed_file_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    
    # Image Quality metrics
    quality_status = Column(Enum(ImageQualityStatus), default=ImageQualityStatus.GOOD)
    quality_score = Column(Float, default=1.0)
    blur_score = Column(Float, default=100.0) # Laplacian variance
    glare_score = Column(Float, default=0.0)  # Over-exposed region %
    lighting_score = Column(Float, default=100.0)
    resolution_w = Column(Integer, default=0)
    resolution_h = Column(Integer, default=0)
    quality_notes = Column(Text, nullable=True)
    preprocessing_status = Column(String(50), default="NOT_REQUIRED") # NOT_REQUIRED, APPLIED, FAILED
    quality_decision = Column(String(30), default="ACCEPTABLE") # ACCEPTABLE, DEGRADED, UNSUITABLE
    retake_guidance = Column(JSON, nullable=True) # list of actionable guidance strings

    # Deterministic Identity and Duplicate Relationships
    content_hash = Column(String(64), nullable=True, index=True) # SHA-256
    perceptual_hash = Column(String(64), nullable=True) # dHash
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, nullable=True)
    duplicate_type = Column(String(30), nullable=True) # EXACT, NEAR_DUPLICATE
    duplicate_reason = Column(Text, nullable=True)

    # OCR Execution Metrics
    ocr_status = Column(String(50), default="PENDING") # PENDING, COMPLETED, NO_TEXT_DETECTED, FAILED
    ocr_engine_used = Column(String(50), nullable=True)
    ocr_confidence = Column(Float, default=0.0)
    ocr_detections_count = Column(Integer, default=0)
    ocr_attempt_count = Column(Integer, default=0)
    ocr_raw_boxes = Column(JSON, nullable=True)

    scan_rel = relationship("Scan", back_populates="images")
    ocr_records = relationship("OCRRecord", back_populates="image_rel", cascade="all, delete-orphan")

class OCRRecord(Base):
    __tablename__ = "ocr_records"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("scan_images.id"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    text = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    bounding_box = Column(JSON, nullable=False) # {"x1": int, "y1": int, "x2": int, "y2": int, "x": int, "y": int, "w": int, "h": int}
    line_number = Column(Integer, default=1)
    engine_name = Column(String(50), default="PaddleOCR-PP-OCRv6")
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    image_rel = relationship("ScanImage", back_populates="ocr_records")
    scan_rel = relationship("Scan", back_populates="ocr_records")


class ExtractedDeclaration(Base):
    __tablename__ = "extracted_declarations"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    field_name = Column(String(50), nullable=False) # mrp, net_quantity, mfg_date, expiry_date, consumer_care, manufacturer_name, manufacturer_address, unit_sale_price
    display_name = Column(String(100), nullable=False) # "Maximum Retail Price (MRP)"
    
    detected_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    raw_ocr_snippet = Column(Text, nullable=True)
    raw_value = Column(Text, nullable=True)
    unit = Column(String(30), nullable=True)
    currency = Column(String(10), nullable=True)
    extraction_method = Column(String(50), default="DETERMINISTIC_CONTEXT")
    extraction_status = Column(String(30), default="NOT_FOUND")
    field_confidence = Column(Float, default=0.0)
    raw_ocr_confidence = Column(Float, default=0.0)
    source_image_id = Column(Integer, ForeignKey("scan_images.id"), nullable=True)
    source_ocr_ids = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    has_conflict = Column(Boolean, default=False)
    alternate_candidates = Column(JSON, nullable=True)
    
    confidence = Column(Float, default=0.0) # 0.0 to 1.0 (e.g. 0.94 -> 94%)
    status = Column(Enum(ComplianceState), default=ComplianceState.UNABLE_TO_VERIFY)
    
    # Bounding box & visual metrics
    bounding_box = Column(JSON, nullable=True) # {"x": ..., "y": ..., "w": ..., "h": ...}
    source_image_role = Column(String(20), default="front")
    
    # Physical font height measurement
    estimated_font_height_mm = Column(Float, nullable=True)
    required_font_height_mm = Column(Float, nullable=True)
    measurement_confidence = Column(String(30), default="ESTIMATED") # ESTIMATED, VERIFIED, UNCALIBRATED

    @property
    def visual_evidence(self):
        if self.evidence and isinstance(self.evidence, dict):
            return self.evidence.get("visual_evidence")
        return None

    scan_rel = relationship("Scan", back_populates="declarations")


class RuleValidationResult(Base):
    __tablename__ = "rule_validation_results"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("compliance_rules.id"), nullable=False)
    
    field_target = Column(String(50), nullable=False)
    expected_requirement = Column(Text, nullable=False)
    detected_value = Column(Text, nullable=True)
    
    status = Column(Enum(ComplianceState), nullable=False)
    confidence = Column(Float, default=0.0)
    reason = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    rule_reference = Column(String(100), nullable=False)
    rule_version = Column(String(20), default="2024.1")

    scan_rel = relationship("Scan", back_populates="rule_results")
    rule_rel = relationship("ComplianceRule", back_populates="validation_results")

class ComplianceEvaluation(Base):
    __tablename__ = "compliance_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    overall_status = Column(String(50), nullable=False) # COMPLIANT, NON_COMPLIANT, REVIEW_REQUIRED
    total_rules = Column(Integer, default=0)
    passed_rules = Column(Integer, default=0)
    failed_rules = Column(Integer, default=0)
    warning_rules = Column(Integer, default=0)
    not_verifiable_rules = Column(Integer, default=0)
    not_applicable_rules = Column(Integer, default=0)
    critical_errors = Column(Integer, default=0)
    summary = Column(Text, nullable=True)

    scan_rel = relationship("Scan", back_populates="evaluations")
    results = relationship("ComplianceRuleResult", back_populates="evaluation_rel", cascade="all, delete-orphan")

class ComplianceRuleResult(Base):
    __tablename__ = "compliance_rule_results"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("compliance_evaluations.id"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    rule_id = Column(String(100), nullable=False, index=True)
    field_name = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False) # CRITICAL, ERROR, WARNING, INFO
    status = Column(String(30), nullable=False) # PASS, FAIL, WARNING, NOT_VERIFIABLE, NOT_APPLICABLE
    reason = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    rule_source = Column(String(200), nullable=False)
    declaration_id = Column(Integer, ForeignKey("extracted_declarations.id"), nullable=True)
    detected_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)

    evaluation_rel = relationship("ComplianceEvaluation", back_populates="results")
    declaration_rel = relationship("ExtractedDeclaration")
