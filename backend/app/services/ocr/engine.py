import os
import time
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.services.ocr.base import BaseOCREngine, OCRResult, OCRBoxResult
from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.providers.rapidocr_provider import RapidOCREngine
from app.services.ocr.providers.easyocr_provider import EasyOCREngine
from app.services.ocr.providers.gemini_provider import GeminiVisionOCREngine
from app.services.image_processing.quality import ImageQualityService
from app.models.models import ImageQualityStatus

class PretrainedOCREngine(BaseOCREngine):
    """
    Production-grade OCR Pipeline Orchestrator for Legal Metrology Packaged Commodities.
    
    Coordinates:
    - Primary Pre-Trained Engine: PaddleOCR PP-OCRv6
    - Operational Fallback: RapidOCR (rapidocr-onnxruntime)
    - Optional Auxiliary Fallbacks: EasyOCR, Gemini Vision
    - Controlled Preprocessing & Retry Strategy (Attempt 1: Original -> Attempt 2: CLAHE Preprocessed)
    - Uncertainty Telemetry & Zero-Fake-Text Guarantee
    """

    def __init__(self, preferred_engine: Optional[str] = None):
        self.preferred_engine_name = preferred_engine or settings.OCR_ENGINE
        self._paddle_engine = PaddleOCRProvider()
        self._rapid_engine = RapidOCREngine()
        self._easy_engine = EasyOCREngine()
        self._gemini_engine = GeminiVisionOCREngine()
        self.engine_name = self._resolve_active_engine_name()

    def _resolve_active_engine_name(self) -> str:
        if self.preferred_engine_name == "paddleocr" and self._paddle_engine.is_available():
            return self._paddle_engine.engine_name
        elif self.preferred_engine_name == "rapidocr" and self._rapid_engine.is_available():
            return self._rapid_engine.engine_name
        elif self.preferred_engine_name == "easyocr" and self._easy_engine.is_available():
            return self._easy_engine.engine_name
        elif self.preferred_engine_name == "gemini" and self._gemini_engine.is_available():
            return self._gemini_engine.engine_name
        elif self._paddle_engine.is_available():
            return self._paddle_engine.engine_name
        elif self._rapid_engine.is_available():
            return self._rapid_engine.engine_name
        return "No-OCR-Engine-Available"

    def _get_primary_provider(self) -> BaseOCREngine:
        if self.preferred_engine_name == "paddleocr" and self._paddle_engine.is_available():
            return self._paddle_engine
        elif self.preferred_engine_name == "rapidocr" and self._rapid_engine.is_available():
            return self._rapid_engine
        elif self.preferred_engine_name == "easyocr" and self._easy_engine.is_available():
            return self._easy_engine
        elif self.preferred_engine_name == "gemini" and self._gemini_engine.is_available():
            return self._gemini_engine
        elif self._paddle_engine.is_available():
            return self._paddle_engine
        return self._rapid_engine

    def extract_text(
        self,
        image_path: str,
        image_id: Optional[int] = None,
        image_type: Optional[str] = "FRONT",
        retry_after_preprocess: bool = True,
        preprocessed_path: Optional[str] = None,
        max_attempts: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        force_preprocess: bool = False,
        **kwargs
    ) -> OCRResult:
        """
        Executes genuine OCR inference with uncertainty handling and controlled retry.
        
        Zero Mock Policy:
        Under no circumstances will fake, filename-based, or template text be returned.
        If no text is detected on an image, returns an empty result with status NO_TEXT_DETECTED.
        """
        start_time = time.time()
        max_tries = max_attempts if max_attempts is not None else settings.OCR_MAX_ATTEMPTS
        threshold = confidence_threshold if confidence_threshold is not None else settings.OCR_CONFIDENCE_THRESHOLD
        provider = self._get_primary_provider()

        if not os.path.exists(image_path):
            return OCRResult(
                image_id=image_id,
                image_type=image_type,
                full_text="",
                boxes=[],
                engine_name=provider.engine_name,
                status="FAILED",
                error_message=f"Image file not found on disk: {image_path}",
                processing_time_ms=0.0
            )

        # Attempt 1: Run inference on original image
        attempt_1_res = provider.extract_text(
            image_path=image_path,
            image_id=image_id,
            image_type=image_type,
            confidence_threshold=threshold
        )
        attempt_1_res.attempt_count = 1
        attempt_1_res.preprocessed_used = False

        # Determine if retry on preprocessed image is warranted
        needs_retry = False
        retry_reason = None
        if force_preprocess:
            needs_retry = True
            retry_reason = "FORCED_PREPROCESS"
        elif attempt_1_res.status == "FAILED":
            needs_retry = True
            retry_reason = "INITIAL_OCR_FAILED"
        elif attempt_1_res.total_detections == 0:
            needs_retry = True
            retry_reason = "NO_TEXT_DETECTED_ON_ORIGINAL"
        elif attempt_1_res.average_confidence < threshold:
            needs_retry = True
            retry_reason = f"LOW_AVERAGE_CONFIDENCE_{attempt_1_res.average_confidence:.2f}_BELOW_{threshold:.2f}"

        if not needs_retry or not retry_after_preprocess or max_tries < 2:
            attempt_1_res.processing_time_ms = round((time.time() - start_time) * 1000.0, 2)
            attempt_1_res.retry_reason = None
            return attempt_1_res

        # Attempt 2: Prepare and run on preprocessed image
        target_prep_path = preprocessed_path
        if not target_prep_path:
            dir_name = os.path.dirname(image_path)
            base_name = os.path.basename(image_path)
            target_prep_path = os.path.join(dir_name, f"preprocessed_{base_name}")

        prep_ok = False
        if not os.path.exists(target_prep_path):
            prep_ok = ImageQualityService.preprocess_image_for_ocr(image_path, target_prep_path)
        else:
            prep_ok = True

        if not prep_ok or not os.path.exists(target_prep_path):
            # Preprocessing failed or could not be generated; return attempt 1
            attempt_1_res.processing_time_ms = round((time.time() - start_time) * 1000.0, 2)
            attempt_1_res.retry_reason = f"{retry_reason}_PREPROCESSING_FAILED"
            return attempt_1_res

        # Run Attempt 2
        attempt_2_res = provider.extract_text(
            image_path=target_prep_path,
            image_id=image_id,
            image_type=image_type,
            confidence_threshold=threshold
        )
        attempt_2_res.attempt_count = 2
        attempt_2_res.preprocessed_used = True
        attempt_2_res.retry_reason = retry_reason

        # Check if optional cloud fallback is enabled and justified
        if (
            attempt_2_res.total_detections == 0 and
            settings.OCR_ENABLE_FALLBACK and
            self._gemini_engine.is_available() and
            provider != self._gemini_engine
        ):
            fallback_res = self._gemini_engine.extract_text(
                image_path=image_path,
                image_id=image_id,
                image_type=image_type
            )
            if fallback_res.total_detections > 0:
                fallback_res.attempt_count = 3
                fallback_res.retry_reason = "FALLBACK_CLOUD_OCR"
                fallback_res.processing_time_ms = round((time.time() - start_time) * 1000.0, 2)
                return fallback_res

        total_attempts = 2

        # Choose best attempt (prefer higher detection count or higher average confidence)
        if attempt_2_res.total_detections > attempt_1_res.total_detections:
            best_res = attempt_2_res
        elif (
            attempt_2_res.total_detections == attempt_1_res.total_detections and
            attempt_2_res.average_confidence >= attempt_1_res.average_confidence
        ):
            best_res = attempt_2_res
        else:
            best_res = attempt_1_res

        best_res.attempt_count = total_attempts
        best_res.retry_reason = retry_reason
        best_res.processing_time_ms = round((time.time() - start_time) * 1000.0, 2)
        return best_res

    def extract_multi_images(
        self,
        images_info: List[Dict[str, Any]],
        confidence_threshold: Optional[float] = None
    ) -> List[OCRResult]:
        """
        Executes OCR independently on multiple package panel images (FRONT, BACK, SIDE, etc.),
        preserving individual image associations and bounding box coordinates.
        """
        results = []
        for info in images_info:
            path = info.get("file_path") or info.get("path")
            img_id = info.get("image_id") or info.get("id")
            img_type = info.get("image_type") or info.get("image_role", "FRONT")
            prep_path = info.get("preprocessed_file_path")

            if not path:
                continue

            res = self.extract_text(
                image_path=path,
                image_id=img_id,
                image_type=img_type,
                preprocessed_path=prep_path,
                confidence_threshold=confidence_threshold
            )
            results.append(res)
        return results
