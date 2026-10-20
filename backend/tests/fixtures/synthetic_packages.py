"""Synthetic Package Generator for MetriCheck Validation & Stress Testing.

Generates realistic packaged commodity images with known statutory declarations
and controlled optical/physical perturbations (blur, glare, lighting, perspective, small text).
"""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def _get_font(size: int, prefer_unicode: bool = True) -> ImageFont.FreeTypeFont:
    """Load system font with Unicode support for ₹ symbol."""
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf"] if prefer_unicode else ["arial.ttf"]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_package_label(
    product_name: str = "ORGANIC BASMATI RICE",
    mrp: str = "MRP: ₹299.00 (Incl. of all taxes)",
    net_qty: str = "Net Quantity: 5 kg",
    mfg_date: str = "Mfg Date: 15/01/2026",
    exp_date: str = "Exp Date: 14/01/2027",
    best_before: str = "Best Before 12 Months from Packaging",
    manufacturer: str = "Manufactured by: Krishna Agro Foods Ltd, Plot 42, Gurugram, Haryana - 122015",
    packer: str = "Packed by: Apex Packaging Ltd, Okhla, New Delhi - 110020",
    consumer_care: str = "Consumer Care: 1800-111-2222 or care@krishnaagro.com",
    country_of_origin: str = "Country of Origin: India",
    distractors: Optional[List[str]] = None,
    width: int = 1000,
    height: int = 700,
    small_text: bool = False,
) -> Image.Image:
    """Renders a clean, realistic statutory packaging label on a simulated cardboard/pouch background."""
    # Background: simulated natural packaging material
    img = Image.new("RGB", (width, height), color=(238, 235, 228))
    draw = ImageDraw.Draw(img)

    # Decorative packaging borders
    draw.rectangle([(15, 15), (width - 15, height - 15)], outline=(200, 195, 185), width=2)
    draw.rectangle([(25, 25), (width - 25, height - 25)], outline=(40, 70, 45), width=3)

    # Header banner
    draw.rectangle([(28, 28), (width - 28, 90)], fill=(40, 70, 45))
    header_font = _get_font(28 if not small_text else 22)
    draw.text((width // 2, 59), "PREMIUM QUALITY FOOD PRODUCTS", fill=(255, 255, 255), font=header_font, anchor="mm")

    # Product Title
    title_font = _get_font(34 if not small_text else 24)
    draw.text((width // 2, 130), product_name, fill=(20, 20, 20), font=title_font, anchor="mm")

    # Statutory information box
    box_top = 170
    box_bottom = height - 40
    draw.rectangle([(45, box_top), (width - 45, box_bottom)], fill=(242, 240, 235), outline=(180, 180, 180), width=1)
    
    # Subheader for mandatory declarations
    decl_header_font = _get_font(18 if not small_text else 14)
    draw.text((60, box_top + 15), "MANDATORY STATUTORY DECLARATIONS", fill=(80, 80, 80), font=decl_header_font)
    draw.line([(60, box_top + 35), (width - 60, box_top + 35)], fill=(220, 220, 220), width=1)

    # Font sizes for body declarations
    body_font_size = 13 if small_text else 18
    body_font = _get_font(body_font_size)
    bold_font = _get_font(body_font_size + 2)

    # Left column: Pricing, Quantity, Dates
    cur_y = box_top + 50
    left_x = 60
    line_spacing = 26 if small_text else 36

    # Net Quantity
    draw.text((left_x, cur_y), net_qty, fill=(10, 10, 10), font=bold_font)
    cur_y += line_spacing

    # MRP
    draw.text((left_x, cur_y), mrp, fill=(10, 10, 10), font=bold_font)
    cur_y += line_spacing

    # Manufacturing & Expiry Dates
    draw.text((left_x, cur_y), mfg_date, fill=(20, 20, 20), font=body_font)
    cur_y += line_spacing
    draw.text((left_x, cur_y), exp_date, fill=(20, 20, 20), font=body_font)
    cur_y += line_spacing
    draw.text((left_x, cur_y), best_before, fill=(50, 50, 50), font=body_font)
    cur_y += line_spacing

    # Country of Origin
    draw.text((left_x, cur_y), country_of_origin, fill=(20, 20, 20), font=body_font)
    cur_y += line_spacing + 5

    # Right column or lower section: Manufacturer, Packer, Consumer Care
    cur_y = box_top + 50
    right_x = width // 2 + 10

    draw.text((right_x, cur_y), "Commercial Details:", fill=(100, 100, 100), font=_get_font(body_font_size - 1))
    cur_y += 24

    # Multi-line Manufacturer
    mfd_lines = [
        manufacturer[:50],
        manufacturer[50:100] if len(manufacturer) > 50 else "",
        manufacturer[100:] if len(manufacturer) > 100 else "",
    ]
    for line in mfd_lines:
        if line.strip():
            draw.text((right_x, cur_y), line.strip(), fill=(25, 25, 25), font=body_font)
            cur_y += line_spacing - 6

    cur_y += 6
    # Packer
    draw.text((right_x, cur_y), packer, fill=(35, 35, 35), font=body_font)
    cur_y += line_spacing

    # Consumer Care
    draw.text((right_x, cur_y), consumer_care, fill=(20, 20, 20), font=body_font)
    cur_y += line_spacing

    # Optional Distractors (non-statutory numbers, discounts, barcodes)
    if distractors:
        cur_y += 10
        for dist in distractors:
            draw.text((left_x, cur_y), dist, fill=(120, 120, 120), font=body_font)
            cur_y += line_spacing - 8

    return img


# ---------------------------------------------------------------------------
# Perturbation Functions
# ---------------------------------------------------------------------------

def apply_blur(image: Image.Image, sigma: float = 2.0, radius: Optional[float] = None) -> Image.Image:
    """Applies Gaussian blur with given radius or sigma."""
    r = radius if radius is not None else sigma
    return image.filter(ImageFilter.GaussianBlur(radius=r))


def apply_glare(
    image: Image.Image,
    center: Optional[Tuple[int, int]] = None,
    radius: int = 120,
    intensity: float = 0.85,
) -> Image.Image:
    """Simulates a hot specular glare spot reflecting off packaging laminate."""
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w = cv_img.shape[:2]
    if center is None:
        center = (w // 3, h // 2)

    mask = np.zeros((h, w), dtype=np.float32)
    cv2.circle(mask, center, radius, 1.0, -1)
    # Smooth radial falloff
    mask = cv2.GaussianBlur(mask, (radius * 2 + 1, radius * 2 + 1), radius / 2)

    # Blend white reflection
    white_overlay = np.full_like(cv_img, 255)
    mask_3ch = np.stack([mask * intensity] * 3, axis=-1)
    blended = (cv_img * (1.0 - mask_3ch) + white_overlay * mask_3ch).clip(0, 255).astype(np.uint8)

    return Image.fromarray(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))


def apply_lighting(
    image: Image.Image,
    brightness_factor: float = 1.0,
    gradient: bool = False,
) -> Image.Image:
    """Simulates underexposure, overexposure, or directional non-uniform lighting."""
    if not gradient:
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(brightness_factor)

    # Directional gradient lighting
    arr = np.array(image, dtype=np.float32)
    h, w = arr.shape[:2]
    # Linear ramp from 0.35 to 1.35 across width
    ramp = np.linspace(0.35, 1.35, w).reshape(1, w, 1)
    arr = (arr * ramp).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def apply_perspective_tilt(image: Image.Image, angle_deg: float = 20.0) -> Image.Image:
    """Simulates realistic handheld angled photo perspective."""
    cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w = cv_img.shape[:2]

    # Compute tilt distortion
    rad = math.radians(angle_deg)
    dx = int(w * 0.15 * math.sin(rad))
    dy = int(h * 0.10 * math.sin(rad))

    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst_pts = np.float32([[dx, dy], [w - dx, 0], [w, h], [0, h - dy]])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(cv_img, M, (w, h), borderValue=(240, 240, 240))
    return Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))


# ---------------------------------------------------------------------------
# Test Matrix Catalog
# ---------------------------------------------------------------------------

def generate_validation_dataset(output_dir: Path) -> List[Dict[str, Any]]:
    """Generates the Master Prompt 06 controlled test matrix images on disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog = []

    # 1. Category A: GOOD IMAGE (Sharp, balanced lighting)
    good_img = render_package_label()
    p_good = output_dir / "val_01_good_clean.png"
    good_img.save(p_good)
    catalog.append({
        "id": "VAL_01_GOOD",
        "path": str(p_good),
        "condition": "GOOD",
        "description": "Sharp, clean packaging label with balanced lighting and clear text",
        "expected_quality": "EXCELLENT",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY", "MANUFACTURING_DATE", "EXPIRY_DATE", "BEST_BEFORE", "MANUFACTURER", "PACKER", "CONSUMER_CARE", "COUNTRY_OF_ORIGIN"],
        "expected_status": "PASS",
    })

    # 2. Category B: BLUR VARIATIONS
    # Mild blur
    b_mild = apply_blur(good_img, sigma=1.0)
    p_b_mild = output_dir / "val_02_blur_mild.png"
    b_mild.save(p_b_mild)
    catalog.append({
        "id": "VAL_02_BLUR_MILD",
        "path": str(p_b_mild),
        "condition": "BLUR_MILD",
        "description": "Mild Gaussian blur (sigma=1.0), OCR should succeed",
        "expected_quality": "GOOD",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY", "MANUFACTURING_DATE", "EXPIRY_DATE"],
        "expected_status": "PASS",
    })

    # Moderate blur
    b_mod = apply_blur(good_img, sigma=2.5)
    p_b_mod = output_dir / "val_03_blur_moderate.png"
    b_mod.save(p_b_mod)
    catalog.append({
        "id": "VAL_03_BLUR_MODERATE",
        "path": str(p_b_mod),
        "condition": "BLUR_MODERATE",
        "description": "Moderate Gaussian blur (sigma=2.5), preprocessing retry candidate",
        "expected_quality": "POOR",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY"],
        "expected_status": "PASS_OR_WARNING",
    })

    # Severe blur
    b_sev = apply_blur(good_img, sigma=5.5)
    p_b_sev = output_dir / "val_04_blur_severe.png"
    b_sev.save(p_b_sev)
    catalog.append({
        "id": "VAL_04_BLUR_SEVERE",
        "path": str(p_b_sev),
        "condition": "BLUR_SEVERE",
        "description": "Severe blur (sigma=5.5), text unreadable -> UNABLE_TO_VERIFY",
        "expected_quality": "CRITICAL",
        "expected_fields": [],
        "expected_status": "UNABLE_TO_VERIFY",
    })

    # 3. Category C: GLARE VARIATIONS
    # Mild reflection
    g_mild = apply_glare(good_img, center=(800, 200), radius=90, intensity=0.55)
    p_g_mild = output_dir / "val_05_glare_mild.png"
    g_mild.save(p_g_mild)
    catalog.append({
        "id": "VAL_05_GLARE_MILD",
        "path": str(p_g_mild),
        "condition": "GLARE_MILD",
        "description": "Mild specular glare on corner not covering text",
        "expected_quality": "GOOD",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY", "MANUFACTURING_DATE"],
        "expected_status": "PASS",
    })

    # Glare directly covering MRP
    # MRP is located at (60, 256) approximately
    g_mrp = apply_glare(good_img, center=(180, 260), radius=100, intensity=0.92)
    p_g_mrp = output_dir / "val_06_glare_over_mrp.png"
    g_mrp.save(p_g_mrp)
    catalog.append({
        "id": "VAL_06_GLARE_OVER_MRP",
        "path": str(p_g_mrp),
        "condition": "GLARE_MRP",
        "description": "Strong specular glare covering MRP text -> MRP UNABLE_TO_VERIFY",
        "expected_quality": "POOR",
        "expected_fields": ["PRODUCT_NAME", "NET_QUANTITY", "MANUFACTURING_DATE"],
        "expected_status": "UNABLE_TO_VERIFY",
    })

    # 4. Category D: LIGHTING VARIATIONS
    # Dark / Underexposed
    l_dark = apply_lighting(good_img, brightness_factor=0.38)
    p_l_dark = output_dir / "val_07_lighting_dark.png"
    l_dark.save(p_l_dark)
    catalog.append({
        "id": "VAL_07_LIGHTING_DARK",
        "path": str(p_l_dark),
        "condition": "LIGHTING_DARK",
        "description": "Underexposed image (brightness=0.38), CLAHE retry candidate",
        "expected_quality": "FAIR",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY"],
        "expected_status": "PASS",
    })

    # Overexposed / Washed out
    l_over = apply_lighting(good_img, brightness_factor=1.75)
    p_l_over = output_dir / "val_08_lighting_overexposed.png"
    l_over.save(p_l_over)
    catalog.append({
        "id": "VAL_08_LIGHTING_OVEREXPOSED",
        "path": str(p_l_over),
        "condition": "LIGHTING_OVEREXPOSED",
        "description": "Overexposed image (brightness=1.75)",
        "expected_quality": "FAIR",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY"],
        "expected_status": "PASS",
    })

    # Uneven gradient lighting
    l_grad = apply_lighting(good_img, gradient=True)
    p_l_grad = output_dir / "val_09_lighting_uneven.png"
    l_grad.save(p_l_grad)
    catalog.append({
        "id": "VAL_09_LIGHTING_UNEVEN",
        "path": str(p_l_grad),
        "condition": "LIGHTING_UNEVEN",
        "description": "Uneven directional lighting gradient across package",
        "expected_quality": "GOOD",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY"],
        "expected_status": "PASS",
    })

    # 5. Category E: PERSPECTIVE TILT
    p_tilt = apply_perspective_tilt(good_img, angle_deg=22.0)
    p_p_tilt = output_dir / "val_10_perspective_tilt.png"
    p_tilt.save(p_p_tilt)
    catalog.append({
        "id": "VAL_10_PERSPECTIVE_TILT",
        "path": str(p_p_tilt),
        "condition": "PERSPECTIVE_TILT",
        "description": "22 degree perspective angle tilt, verifying polygon bounding boxes",
        "expected_quality": "GOOD",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY"],
        "expected_status": "PASS",
    })

    # 6. Category F: SMALL STATUTORY TEXT
    small_img = render_package_label(small_text=True, width=900, height=600)
    p_small = output_dir / "val_11_small_text.png"
    small_img.save(p_small)
    catalog.append({
        "id": "VAL_11_SMALL_TEXT",
        "path": str(p_small),
        "condition": "SMALL_TEXT",
        "description": "Small statutory declarations (12-14px) relative to title",
        "expected_quality": "EXCELLENT",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY", "MANUFACTURING_DATE"],
        "expected_status": "PASS",
    })

    # 7. Category G: FALSE POSITIVE DISTRACTORS
    distractor_img = render_package_label(
        distractors=[
            "Special Promo: Save 20% Today!",
            "Net Carbs: 45 g per 100 g serving",
            "Batch Ref: BATCH-889920",
            "Contact for Distributor inquiries: 9988776655",
        ]
    )
    p_dist = output_dir / "val_12_distractors.png"
    distractor_img.save(p_dist)
    catalog.append({
        "id": "VAL_12_DISTRACTORS",
        "path": str(p_dist),
        "condition": "DISTRACTORS",
        "description": "Contains non-statutory percentages, serving numbers, and distributor phones",
        "expected_quality": "EXCELLENT",
        "expected_fields": ["PRODUCT_NAME", "MRP", "NET_QUANTITY", "CONSUMER_CARE"],
        "expected_status": "PASS",
    })

    return catalog
