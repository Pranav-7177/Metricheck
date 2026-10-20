import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.database.session import get_db
from app.models.models import (
    Scan, ScanImage, ExtractedDeclaration, RuleValidationResult,
    ProductCategory, ComplianceRule, ComplianceState, ImageQualityStatus,
    ImageType, OCRRecord, ComplianceEvaluation, ComplianceRuleResult
)
from app.schemas.schemas import (
    ScanSummaryResponse, ScanDetailResponse,
    ScanQualityCheckResponse, ImageQualityResponse, ImageQualityPreviewResponse,
    ScanOCRResponse, OCRResultResponse, OCRBoxResponse,
    ExtractedFieldResponse, ScanExtractResponse,
    RuleResultResponse, ComplianceSummaryResponse, ScanEvaluationResponse
)
from app.services.image_processing.quality import ImageQualityService
from app.services.image_processing.image_validator import ImageValidator, ImageValidationError
from app.services.ocr.engine import PretrainedOCREngine
from app.services.extraction.declarations import DeclarationExtractorService
from app.services.rules.engine import ComplianceRuleEngine
from app.services.compliance.rule_engine import ComplianceEngine
from app.services.measurement.calibration import PhysicalMeasurementService
from app.services.reporting.generator import ReportGeneratorService

router = APIRouter(prefix="/scans", tags=["Scans"])
ocr_engine = PretrainedOCREngine()

def get_local_path_from_url(url_or_path: str) -> str:
    """Resolves URL path or relative path to absolute disk path."""
    if not url_or_path:
        return ""
    if url_or_path.startswith("/uploads/"):
        rel = url_or_path[len("/uploads/"):]
        return os.path.join(settings.UPLOAD_DIR, rel.replace("/", os.sep))
    elif url_or_path.startswith("uploads/"):
        rel = url_or_path[len("uploads/"):]
        return os.path.join(settings.UPLOAD_DIR, rel.replace("/", os.sep))
    elif os.path.isabs(url_or_path):
        return url_or_path
    return os.path.join(settings.UPLOAD_DIR, url_or_path)

@router.get("", response_model=List[ScanSummaryResponse])
def list_scans(
    status: Optional[ComplianceState] = Query(None, description="Filter by compliance state"),
    category_id: Optional[int] = Query(None, description="Filter by product category"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent packaging commodity compliance scans."""
    query = db.query(Scan)
    if status:
        query = query.filter(Scan.overall_status == status)
    if category_id:
        query = query.filter(Scan.category_id == category_id)

    db_scans = query.order_by(desc(Scan.created_at)).offset(skip).limit(limit).all()
    
    res = []
    for s in db_scans:
        res.append(ScanSummaryResponse(
            id=s.id,
            product_name=s.product_name,
            category_id=s.category_id,
            category_name=s.category_rel.name if s.category_rel else "General",
            created_at=s.created_at,
            overall_status=s.overall_status,
            compliance_score=s.compliance_score,
            summary_verdict=s.summary_verdict,
            is_calibrated=s.is_calibrated,
            is_demo=s.is_demo,
            images_count=len(s.images)
        ))
    return res

@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan_details(scan_id: int, db: Session = Depends(get_db)):
    """Retrieve complete audit-style report for a scan, including images, declarations, rule checks, and latest compliance evaluation."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")
    
    resp = ScanDetailResponse.model_validate(scan)
    resp.category_name = scan.category_rel.name if scan.category_rel else "General"

    latest_eval = db.query(ComplianceEvaluation).filter(ComplianceEvaluation.scan_id == scan_id).order_by(desc(ComplianceEvaluation.evaluated_at)).first()
    if latest_eval:
        summary_resp = ComplianceSummaryResponse(
            overall_status=latest_eval.overall_status,
            total_rules=latest_eval.total_rules,
            passed_rules=latest_eval.passed_rules,
            failed_rules=latest_eval.failed_rules,
            warning_rules=latest_eval.warning_rules,
            not_verifiable_rules=latest_eval.not_verifiable_rules,
            not_applicable_rules=latest_eval.not_applicable_rules,
            critical_errors=latest_eval.critical_errors,
            summary=latest_eval.summary
        )
        rule_resps = [
            RuleResultResponse(
                id=r.id,
                rule_id=r.rule_id,
                field_name=r.field_name,
                severity=r.severity,
                status=r.status,
                reason=r.reason,
                suggested_action=r.suggested_action,
                rule_source=r.rule_source,
                declaration_id=r.declaration_id,
                detected_value=r.detected_value,
                normalized_value=r.normalized_value,
                evidence=r.evidence
            )
            for r in latest_eval.results
        ]
        resp.latest_evaluation = ScanEvaluationResponse(
            scan_id=scan.id,
            overall_status=latest_eval.overall_status,
            evaluated_at=latest_eval.evaluated_at,
            summary=summary_resp,
            results=rule_resps
        )

    return resp

@router.post("", response_model=ScanDetailResponse)
async def create_scan(
    product_name: str = Form(..., description="Product name and variant"),
    category_id: int = Form(..., description="Selected product category ID"),
    calibration_method: Optional[str] = Form("uncalibrated_heuristic"),
    pixels_per_mm: Optional[float] = Form(None),
    front_image: UploadFile = File(..., description="Primary / Principal Display Panel photograph"),
    back_image: Optional[UploadFile] = File(None, description="Back panel photograph (optional)"),
    side_image: Optional[UploadFile] = File(None, description="Side panel photograph (optional)"),
    left_side_image: Optional[UploadFile] = File(None, description="Left side panel photograph (optional)"),
    right_side_image: Optional[UploadFile] = File(None, description="Right side panel photograph (optional)"),
    top_image: Optional[UploadFile] = File(None, description="Top panel photograph (optional)"),
    bottom_image: Optional[UploadFile] = File(None, description="Bottom panel photograph (optional)"),
    close_up_image: Optional[UploadFile] = File(None, description="Close-up declaration panel photograph (optional)"),
    db: Session = Depends(get_db)
):
    """
    Executes the uncertainty-aware Legal Metrology inspection analysis pipeline:
    1. Upload validation & EXIF orientation normalization
    2. Exact and near-duplicate detection
    3. Quality Check & retake guidance (blur, glare, resolution, shadows, contrast)
    4. Image Preprocessing (when beneficial)
    5. Multi-image Pretrained OCR with bounded retry
    6. Mandatory Declaration Extraction with conflict preservation
    7. Category-Specific Versioned Rule Validation
    8. Physical Font Measurement & Calibration Check
    9. Explainable Report Generation with Scan Reliability and Coverage Summaries
    """
    # 1. Validate Category
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid product category ID.")

    # 2. Ensure upload storage directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    scan_uid = str(uuid.uuid4())[:8]
    scan_upload_dir = os.path.join(settings.UPLOAD_DIR, scan_uid)
    os.makedirs(scan_upload_dir, exist_ok=True)

    # 3. Create initial Scan record in DB
    is_calibrated = bool(pixels_per_mm and pixels_per_mm > 0)
    scan = Scan(
        product_name=product_name.strip(),
        category_id=category_id,
        overall_status=ComplianceState.REVIEW_REQUIRED,
        compliance_score=0.0,
        is_calibrated=is_calibrated,
        calibration_method=calibration_method or "uncalibrated_heuristic",
        pixels_per_mm=pixels_per_mm,
        analysis_step="UPLOADING",
        is_demo=False,
        created_at=datetime.utcnow()
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # 4. Read and validate uploaded images
    image_slots = [
        ("front", front_image),
        ("back", back_image),
        ("side", side_image),
        ("left_side", left_side_image),
        ("right_side", right_side_image),
        ("top", top_image),
        ("bottom", bottom_image),
        ("close_up", close_up_image),
    ]

    validated_uploads = []
    for role, upload in image_slots:
        if not upload or not upload.filename:
            continue

        try:
            content = await upload.read()
        except Exception:
            try:
                content = upload.file.read()
            except Exception:
                content = b""

        if not content:
            if role == "front":
                raise HTTPException(status_code=400, detail="Primary front image is empty (0 bytes).")
            continue

        ext = os.path.splitext(upload.filename)[1].lower()
        if not ext:
            ext = ".jpg"

        filename = f"{role}_{uuid.uuid4().hex[:6]}{ext}"
        target_path = os.path.join(scan_upload_dir, filename)

        try:
            val_res = ImageValidator.validate_and_save_upload(
                file_bytes=content,
                filename=upload.filename,
                target_path=target_path
            )
            validated_uploads.append({
                "role": role,
                "upload_filename": upload.filename,
                "filename": filename,
                "target_path": target_path,
                "validation": val_res
            })
        except ImageValidationError as e:
            if role == "front":
                raise HTTPException(status_code=400, detail=f"Image validation failed: {str(e)}")
            # For non-primary images, skip safely without crashing the scan pipeline
            continue

    if not validated_uploads:
        raise HTTPException(status_code=400, detail="No valid images could be decoded for this scan.")

    # 5. Detect exact and near-duplicates across the batch
    meta_for_dups = [
        {
            "id": idx + 1,
            "content_hash": v["validation"]["content_hash"],
            "perceptual_hash": v["validation"]["perceptual_hash"],
            "width": v["validation"]["width"],
            "height": v["validation"]["height"],
        }
        for idx, v in enumerate(validated_uploads)
    ]
    annotated_dups = ImageValidator.detect_duplicates(meta_for_dups)

    saved_images_info = []
    ocr_results = []
    quality_evaluations = []
    ocr_by_image_id = {}

    for idx, item in enumerate(validated_uploads):
        role = item["role"]
        filename = item["filename"]
        target_path = item["target_path"]
        val_res = item["validation"]
        dup_info = annotated_dups[idx]

        prep_filename = f"preprocessed_{filename}"
        prep_path = os.path.join(scan_upload_dir, prep_filename)

        # Run CV quality pipeline (with retake guidance and decision tier)
        quality = ImageQualityService.run_quality_pipeline(target_path, prep_path)
        quality_evaluations.append(quality)

        relative_path = f"/uploads/{scan_uid}/{filename}"
        relative_prep_path = f"/uploads/{scan_uid}/{prep_filename}" if quality.get("preprocessing_applied") else None

        # Resolve duplicate of DB ID
        dup_of_idx = dup_info.get("duplicate_of_id")
        dup_of_db_id = saved_images_info[dup_of_idx - 1].id if (dup_of_idx and 1 <= dup_of_idx <= len(saved_images_info)) else None

        img_record = ScanImage(
            scan_id=scan.id,
            image_role=role,
            image_type=ImageValidator.normalize_role(role),
            file_path=relative_path,
            preprocessed_file_path=relative_prep_path,
            original_filename=item["upload_filename"],
            quality_status=quality["quality_status"],
            quality_score=quality.get("quality_score", 1.0),
            blur_score=quality["blur_score"],
            glare_score=quality["glare_score"],
            lighting_score=quality["lighting_score"],
            resolution_w=val_res["width"],
            resolution_h=val_res["height"],
            quality_notes=quality["quality_notes"],
            preprocessing_status="APPLIED" if quality.get("preprocessing_applied") else "NOT_REQUIRED",
            quality_decision=quality.get("quality_decision", "ACCEPTABLE"),
            retake_guidance=quality.get("retake_guidance", []),
            content_hash=val_res["content_hash"],
            perceptual_hash=val_res["perceptual_hash"],
            is_duplicate=dup_info.get("is_duplicate", False),
            duplicate_of_id=dup_of_db_id,
            duplicate_type=dup_info.get("duplicate_type"),
            duplicate_reason=dup_info.get("duplicate_reason")
        )
        db.add(img_record)
        db.commit()
        db.refresh(img_record)

        # OCR Execution: If exact duplicate of an earlier image, safely reuse its OCR result
        is_exact_dup = dup_info.get("is_duplicate") and dup_info.get("duplicate_type") == "EXACT" and dup_of_db_id in ocr_by_image_id
        if is_exact_dup:
            parent_ocr = ocr_by_image_id[dup_of_db_id]
            reused_boxes = [
                OCRBoxResponse(
                    text=b.text,
                    confidence=b.confidence,
                    bounding_box=b.bounding_box,
                    line_number=b.line_number,
                    image_id=img_record.id,
                    image_type=img_record.image_type
                )
                for b in parent_ocr.boxes
            ]
            ocr_res = OCRResultResponse(
                image_id=img_record.id,
                image_type=img_record.image_type,
                full_text=parent_ocr.full_text,
                boxes=reused_boxes,
                total_detections=parent_ocr.total_detections,
                average_confidence=parent_ocr.average_confidence,
                min_confidence=parent_ocr.min_confidence,
                max_confidence=parent_ocr.max_confidence,
                high_confidence_count=parent_ocr.high_confidence_count,
                engine_name=parent_ocr.engine_name,
                processing_time_ms=0.0,
                attempt_count=1,
                preprocessed_used=False,
                status="COMPLETED"
            )
        else:
            ocr_res = ocr_engine.extract_text(
                image_path=target_path,
                image_id=img_record.id,
                image_type=img_record.image_type,
                preprocessed_path=prep_path
            )

        ocr_results.append(ocr_res)
        ocr_by_image_id[img_record.id] = ocr_res

        # Persist OCR detections into ocr_records table
        for box in ocr_res.boxes:
            ocr_rec = OCRRecord(
                image_id=img_record.id,
                scan_id=scan.id,
                text=box.text,
                confidence=box.confidence,
                bounding_box=box.bounding_box,
                line_number=box.line_number,
                engine_name=ocr_res.engine_name,
                attempt_number=ocr_res.attempt_count
            )
            db.add(ocr_rec)

        # Update ScanImage with OCR execution summary
        img_record.ocr_status = ocr_res.status
        img_record.ocr_engine_used = ocr_res.engine_name
        img_record.ocr_confidence = ocr_res.average_confidence
        img_record.ocr_detections_count = ocr_res.total_detections
        img_record.ocr_attempt_count = ocr_res.attempt_count
        img_record.ocr_raw_boxes = [b.model_dump() for b in ocr_res.boxes]
        db.commit()

        saved_images_info.append(img_record)

    db.commit()

    # 6. Extract Declarations with duplicate and quality contexts
    img_qualities = {
        img.id: {
            "blur_score": img.blur_score,
            "glare_score": img.glare_score,
            "overall_status": img.quality_status,
            "quality_score": img.quality_score
        }
        for img in saved_images_info
    }
    calib_contexts = None
    if is_calibrated and pixels_per_mm and pixels_per_mm > 0:
        calib_contexts = {
            img.id: {
                "pixels_per_mm": pixels_per_mm,
                "calibration_method": calibration_method or "KNOWN_REFERENCE_OBJECT",
                "confidence": 0.95
            }
            for img in saved_images_info
        }
    img_paths = {
        img.id: os.path.join(scan_upload_dir, os.path.basename(img.file_path))
        for img in saved_images_info
    }
    img_dimensions = {
        img.id: (img.resolution_w, img.resolution_h)
        for img in saved_images_info
    }
    duplicates_by_id = {
        img.id: {
            "is_duplicate": img.is_duplicate,
            "duplicate_of_id": img.duplicate_of_id,
            "duplicate_type": img.duplicate_type
        }
        for img in saved_images_info
    }

    extracted_data = DeclarationExtractorService.extract_all_declarations(
        ocr_results=ocr_results,
        category_code=category.code,
        source_image_role="front",
        image_qualities=img_qualities,
        calibration_contexts=calib_contexts,
        image_paths=img_paths,
        image_dimensions=img_dimensions,
        duplicates_info=duplicates_by_id
    )

    db_declarations = []
    for decl in extracted_data:
        d_record = ExtractedDeclaration(
            scan_id=scan.id,
            field_name=decl.get("canonical_field_name") or decl["field_name"],
            display_name=decl["display_name"],
            detected_value=decl["detected_value"],
            normalized_value=decl["normalized_value"],
            raw_value=decl.get("raw_value"),
            raw_ocr_snippet=decl.get("raw_ocr_snippet"),
            unit=decl.get("unit"),
            currency=decl.get("currency"),
            extraction_method=decl.get("extraction_method", "DETERMINISTIC_CONTEXT"),
            extraction_status=decl.get("extraction_status", "NOT_FOUND"),
            field_confidence=decl.get("field_confidence", decl["confidence"]),
            raw_ocr_confidence=decl.get("raw_ocr_confidence", 0.0),
            confidence=decl["confidence"],
            status=decl["status"],
            bounding_box=decl.get("bounding_box"),
            source_image_id=decl.get("source_image_id"),
            source_image_role=decl.get("source_image_role", "front"),
            source_ocr_ids=decl.get("source_ocr_ids", []),
            evidence=decl.get("evidence", {}),
            has_conflict=decl.get("has_conflict", False),
            alternate_candidates=decl.get("alternate_candidates", []),
            estimated_font_height_mm=decl.get("estimated_font_height_mm"),
            required_font_height_mm=decl.get("required_font_height_mm"),
            measurement_confidence=decl.get("measurement_confidence", "ESTIMATED")
        )
        db.add(d_record)
        db_declarations.append(d_record)

    db.commit()

    # 7. Retrieve rules and evaluate compliance
    rules = db.query(ComplianceRule).filter(
        ComplianceRule.is_active == True,
        (ComplianceRule.category_id == category.id) | (ComplianceRule.category_id == None)
    ).all()

    rule_eval_results = ComplianceRuleEngine.evaluate_rules(
        rules=rules,
        extracted_declarations=extracted_data,
        category_code=category.code
    )

    for r_res in rule_eval_results:
        rule_db_rec = RuleValidationResult(
            scan_id=scan.id,
            rule_id=r_res["rule_id"],
            field_target=r_res["field_target"],
            expected_requirement=r_res["expected_requirement"],
            detected_value=r_res["detected_value"],
            status=r_res["status"],
            confidence=r_res["confidence"],
            reason=r_res["reason"],
            suggested_action=r_res["suggested_action"],
            rule_reference=r_res["rule_reference"],
            rule_version=r_res["rule_version"]
        )
        db.add(rule_db_rec)

    # 7b. Evaluate Compliance with ComplianceEngine
    comp_eval = ComplianceEngine.evaluate_declarations(db_declarations)
    summary_data = comp_eval["summary"]
    now = datetime.utcnow()
    m4_evaluation = ComplianceEvaluation(
        scan_id=scan.id,
        evaluated_at=now,
        overall_status=comp_eval["overall_status"],
        total_rules=summary_data["total_rules"],
        passed_rules=summary_data["passed"],
        failed_rules=summary_data["failed"],
        warning_rules=summary_data["warnings"],
        not_verifiable_rules=summary_data["not_verifiable"],
        not_applicable_rules=summary_data["not_applicable"],
        critical_errors=sum(1 for r in comp_eval["results"] if r.get("severity") in ("CRITICAL", "ERROR") and r.get("status") == "FAIL"),
        summary=f"Evaluated {summary_data['total_rules']} rules: {summary_data['passed']} PASS, {summary_data['failed']} FAIL, {summary_data['warnings']} WARNING, {summary_data['not_verifiable']} NOT_VERIFIABLE, {summary_data['not_applicable']} NOT_APPLICABLE."
    )
    db.add(m4_evaluation)
    db.flush()

    decl_by_f = {d.field_name.upper(): d for d in db_declarations}
    for r in comp_eval["results"]:
        target_d = decl_by_f.get(r["field_name"].upper())
        cr_rec = ComplianceRuleResult(
            evaluation_id=m4_evaluation.id,
            scan_id=scan.id,
            rule_id=r["rule_id"],
            field_name=r["field_name"],
            severity=r.get("severity", "ERROR"),
            status=r["status"],
            reason=r.get("reason") or r.get("message") or "",
            suggested_action=r.get("suggested_action"),
            rule_source=r.get("rule_source") or r.get("rule_reference") or "APPROVED_RULE_REFERENCE",
            declaration_id=target_d.id if target_d else None,
            detected_value=r.get("field_value") or (target_d.detected_value if target_d else None),
            normalized_value=target_d.normalized_value if target_d else None,
            evidence=r.get("evidence") or (target_d.evidence if target_d else None)
        )
        db.add(cr_rec)

    db.commit()

    # 8. Generate explainable synthesis report with coverage and reliability
    report = ReportGeneratorService.generate_overall_assessment(
        rule_results=rule_eval_results,
        image_qualities=quality_evaluations,
        product_name=product_name,
        category_name=category.name,
        declarations=db_declarations,
        images=saved_images_info,
        ocr_results=ocr_results
    )

    # 9. Update scan final status
    scan.overall_status = report["overall_status"]
    scan.compliance_score = report["compliance_score"]
    scan.summary_verdict = report["summary_verdict"]
    scan.scan_reliability = report.get("scan_reliability")
    scan.coverage_summary = report.get("coverage_summary")
    scan.analysis_step = "COMPLETED"
    db.commit()
    db.refresh(scan)

    resp = ScanDetailResponse.model_validate(scan)
    resp.category_name = category.name
    return resp

@router.post("/{scan_id}/quality-check", response_model=ScanQualityCheckResponse)
def run_scan_quality_check(scan_id: int, db: Session = Depends(get_db)):
    """
    Executes computer vision quality analysis (blur, glare, brightness, resolution)
    across all uploaded package photographs. Preprocesses images with CLAHE/denoising
    if optical quality requires enhancement.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    if not scan.images:
        raise HTTPException(status_code=400, detail="Scan has no images uploaded for quality checking.")

    scan.analysis_step = "QUALITY_CHECK"
    db.commit()

    overall_status = ImageQualityStatus.GOOD
    quality_responses = []

    for img in scan.images:
        local_path = get_local_path_from_url(img.file_path)
        if not os.path.exists(local_path):
            continue

        dir_name = os.path.dirname(local_path)
        base_name = os.path.basename(local_path)
        prep_path = os.path.join(dir_name, f"preprocessed_{base_name}")

        q_res = ImageQualityService.run_quality_pipeline(local_path, prep_path)

        # Update DB record
        img.quality_status = q_res["quality_status"]
        img.quality_score = q_res.get("quality_score", 1.0)
        img.blur_score = q_res["blur_score"]
        img.glare_score = q_res["glare_score"]
        img.lighting_score = q_res["lighting_score"]
        img.resolution_w = q_res["resolution_w"]
        img.resolution_h = q_res["resolution_h"]
        img.quality_notes = q_res["quality_notes"]

        if q_res.get("preprocessing_applied"):
            img.preprocessing_status = "APPLIED"
            scan_uid = os.path.basename(dir_name)
            img.preprocessed_file_path = f"/uploads/{scan_uid}/preprocessed_{base_name}"
        else:
            img.preprocessing_status = "NOT_REQUIRED"

        if q_res["quality_status"] in (ImageQualityStatus.POOR, ImageQualityStatus.CRITICAL_ISSUES):
            overall_status = ImageQualityStatus.POOR
        elif q_res["quality_status"] == ImageQualityStatus.ACCEPTABLE and overall_status != ImageQualityStatus.POOR:
            overall_status = ImageQualityStatus.ACCEPTABLE

        quality_responses.append(ImageQualityResponse(
            image_id=img.id,
            image_type=img.image_type or img.image_role.upper(),
            file_path=img.file_path,
            quality_status=img.quality_status,
            quality_score=img.quality_score,
            blur_score=img.blur_score,
            brightness_score=q_res.get("brightness_score", 1.0),
            glare_percentage=q_res.get("glare_percentage", 0.0),
            resolution_w=img.resolution_w,
            resolution_h=img.resolution_h,
            resolution_ok=q_res.get("resolution_ok", True),
            preprocessing_applied=bool(q_res.get("preprocessing_applied")),
            preprocessed_file_path=img.preprocessed_file_path,
            quality_notes=img.quality_notes
        ))

    db.commit()
    return ScanQualityCheckResponse(
        scan_id=scan.id,
        overall_quality_status=overall_status,
        images=quality_responses
    )

@router.post("/{scan_id}/ocr", response_model=ScanOCRResponse)
def run_scan_ocr(
    scan_id: int,
    confidence_threshold: Optional[float] = Query(None, description="Override minimum confidence threshold"),
    db: Session = Depends(get_db)
):
    """
    Executes real Pre-Trained OCR (RapidOCR) on each image linked to the scan.
    Returns per-token detections, coordinates, and confidence scores without any mock text.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    if not scan.images:
        raise HTTPException(status_code=400, detail="Scan has no images to process OCR.")

    scan.analysis_step = "OCR"
    db.commit()

    # Clear prior OCR records for fresh re-run
    db.query(OCRRecord).filter(OCRRecord.scan_id == scan_id).delete()
    db.commit()

    all_ocr_results = []
    total_detections_sum = 0
    confidences_list = []

    for img in scan.images:
        local_path = get_local_path_from_url(img.file_path)
        prep_path = get_local_path_from_url(img.preprocessed_file_path) if img.preprocessed_file_path else None

        ocr_res = ocr_engine.extract_text(
            image_path=local_path,
            image_id=img.id,
            image_type=img.image_type or img.image_role.upper(),
            preprocessed_path=prep_path,
            confidence_threshold=confidence_threshold
        )

        # Persist OCRRecord rows
        for b in ocr_res.boxes:
            ocr_rec = OCRRecord(
                image_id=img.id,
                scan_id=scan.id,
                text=b.text,
                confidence=b.confidence,
                bounding_box=b.bounding_box,
                line_number=b.line_number,
                engine_name=ocr_res.engine_name,
                attempt_number=ocr_res.attempt_count
            )
            db.add(ocr_rec)

        # Update ScanImage metrics
        img.ocr_status = ocr_res.status
        img.ocr_engine_used = ocr_res.engine_name
        img.ocr_confidence = ocr_res.average_confidence
        img.ocr_detections_count = ocr_res.total_detections
        img.ocr_attempt_count = ocr_res.attempt_count
        img.ocr_raw_boxes = [b.model_dump() for b in ocr_res.boxes]

        total_detections_sum += ocr_res.total_detections
        if ocr_res.boxes:
            confidences_list.extend([b.confidence for b in ocr_res.boxes])

        # Build response schema
        boxes_resp = [
            OCRBoxResponse(
                text=b.text,
                confidence=b.confidence,
                bounding_box=b.bounding_box,
                line_number=b.line_number,
                image_id=b.image_id,
                image_type=b.image_type
            )
            for b in ocr_res.boxes
        ]

        all_ocr_results.append(OCRResultResponse(
            image_id=img.id,
            image_type=img.image_type or img.image_role.upper(),
            full_text=ocr_res.full_text,
            boxes=boxes_resp,
            total_detections=ocr_res.total_detections,
            average_confidence=ocr_res.average_confidence,
            min_confidence=ocr_res.min_confidence,
            max_confidence=ocr_res.max_confidence,
            high_confidence_count=ocr_res.high_confidence_count,
            engine_name=ocr_res.engine_name,
            processing_time_ms=ocr_res.processing_time_ms,
            attempt_count=ocr_res.attempt_count,
            preprocessed_used=ocr_res.preprocessed_used,
            status=ocr_res.status,
            error_message=ocr_res.error_message
        ))

    db.commit()

    overall_avg_conf = round(sum(confidences_list) / len(confidences_list), 4) if confidences_list else 0.0

    return ScanOCRResponse(
        scan_id=scan.id,
        total_detections=total_detections_sum,
        average_confidence=overall_avg_conf,
        ocr_engine=ocr_engine.engine_name,
        results=all_ocr_results
    )

@router.post("/{scan_id}/extract", response_model=ScanExtractResponse)
def extract_scan_declarations(
    scan_id: int,
    db: Session = Depends(get_db)
):
    """
    Staged Milestone 3 Extraction Endpoint:
    Reads persisted OCR detections across all panels for the given scan,
    runs the deterministic field extraction and spatial evidence matching pipeline,
    persists structured ExtractedDeclaration records, and returns them.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    if not scan.images:
        raise HTTPException(status_code=400, detail="Scan has no images to extract declarations from.")

    # Retrieve persisted OCR records grouped by image
    image_boxes_map = []
    total_ocr_records = 0
    for img in scan.images:
        ocr_recs = db.query(OCRRecord).filter(OCRRecord.image_id == img.id).all()
        total_ocr_records += len(ocr_recs)
        boxes = [
            {
                "id": rec.id,
                "text": rec.text,
                "confidence": rec.confidence,
                "bounding_box": rec.bounding_box,
                "line_number": rec.line_number,
                "image_id": rec.image_id,
                "image_type": img.image_type or img.image_role.upper()
            }
            for rec in ocr_recs
        ]
        image_boxes_map.append({
            "image_id": img.id,
            "image_role": (img.image_role or "front").lower(),
            "image_type": img.image_type or img.image_role.upper(),
            "boxes": boxes,
            "quality": {
                "blur_score": img.blur_score,
                "glare_score": img.glare_score,
                "overall_status": img.quality_status,
                "quality_score": img.quality_score
            }
        })

    # Run extraction across panels
    extracted_fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)

    # Clear prior declarations for fresh extraction
    db.query(ExtractedDeclaration).filter(ExtractedDeclaration.scan_id == scan_id).delete()
    db.commit()

    fields_response = []
    for fc in extracted_fields:
        if fc.status == "FOUND":
            comp_status = ComplianceState.VERIFIED_COMPLIANT
        elif fc.status == "NOT_FOUND":
            comp_status = ComplianceState.NOT_FOUND
        elif fc.status in ("UNABLE_TO_VERIFY", "LOW_CONFIDENCE"):
            comp_status = ComplianceState.UNABLE_TO_VERIFY
        else: # AMBIGUOUS
            comp_status = ComplianceState.REVIEW_REQUIRED

        d_record = ExtractedDeclaration(
            scan_id=scan.id,
            field_name=fc.field_name,
            display_name=fc.display_name,
            detected_value=fc.value,
            normalized_value=fc.normalized_value,
            raw_value=fc.raw_value,
            raw_ocr_snippet=fc.raw_value,
            unit=fc.unit,
            currency=fc.currency,
            confidence=fc.confidence,
            field_confidence=fc.confidence,
            raw_ocr_confidence=fc.raw_ocr_confidence,
            status=comp_status,
            extraction_status=fc.status,
            bounding_box=fc.bounding_box,
            source_image_id=fc.source_image_id,
            source_image_role=fc.source_image_role or "front",
            source_ocr_ids=fc.source_ocr_ids,
            evidence=fc.evidence,
            extraction_method=fc.extraction_method,
            has_conflict=fc.has_conflict,
            alternate_candidates=fc.alternate_candidates
        )
        db.add(d_record)

        fields_response.append(ExtractedFieldResponse(
            field_name=fc.field_name,
            display_name=fc.display_name,
            value=fc.value,
            raw_value=fc.raw_value,
            normalized_value=fc.normalized_value,
            currency=fc.currency,
            unit=fc.unit,
            confidence=fc.confidence,
            raw_ocr_confidence=fc.raw_ocr_confidence,
            status=fc.status,
            source_image_id=fc.source_image_id,
            source_image_role=fc.source_image_role,
            source_ocr_ids=fc.source_ocr_ids,
            evidence=fc.evidence,
            bounding_box=fc.bounding_box,
            extraction_method=fc.extraction_method,
            has_conflict=fc.has_conflict,
            alternate_candidates=fc.alternate_candidates
        ))

    scan.analysis_step = "EXTRACTION"
    db.commit()

    return ScanExtractResponse(
        scan_id=scan.id,
        total_fields=len(fields_response),
        fields=fields_response
    )

@router.post("/{scan_id}/evaluate", response_model=ScanEvaluationResponse)
def evaluate_scan_compliance(
    scan_id: int,
    db: Session = Depends(get_db)
):
    """
    Milestone 4 Compliance Rule Evaluation Endpoint:
    Consumes persisted ExtractedDeclaration records for the scan,
    executes deterministic Legal Metrology rules with strictly decoupled severity and status,
    persists ComplianceEvaluation and ComplianceRuleResult records, updates scan status,
    and returns a structured compliance audit report.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    declarations = db.query(ExtractedDeclaration).filter(ExtractedDeclaration.scan_id == scan_id).all()
    if not declarations:
        raise HTTPException(
            status_code=400,
            detail="Scan has no extracted declarations to evaluate. Please run extraction first."
        )

    # Run ComplianceEngine
    eval_result = ComplianceEngine.evaluate_declarations(declarations)

    # Persist ComplianceEvaluation
    summary_data = eval_result["summary"]
    now = datetime.utcnow()

    # Clear prior evaluations for clean state or add new evaluation
    evaluation = ComplianceEvaluation(
        scan_id=scan.id,
        evaluated_at=now,
        overall_status=eval_result["overall_status"],
        total_rules=summary_data["total_rules"],
        passed_rules=summary_data["passed"],
        failed_rules=summary_data["failed"],
        warning_rules=summary_data["warnings"],
        not_verifiable_rules=summary_data["not_verifiable"],
        not_applicable_rules=summary_data["not_applicable"],
        critical_errors=sum(1 for r in eval_result["results"] if r.get("severity") in ("CRITICAL", "ERROR") and r.get("status") == "FAIL"),
        summary=f"Evaluated {summary_data['total_rules']} rules: {summary_data['passed']} PASS, {summary_data['failed']} FAIL, {summary_data['warnings']} WARNING, {summary_data['not_verifiable']} NOT_VERIFIABLE, {summary_data['not_applicable']} NOT_APPLICABLE."
    )
    db.add(evaluation)
    db.flush()

    decl_by_field = {d.field_name.upper(): d for d in declarations}

    persisted_results = []
    response_results = []
    for r in eval_result["results"]:
        target_decl = decl_by_field.get(r["field_name"].upper())
        rule_rec = ComplianceRuleResult(
            evaluation_id=evaluation.id,
            scan_id=scan.id,
            rule_id=r["rule_id"],
            field_name=r["field_name"],
            severity=r.get("severity", "ERROR"),
            status=r["status"],
            reason=r.get("reason") or r.get("message") or "",
            suggested_action=r.get("suggested_action"),
            rule_source=r.get("rule_source") or r.get("rule_reference") or "APPROVED_RULE_REFERENCE",
            declaration_id=target_decl.id if target_decl else None,
            detected_value=r.get("field_value") or (target_decl.detected_value if target_decl else None),
            normalized_value=target_decl.normalized_value if target_decl else None,
            evidence=r.get("evidence") or (target_decl.evidence if target_decl else None)
        )
        db.add(rule_rec)
        persisted_results.append(rule_rec)

    # Synchronize legacy RuleValidationResult table
    db.query(RuleValidationResult).filter(RuleValidationResult.scan_id == scan_id).delete()
    for r in eval_result["results"]:
        st = r["status"]
        if st == "PASS":
            c_state = ComplianceState.PASS
        elif st == "FAIL":
            c_state = ComplianceState.FAIL
        elif st == "WARNING":
            c_state = ComplianceState.WARNING
        elif st == "NOT_APPLICABLE":
            c_state = ComplianceState.NOT_APPLICABLE
        else:
            c_state = ComplianceState.NOT_VERIFIABLE

        matching_cr = db.query(ComplianceRule).filter(ComplianceRule.rule_id == r["rule_id"]).first()
        rule_fk_id = matching_cr.id if matching_cr else 1
        legacy_res = RuleValidationResult(
            scan_id=scan.id,
            rule_id=rule_fk_id,
            field_target=r["field_name"].lower(),
            expected_requirement=r.get("reason", ""),
            detected_value=r.get("field_value"),
            status=c_state,
            confidence=r.get("confidence", 1.0),
            reason=r.get("reason") or r.get("message") or "",
            suggested_action=r.get("suggested_action"),
            rule_reference=r.get("rule_source") or r.get("rule_reference") or "APPROVED_RULE_REFERENCE",
            rule_version="2024.1"
        )
        db.add(legacy_res)

    # Update scan overall status and score
    if eval_result["overall_status"] == "COMPLIANT":
        scan.overall_status = ComplianceState.PASS
    elif eval_result["overall_status"] == "NON_COMPLIANT":
        scan.overall_status = ComplianceState.FAIL
    else:
        scan.overall_status = ComplianceState.REVIEW_REQUIRED

    scan.compliance_score = eval_result.get("compliance_score", 0.0)
    scan.summary_verdict = evaluation.summary
    scan.analysis_step = "COMPLETED"

    db.commit()

    for pr in persisted_results:
        response_results.append(RuleResultResponse(
            id=pr.id,
            rule_id=pr.rule_id,
            field_name=pr.field_name,
            severity=pr.severity,
            status=pr.status,
            reason=pr.reason,
            suggested_action=pr.suggested_action,
            rule_source=pr.rule_source,
            declaration_id=pr.declaration_id,
            detected_value=pr.detected_value,
            normalized_value=pr.normalized_value,
            evidence=pr.evidence
        ))

    return ScanEvaluationResponse(
        scan_id=scan.id,
        overall_status=eval_result["overall_status"],
        evaluated_at=now,
        summary=ComplianceSummaryResponse(
            overall_status=eval_result["overall_status"],
            total_rules=evaluation.total_rules,
            passed_rules=evaluation.passed_rules,
            failed_rules=evaluation.failed_rules,
            warning_rules=evaluation.warning_rules,
            not_verifiable_rules=evaluation.not_verifiable_rules,
            not_applicable_rules=evaluation.not_applicable_rules,
            critical_errors=evaluation.critical_errors,
            summary=evaluation.summary
        ),
        results=response_results
    )

def _re_evaluate_scan_complete(scan_id: int, db: Session) -> ScanDetailResponse:
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    category = scan.category_rel
    category_code = category.code if category else "food_grocery"

    images = scan.images or []
    if not images:
        raise HTTPException(status_code=400, detail="Scan has no images to evaluate.")

    # Gather OCR boxes grouped by image
    image_boxes_map = []
    ocr_results = []
    for img in images:
        ocr_recs = db.query(OCRRecord).filter(OCRRecord.image_id == img.id).all()
        boxes = [
            {
                "id": rec.id,
                "text": rec.text,
                "confidence": rec.confidence,
                "bounding_box": rec.bounding_box,
                "line_number": rec.line_number,
                "image_id": rec.image_id,
                "image_type": img.image_type or img.image_role.upper()
            }
            for rec in ocr_recs
        ]
        image_boxes_map.append({
            "image_id": img.id,
            "image_role": (img.image_role or "front").lower(),
            "image_type": img.image_type or img.image_role.upper(),
            "boxes": boxes,
            "is_duplicate": img.is_duplicate,
            "duplicate_of_id": img.duplicate_of_id,
            "duplicate_type": img.duplicate_type,
            "quality": {
                "blur_score": img.blur_score,
                "glare_score": img.glare_score,
                "overall_status": img.quality_status,
                "quality_score": img.quality_score
            }
        })
        ocr_results.append(OCRResultResponse(
            image_id=img.id,
            image_type=img.image_type or img.image_role.upper(),
            full_text=" ".join([b["text"] for b in boxes]),
            boxes=[OCRBoxResponse(**b) for b in boxes],
            total_detections=len(boxes),
            average_confidence=img.ocr_confidence or 0.0,
            engine_name=img.ocr_engine_used or "PaddleOCR-PP-OCRv6",
            status=img.ocr_status or "COMPLETED"
        ))

    # Run extraction across panels
    extracted_fields = DeclarationExtractorService.extract_from_boxes_by_image(image_boxes_map)

    # Clear prior declarations
    db.query(ExtractedDeclaration).filter(ExtractedDeclaration.scan_id == scan_id).delete()
    db.commit()

    db_declarations = []
    for fc in extracted_fields:
        if fc.status == "FOUND":
            comp_status = ComplianceState.VERIFIED_COMPLIANT
        elif fc.status == "NOT_FOUND":
            comp_status = ComplianceState.NOT_FOUND
        elif fc.status in ("UNABLE_TO_VERIFY", "LOW_CONFIDENCE"):
            comp_status = ComplianceState.UNABLE_TO_VERIFY
        else:
            comp_status = ComplianceState.REVIEW_REQUIRED

        d_record = ExtractedDeclaration(
            scan_id=scan.id,
            field_name=fc.field_name,
            display_name=fc.display_name,
            detected_value=fc.value,
            normalized_value=fc.normalized_value,
            raw_value=fc.raw_value,
            raw_ocr_snippet=fc.raw_value,
            unit=fc.unit,
            currency=fc.currency,
            confidence=fc.confidence,
            field_confidence=fc.confidence,
            raw_ocr_confidence=fc.raw_ocr_confidence,
            status=comp_status,
            extraction_status=fc.status,
            bounding_box=fc.bounding_box,
            source_image_id=fc.source_image_id,
            source_image_role=fc.source_image_role or "front",
            source_ocr_ids=fc.source_ocr_ids,
            evidence=fc.evidence,
            extraction_method=fc.extraction_method,
            has_conflict=fc.has_conflict,
            alternate_candidates=fc.alternate_candidates,
            estimated_font_height_mm=fc.estimated_font_height_mm,
            required_font_height_mm=fc.required_font_height_mm,
            measurement_confidence=fc.measurement_confidence or "ESTIMATED"
        )
        db.add(d_record)
        db_declarations.append(d_record)

    db.commit()

    # Retrieve rules and evaluate compliance
    rules = db.query(ComplianceRule).filter(
        ComplianceRule.is_active == True,
        (ComplianceRule.category_id == (category.id if category else None)) | (ComplianceRule.category_id == None)
    ).all()

    rule_eval_results = ComplianceRuleEngine.evaluate_rules(
        rules=rules,
        extracted_declarations=[
            {
                "field_name": d.field_name,
                "canonical_field_name": d.field_name,
                "display_name": d.display_name,
                "detected_value": d.detected_value,
                "normalized_value": d.normalized_value,
                "unit": d.unit,
                "currency": d.currency,
                "status": d.status,
                "extraction_status": d.extraction_status,
                "confidence": d.confidence,
                "has_conflict": d.has_conflict,
                "evidence": d.evidence
            }
            for d in db_declarations
        ],
        category_code=category_code
    )

    db.query(RuleValidationResult).filter(RuleValidationResult.scan_id == scan_id).delete()
    for r_res in rule_eval_results:
        rule_db_rec = RuleValidationResult(
            scan_id=scan.id,
            rule_id=r_res["rule_id"],
            field_target=r_res["field_target"],
            expected_requirement=r_res["expected_requirement"],
            detected_value=r_res["detected_value"],
            status=r_res["status"],
            confidence=r_res["confidence"],
            reason=r_res["reason"],
            suggested_action=r_res["suggested_action"],
            rule_reference=r_res["rule_reference"],
            rule_version=r_res["rule_version"]
        )
        db.add(rule_db_rec)

    # ComplianceEngine evaluation
    comp_eval = ComplianceEngine.evaluate_declarations(db_declarations)
    summary_data = comp_eval["summary"]
    now = datetime.utcnow()
    m4_evaluation = ComplianceEvaluation(
        scan_id=scan.id,
        evaluated_at=now,
        overall_status=comp_eval["overall_status"],
        total_rules=summary_data["total_rules"],
        passed_rules=summary_data["passed"],
        failed_rules=summary_data["failed"],
        warning_rules=summary_data["warnings"],
        not_verifiable_rules=summary_data["not_verifiable"],
        not_applicable_rules=summary_data["not_applicable"],
        critical_errors=sum(1 for r in comp_eval["results"] if r.get("severity") in ("CRITICAL", "ERROR") and r.get("status") == "FAIL"),
        summary=f"Evaluated {summary_data['total_rules']} rules: {summary_data['passed']} PASS, {summary_data['failed']} FAIL, {summary_data['warnings']} WARNING, {summary_data['not_verifiable']} NOT_VERIFIABLE, {summary_data['not_applicable']} NOT_APPLICABLE."
    )
    db.add(m4_evaluation)
    db.flush()

    decl_by_f = {d.field_name.upper(): d for d in db_declarations}
    for r in comp_eval["results"]:
        target_d = decl_by_f.get(r["field_name"].upper())
        cr_rec = ComplianceRuleResult(
            evaluation_id=m4_evaluation.id,
            scan_id=scan.id,
            rule_id=r["rule_id"],
            field_name=r["field_name"],
            severity=r.get("severity", "ERROR"),
            status=r["status"],
            reason=r.get("reason") or r.get("message") or "",
            suggested_action=r.get("suggested_action"),
            rule_source=r.get("rule_source") or r.get("rule_reference") or "APPROVED_RULE_REFERENCE",
            declaration_id=target_d.id if target_d else None,
            detected_value=r.get("field_value") or (target_d.detected_value if target_d else None),
            normalized_value=target_d.normalized_value if target_d else None,
            evidence=r.get("evidence") or (target_d.evidence if target_d else None)
        )
        db.add(cr_rec)

    quality_evals = [
        {
            "quality_status": img.quality_status,
            "quality_score": img.quality_score,
            "blur_score": img.blur_score,
            "glare_score": img.glare_score,
            "quality_notes": img.quality_notes,
            "retake_guidance": img.retake_guidance or []
        }
        for img in images
    ]

    report = ReportGeneratorService.generate_overall_assessment(
        rule_results=rule_eval_results,
        image_qualities=quality_evals,
        product_name=scan.product_name,
        category_name=category.name if category else "General",
        declarations=db_declarations,
        images=images,
        ocr_results=ocr_results
    )

    scan.overall_status = report["overall_status"]
    scan.compliance_score = report["compliance_score"]
    scan.summary_verdict = report["summary_verdict"]
    scan.scan_reliability = report.get("scan_reliability")
    scan.coverage_summary = report.get("coverage_summary")
    scan.analysis_step = "COMPLETED"
    db.commit()
    db.refresh(scan)

    return get_scan_details(scan.id, db)

@router.post("/{scan_id}/images", response_model=ScanDetailResponse)
async def add_scan_image(
    scan_id: int,
    image: UploadFile = File(..., description="Package photograph to add or replace"),
    role: Optional[str] = Form("UNKNOWN", description="Role of the panel: FRONT, BACK, LEFT_SIDE, RIGHT_SIDE, TOP, BOTTOM, CLOSE_UP, UNKNOWN"),
    db: Session = Depends(get_db)
):
    """
    Adds an additional or replacement package panel photograph to an existing scan
    and deterministically re-evaluates multi-image evidence, compliance, and coverage.
    Preserves all existing valid evidence without loss.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    try:
        content = await image.read()
    except Exception:
        try:
            content = image.file.read()
        except Exception:
            content = b""

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty (0 bytes).")

    if scan.images:
        first_local = get_local_path_from_url(scan.images[0].file_path)
        scan_upload_dir = os.path.dirname(first_local)
        scan_uid = os.path.basename(scan_upload_dir)
    else:
        scan_uid = str(uuid.uuid4())[:8]
        scan_upload_dir = os.path.join(settings.UPLOAD_DIR, scan_uid)

    os.makedirs(scan_upload_dir, exist_ok=True)

    normalized_role = ImageValidator.normalize_role(role)
    ext = os.path.splitext(image.filename)[1].lower() if image.filename else ".jpg"
    if not ext:
        ext = ".jpg"
    filename = f"{normalized_role.lower()}_{uuid.uuid4().hex[:6]}{ext}"
    target_path = os.path.join(scan_upload_dir, filename)

    try:
        val_res = ImageValidator.validate_and_save_upload(
            file_bytes=content,
            filename=image.filename or "upload.jpg",
            target_path=target_path
        )
    except ImageValidationError as e:
        raise HTTPException(status_code=400, detail=f"Image validation failed: {str(e)}")

    prep_filename = f"preprocessed_{filename}"
    prep_path = os.path.join(scan_upload_dir, prep_filename)

    # Run CV quality pipeline
    quality = ImageQualityService.run_quality_pipeline(target_path, prep_path)

    # Check duplicates against prior images in this scan
    existing_meta = [
        {
            "id": img.id,
            "content_hash": img.content_hash,
            "perceptual_hash": img.perceptual_hash,
            "width": img.resolution_w,
            "height": img.resolution_h
        }
        for img in scan.images
    ]
    existing_meta.append({
        "id": 999999,
        "content_hash": val_res["content_hash"],
        "perceptual_hash": val_res["perceptual_hash"],
        "width": val_res["width"],
        "height": val_res["height"]
    })
    dup_annotated = ImageValidator.detect_duplicates(existing_meta)
    new_dup_info = dup_annotated[-1]

    relative_path = f"/uploads/{scan_uid}/{filename}"
    relative_prep_path = f"/uploads/{scan_uid}/{prep_filename}" if quality.get("preprocessing_applied") else None

    new_img_record = ScanImage(
        scan_id=scan.id,
        image_role=normalized_role.lower(),
        image_type=normalized_role,
        file_path=relative_path,
        preprocessed_file_path=relative_prep_path,
        original_filename=image.filename,
        quality_status=quality["quality_status"],
        quality_score=quality.get("quality_score", 1.0),
        blur_score=quality["blur_score"],
        glare_score=quality["glare_score"],
        lighting_score=quality["lighting_score"],
        resolution_w=val_res["width"],
        resolution_h=val_res["height"],
        quality_notes=quality["quality_notes"],
        preprocessing_status="APPLIED" if quality.get("preprocessing_applied") else "NOT_REQUIRED",
        quality_decision=quality.get("quality_decision", "ACCEPTABLE"),
        retake_guidance=quality.get("retake_guidance", []),
        content_hash=val_res["content_hash"],
        perceptual_hash=val_res["perceptual_hash"],
        is_duplicate=new_dup_info.get("is_duplicate", False),
        duplicate_of_id=new_dup_info.get("duplicate_of_id"),
        duplicate_type=new_dup_info.get("duplicate_type"),
        duplicate_reason=new_dup_info.get("duplicate_reason")
    )
    db.add(new_img_record)
    db.commit()
    db.refresh(new_img_record)

    # Run OCR on the newly added image
    ocr_res = ocr_engine.extract_text(
        image_path=target_path,
        image_id=new_img_record.id,
        image_type=new_img_record.image_type,
        preprocessed_path=prep_path
    )
    for box in ocr_res.boxes:
        ocr_rec = OCRRecord(
            image_id=new_img_record.id,
            scan_id=scan.id,
            text=box.text,
            confidence=box.confidence,
            bounding_box=box.bounding_box,
            line_number=box.line_number,
            engine_name=ocr_res.engine_name,
            attempt_number=ocr_res.attempt_count
        )
        db.add(ocr_rec)

    new_img_record.ocr_status = ocr_res.status
    new_img_record.ocr_engine_used = ocr_res.engine_name
    new_img_record.ocr_confidence = ocr_res.average_confidence
    new_img_record.ocr_detections_count = ocr_res.total_detections
    new_img_record.ocr_attempt_count = ocr_res.attempt_count
    new_img_record.ocr_raw_boxes = [b.model_dump() for b in ocr_res.boxes]
    db.commit()

    return _re_evaluate_scan_complete(scan.id, db)

@router.post("/quality-preview", response_model=ImageQualityPreviewResponse)
async def preview_image_quality(
    image: UploadFile = File(..., description="Photograph to analyze for sharpness, glare, lighting, and retake guidance")
):
    """
    Immediate lightweight CV quality check for mobile field inspectors.
    Evaluates blur (Laplacian variance), specular glare, brightness, and resolution,
    returning immediate actionable capture guidance without creating a scan record.
    """
    import tempfile
    try:
        content = await image.read()
    except Exception:
        try:
            content = image.file.read()
        except Exception:
            content = b""

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded image is empty (0 bytes).")

    ext = os.path.splitext(image.filename)[1].lower() if image.filename else ".jpg"
    if not ext:
        ext = ".jpg"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        q_res = ImageQualityService.evaluate_image_file(tmp_path)
        return ImageQualityPreviewResponse(
            quality_status=q_res["quality_status"],
            quality_decision=q_res.get("quality_decision", "ACCEPTABLE"),
            quality_score=q_res.get("quality_score", 1.0),
            blur_score=q_res.get("blur_score", 0.0),
            glare_score=q_res.get("glare_score", 0.0),
            glare_percentage=q_res.get("glare_percentage", 0.0),
            lighting_score=q_res.get("lighting_score", 100.0),
            brightness_score=q_res.get("brightness_score", 1.0),
            resolution_w=q_res.get("resolution_w", 0),
            resolution_h=q_res.get("resolution_h", 0),
            resolution_ok=q_res.get("resolution_ok", True),
            perspective_skew=q_res.get("perspective_skew", False),
            quality_notes=q_res.get("quality_notes", ""),
            retake_guidance=q_res.get("retake_guidance", [])
        )
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@router.patch("/{scan_id}/images/{image_id}/role", response_model=ScanDetailResponse)
def update_image_role(
    scan_id: int,
    image_id: int,
    role: str = Form(..., description="Corrected panel role: FRONT, BACK, SIDE, LEFT_SIDE, RIGHT_SIDE, TOP, BOTTOM, CLOSE_UP, UNKNOWN"),
    db: Session = Depends(get_db)
):
    """
    Updates or corrects the assigned panel role of an uploaded packaging photograph
    and triggers a complete, deterministic re-evaluation of multi-panel evidence.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")

    target_img = db.query(ScanImage).filter(ScanImage.id == image_id, ScanImage.scan_id == scan_id).first()
    if not target_img:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found in scan {scan_id}.")

    normalized_role = ImageValidator.normalize_role(role)
    target_img.image_role = normalized_role.lower()
    target_img.image_type = normalized_role
    db.commit()

    return _re_evaluate_scan_complete(scan.id, db)

@router.delete("/{scan_id}")
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    """Delete a scan record and its associated declarations/validation results."""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found.")
    
    db.delete(scan)
    db.commit()
    return {"message": f"Scan {scan_id} deleted successfully."}
