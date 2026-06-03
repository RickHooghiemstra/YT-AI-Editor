"""
Generates a YouTube thumbnail from the recommended gameplay frame.
Overlays title text and optional webcam face crop using Pillow.
Three template styles: action (default), bold, minimal.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()

THUMB_W = 1280
THUMB_H = 720

TONE_COLORS = {
    "energetic": {"bg": (255, 50, 0),    "text": (255, 255, 255), "accent": (255, 220, 0),  "label": (200, 30, 0)},
    "chill":     {"bg": (0, 100, 200),   "text": (255, 255, 255), "accent": (0, 230, 210),  "label": (0, 70, 160)},
    "educational":{"bg": (20, 20, 80),   "text": (255, 255, 255), "accent": (80, 180, 255), "label": (10, 10, 60)},
    "funny":     {"bg": (255, 190, 0),   "text": (20, 20, 20),    "accent": (255, 80, 0),   "label": (220, 150, 0)},
    "dramatic":  {"bg": (80, 0, 120),    "text": (255, 255, 255), "accent": (220, 100, 255),"label": (50, 0, 80)},
}


def generate_thumbnail(
    key_frames_dir: Path,
    recommended_frame_index: int,
    webcam_video: Path,
    title_text: str,
    subtext: str,
    tone: str,
    output_path: Path,
    style: str = "action",
) -> Path:
    """
    Generate a thumbnail.
    style: 'action' (default) | 'bold' | 'minimal'
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
    except ImportError:
        raise ImportError("Pillow required for thumbnails")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    colors = TONE_COLORS.get(tone, TONE_COLORS["energetic"])

    frame_files = sorted(key_frames_dir.glob("*.jpg"))
    if not frame_files:
        raise FileNotFoundError(f"No frames in {key_frames_dir}")

    frame_idx = min(recommended_frame_index, len(frame_files) - 1)
    bg = Image.open(frame_files[frame_idx]).convert("RGB").resize((THUMB_W, THUMB_H))

    face_img = _extract_best_face_frame(webcam_video)

    if style == "bold":
        result = _style_bold(bg, face_img, title_text, subtext, colors)
    elif style == "minimal":
        result = _style_minimal(bg, face_img, title_text, subtext, colors)
    else:
        result = _style_action(bg, face_img, title_text, subtext, colors)

    result.save(str(output_path), quality=95)
    console.print(f"[green]Thumbnail saved:[/green] {output_path}")
    return output_path


# ── Style: action (original style, enhanced) ─────────────────────────────────

def _style_action(bg, face_img, title_text, subtext, colors):
    from PIL import Image, ImageDraw, ImageEnhance

    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    draw = ImageDraw.Draw(bg)

    # Bottom gradient
    grad = Image.new("RGBA", (THUMB_W, 320), (0, 0, 0, 0))
    for y in range(320):
        alpha = int(200 * (y / 320))
        grad.paste((0, 0, 0, alpha), (0, y, THUMB_W, y + 1))
    bg.paste(grad, (0, THUMB_H - 320), grad)

    # Left accent bar
    draw.rectangle([(0, 0), (14, THUMB_H)], fill=colors["bg"])

    # Title with label background
    title_font = _load_font(86)
    sub_font = _load_font(44)
    title_upper = title_text.upper()

    if title_upper:
        bbox = draw.textbbox((0, 0), title_upper, font=title_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = THUMB_W // 2
        ty = THUMB_H - 155
        # Label pill background
        pad = 18
        draw.rounded_rectangle(
            [tx - tw // 2 - pad, ty - th // 2 - pad, tx + tw // 2 + pad, ty + th // 2 + pad],
            radius=12, fill=(*colors["label"], 200),
        )
        _draw_text_shadow(draw, title_upper, title_font, (tx, ty), colors["text"])

    if subtext:
        _draw_text_shadow(draw, subtext, sub_font, (THUMB_W // 2, THUMB_H - 58), colors["accent"])

    # Face circle top-right
    if face_img is not None:
        _paste_face_circle(bg, face_img, x=THUMB_W - 220, y=20, size=200, border_color=colors["accent"])

    return bg


# ── Style: bold ───────────────────────────────────────────────────────────────

def _style_bold(bg, face_img, title_text, subtext, colors):
    """Large color-blocked title area filling the bottom third."""
    from PIL import Image, ImageDraw, ImageEnhance

    bg = ImageEnhance.Brightness(bg).enhance(0.65)
    draw = ImageDraw.Draw(bg)

    # Solid color band at the bottom
    band_h = 200
    band_overlay = Image.new("RGBA", (THUMB_W, band_h), (*colors["bg"], 230))
    bg.paste(band_overlay, (0, THUMB_H - band_h), band_overlay)

    # Thick top border on band
    draw.rectangle([(0, THUMB_H - band_h), (THUMB_W, THUMB_H - band_h + 8)], fill=colors["accent"])

    # Title inside band
    title_font = _load_font(92)
    sub_font = _load_font(40)
    title_upper = title_text.upper()
    if title_upper:
        _draw_text_shadow(draw, title_upper, title_font, (THUMB_W // 2, THUMB_H - band_h // 2 - 18), colors["text"])
    if subtext:
        _draw_text_shadow(draw, subtext, sub_font, (THUMB_W // 2, THUMB_H - 38), colors["accent"])

    # Left edge bar
    draw.rectangle([(0, 0), (16, THUMB_H)], fill=colors["accent"])

    # Face circle top-left
    if face_img is not None:
        _paste_face_circle(bg, face_img, x=30, y=20, size=180, border_color=colors["text"])

    return bg


# ── Style: minimal ────────────────────────────────────────────────────────────

def _style_minimal(bg, face_img, title_text, subtext, colors):
    """Clean dark vignette with large text, no solid color blocks."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    bg = ImageEnhance.Brightness(bg).enhance(0.50)
    # Soft vignette
    vign = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vign)
    for i in range(120):
        alpha = int(180 * (i / 120))
        vdraw.rectangle([i, i, THUMB_W - i, THUMB_H - i], outline=(0, 0, 0, alpha))
    bg.paste(vign, (0, 0), vign)

    draw = ImageDraw.Draw(bg)
    title_font = _load_font(100)
    sub_font = _load_font(46)

    # Centered title
    if title_text.upper():
        _draw_text_shadow(draw, title_text.upper(), title_font, (THUMB_W // 2, THUMB_H // 2 + 20), colors["text"])
    if subtext:
        _draw_text_shadow(draw, subtext, sub_font, (THUMB_W // 2, THUMB_H // 2 + 90), colors["accent"])

    # Thin bottom accent line
    draw.rectangle([(0, THUMB_H - 8), (THUMB_W, THUMB_H)], fill=colors["accent"])

    # Face circle top-right
    if face_img is not None:
        _paste_face_circle(bg, face_img, x=THUMB_W - 210, y=20, size=190, border_color=colors["accent"])

    return bg


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw_text_shadow(draw, text: str, font, position: tuple, color: tuple, shadow_offset: int = 4) -> None:
    x, y = position
    for dx in range(-shadow_offset, shadow_offset + 1, shadow_offset):
        for dy in range(-shadow_offset, shadow_offset + 1, shadow_offset):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 200), anchor="mm")
    draw.text((x, y), text, font=font, fill=color, anchor="mm")


def _paste_face_circle(bg, face_img, x: int, y: int, size: int, border_color: tuple) -> None:
    from PIL import Image, ImageDraw

    face = face_img.resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    face.putalpha(mask)

    # Draw colored ring behind the circle
    ring_size = size + 10
    ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, ring_size, ring_size), fill=(*border_color[:3], 255))
    bg.paste(ring, (x - 5, y - 5), ring)
    bg.paste(face, (x, y), face)


def _load_font(size: int):
    from PIL import ImageFont

    font_paths = [
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial Bold.ttf",
        # Windows
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/ariblk.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _extract_best_face_frame(webcam_video: Path):
    """Extract a face frame from webcam video — picks a frame at ~30% in."""
    try:
        import cv2
        from PIL import Image

        cap = cv2.VideoCapture(str(webcam_video))
        if not cap.isOpened():
            return None
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.3))
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    except Exception:
        return None
