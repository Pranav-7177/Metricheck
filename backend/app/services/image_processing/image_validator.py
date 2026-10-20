import hashlib
import io
import os
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageOps

from app.core.config import settings


class ImageValidationError(ValueError):
    """Raised when an uploaded package image is corrupt, empty, or violates safety limits."""
    pass


class ImageValidator:
    """
    Validates uploaded packaging photographs for security, integrity, and geometry.
    Performs:
    1. MIME & file extension validation
    2. File-size and decompression-bomb safety limits
    3. Decode verification and EXIF orientation transposition
    4. Deterministic content hashing (SHA-256)
    5. Lightweight perceptual hashing (dHash)
    6. Multi-image duplicate & near-duplicate detection
    """

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max per image
    MAX_PIXELS = 50_000_000                  # 50 Megapixels max
    DEFAULT_NEAR_DUP_THRESHOLD = 6           # Max Hamming distance (out of 64 bits)

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

    SUPPORTED_ROLES = {
        "front": "FRONT",
        "back": "BACK",
        "side": "SIDE",
        "left_side": "LEFT_SIDE",
        "right_side": "RIGHT_SIDE",
        "top": "TOP",
        "bottom": "BOTTOM",
        "close_up": "CLOSE_UP",
        "unknown": "UNKNOWN",
        "other": "OTHER",
    }

    @classmethod
    def normalize_role(cls, role_input: Optional[str]) -> str:
        """
        Normalizes image panel role metadata.
        Retains UNKNOWN when unclassified rather than inventing a role.
        """
        if not role_input:
            return "UNKNOWN"
        cleaned = role_input.strip().lower().replace("-", "_").replace(" ", "_")
        return cls.SUPPORTED_ROLES.get(cleaned, "UNKNOWN")

    @classmethod
    def compute_sha256(cls, file_bytes: bytes) -> str:
        """Computes deterministic cryptographic SHA-256 content hash."""
        return hashlib.sha256(file_bytes).hexdigest()

    @classmethod
    def compute_dhash(cls, pil_img: Image.Image, hash_size: int = 8) -> str:
        """
        Computes difference perceptual hash (dHash).
        Resizes to (hash_size + 1, hash_size) grayscale, compares adjacent columns.
        Returns 16-character hexadecimal string representing 64-bit fingerprint.
        """
        try:
            gray = pil_img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BOX)
            if hasattr(gray, "get_flattened_data"):
                pixels = list(gray.get_flattened_data())
            else:
                pixels = list(gray.getdata())
            width = hash_size + 1
            diff = []
            for row in range(hash_size):
                row_start = row * width
                for col in range(hash_size):
                    diff.append(pixels[row_start + col] > pixels[row_start + col + 1])
            decimal_val = 0
            for bit in diff:
                decimal_val = (decimal_val << 1) | (1 if bit else 0)
            return f"{decimal_val:016x}"
        except Exception:
            return "0" * 16

    @classmethod
    def hamming_distance(cls, hash1_hex: str, hash2_hex: str) -> int:
        """Computes Hamming distance between two hex perceptual hashes."""
        if not hash1_hex or not hash2_hex:
            return 64
        try:
            val1 = int(hash1_hex, 16)
            val2 = int(hash2_hex, 16)
            return bin(val1 ^ val2).count("1")
        except Exception:
            return 64

    @classmethod
    def validate_and_save_upload(
        cls,
        file_bytes: bytes,
        filename: str,
        target_path: str,
        max_size_bytes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Safely validates and writes uploaded packaging image.
        Applies EXIF orientation normalization so all downstream CV and OCR
        receive properly oriented photographs.
        """
        limit = max_size_bytes or cls.MAX_FILE_SIZE_BYTES

        # 1. Byte length checks
        if not file_bytes or len(file_bytes) == 0:
            raise ImageValidationError("Uploaded image is empty (0 bytes).")

        if len(file_bytes) > limit:
            raise ImageValidationError(
                f"Image file size ({len(file_bytes)} bytes) exceeds the maximum allowed limit of {limit} bytes."
            )

        # 2. File extension check
        ext = os.path.splitext(filename)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ImageValidationError(
                f"Unsupported image format '{ext}'. Supported formats: {sorted(list(cls.ALLOWED_EXTENSIONS))}"
            )

        # 3. Decode & Decompression Bomb Protection
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()  # verify headers
        except Exception as e:
            raise ImageValidationError(f"Malformed or corrupt image file: {str(e)}")

        # Re-open after verify() (Pillow verify closes/invalidates the stream)
        try:
            img = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ImageValidationError(f"Unable to decode image pixels: {str(e)}")

        w, h = img.size
        if w <= 0 or h <= 0:
            raise ImageValidationError("Invalid image dimensions (0x0).")

        if (w * h) > cls.MAX_PIXELS:
            raise ImageValidationError(
                f"Image resolution ({w}x{h} = {w * h} pixels) exceeds safety limit of {cls.MAX_PIXELS} pixels."
            )

        # 4. Handle EXIF Orientation transpose (camera / mobile uploads)
        transposed_img = ImageOps.exif_transpose(img)
        if transposed_img is None:
            transposed_img = img

        new_w, new_h = transposed_img.size

        # 5. Save normalized image to disk
        dir_name = os.path.dirname(target_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        # Convert RGBA to RGB for JPEG target
        if ext in (".jpg", ".jpeg") and transposed_img.mode in ("RGBA", "P"):
            save_img = transposed_img.convert("RGB")
        else:
            save_img = transposed_img

        save_img.save(target_path)

        # 6. Compute Hashes
        content_hash = cls.compute_sha256(file_bytes)
        perceptual_hash = cls.compute_dhash(transposed_img)

        return {
            "is_valid": True,
            "filename": filename,
            "target_path": target_path,
            "width": new_w,
            "height": new_h,
            "format": img.format or ext.lstrip(".").upper(),
            "content_hash": content_hash,
            "perceptual_hash": perceptual_hash,
            "file_size_bytes": len(file_bytes),
            "orientation_transposed": (w != new_w or h != new_h)
        }

    @classmethod
    def detect_duplicates(
        cls,
        images_meta: List[Dict[str, Any]],
        near_dup_threshold: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Detects exact and near-duplicate images within a multi-image scan.
        Records duplicate relationships without deleting original uploads.
        """
        threshold = near_dup_threshold if near_dup_threshold is not None else cls.DEFAULT_NEAR_DUP_THRESHOLD
        annotated: List[Dict[str, Any]] = []

        for idx, cur in enumerate(images_meta):
            entry = dict(cur)
            entry["is_duplicate"] = False
            entry["duplicate_of_id"] = None
            entry["duplicate_type"] = None
            entry["duplicate_reason"] = None

            cur_chash = entry.get("content_hash")
            cur_phash = entry.get("perceptual_hash")
            cur_w = entry.get("width") or entry.get("resolution_w") or 1
            cur_h = entry.get("height") or entry.get("resolution_h") or 1
            cur_aspect = cur_w / max(cur_h, 1)

            # Compare against preceding images
            for prior in annotated:
                prior_id = prior.get("id") or prior.get("image_id")
                prior_chash = prior.get("content_hash")
                prior_phash = prior.get("perceptual_hash")
                prior_w = prior.get("width") or prior.get("resolution_w") or 1
                prior_h = prior.get("height") or prior.get("resolution_h") or 1
                prior_aspect = prior_w / max(prior_h, 1)

                # 1. Exact duplicate check (SHA-256)
                if cur_chash and prior_chash and cur_chash == prior_chash:
                    entry["is_duplicate"] = True
                    entry["duplicate_of_id"] = prior_id
                    entry["duplicate_type"] = "EXACT"
                    entry["duplicate_reason"] = "Exact cryptographic byte match (SHA-256)"
                    break

                # 2. Near-duplicate check (Perceptual hash dHash)
                if cur_phash and prior_phash:
                    dist = cls.hamming_distance(cur_phash, prior_phash)
                    # Also require aspect ratio agreement so different panels aren't conflated
                    if dist <= threshold and abs(cur_aspect - prior_aspect) <= 0.25:
                        entry["is_duplicate"] = True
                        entry["duplicate_of_id"] = prior_id
                        entry["duplicate_type"] = "NEAR_DUPLICATE"
                        entry["duplicate_reason"] = (
                            f"Near-duplicate photograph detected (perceptual Hamming distance {dist} <= {threshold})"
                        )
                        break

            annotated.append(entry)

        return annotated
