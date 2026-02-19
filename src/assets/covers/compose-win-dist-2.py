#!/usr/bin/env python3
"""Compose win-distribution cover: grayscale chart on colored gradient."""
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

CANVAS_W, CANVAS_H = 1200, 630

# Deep slate/steel gradient
COLOR1 = (28, 32, 42)    # #1c202a
COLOR2 = (72, 90, 112)   # #485a70

def make_gradient(w, h, c1, c2):
    xs = np.arange(w)
    ys = np.arange(h)
    xx, yy = np.meshgrid(xs, ys)
    t = (xx + yy).astype(np.float64) / (w + h - 2)
    pixels = np.zeros((h, w, 3), dtype=np.uint8)
    for ch in range(3):
        pixels[:, :, ch] = (c1[ch] + t * (c2[ch] - c1[ch])).astype(np.uint8)
    return Image.fromarray(pixels, 'RGB')

# Load the 2x chart screenshot
chart = Image.open('/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/win-dist-chart-2x.png').convert('RGBA')
cw, ch = chart.size
print(f"Chart size: {cw}x{ch}")

# Crop off the top title area ("Projected Win Distribution") since it overlaps
# with the confidence interval text. Keep the CI text and everything below.
# The title is roughly in the top 3% of the image
crop_top = int(ch * 0.095)
chart = chart.crop((0, crop_top, cw, ch))
cw, ch = chart.size
print(f"After top crop: {cw}x{ch}")

arr = np.array(chart)

r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
brightness = (r.astype(float) + g.astype(float) + b.astype(float)) / 3

# 1) Remove white/light background
is_bg = (brightness > 200) & (np.abs(r.astype(float) - g.astype(float)) < 30) & (np.abs(g.astype(float) - b.astype(float)) < 30)
arr[is_bg, 3] = 0

# 2) Remove the confidence interval shaded region (light beige/tan)
# These are the semi-transparent fill between the dashed lines
is_shaded = (r.astype(float) > 200) & (g.astype(float) > 180) & (b.astype(float) > 170) & (brightness < 240) & (a > 0) & (~is_bg)
arr[is_shaded, 3] = 0  # fully transparent — let gradient show through

# 3) Handle grid lines — make them subtle on dark bg
is_grid = (brightness > 190) & (brightness < 250) & (np.abs(r.astype(float) - g.astype(float)) < 15) & (np.abs(g.astype(float) - b.astype(float)) < 15) & (arr[:,:,3] > 0)
arr[is_grid, 0] = 255
arr[is_grid, 1] = 255
arr[is_grid, 2] = 255
arr[is_grid, 3] = 25

# 4) Lighten dark text (axis labels, tick marks) for dark background
is_dark_text = (brightness < 100) & (np.abs(r.astype(float) - g.astype(float)) < 40) & (np.abs(g.astype(float) - b.astype(float)) < 40) & (arr[:,:,3] > 0)
arr[is_dark_text, 0] = 210
arr[is_dark_text, 1] = 215
arr[is_dark_text, 2] = 220

# 5) Grayscale orange bars (histogram bars)
is_orange = (r.astype(float) > 150) & (g.astype(float) < 180) & (b.astype(float) < 100) & (arr[:,:,3] > 0) & (~is_bg)
is_peach = (r.astype(float) > 180) & (g.astype(float) > 140) & (g.astype(float) < 215) & (b.astype(float) < 180) & (arr[:,:,3] > 0) & (~is_bg)
is_colored = is_orange | is_peach

gray_val = (0.299 * r.astype(float) + 0.587 * g.astype(float) + 0.114 * b.astype(float))
# Boost brightness so bars are clearly visible on dark gradient
gray_val = np.clip(gray_val * 1.2 + 60, 80, 240).astype(np.uint8)

arr[is_colored, 0] = gray_val[is_colored]
arr[is_colored, 1] = gray_val[is_colored]
arr[is_colored, 2] = gray_val[is_colored]

# 6) Grayscale the dashed CI boundary lines
is_dashed = (r.astype(float) > 180) & (g.astype(float) < 140) & (b.astype(float) < 80) & (arr[:,:,3] > 0) & (~is_bg)
arr[is_dashed, 0] = 170
arr[is_dashed, 1] = 175
arr[is_dashed, 2] = 180

# 7) Grayscale the "81 wins" annotation text and arrow (orange)
# Already covered by is_orange above — the text and arrow are also orange

chart_processed = Image.fromarray(arr, 'RGBA')

# Scale to fit canvas — prioritize showing the full chart height (including x-axis label)
# Scale based on height to ensure nothing is cropped
target_h = CANVAS_H - 50  # 25px padding top + bottom
scale = target_h / ch
target_w = int(cw * scale)

# If too wide, scale by width instead
if target_w > CANVAS_W - 20:
    target_w = CANVAS_W - 20
    scale = target_w / cw
    target_h = int(ch * scale)

chart_scaled = chart_processed.resize((target_w, target_h), Image.LANCZOS)
print(f"Scaled chart: {target_w}x{target_h}")

# Create gradient canvas
canvas = make_gradient(CANVAS_W, CANVAS_H, COLOR1, COLOR2).convert('RGBA')

# Center on canvas
paste_x = (CANVAS_W - target_w) // 2
paste_y = (CANVAS_H - target_h) // 2

print(f"Pasting at ({paste_x}, {paste_y})")
canvas.paste(chart_scaled, (paste_x, paste_y), chart_scaled)

# Save
out = '/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/win-distribution-cover-1.jpg'
canvas.convert('RGB').save(out, 'JPEG', quality=94)
print(f"Saved: {out}")
