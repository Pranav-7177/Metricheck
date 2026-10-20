import math
from typing import Dict, Any, Optional, Tuple, List

class GeometryService:
    """
    Deterministic geometry extraction and bounding box analysis.
    Supports quadrilateral coordinates from PaddleOCR, axis-aligned boxes,
    and perspective distortion quantification.
    """

    @classmethod
    def parse_box_coordinates(cls, raw_box: Any) -> Optional[Dict[str, float]]:
        """
        Parses various bounding box representations into normalized bounding box attributes.
        Returns a dictionary with x1, y1, x2, y2, w, h, center_x, center_y or None if malformed.
        """
        if not raw_box:
            return None

        try:
            # Format A: 4-point polygon [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] (PaddleOCR default)
            if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4 and isinstance(raw_box[0], (list, tuple)):
                xs = [float(p[0]) for p in raw_box]
                ys = [float(p[1]) for p in raw_box]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)
                w = max(0.0, x2 - x1)
                h = max(0.0, y2 - y1)
                return {
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "w": w, "h": h,
                    "center_x": (x1 + x2) / 2.0,
                    "center_y": (y1 + y2) / 2.0,
                    "polygon": [[float(p[0]), float(p[1])] for p in raw_box]
                }

            # Format B: 4-value list [x1, y1, x2, y2]
            if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4 and all(isinstance(v, (int, float)) for v in raw_box):
                x1, y1, x2, y2 = [float(v) for v in raw_box]
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)
                w = max_x - min_x
                h = max_y - min_y
                return {
                    "x1": min_x, "y1": min_y, "x2": max_x, "y2": max_y,
                    "w": w, "h": h,
                    "center_x": (min_x + max_x) / 2.0,
                    "center_y": (min_y + max_y) / 2.0,
                    "polygon": None
                }

            # Format C: Dictionary with keys
            if isinstance(raw_box, dict):
                if "x1" in raw_box and "y1" in raw_box and "x2" in raw_box and "y2" in raw_box:
                    x1 = float(raw_box["x1"])
                    y1 = float(raw_box["y1"])
                    x2 = float(raw_box["x2"])
                    y2 = float(raw_box["y2"])
                    min_x, max_x = min(x1, x2), max(x1, x2)
                    min_y, max_y = min(y1, y2), max(y1, y2)
                    return {
                        "x1": min_x, "y1": min_y, "x2": max_x, "y2": max_y,
                        "w": max_x - min_x, "h": max_y - min_y,
                        "center_x": (min_x + max_x) / 2.0,
                        "center_y": (min_y + max_y) / 2.0,
                        "polygon": raw_box.get("polygon")
                    }
                elif "x" in raw_box and "y" in raw_box and "w" in raw_box and "h" in raw_box:
                    x = float(raw_box["x"])
                    y = float(raw_box["y"])
                    w = max(0.0, float(raw_box["w"]))
                    h = max(0.0, float(raw_box["h"]))
                    return {
                        "x1": x, "y1": y, "x2": x + w, "y2": y + h,
                        "w": w, "h": h,
                        "center_x": x + w / 2.0,
                        "center_y": y + h / 2.0,
                        "polygon": raw_box.get("polygon")
                    }
        except (ValueError, TypeError, IndexError):
            return None

        return None

    @classmethod
    def analyze_box_geometry(cls, raw_box: Any) -> Dict[str, Any]:
        """
        Computes text height, width, orientation, area, and perspective integrity score.
        """
        parsed = cls.parse_box_coordinates(raw_box)
        if not parsed:
            return {
                "text_height_px": 0.0,
                "text_width_px": 0.0,
                "orientation_deg": 0.0,
                "area_px": 0.0,
                "perspective_score": 1.0,
                "is_curved_surface": False,
                "parsed_box": None
            }

        poly = parsed.get("polygon")
        if poly and len(poly) == 4:
            # Rotated quadrilateral calculation:
            # p0: top-left, p1: top-right, p2: bottom-right, p3: bottom-left
            p0, p1, p2, p3 = poly

            # Edge lengths
            top_w = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            bottom_w = math.hypot(p2[0] - p3[0], p2[1] - p3[1])
            right_h = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            left_h = math.hypot(p3[0] - p0[0], p3[1] - p0[1])

            # Effective dimensions
            text_width_px = max(top_w, bottom_w)
            text_height_px = max(right_h, left_h)

            # Orientation from top horizontal edge
            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]
            orientation_deg = math.degrees(math.atan2(dy, dx)) if (dx != 0 or dy != 0) else 0.0

            # Perspective distortion score: check parallelism of opposite sides
            ratio_w = min(top_w, bottom_w) / max(max(top_w, bottom_w), 1e-5)
            ratio_h = min(left_h, right_h) / max(max(left_h, right_h), 1e-5)
            perspective_score = round(ratio_w * ratio_h, 3)

            # Curved surface check: non-parallel sides or heavy skew
            is_curved_surface = perspective_score < 0.65 or abs(orientation_deg) > 35.0
        else:
            # Axis-aligned box fallback
            text_height_px = parsed["h"]
            text_width_px = parsed["w"]
            orientation_deg = 0.0
            perspective_score = 1.0
            is_curved_surface = False

        area_px = text_width_px * text_height_px

        return {
            "text_height_px": round(text_height_px, 2),
            "text_width_px": round(text_width_px, 2),
            "orientation_deg": round(orientation_deg, 2),
            "area_px": round(area_px, 2),
            "perspective_score": perspective_score,
            "is_curved_surface": is_curved_surface,
            "parsed_box": parsed
        }
