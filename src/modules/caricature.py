"""
Caricature filter core: detects facial expressions via MediaPipe Face Mesh
and applies stylized exaggeration + cartoon shading per frame.

Pipeline per frame:
  1. Detect 468 face landmarks
  2. Compute expression intensities relative to neutral baseline
  3. Exaggerate intensities (power curve + multiplier)
  4. Warp face regions (eyes, brows, mouth) to exaggerated positions
  5. Apply cartoon shader (bilateral smooth + edge overlay + saturation)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# MediaPipe landmark indices for key facial features
# ---------------------------------------------------------------------------
# Mouth
MOUTH_TOP_IDX = 13
MOUTH_BOTTOM_IDX = 14
MOUTH_LEFT_IDX = 61
MOUTH_RIGHT_IDX = 291

# Eyes
LEFT_EYE_TOP_IDX = 159
LEFT_EYE_BOTTOM_IDX = 145
RIGHT_EYE_TOP_IDX = 386
RIGHT_EYE_BOTTOM_IDX = 374
LEFT_EYE_CENTER_IDX = 468   # iris center (requires refine_landmarks=True)
RIGHT_EYE_CENTER_IDX = 473

# Eyebrows
LEFT_BROW_IDX = 107
RIGHT_BROW_IDX = 336
LEFT_EYE_UPPER_IDX = 159
RIGHT_EYE_UPPER_IDX = 386

# Face boundary for scale reference
CHIN_IDX = 152
FOREHEAD_IDX = 10
LEFT_CHEEK_IDX = 234
RIGHT_CHEEK_IDX = 454


@dataclass
class ExpressionState:
    mouth_open: float = 0.0      # 0 (closed) → 1 (fully open)
    smile: float = 0.0           # 0 (neutral) → 1 (wide smile)
    left_brow_raise: float = 0.0 # 0 (neutral) → 1 (fully raised)
    right_brow_raise: float = 0.0
    left_eye_wide: float = 0.0   # 0 (normal) → 1 (wide open / surprised)
    right_eye_wide: float = 0.0

    @property
    def surprise(self) -> float:
        brow = (self.left_brow_raise + self.right_brow_raise) / 2
        eye = (self.left_eye_wide + self.right_eye_wide) / 2
        return (brow + eye) / 2

    @property
    def happiness(self) -> float:
        return (self.smile + self.mouth_open * 0.3) / 1.3


@dataclass
class NeutralBaseline:
    """Neutral face landmark ratios for one person, loaded from their calibration photo."""
    mouth_open_ratio: float = 0.02
    smile_ratio: float = 0.45
    left_brow_eye_ratio: float = 0.12
    right_brow_eye_ratio: float = 0.12
    left_eye_ratio: float = 0.09
    right_eye_ratio: float = 0.09

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: Path) -> "NeutralBaseline":
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def default(cls) -> "NeutralBaseline":
        return cls()


class CaricatureFilter:
    """
    Applies a caricature + cartoon effect to video frames.
    Exaggerates facial expressions relative to a personal neutral baseline.
    """

    def __init__(
        self,
        exaggeration: float = 2.5,
        cartoon_strength: float = 0.75,
        neutral: Optional[NeutralBaseline] = None,
    ) -> None:
        self.exaggeration = exaggeration
        self.cartoon_strength = cartoon_strength
        self.neutral = neutral or NeutralBaseline.default()
        self._face_mesh = None

    def _get_mesh(self):
        if self._face_mesh is None:
            import mediapipe as mp
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        return self._face_mesh

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Apply the full caricature pipeline to one BGR frame."""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = self._get_mesh().process(rgb)
        if not result.multi_face_landmarks:
            # No face detected — apply light cartoon shader only
            return self._apply_cartoon_shader(frame)

        lm = result.multi_face_landmarks[0].landmark
        pts = np.array([[int(l.x * w), int(l.y * h)] for l in lm], dtype=np.float32)

        expressions = self._detect_expressions(pts, h, w)
        warped = self._apply_feature_warp(frame.copy(), pts, expressions, h, w)
        cartoon = self._apply_cartoon_shader(warped)
        return self._add_reaction_overlay(cartoon, expressions, h, w)

    def calibrate(self, frame: np.ndarray) -> NeutralBaseline:
        """Extract neutral ratios from a frame or photo of the person."""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        import mediapipe as mp
        mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
        result = mesh.process(rgb)
        mesh.close()

        if not result.multi_face_landmarks:
            return NeutralBaseline.default()

        lm = result.multi_face_landmarks[0].landmark
        pts = np.array([[int(l.x * w), int(l.y * h)] for l in lm], dtype=np.float32)

        face_h = _dist(pts[FOREHEAD_IDX], pts[CHIN_IDX])
        face_w = _dist(pts[LEFT_CHEEK_IDX], pts[RIGHT_CHEEK_IDX])

        mouth_open = _dist(pts[MOUTH_TOP_IDX], pts[MOUTH_BOTTOM_IDX]) / face_h
        smile = _dist(pts[MOUTH_LEFT_IDX], pts[MOUTH_RIGHT_IDX]) / face_w
        left_brow_eye = (pts[LEFT_BROW_IDX][1] - pts[LEFT_EYE_UPPER_IDX][1]) / face_h * -1
        right_brow_eye = (pts[RIGHT_BROW_IDX][1] - pts[RIGHT_EYE_UPPER_IDX][1]) / face_h * -1
        left_eye = _dist(pts[LEFT_EYE_TOP_IDX], pts[LEFT_EYE_BOTTOM_IDX]) / face_h
        right_eye = _dist(pts[RIGHT_EYE_TOP_IDX], pts[RIGHT_EYE_BOTTOM_IDX]) / face_h

        baseline = NeutralBaseline(
            mouth_open_ratio=float(max(mouth_open, 0.01)),
            smile_ratio=float(max(smile, 0.1)),
            left_brow_eye_ratio=float(max(left_brow_eye, 0.05)),
            right_brow_eye_ratio=float(max(right_brow_eye, 0.05)),
            left_eye_ratio=float(max(left_eye, 0.03)),
            right_eye_ratio=float(max(right_eye, 0.03)),
        )
        self.neutral = baseline
        return baseline

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_expressions(self, pts: np.ndarray, h: int, w: int) -> ExpressionState:
        face_h = max(_dist(pts[FOREHEAD_IDX], pts[CHIN_IDX]), 1)
        face_w = max(_dist(pts[LEFT_CHEEK_IDX], pts[RIGHT_CHEEK_IDX]), 1)

        mouth_open_raw = _dist(pts[MOUTH_TOP_IDX], pts[MOUTH_BOTTOM_IDX]) / face_h
        smile_raw = _dist(pts[MOUTH_LEFT_IDX], pts[MOUTH_RIGHT_IDX]) / face_w
        l_brow_raw = max(0.0, (pts[LEFT_EYE_UPPER_IDX][1] - pts[LEFT_BROW_IDX][1]) / face_h)
        r_brow_raw = max(0.0, (pts[RIGHT_EYE_UPPER_IDX][1] - pts[RIGHT_BROW_IDX][1]) / face_h)
        l_eye_raw = _dist(pts[LEFT_EYE_TOP_IDX], pts[LEFT_EYE_BOTTOM_IDX]) / face_h
        r_eye_raw = _dist(pts[RIGHT_EYE_TOP_IDX], pts[RIGHT_EYE_BOTTOM_IDX]) / face_h

        n = self.neutral
        mouth_open = _clamp(_normalize(mouth_open_raw, n.mouth_open_ratio, 0.15))
        smile = _clamp(_normalize(smile_raw, n.smile_ratio, 0.65))
        l_brow = _clamp(_normalize(l_brow_raw, n.left_brow_eye_ratio, 0.22))
        r_brow = _clamp(_normalize(r_brow_raw, n.right_brow_eye_ratio, 0.22))
        l_eye = _clamp(_normalize(l_eye_raw, n.left_eye_ratio, 0.16))
        r_eye = _clamp(_normalize(r_eye_raw, n.right_eye_ratio, 0.16))

        return ExpressionState(
            mouth_open=_exaggerate(mouth_open, self.exaggeration),
            smile=_exaggerate(smile, self.exaggeration * 0.8),
            left_brow_raise=_exaggerate(l_brow, self.exaggeration),
            right_brow_raise=_exaggerate(r_brow, self.exaggeration),
            left_eye_wide=_exaggerate(l_eye, self.exaggeration * 1.2),
            right_eye_wide=_exaggerate(r_eye, self.exaggeration * 1.2),
        )

    def _apply_feature_warp(
        self,
        frame: np.ndarray,
        pts: np.ndarray,
        expr: ExpressionState,
        h: int,
        w: int,
    ) -> np.ndarray:
        """Warp facial feature regions based on exaggerated expression values."""
        face_h = max(_dist(pts[FOREHEAD_IDX], pts[CHIN_IDX]), 1)

        result = frame.copy()

        # ---- Eyes: scale vertically when wide open ----
        eye_scale = 1.0 + expr.left_eye_wide * 0.35
        result = _warp_region_scale(result, pts, LEFT_EYE_TOP_IDX, LEFT_EYE_BOTTOM_IDX,
                                    eye_scale, face_h * 0.1, h, w)

        eye_scale = 1.0 + expr.right_eye_wide * 0.35
        result = _warp_region_scale(result, pts, RIGHT_EYE_TOP_IDX, RIGHT_EYE_BOTTOM_IDX,
                                    eye_scale, face_h * 0.1, h, w)

        # ---- Brows: shift upward when raised ----
        brow_shift = int(expr.left_brow_raise * face_h * 0.06)
        result = _shift_region(result, pts, LEFT_BROW_IDX, face_h * 0.06, 0, -brow_shift, h, w)

        brow_shift = int(expr.right_brow_raise * face_h * 0.06)
        result = _shift_region(result, pts, RIGHT_BROW_IDX, face_h * 0.06, 0, -brow_shift, h, w)

        # ---- Mouth: scale vertically when open, horizontally when smiling ----
        mouth_v_scale = 1.0 + expr.mouth_open * 0.5
        mouth_h_scale = 1.0 + expr.smile * 0.3
        result = _warp_mouth(result, pts, mouth_v_scale, mouth_h_scale, face_h, h, w)

        return result

    def _apply_cartoon_shader(self, frame: np.ndarray) -> np.ndarray:
        """Bilateral smooth + edge detection overlay for cartoon look."""
        # Progressive bilateral filter passes for strong cartoon smoothing
        smooth = frame
        for _ in range(3):
            smooth = cv2.bilateralFilter(smooth, d=9, sigmaColor=75, sigmaSpace=75)

        # Edge detection on grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            blockSize=9,
            C=2,
        )
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # Combine: smooth frame with dark edges
        cartoon = cv2.bitwise_and(smooth, edges)

        # Boost saturation
        hsv = cv2.cvtColor(cartoon, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * 1.4, 0, 255)
        cartoon = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Blend with original by cartoon_strength
        return cv2.addWeighted(cartoon, self.cartoon_strength,
                               frame, 1 - self.cartoon_strength, 0)

    def _add_reaction_overlay(
        self,
        frame: np.ndarray,
        expr: ExpressionState,
        h: int,
        w: int,
    ) -> np.ndarray:
        """Add subtle comic-style visual cues on strong reactions."""
        if expr.surprise > 0.7:
            frame = _draw_shock_lines(frame, h, w, int(expr.surprise * 12))
        if expr.mouth_open > 0.85:
            frame = _draw_sweat_drop(frame, h, w)
        return frame

    def close(self) -> None:
        if self._face_mesh:
            self._face_mesh.close()
            self._face_mesh = None


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _normalize(value: float, neutral: float, peak: float) -> float:
    """Map value from [neutral, peak] → [0, 1]."""
    span = peak - neutral
    if span <= 0:
        return 0.0
    return (value - neutral) / span


def _exaggerate(intensity: float, factor: float) -> float:
    """Non-linear exaggeration: small movements get amplified more than large ones."""
    exag = pow(intensity, 0.6) * factor
    return _clamp(exag)


def _warp_region_scale(
    frame: np.ndarray,
    pts: np.ndarray,
    top_idx: int,
    bottom_idx: int,
    scale: float,
    radius: float,
    h: int,
    w: int,
) -> np.ndarray:
    """Scale a circular region around the midpoint of two landmarks."""
    center = ((pts[top_idx] + pts[bottom_idx]) / 2).astype(int)
    r = int(radius)
    cx, cy = int(center[0]), int(center[1])

    x1, x2 = max(cx - r, 0), min(cx + r, w)
    y1, y2 = max(cy - r, 0), min(cy + r, h)
    if x1 >= x2 or y1 >= y2:
        return frame

    region = frame[y1:y2, x1:x2]
    rh, rw = region.shape[:2]
    scaled = cv2.resize(region, (int(rw * scale), int(rh * scale)))

    # Paste back, centered
    sh, sw = scaled.shape[:2]
    dy, dx = (sh - rh) // 2, (sw - rw) // 2
    src_y1, src_x1 = max(dy, 0), max(dx, 0)
    src_y2, src_x2 = src_y1 + rh, src_x1 + rw
    src_y2 = min(src_y2, sh)
    src_x2 = min(src_x2, sw)

    patch = scaled[src_y1:src_y2, src_x1:src_x2]
    ph, pw = patch.shape[:2]
    if ph > 0 and pw > 0:
        frame[y1:y1 + ph, x1:x1 + pw] = patch

    return frame


def _shift_region(
    frame: np.ndarray,
    pts: np.ndarray,
    center_idx: int,
    radius: float,
    dx: int,
    dy: int,
    h: int,
    w: int,
) -> np.ndarray:
    """Translate a circular region by (dx, dy)."""
    cx, cy = int(pts[center_idx][0]), int(pts[center_idx][1])
    r = int(radius)

    x1, x2 = max(cx - r, 0), min(cx + r, w)
    y1, y2 = max(cy - r, 0), min(cy + r, h)
    if x1 >= x2 or y1 >= y2:
        return frame

    region = frame[y1:y2, x1:x2].copy()
    rh, rw = region.shape[:2]

    # Create Gaussian blend mask for smooth edges
    mask = _gaussian_mask(rh, rw)

    nx1 = _clamp(x1 + dx, 0, w - rw)
    ny1 = _clamp(y1 + dy, 0, h - rh)
    nx2, ny2 = nx1 + rw, ny1 + rh

    if nx2 > w or ny2 > h:
        return frame

    dst = frame[ny1:ny2, nx1:nx2].astype(np.float32)
    src = region.astype(np.float32)
    blended = src * mask + dst * (1 - mask)
    frame[ny1:ny2, nx1:nx2] = blended.astype(np.uint8)
    return frame


def _warp_mouth(
    frame: np.ndarray,
    pts: np.ndarray,
    v_scale: float,
    h_scale: float,
    face_h: float,
    h: int,
    w: int,
) -> np.ndarray:
    cx = int((pts[MOUTH_LEFT_IDX][0] + pts[MOUTH_RIGHT_IDX][0]) / 2)
    cy = int((pts[MOUTH_TOP_IDX][1] + pts[MOUTH_BOTTOM_IDX][1]) / 2)
    rw = int(_dist(pts[MOUTH_LEFT_IDX], pts[MOUTH_RIGHT_IDX]) * 0.7)
    rh = int(face_h * 0.13)

    x1, x2 = max(cx - rw, 0), min(cx + rw, w)
    y1, y2 = max(cy - rh, 0), min(cy + rh, h)
    if x1 >= x2 or y1 >= y2:
        return frame

    region = frame[y1:y2, x1:x2]
    rrh, rrw = region.shape[:2]
    new_w = int(rrw * h_scale)
    new_h = int(rrh * v_scale)

    if new_w <= 0 or new_h <= 0:
        return frame

    scaled = cv2.resize(region, (new_w, new_h))

    # Paste centered, clamped to frame bounds
    paste_x = cx - new_w // 2
    paste_y = cy - new_h // 2
    src_x1 = max(0, -paste_x)
    src_y1 = max(0, -paste_y)
    dst_x1 = max(0, paste_x)
    dst_y1 = max(0, paste_y)
    copy_w = min(new_w - src_x1, w - dst_x1)
    copy_h = min(new_h - src_y1, h - dst_y1)

    if copy_w > 0 and copy_h > 0:
        frame[dst_y1:dst_y1 + copy_h, dst_x1:dst_x1 + copy_w] = \
            scaled[src_y1:src_y1 + copy_h, src_x1:src_x1 + copy_w]

    return frame


def _gaussian_mask(h: int, w: int) -> np.ndarray:
    """Soft circular blend mask."""
    y = np.linspace(-1, 1, h)
    x = np.linspace(-1, 1, w)
    xv, yv = np.meshgrid(x, y)
    mask = np.exp(-(xv**2 + yv**2) * 3)
    mask = np.clip(mask, 0, 1)
    return mask[:, :, np.newaxis]


def _clamp(v, lo=0, hi=None):
    if isinstance(v, float):
        return max(lo, min(hi if hi is not None else 1.0, v))
    return max(lo, v)


# ---------------------------------------------------------------------------
# Comic reaction overlays
# ---------------------------------------------------------------------------

def _draw_shock_lines(frame: np.ndarray, h: int, w: int, n: int) -> np.ndarray:
    """Radial manga-style shock lines from center."""
    cx, cy = w // 2, h // 2
    overlay = frame.copy()
    for i in range(n):
        angle = (i / n) * 2 * np.pi
        x2 = int(cx + np.cos(angle) * min(h, w) * 0.5)
        y2 = int(cy + np.sin(angle) * min(h, w) * 0.5)
        cv2.line(overlay, (cx, cy), (x2, y2), (255, 255, 255), 1)
    return cv2.addWeighted(overlay, 0.25, frame, 0.75, 0)


def _draw_sweat_drop(frame: np.ndarray, h: int, w: int) -> np.ndarray:
    """Blue sweat drop in top-right corner for 'oh no' moments."""
    cx, cy, r = w - 30, 30, 14
    cv2.circle(frame, (cx, cy), r, (200, 130, 50), -1)
    pts = np.array([[cx - r//2, cy], [cx + r//2, cy], [cx, cy - r*2]], np.int32)
    cv2.fillPoly(frame, [pts], (200, 130, 50))
    cv2.circle(frame, (cx - 4, cy - 4), 4, (255, 255, 255), -1)
    return frame
