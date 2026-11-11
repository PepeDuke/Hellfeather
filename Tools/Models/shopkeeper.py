"""Builds Assets/ShopKeeper.qvox from the character sheet in Assets/Reference.

The front and side views are cut out from their dark backgrounds and scaled to
the model's height. Each row of the model is the intersection of the two
silhouettes, rounded into ellipses so the body is not boxy. Faces that look
forward take their color from the front view, the rest from the side view.

    python Tools/Models/shopkeeper.py                  write the model
    python Tools/Models/shopkeeper.py --preview p.png  also save front, side and 3/4 renders
"""
import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / 'Assets/Reference/ShopKeeper.png'
OUTPUT = ROOT / 'Assets/ShopKeeper.qvox'
HEIGHT = 72          # voxels from sole to crown
COLORS = 200         # palette size of the model
BACKGROUND = 13      # brightest channel of the background, averaged nearby
# Each view's panel on the sheet, as left, top, right, bottom.
FRONT = (125, 190, 520, 706)
SIDE = (1290, 190, 1610, 706)


def cut_out(sheet, box):
    """Returns the panel's pixels and a mask of the character. The box's bottom
    edge is the soles, so both views share a scale."""
    pixels = np.asarray(sheet.crop(box), dtype=np.int32)
    height, width, _ = pixels.shape
    # Dark cloth is dithered against near-black, so judge a neighborhood. Cloth
    # and leather are also warm, where the background is neutral.
    bright = blur(pixels.max(axis=2).astype(float), 3)
    warm = blur((pixels[:, :, 0] - pixels[:, :, 2]).astype(float), 3)
    mask = (bright > BACKGROUND) | (warm > 7)
    # The floor shadow around the boots is only faintly warm.
    floor = height - 22
    mask[floor:] &= warm[floor:] > 14
    # Close hairline gaps between pieces of dark clothing.
    mask = blur(mask.astype(float), 2) > 0.5
    kept = large_pieces(mask, 800)
    kept |= small_holes(kept, 600)
    kept = bridge_columns(kept, 24)
    ys, xs = np.nonzero(kept)
    top, left, right = ys.min(), xs.min(), xs.max() + 1
    return pixels[top:, left:right], kept[top:, left:right]


def pieces(mask):
    """Yields each 4-connected piece of the mask as a list of (y, x)."""
    height, width = mask.shape
    seen = np.zeros_like(mask)
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            piece = []
            queue = deque([(y, x)])
            seen[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                piece.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            yield piece


def large_pieces(mask, limit):
    """Drops specks. A dark band can part his legs from his body, so every
    sizable piece is kept, not only the largest."""
    kept = np.zeros_like(mask)
    for piece in pieces(mask):
        if len(piece) >= limit:
            for y, x in piece:
                kept[y, x] = True
    return kept


def bridge_columns(mask, limit):
    """Fills short vertical gaps, such as the dark hem between coat and boots."""
    bridged = mask.copy()
    for x in range(mask.shape[1]):
        rows = np.nonzero(mask[:, x])[0]
        for a, b in zip(rows[:-1], rows[1:]):
            if 1 < b - a <= limit:
                bridged[a:b, x] = True
    return bridged


def small_holes(mask, limit):
    """Background enclosed by the mask, in pieces under limit pixels. The gaps
    inside his bent arms are larger and stay open."""
    filled = np.zeros_like(mask)
    height, width = mask.shape
    for piece in pieces(~mask):
        touches = any(y in (0, height - 1) or x in (0, width - 1) for y, x in piece)
        if not touches and len(piece) < limit:
            for y, x in piece:
                filled[y, x] = True
    return filled


def blur(values, radius):
    padded = np.pad(values, radius, mode='edge')
    total = np.zeros_like(values)
    size = 2 * radius + 1
    for dy in range(size):
        for dx in range(size):
            total += padded[dy:dy + values.shape[0], dx:dx + values.shape[1]]
    return total / (size * size)


def shrink(pixels, mask, scale):
    """Averages each cell of the view into one voxel. Returns colors and coverage."""
    height = max(1, round(mask.shape[0] * scale))
    width = max(1, round(mask.shape[1] * scale))
    colors = np.zeros((height, width, 3))
    cover = np.zeros((height, width), dtype=bool)
    for y in range(height):
        y0, y1 = int(y / scale), max(int(y / scale) + 1, int((y + 1) / scale))
        for x in range(width):
            x0, x1 = int(x / scale), max(int(x / scale) + 1, int((x + 1) / scale))
            cell = mask[y0:y1, x0:x1]
            if cell.mean() < 0.45:
                continue
            cover[y, x] = True
            colors[y, x] = pixels[y0:y1, x0:x1][cell].mean(axis=0)
    # Image rows run down; model rows run up.
    return colors[::-1], cover[::-1]


def runs(row):
    found = []
    start = None
    for i, value in enumerate(list(row) + [False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            found.append((start, i - 1))
            start = None
    return found


def build():
    sheet = Image.open(SHEET).convert('RGB')
    front_pixels, front_mask = cut_out(sheet, FRONT)
    side_pixels, side_mask = cut_out(sheet, SIDE)
    front, front_cover = shrink(front_pixels, front_mask, HEIGHT / front_mask.shape[0])
    side, side_cover = shrink(side_pixels, side_mask, HEIGHT / side_mask.shape[0])
    height = min(front_cover.shape[0], side_cover.shape[0])
    width = front_cover.shape[1]
    depth = side_cover.shape[1]
    solid = np.zeros((width, height, depth), dtype=bool)
    color = np.zeros((width, height, depth, 3))
    for y in range(height):
        for x0, x1 in runs(front_cover[y]):
            cx, rx = (x0 + x1) / 2, (x1 - x0) / 2 + 0.5
            for z0, z1 in runs(side_cover[y]):
                cz, rz = (z0 + z1) / 2, (z1 - z0) / 2 + 0.5
                for x in range(x0, x1 + 1):
                    for z in range(z0, z1 + 1):
                        u, w = (x - cx) / rx, (z - cz) / rz
                        # A squarish ellipse: rounder than a box, fuller than a circle.
                        if abs(u) ** 2.6 + abs(w) ** 2.6 > 1.0:
                            continue
                        solid[x, y, z] = True
                        # Faces turned toward the front take the front view's color.
                        facing = w / max(rz, 1.0) / (abs(u) / max(rx, 1.0) + abs(w) / max(rz, 1.0) + 1e-6)
                        color[x, y, z] = front[y, x] if facing > 0.0 else side[y, z]
    return solid, color


def quantize(solid, color):
    cells = color[solid].astype(np.uint8)
    strip = Image.fromarray(cells.reshape(1, -1, 3), 'RGB').quantize(COLORS, method=Image.Quantize.MEDIANCUT)
    palette = np.array(strip.getpalette()[:COLORS * 3]).reshape(-1, 3)
    indexes = np.asarray(strip).reshape(-1)
    grid = np.full(solid.shape, -1, dtype=np.int32)
    grid[solid] = indexes
    return grid, palette


def write(grid, palette):
    width, height, depth = grid.shape
    lines = ['qvox 1', f'size {width} {height} {depth}', '']
    for i, (r, g, b) in enumerate(palette):
        lines.append(f'color {i:02X} {r:02X}{g:02X}{b:02X}')
    for y in range(height):
        lines.append('')
        lines.append(f'# y = {y}')
        for z in range(depth):
            lines.append(''.join('..' if grid[x, y, z] < 0 else f'{grid[x, y, z]:02X}' for x in range(width)))
    OUTPUT.write_text('\n'.join(lines) + '\n', encoding='ascii')


def preview(grid, palette, path):
    """Front, side and 3/4 renders, nearest voxel wins, lit like the game's faces."""
    width, height, depth = grid.shape
    views = []
    for yaw in (0.0, 45.0, 90.0):
        angle = np.radians(yaw)
        size = int(width + depth) + 2
        image = np.zeros((height, size, 3), dtype=np.uint8)
        best = np.full((height, size), -1e9)
        for x, y, z in zip(*np.nonzero(grid >= 0)):
            px, pz = x - width / 2, z - depth / 2
            u = int(px * np.cos(angle) + pz * np.sin(angle) + size / 2)
            near = pz * np.cos(angle) - px * np.sin(angle)
            if near > best[height - 1 - y, u]:
                best[height - 1 - y, u] = near
                image[height - 1 - y, u] = palette[grid[x, y, z]]
        views.append(image)
    sheet = np.concatenate(views, axis=1)
    Image.fromarray(sheet).resize((sheet.shape[1] * 6, sheet.shape[0] * 6), Image.NEAREST).save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview')
    args = parser.parse_args()
    solid, color = build()
    grid, palette = quantize(solid, color)
    write(grid, palette)
    print(f'{OUTPUT.name}: {grid.shape[0]} x {grid.shape[1]} x {grid.shape[2]}, {int(solid.sum())} voxels')
    if args.preview:
        preview(grid, palette, args.preview)


if __name__ == '__main__':
    main()
