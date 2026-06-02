"""
Generates a YouTube thumbnail from the recommended gameplay frame.
Overlays title text and optional webcam face crop using Pillow.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()

THUMB_W = 1280
THUMB_H = 720

# Color schemes by tone
TONE_COLORS = {
    "energetic": {"bg": (255, 60, 0), "text": (255, 255, 255), "accent": (255, 220, 0)},
    "chill": {"bg": (0, 120, 200), "text": (255, 255, 255), "accent": (0, 220, 200)},
    "educational": {"bg": (30, 30, 80), "text": (255, 255, 255), "accent": (100, 200, 255)},
    "funny": {"bg": (255, 200, 0), "text": (30, 30, 30), "accent": (255, 100, 0)},
}


def generate_thumbnail(
    key_frames_dir: Path,
    recommended_frame_index: int,
    webcam_video: Path,
    title_text: str,
    subtext: str,
    tone: str,
    output_path: Path,
) -> Path:
    """
    Create a thumbnail by overlaying text on the best gameplay frame.
    Also composites a small face crop from the webcam in the corner.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
        import cv2
        import numpy as np
    except ImportError:
        raise ImportError("Pillow and opencv-python required for thumbnails")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    colors = TONE_COLORS.get(tone, TONE_COLORS["energetic"])

    # Load best gameplay frame
    frame_files = sorted(key_frames_dir.glob("*.jpg"))
    if not frame_files:
        raise FileNotFoundError(f"No frames in {key_frames_dir}")

    frame_idx = min(recommended_frame_index, len(frame_files) - 1)
    frame_path = frame_files[frame_idx]

    bg = Image.open(frame_path).convert("RGB").resize((THUMB_W, THUMB_H))

    # Slightly darken for text contrast
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.6)

    draw = ImageDraw.Draw(bg)

    # Gradient overlay at bottom
    gradient = Image.new("RGBA", (THUMB_W, THUMB_H // 2), (0, 0, 0, 0))
    for y in range(THUMB_H // 2):
        alpha = int(180 * (y / (THUMB_H // 2)))
        for x in range(THUMB_W):
            gradient.putpixel((x, y), (0, 0, 0, alpha))
    bg.paste(gradient, (0, THUMB_H // 2), gradient)

    # Load fonts (fallback to default if not available)
    title_font = _load_font(80)
    sub_font = _load_font(40)

    # Title text with shadow
    title_upper = title_text.upper()
    _draw_text_with_shadow(draw, title_upper, title_font, (THUMB_W // 2, THUMB_H - 160), colors["text"])

    if subtext:
        _draw_text_with_shadow(draw, subtext, sub_font, (THUMB_W // 2, THUMB_H - 70), colors["accent"])

    # Webcam face crop (top-right corner)
    face_img = _extract_best_face_frame(webcam_video)
    if face_img is not None:
        face_size = 200
        face_resized = face_img.resize((face_size, face_size))
        # Circular mask
        mask = Image.new("L", (face_size, face_size), 0)
        from PIL import ImageDraw as ID
        mask_draw = ID.Draw(mask)
        mask_draw.ellipse((0, 0, face_size, face_size), fill=255)
        face_resized.putalpha(mask)
        bg.paste(face_resized, (THUMB_W - face_size - 20, 20), face_resized)

    # Accent bar on the left edge
    draw.rectangle([(0, 0), (12, THUMB_H)], fill=colors["bg"])

    bg.save(str(output_path), quality=95)
    console.print(f"[green]Thumbnail saved:[/green] {output_path}")
    return output_path


def _draw_text_with_shadow(draw, text: str, font, position: tuple, color: tuple) -> None:
    x, y = position
    # Shadow
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 180), anchor="mm")
    # Main text
    draw.text((x, y), text, font=font, fill=color, anchor="mm")


def _load_font(size: int):
    from PIL import ImageFont

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _extract_best_face_frame(webcam_video: Path) -> "Image | None":
    """Extract a single good frame from webcam video for the face circle."""
    try:
        import cv2
        from PIL import Image
        import numpy as np

        cap = cv2.VideoCapture(str(webcam_video))
        if not cap.isOpened():
            return None

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 3)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    except Exception:
        return None
