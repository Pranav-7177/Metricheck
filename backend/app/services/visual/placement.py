from typing import Dict, Any, Optional
from app.services.visual.evidence import PlacementRegion, VisibilityStatus

class PlacementService:
    """
    Deterministic declaration placement and visibility analysis.
    Evaluates relative coordinate positioning across package panels and detects boundary clipping.
    """

    @classmethod
    def analyze_placement_and_visibility(
        cls,
        parsed_box: Optional[Dict[str, float]],
        image_width: float = 1000.0,
        image_height: float = 1000.0,
        image_role: str = "front"
    ) -> Dict[str, Any]:
        """
        Determines normalized coordinates, regional placement, and image-edge visibility clipping.
        """
        if not parsed_box:
            return {
                "placement": PlacementRegion.UNKNOWN.value,
                "visibility": VisibilityStatus.OUT_OF_FRAME.value,
                "normalized_x": 0.5,
                "normalized_y": 0.5,
                "explanation": "No spatial bounding box available for placement analysis.",
                "recommendation": None
            }

        from app.services.visual.geometry import GeometryService
        if "center_x" not in parsed_box or "x1" not in parsed_box:
            parsed = GeometryService.parse_box_coordinates(parsed_box)
            if parsed:
                parsed_box = parsed

        img_w = max(image_width, 10.0)
        img_h = max(image_height, 10.0)

        cx = parsed_box.get("center_x", img_w / 2.0)
        cy = parsed_box.get("center_y", img_h / 2.0)

        norm_x = round(min(1.0, max(0.0, cx / img_w)), 3)
        norm_y = round(min(1.0, max(0.0, cy / img_h)), 3)

        # Region quadrant determination
        v_tag = "TOP" if norm_y < 0.33 else ("BOTTOM" if norm_y > 0.66 else "CENTER")
        h_tag = "LEFT" if norm_x < 0.33 else ("RIGHT" if norm_x > 0.66 else "CENTER")

        if v_tag == "CENTER" and h_tag == "CENTER":
            region_name = PlacementRegion.CENTER.value
        elif v_tag == "CENTER":
            region_name = f"CENTER_{h_tag}"
        elif h_tag == "CENTER":
            region_name = f"{v_tag}_CENTER"
        else:
            region_name = f"{v_tag}_{h_tag}"

        # Visibility clipping check
        x1 = parsed_box.get("x1", 0.0)
        y1 = parsed_box.get("y1", 0.0)
        x2 = parsed_box.get("x2", img_w)
        y2 = parsed_box.get("y2", img_h)

        overlap_w = max(0.0, min(x2, img_w) - max(x1, 0.0))
        overlap_h = max(0.0, min(y2, img_h) - max(y1, 0.0))
        is_outside = overlap_w <= 0.0 or overlap_h <= 0.0 or x2 <= 0.0 or y2 <= 0.0 or x1 >= img_w or y1 >= img_h

        # Margin check: touching image boundary (< 4px from border)
        edge_margin = 4.0
        touches_left = x1 <= edge_margin
        touches_top = y1 <= edge_margin
        touches_right = x2 >= (img_w - edge_margin)
        touches_bottom = y2 >= (img_h - edge_margin)

        is_clipped = touches_left or touches_top or touches_right or touches_bottom


        if is_outside:
            visibility = VisibilityStatus.OUT_OF_FRAME.value
            explanation = "The declaration bounding box is located outside the visible camera frame."
            recommendation = "Capture an uncropped photograph centered on this declaration."
        elif is_clipped:
            visibility = VisibilityStatus.PARTIALLY_VISIBLE.value
            explanation = "The declaration is partially outside the visible image region. Capture the complete package panel."
            recommendation = "Capture the complete declaration region."
        else:
            visibility = VisibilityStatus.FULLY_VISIBLE.value
            explanation = f"Declaration is fully visible on the {image_role.upper()} panel ({region_name})."
            recommendation = None

        return {
            "placement": region_name,
            "visibility": visibility,
            "normalized_x": norm_x,
            "normalized_y": norm_y,
            "explanation": explanation,
            "recommendation": recommendation
        }
