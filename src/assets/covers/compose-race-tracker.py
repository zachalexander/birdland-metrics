#!/usr/bin/env python3
"""Compose race tracker cover: grayscale chart on colored gradient."""
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

CANVAS_W, CANVAS_H = 1200, 630

# Deep copper/bronze gradient — warm, distinct from other covers
COLOR1 = (42, 28, 20)    # #2a1c14 — dark brown
COLOR2 = (112, 78, 52)   # #704e34 — warm bronze

def make_gradient(w, h, c1, c2):
    xs = np.arange(w)
    ys = np.arange(h)
    xx, yy = np.meshgrid(xs, ys)
    t = (xx + yy).astype(np.float64) / (w + h - 2)
    pixels = np.zeros((h, w, 3), dtype=np.uint8)
    for ch in range(3):
        pixels[:, :, ch] = (c1[ch] + t * (c2[ch] - c1[ch])).astype(np.uint8)
    return Image.fromarray(pixels, 'RGB')

# Load the 2x screenshot
chart = Image.open('/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/race-tracker-2x.png').convert('RGBA')
cw, ch = chart.size
print(f"Chart size: {cw}x{ch}")

# Crop: remove title/toggles from top, standings table from bottom
# Keep just the chart area (lines + axes)
# Title + toggles ~ top 18%, standings table ~ bottom 38%
crop_top = int(ch * 0.18)
crop_bottom = int(ch * 0.58)
chart = chart.crop((0, crop_top, cw, crop_bottom))
cw, ch = chart.size
print(f"After crop: {cw}x{ch}")

arr = np.array(chart)
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
brightness = (r.astype(float) + g.astype(float) + b.astype(float)) / 3

# 1) Remove white/light background
is_bg = (brightness > 235) & (np.abs(r.astype(float) - g.astype(float)) < 15) & (np.abs(g.astype(float) - b.astype(float)) < 15)
arr[is_bg, 3] = 0

# Also catch slightly off-white bg (the card gradient goes from #fdfdfd to #faf8f5)
is_bg2 = (brightness > 220) & (r.astype(float) > 230) & (g.astype(float) > 228) & (b.astype(float) > 225) & (arr[:,:,3] > 0)
arr[is_bg2, 3] = 0

# 2) Grid lines — make very subtle
is_grid = (brightness > 200) & (brightness < 245) & (np.abs(r.astype(float) - g.astype(float)) < 12) & (np.abs(g.astype(float) - b.astype(float)) < 12) & (arr[:,:,3] > 0)
arr[is_grid, 0] = 255
arr[is_grid, 1] = 255
arr[is_grid, 2] = 255
arr[is_grid, 3] = 20

# 3) Lighten dark/gray text (axis labels, team abbreviations) for dark background
is_dark_text = (brightness < 120) & (np.abs(r.astype(float) - g.astype(float)) < 30) & (np.abs(g.astype(float) - b.astype(float)) < 30) & (arr[:,:,3] > 0)
arr[is_dark_text, 0] = 210
arr[is_dark_text, 1] = 210
arr[is_dark_text, 2] = 210

# 4) Convert all colored lines to grayscale
# Identify non-background, non-text colored pixels (the team lines)
is_remaining = (arr[:,:,3] > 0) & (~is_bg) & (~is_bg2) & (~is_grid) & (~is_dark_text)
gray_val = (0.299 * r.astype(float) + 0.587 * g.astype(float) + 0.114 * b.astype(float))

# Lighten so lines are visible on dark bg — spread out the grayscale values
# Different teams should still have distinct gray tones
gray_boosted = np.clip(gray_val * 1.4 + 80, 120, 250).astype(np.uint8)

arr[is_remaining, 0] = gray_boosted[is_remaining]
arr[is_remaining, 1] = gray_boosted[is_remaining]
arr[is_remaining, 2] = gray_boosted[is_remaining]

chart_processed = Image.fromarray(arr, 'RGBA')

# Scale to fit canvas
target_h = CANVAS_H + 40  # overflow slightly for zoomed-in feel
scale = target_h / ch
target_w = int(cw * scale)

if target_w > CANVAS_W + 60:
    target_w = CANVAS_W + 60
    scale = target_w / cw
    target_h = int(ch * scale)

chart_scaled = chart_processed.resize((target_w, target_h), Image.LANCZOS)
print(f"Scaled chart: {target_w}x{target_h}")

# Create gradient canvas
canvas = make_gradient(CANVAS_W, CANVAS_H, COLOR1, COLOR2).convert('RGBA')

# Center
paste_x = (CANVAS_W - target_w) // 2
paste_y = (CANVAS_H - target_h) // 2

print(f"Pasting at ({paste_x}, {paste_y})")
canvas.paste(chart_scaled, (paste_x, paste_y), chart_scaled)

out = '/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers/race-tracker-cover-1.jpg'
canvas.convert('RGB').save(out, 'JPEG', quality=94)
print(f"Saved: {out}")
