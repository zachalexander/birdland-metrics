#!/usr/bin/env python3.8
"""Process cover photos: remove background, grayscale, heavy blur to remove all jersey text."""
from rembg import remove
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw
import os

SRC = '/Users/zdalexander/Desktop/birdland-metrics/src/app/assets/covers'
DST = '/Users/zdalexander/Desktop/birdland-metrics/src/assets/covers'
OUT_H = 500

IMAGES = {
    'pexels-pixabay-209804.jpg': {
        'crop': (0.25, 0.0, 0.75, 1.0),
        'out': '01-photo.png',
    },
    'pexels-pixabay-163487.jpg': {
        'crop': (0.20, 0.0, 0.80, 1.0),
        'out': '02-photo.png',
    },
    'pexels-expressivestanley-2475108.jpg': {
        'crop': (0.22, 0.05, 0.72, 0.95),
        'out': '03-photo.png',
    },
    'pexels-pixabay-260635.jpg': {
        'crop': (0.08, 0.05, 0.92, 0.95),
        'out': '04-photo.png',
    },
    'pexels-pixabay-163401.jpg': {
        'crop': (0.10, 0.0, 0.95, 1.0),
        'out': '05-photo.png',
    },
}


def create_edge_fade_mask(w, h, fade_px=25):
    mask = Image.new('L', (w, h), 255)
    draw = ImageDraw.Draw(mask)
    for i in range(fade_px):
        alpha = int(255 * (i / fade_px))
        draw.line([(0, i), (w, i)], fill=alpha)
        draw.line([(0, h - 1 - i), (w, h - 1 - i)], fill=alpha)
        draw.line([(i, 0), (i, h)], fill=alpha)
        draw.line([(w - 1 - i, 0), (w - 1 - i, h)], fill=alpha)
    return mask


def process_image(filename, config):
    path = os.path.join(SRC, filename)
    print(f'Processing {filename}...')

    img = Image.open(path)
    w, h = img.size
    cl, ct, cr, cb = config['crop']
    crop = img.crop((int(w * cl), int(h * ct), int(w * cr), int(h * cb)))

    print(f'  Removing background...')
    nobg = remove(crop)

    cw, ch = nobg.size
    scale = OUT_H / ch
    new_w = int(cw * scale)
    nobg = nobg.resize((new_w, OUT_H), Image.LANCZOS)

    r, g, b, a = nobg.split()

    # Grayscale — no blur, keep sharp and identical to original
    gray = ImageOps.grayscale(nobg.convert('RGB'))

    # Recombine as RGBA with original sharpness
    result = Image.merge('RGBA', (gray, gray, gray, a))

    # Subtle edge fade
    edge_mask = create_edge_fade_mask(new_w, OUT_H, fade_px=25)
    final_a = result.split()[3]
    combined_a = Image.new('L', (new_w, OUT_H))
    fa_pixels = final_a.load()
    ea_pixels = edge_mask.load()
    ca_pixels = combined_a.load()
    for y in range(OUT_H):
        for x in range(new_w):
            ca_pixels[(x, y)] = int(fa_pixels[(x, y)] * ea_pixels[(x, y)] / 255)
    result.putalpha(combined_a)

    out_path = os.path.join(DST, config['out'])
    result.save(out_path, 'PNG')
    print(f'  -> {config["out"]} ({new_w}x{OUT_H})')


for filename, config in IMAGES.items():
    process_image(filename, config)

print('\nAll done!')
