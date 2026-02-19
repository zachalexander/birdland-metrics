#!/usr/bin/env python3
"""
Birdland Metrics — Cover Image Generator
=========================================
Reusable script for creating consistent article cover art.

Pipeline:
  1. Remove background (BiRefNet model via rembg)
  2. Convert to grayscale + boost contrast
  3. Compose onto a diagonal gradient background
  4. Output 1200x630 JPG

Usage examples:

  Single player, centered:
    python3 generate-cover.py \
      --photos player.jpg \
      --gradient "#1c3d4f,#5aa0b4" \
      --output my-cover.jpg

  Single player, cropped at neck (headshot style):
    python3 generate-cover.py \
      --photos player.jpg \
      --gradient "#2d1b2e,#8f5a78" \
      --crop-top 0.62 \
      --output headshot-cover.jpg

  Multi-player composite:
    python3 generate-cover.py \
      --photos left.jpg center.jpg right.jpg \
      --gradient "#0d2818,#3d8c5e" \
      --output trio-cover.jpg

  Custom positioning (x_offset, y_offset, height per photo):
    python3 generate-cover.py \
      --photos left.jpg center.jpg right.jpg \
      --positions "-80,30,700" "250,10,700" "580,20,700" \
      --gradient "#0d2818,#3d8c5e" \
      --output trio-cover.jpg

Gradient presets (used in existing covers):
  Orange (Orioles):  "#d4713b,#f0b888"
  Teal:              "#1c3d4f,#5aa0b4"
  Plum:              "#2d1b2e,#8f5a78"
  Navy:              "#0f1923,#33546e"
  Emerald:           "#0d2818,#3d8c5e"

Dependencies:
  pip install rembg pillow numpy onnxruntime
  (BiRefNet model downloads automatically on first use, ~973MB)
"""

import argparse
import numpy as np
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance


# ── Defaults ─────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 1200, 630
MODEL = "birefnet-general"
PLAYER_OPACITY = 0.88
CONTRAST_BOOST = 1.1
PLAYER_HEIGHT = 700  # default height for single-player covers
QUALITY = 92


def hex_to_rgb(h: str) -> tuple:
    """Convert '#rrggbb' to (r, g, b)."""
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def make_gradient(w: int, h: int, color1: str, color2: str) -> Image.Image:
    """Create a diagonal linear gradient from top-left to bottom-right."""
    c1 = np.array(hex_to_rgb(color1), dtype=np.float64)
    c2 = np.array(hex_to_rgb(color2), dtype=np.float64)

    # Diagonal: interpolate based on (x + y) / (w + h)
    xs = np.arange(w)
    ys = np.arange(h)
    xx, yy = np.meshgrid(xs, ys)
    t = (xx + yy).astype(np.float64) / (w + h - 2)

    pixels = np.zeros((h, w, 3), dtype=np.uint8)
    for ch in range(3):
        pixels[:, :, ch] = (c1[ch] + t * (c2[ch] - c1[ch])).astype(np.uint8)

    return Image.fromarray(pixels, "RGB")


def remove_background(img: Image.Image) -> Image.Image:
    """Remove background using BiRefNet model."""
    from rembg import remove, new_session

    session = new_session(MODEL)
    return remove(img, session=session)


def to_grayscale_rgba(img: Image.Image, contrast: float = CONTRAST_BOOST) -> Image.Image:
    """Convert RGBA image to grayscale while preserving alpha."""
    r, g, b, a = img.split()
    gray = ImageOps.grayscale(img.convert("RGB"))
    if contrast != 1.0:
        gray = ImageEnhance.Contrast(gray).enhance(contrast)
    return Image.merge("RGBA", (gray, gray, gray, a))


def apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Scale the alpha channel by opacity (0.0–1.0)."""
    r, g, b, a = img.split()
    a = a.point(lambda p: int(p * opacity))
    return Image.merge("RGBA", (r, g, b, a))


def crop_and_scale(img: Image.Image, crop_top: float, target_height: int) -> Image.Image:
    """Optionally crop from top (headshot style) and scale to target height."""
    w, h = img.size
    if crop_top < 1.0:
        crop_y = int(h * crop_top)
        img = img.crop((0, 0, w, crop_y))
    w, h = img.size
    scale = target_height / h
    return img.resize((int(w * scale), target_height), Image.LANCZOS)


def auto_positions(count: int, canvas_w: int, canvas_h: int, height: int):
    """Generate evenly spaced positions for N players."""
    if count == 1:
        # Centered, bottom-aligned
        return [(canvas_w // 2, canvas_h, height)]
    elif count == 2:
        third = canvas_w // 3
        return [
            (third, canvas_h, height),
            (third * 2, canvas_h, height),
        ]
    elif count == 3:
        quarter = canvas_w // 4
        return [
            (quarter - 40, canvas_h, height),
            (canvas_w // 2 + 80, canvas_h, height),
            (canvas_w - quarter + 40, canvas_h, height),
        ]
    else:
        spacing = canvas_w // (count + 1)
        return [(spacing * (i + 1), canvas_h, height) for i in range(count)]


def parse_position(pos_str: str) -> tuple:
    """Parse 'x_offset,y_offset,height' string."""
    parts = pos_str.split(",")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def compose_cover(
    photo_paths: list[str],
    gradient_colors: tuple[str, str],
    output_path: str,
    positions: list[tuple] | None = None,
    crop_top: float = 1.0,
    opacity: float = PLAYER_OPACITY,
    contrast: float = CONTRAST_BOOST,
    player_height: int = PLAYER_HEIGHT,
    skip_bg_removal: bool = False,
):
    """Main composition pipeline."""

    # 1. Create gradient canvas
    print(f"Creating {CANVAS_W}x{CANVAS_H} gradient: {gradient_colors[0]} → {gradient_colors[1]}")
    canvas = make_gradient(CANVAS_W, CANVAS_H, *gradient_colors)
    canvas = canvas.convert("RGBA")

    # 2. Determine positions
    if positions is None:
        positions = auto_positions(len(photo_paths), CANVAS_W, CANVAS_H, player_height)

    # 3. Process each photo
    for i, photo_path in enumerate(photo_paths):
        print(f"Processing {Path(photo_path).name}...")

        img = Image.open(photo_path).convert("RGBA")

        # Background removal
        if not skip_bg_removal:
            print("  Removing background (BiRefNet)...")
            img = remove_background(img)

        # Crop (for headshot-style covers)
        target_h = positions[i][2] if len(positions) > i else player_height
        img = crop_and_scale(img, crop_top, target_h)

        # Grayscale + contrast
        img = to_grayscale_rgba(img, contrast)

        # Opacity
        img = apply_opacity(img, opacity)

        # Position: (center_x, bottom_y, height)
        cx, by = positions[i][0], positions[i][1]
        pw, ph = img.size
        paste_x = cx - pw // 2
        paste_y = by - ph

        print(f"  Placing at ({paste_x}, {paste_y}), size {pw}x{ph}")
        canvas.paste(img, (paste_x, paste_y), img)

    # 4. Save
    final = canvas.convert("RGB")
    final.save(output_path, "JPEG", quality=QUALITY)
    print(f"\nSaved: {output_path} ({CANVAS_W}x{CANVAS_H})")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Birdland Metrics cover art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Gradient presets:
  orange   #d4713b,#f0b888   (Orioles default)
  teal     #1c3d4f,#5aa0b4
  plum     #2d1b2e,#8f5a78
  navy     #0f1923,#33546e
  emerald  #0d2818,#3d8c5e
        """,
    )
    parser.add_argument("--photos", nargs="+", required=True, help="Source photo(s)")
    parser.add_argument(
        "--gradient",
        required=True,
        help='Two hex colors: "#rrggbb,#rrggbb" or preset name (orange/teal/plum/navy/emerald)',
    )
    parser.add_argument("--output", required=True, help="Output JPG path")
    parser.add_argument(
        "--positions",
        nargs="+",
        help='Per-photo position: "center_x,bottom_y,height"',
    )
    parser.add_argument("--crop-top", type=float, default=1.0, help="Crop fraction from top (e.g. 0.62 for neck crop)")
    parser.add_argument("--opacity", type=float, default=PLAYER_OPACITY, help=f"Player opacity (default: {PLAYER_OPACITY})")
    parser.add_argument("--contrast", type=float, default=CONTRAST_BOOST, help=f"Contrast boost (default: {CONTRAST_BOOST})")
    parser.add_argument("--height", type=int, default=PLAYER_HEIGHT, help=f"Player height in px (default: {PLAYER_HEIGHT})")
    parser.add_argument("--skip-bg-removal", action="store_true", help="Skip background removal (for pre-processed PNGs)")
    parser.add_argument("--color", action="store_true", help="Keep original colors (skip grayscale)")

    args = parser.parse_args()

    # Resolve gradient
    presets = {
        "orange": ("#d4713b", "#f0b888"),
        "teal": ("#1c3d4f", "#5aa0b4"),
        "plum": ("#2d1b2e", "#8f5a78"),
        "navy": ("#0f1923", "#33546e"),
        "emerald": ("#0d2818", "#3d8c5e"),
    }
    if args.gradient in presets:
        gradient = presets[args.gradient]
    else:
        parts = args.gradient.split(",")
        gradient = (parts[0].strip(), parts[1].strip())

    # Parse positions
    positions = None
    if args.positions:
        positions = [parse_position(p) for p in args.positions]

    compose_cover(
        photo_paths=args.photos,
        gradient_colors=gradient,
        output_path=args.output,
        positions=positions,
        crop_top=args.crop_top,
        opacity=args.opacity,
        contrast=args.contrast,
        player_height=args.height,
        skip_bg_removal=args.skip_bg_removal,
    )


if __name__ == "__main__":
    main()
