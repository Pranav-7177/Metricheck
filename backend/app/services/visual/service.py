from typing import Dict, Any, Optional, List, Union
from app.services.visual.evidence import (
    VisualEvidence, VisualEvidenceStatus, ReadabilityStatus,
    VisibilityStatus, PlacementRegion, CalibrationMethod
)
from app.services.visual.geometry import GeometryService
from app.services.visual.calibration import CalibrationService
from app.services.visual.text_measurement import TextMeasurementService
from app.services.visual.readability import ReadabilityService
from app.services.visual.placement import PlacementService

class VisualComplianceService:
    """
    Master orchestrator for visual compliance, geometry measurement,
    readability verification, and calibrated physical font estimation.
    """

    @classmethod
    def evaluate_declaration_visual_evidence(
        cls,
        field_name: str,
        bounding_box: Any,
        image_path: Optional[str] = None,
        image_id: Optional[int] = None,
        image_role: str = "front",
        image_dimensions: Optional[tuple] = None,
        ocr_confidence: float = 0.90,
        calibration_context: Optional[Dict[str, Any]] = None
    ) -> VisualEvidence:
        """
        Executes complete visual compliance pipeline for a single statutory declaration.
        """
        img_w, img_h = image_dimensions if image_dimensions else (1000.0, 1000.0)

        # 1. Geometry analysis
        geometry = GeometryService.analyze_box_geometry(bounding_box)
        parsed_box = geometry.get("parsed_box")

        # 2. Calibration determination
        calib_ctx = calibration_context or {}
        if calib_ctx.get("pixels_per_mm") and float(calib_ctx["pixels_per_mm"]) > 0:
            calibration = CalibrationService.calibrate_from_pixels_per_mm(
                pixels_per_mm=float(calib_ctx["pixels_per_mm"]),
                calibration_method=calib_ctx.get("calibration_method", CalibrationMethod.KNOWN_REFERENCE_OBJECT.value),
                confidence=float(calib_ctx.get("confidence", 0.90)),
                source=calib_ctx.get("source", "Pre-calibrated camera scale")
            )
        elif calib_ctx.get("reference_type") and calib_ctx.get("detected_reference_pixel_dimension"):
            calibration = CalibrationService.calibrate_from_reference(
                reference_type=calib_ctx["reference_type"],
                detected_pixel_dimension=float(calib_ctx["detected_reference_pixel_dimension"]),
                detection_confidence=float(calib_ctx.get("confidence", 0.90))
            )
        elif calib_ctx.get("known_package_dimension_mm") and calib_ctx.get("detected_package_pixel_dimension"):
            calibration = CalibrationService.calibrate_from_package_dimension(
                known_dimension_mm=float(calib_ctx["known_package_dimension_mm"]),
                detected_pixel_dimension=float(calib_ctx["detected_package_pixel_dimension"]),
                dimension_axis=calib_ctx.get("dimension_axis", "height"),
                confidence=float(calib_ctx.get("confidence", 0.85))
            )
        else:
            calibration = CalibrationService.get_uncalibrated_result()


        # 3. Text physical measurement
        measurement = TextMeasurementService.measure_declaration_text(geometry, calibration)

        # 4. Readability analysis (ROI contrast, blur, glare overlap)
        readability_res = ReadabilityService.analyze_readability(
            parsed_box=parsed_box,
            image_input=image_path,
            ocr_confidence=ocr_confidence
        )

        # 5. Placement & visibility clipping analysis
        placement_res = PlacementService.analyze_placement_and_visibility(
            parsed_box=parsed_box,
            image_width=img_w,
            image_height=img_h,
            image_role=image_role
        )

        # 6. Overall visual evidence classification
        is_unreadable_glare = readability_res["readability"] == ReadabilityStatus.UNABLE_TO_VERIFY.value
        is_clipped = placement_res["visibility"] in (VisibilityStatus.PARTIALLY_VISIBLE.value, VisibilityStatus.OUT_OF_FRAME.value)
        is_distorted = measurement["measurement_status"] == VisualEvidenceStatus.UNABLE_TO_VERIFY.value

        explanation = ""
        recommendation = None

        if is_unreadable_glare:
            visual_status = VisualEvidenceStatus.UNABLE_TO_VERIFY.value
            explanation = "Glare overlaps the declaration region and prevents reliable visual verification. Capture the package with reduced reflections."
            recommendation = "Capture image with reduced reflections."
        elif is_clipped:
            visual_status = VisualEvidenceStatus.UNABLE_TO_VERIFY.value
            explanation = "The declaration is partially outside the visible image region. Capture the complete package panel."
            recommendation = "Capture the complete declaration region."
        elif is_distorted:
            visual_status = VisualEvidenceStatus.UNABLE_TO_VERIFY.value
            explanation = "The declaration region is significantly distorted by perspective. Capture the package more directly."
            recommendation = "Capture the package more directly."
        elif measurement["measurement_status"] == VisualEvidenceStatus.MEASURABLE.value:
            visual_status = VisualEvidenceStatus.MEASURABLE.value
            explanation = measurement["explanation"]
            recommendation = None
        elif readability_res["readability"] in (ReadabilityStatus.READABLE.value, ReadabilityStatus.MARGINAL.value):
            visual_status = VisualEvidenceStatus.READABLE_ONLY.value
            explanation = "The declaration is readable, but physical size compliance cannot be established from the available calibration evidence."
            recommendation = "Provide a known package dimension or calibrated reference."
        else:
            visual_status = VisualEvidenceStatus.NOT_MEASURABLE.value
            explanation = "The declaration is readable, but its physical size could not be measured reliably because no valid calibration reference was available."
            recommendation = "Provide a known package dimension or calibrated reference."

        return VisualEvidence(
            field=field_name,
            image_id=image_id,
            source_image_role=image_role,
            bbox=bounding_box,
            text_height_px=geometry["text_height_px"],
            text_width_px=geometry["text_width_px"],
            orientation_deg=geometry["orientation_deg"],
            area_px=geometry["area_px"],
            perspective_score=geometry["perspective_score"],
            is_curved_surface=geometry["is_curved_surface"],
            font_height_mm=measurement["font_height_mm"],
            pixels_per_mm=measurement["pixels_per_mm"],
            calibration_method=calibration["calibration_method"],
            calibration_confidence=calibration["calibration_confidence"],
            blur_score=readability_res["blur_score"],
            contrast_score=readability_res["contrast_score"],
            glare_overlap_percentage=readability_res["glare_overlap_percentage"],
            shadow_overlap_percentage=readability_res["shadow_overlap_percentage"],
            readability=readability_res["readability"],
            visibility=placement_res["visibility"],
            placement=placement_res["placement"],
            normalized_x=placement_res["normalized_x"],
            normalized_y=placement_res["normalized_y"],
            visual_status=visual_status,
            explanation=explanation,
            recommendation=recommendation
        )

    @classmethod
    def aggregate_multi_image_visual_evidence(
        cls,
        evidence_items: List[VisualEvidence]
    ) -> Optional[VisualEvidence]:
        """
        Consolidates visual evidence from multiple photographs.
        Preserves all alternates and identifies material measurement conflicts.
        """
        if not evidence_items:
            return None

        if len(evidence_items) == 1:
            return evidence_items[0]

        # Prioritize MEASURABLE over READABLE_ONLY over UNABLE_TO_VERIFY over NOT_MEASURABLE
        priority_map = {
            VisualEvidenceStatus.MEASURABLE.value: 4,
            VisualEvidenceStatus.READABLE_ONLY.value: 3,
            VisualEvidenceStatus.NOT_MEASURABLE.value: 2,
            VisualEvidenceStatus.UNABLE_TO_VERIFY.value: 1,
            VisualEvidenceStatus.AMBIGUOUS.value: 0
        }

        sorted_items = sorted(
            evidence_items,
            key=lambda item: (
                priority_map.get(item.visual_status, 0),
                item.calibration_confidence,
                item.text_height_px
            ),
            reverse=True
        )

        primary = sorted_items[0]
        alternates = sorted_items[1:]

        # Check for material physical measurement conflict between measurable items
        has_conflict = False
        measurable_items = [it for it in evidence_items if it.visual_status == VisualEvidenceStatus.MEASURABLE.value and it.font_height_mm is not None]
        if len(measurable_items) >= 2:
            heights = [it.font_height_mm for it in measurable_items]
            min_h, max_h = min(heights), max(heights)
            # Difference > 35% constitutes a material conflict
            if min_h > 0 and ((max_h - min_h) / min_h) > 0.35:
                has_conflict = True

        primary.alternate_visual_evidence = [alt.to_dict() for alt in alternates]

        if has_conflict:
            primary.visual_status = VisualEvidenceStatus.AMBIGUOUS.value
            primary.explanation = "Multiple conflicting physical font measurements detected across photographs. Manual review is required."
            primary.recommendation = "Review the conflicting visual measurements across the submitted images."

        return primary
