import cv2
import numpy as np
from PIL import Image
import os
from typing import Dict, Any, Tuple, Optional, List
from app.models.models import ImageQualityStatus

class ImageQualityService:
    """
    Evaluates photograph quality for packaged commodities compliance scanning.
    Assesses blur (Laplacian variance), glare/reflections, lighting, resolution,
    and perspective skew to handle uncertainty reliably.
    """

    MIN_ACCEPTABLE_WIDTH = 600
    MIN_ACCEPTABLE_HEIGHT = 600
    BLUR_THRESHOLD_POOR = 40.0
    BLUR_THRESHOLD_GOOD = 100.0
    GLARE_THRESHOLD_PERCENT = 12.0 # % pixels saturated above 245 in luminance

    @classmethod
    def evaluate_image_file(cls, file_path: str) -> Dict[str, Any]:
        """Reads image from disk and performs full CV quality assessment."""
        if not os.path.exists(file_path):
            return {
                "quality_status": ImageQualityStatus.CRITICAL_ISSUES,
                "blur_score": 0.0,
                "glare_score": 0.0,
                "lighting_score": 0.0,
                "resolution_w": 0,
                "resolution_h": 0,
                "quality_notes": "Image file not found on disk."
            }

        try:
            # Read via OpenCV
            img = cv2.imread(file_path)
            if img is None:
                # Fallback to PIL in case of special color formats
                pil_img = Image.open(file_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            h, w = img.shape[:2]

            # 1. Blur evaluation using Laplacian variance
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # 2. Glare, shadow, and lighting assessment
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
            glare_pixels = np.sum(v_channel >= 245)
            shadow_pixels = np.sum(v_channel <= 30)
            total_pixels = h * w
            glare_percentage = float((glare_pixels / max(total_pixels, 1)) * 100.0)
            shadow_percentage = float((shadow_pixels / max(total_pixels, 1)) * 100.0)
            avg_brightness = float(np.mean(v_channel))

            # Local contrast
            min_val, max_val = float(np.min(gray)), float(np.max(gray))
            contrast_score = round((max_val - min_val) / max(max_val + min_val, 1e-5), 2)

            # Perspective skew estimation (aspect variance of dominant edges)
            perspective_skew = False
            try:
                edges = cv2.Canny(gray, 50, 150, apertureSize=3)
                lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=10)
                if lines is not None and len(lines) >= 4:
                    angles = []
                    for l in lines[:10]:
                        x1, y1, x2, y2 = l[0]
                        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180
                        angles.append(angle)
                    skewed_angles = [a for a in angles if 15 < a < 75 or 105 < a < 165]
                    if len(skewed_angles) > len(angles) * 0.4:
                        perspective_skew = True
            except Exception:
                perspective_skew = False

            # Lighting score (100 is ideal ~120-180 brightness, drops if too dark <50 or too bright >220)
            if avg_brightness < 60:
                lighting_score = max(10.0, (avg_brightness / 60.0) * 60.0)
            elif avg_brightness > 230:
                lighting_score = max(10.0, (255.0 - avg_brightness) / 25.0 * 60.0)
            else:
                lighting_score = 95.0

            # 3. Overall quality classification
            notes = []
            status = ImageQualityStatus.GOOD

            if w < cls.MIN_ACCEPTABLE_WIDTH or h < cls.MIN_ACCEPTABLE_HEIGHT:
                status = ImageQualityStatus.POOR
                notes.append(f"Low resolution: {w}x{h}px. At least 800x800 recommended for font measurement.")

            if laplacian_var < cls.BLUR_THRESHOLD_POOR:
                status = ImageQualityStatus.POOR
                notes.append(f"Image is blurry (sharpness score {laplacian_var:.1f}). Text characters may be degraded.")
            elif laplacian_var < cls.BLUR_THRESHOLD_GOOD:
                if status == ImageQualityStatus.GOOD:
                    status = ImageQualityStatus.ACCEPTABLE
                notes.append(f"Moderate sharpness ({laplacian_var:.1f}).")

            if glare_percentage > cls.GLARE_THRESHOLD_PERCENT:
                status = ImageQualityStatus.POOR
                notes.append(f"Significant glare/reflection detected ({glare_percentage:.1f}% washed out).")
            elif glare_percentage > 5.0:
                notes.append(f"Minor reflections detected ({glare_percentage:.1f}%).")

            if shadow_percentage > 20.0:
                notes.append(f"Heavy shadow regions detected ({shadow_percentage:.1f}% dark area).")

            if perspective_skew:
                notes.append("Perspective distortion: package panel photographed at an angle.")

            if avg_brightness < 50:
                notes.append("Under-exposed: lighting is dim.")
            elif avg_brightness > 210:
                notes.append("Over-exposed: lighting is harsh.")

            if not notes:
                notes.append("Image resolution, sharpness, and lighting are optimal for text extraction.")

            # Compute normalized quality score (0.0 to 1.0)
            blur_norm = min(1.0, max(0.0, laplacian_var / 150.0))
            glare_penalty = min(1.0, glare_percentage / 25.0)
            shadow_penalty = min(1.0, shadow_percentage / 30.0)
            lighting_norm = lighting_score / 100.0
            res_ok = bool(w >= cls.MIN_ACCEPTABLE_WIDTH and h >= cls.MIN_ACCEPTABLE_HEIGHT)
            res_factor = 1.0 if res_ok else 0.6
            overall_score = round(max(0.0, min(1.0, (blur_norm * 0.40 + (1.0 - glare_penalty) * 0.20 + (1.0 - shadow_penalty) * 0.10 + lighting_norm * 0.30) * res_factor)), 2)

            # Master Prompt 10 Decision Tier
            if status in (ImageQualityStatus.GOOD, ImageQualityStatus.ACCEPTABLE) and overall_score >= 0.60:
                quality_decision = "ACCEPTABLE"
            elif laplacian_var < 15.0 or (glare_percentage > 35.0 and laplacian_var < 30.0) or (w < 300 or h < 300):
                quality_decision = "UNSUITABLE"
            else:
                quality_decision = "DEGRADED"

            result_dict = {
                "quality_status": status,
                "quality_decision": quality_decision,
                "quality_score": overall_score,
                "blur_score": round(laplacian_var, 2),
                "glare_score": round(glare_percentage, 2),
                "glare_percentage": round(glare_percentage, 2),
                "shadow_score": round(shadow_percentage, 2),
                "shadow_percentage": round(shadow_percentage, 2),
                "contrast_score": contrast_score,
                "perspective_skew": perspective_skew,
                "lighting_score": round(lighting_score, 2),
                "brightness_score": round(avg_brightness / 255.0, 2),
                "resolution_w": w,
                "resolution_h": h,
                "resolution_ok": res_ok,
                "preprocessing_applied": False,
                "quality_notes": " | ".join(notes)
            }
            result_dict["retake_guidance"] = cls.generate_retake_guidance(result_dict)
            return result_dict

        except Exception as e:
            fallback_dict = {
                "quality_status": ImageQualityStatus.POOR,
                "quality_decision": "DEGRADED",
                "quality_score": 0.2,
                "blur_score": 25.0,
                "glare_score": 0.0,
                "glare_percentage": 0.0,
                "shadow_score": 0.0,
                "shadow_percentage": 0.0,
                "contrast_score": 0.5,
                "perspective_skew": False,
                "lighting_score": 50.0,
                "brightness_score": 0.5,
                "resolution_w": 0,
                "resolution_h": 0,
                "resolution_ok": False,
                "preprocessing_applied": False,
                "quality_notes": f"Quality assessment fallback: {str(e)}"
            }
            fallback_dict["retake_guidance"] = cls.generate_retake_guidance(fallback_dict)
            return fallback_dict

    @classmethod
    def generate_retake_guidance(
        cls,
        quality_data: Dict[str, Any],
        has_cropped_text: bool = False
    ) -> List[str]:
        """
        Generates specific, actionable guidance based on measured physical conditions.
        Deduplicates advice so identical messages are never repeated.
        """
        guidance: List[str] = []
        seen = set()

        def add_tip(msg: str):
            if msg not in seen:
                seen.add(msg)
                guidance.append(msg)

        blur_val = quality_data.get("blur_score", 100.0)
        glare_val = quality_data.get("glare_score", quality_data.get("glare_percentage", 0.0))
        shadow_val = quality_data.get("shadow_score", quality_data.get("shadow_percentage", 0.0))
        rw = quality_data.get("resolution_w", 1000)
        rh = quality_data.get("resolution_h", 1000)
        bright_val = quality_data.get("brightness_score", 0.6)
        skew_val = quality_data.get("perspective_skew", False)

        if blur_val < cls.BLUR_THRESHOLD_POOR:
            add_tip("Retake the image while holding the camera steady.")

        if glare_val > 5.0 or glare_val > cls.GLARE_THRESHOLD_PERCENT:
            add_tip("Tilt the package or move away from direct reflections.")

        if rw < cls.MIN_ACCEPTABLE_WIDTH or rh < cls.MIN_ACCEPTABLE_HEIGHT:
            add_tip("Move closer or upload a higher-resolution image.")

        if has_cropped_text:
            add_tip("Include the complete declaration and surrounding label.")

        if skew_val:
            add_tip("Photograph the panel more directly.")

        if bright_val < 0.20 or bright_val > 0.94 or shadow_val > 25.0:
            add_tip("Use even lighting without harsh shadows.")

        return guidance

    @classmethod
    def preprocess_image_for_ocr(cls, input_path: str, output_path: str) -> bool:
        """
        Enhances image for OCR: grayscale conversion, contrast enhancement (CLAHE),
        and subtle denoising.
        """
        try:
            img = cv2.imread(input_path)
            if img is None:
                return False

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Contrast Limited Adaptive Histogram Equalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            cv2.imwrite(output_path, denoised)
            return True
        except Exception:
            return False

    @classmethod
    def run_quality_pipeline(cls, file_path: str, preprocessed_output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs complete quality assessment and applies justified CLAHE/denoising preprocessing
        if image quality indicates blur/contrast issues, then re-evaluates the preprocessed copy.
        """
        original_eval = cls.evaluate_image_file(file_path)
        needs_prep = original_eval["quality_status"] in (ImageQualityStatus.POOR, ImageQualityStatus.ACCEPTABLE)

        if needs_prep and preprocessed_output_path:
            prep_success = cls.preprocess_image_for_ocr(file_path, preprocessed_output_path)
            if prep_success and os.path.exists(preprocessed_output_path):
                prep_eval = cls.evaluate_image_file(preprocessed_output_path)
                return {
                    **original_eval,
                    "preprocessing_applied": True,
                    "preprocessed_path": preprocessed_output_path,
                    "preprocessed_blur_score": prep_eval["blur_score"],
                    "preprocessed_quality_status": prep_eval["quality_status"],
                    "retake_guidance": original_eval.get("retake_guidance", []),
                    "quality_notes": f"{original_eval['quality_notes']} | CLAHE contrast enhancement & denoising applied."
                }

        return {
            **original_eval,
            "preprocessing_applied": False,
            "preprocessed_path": None
        }

