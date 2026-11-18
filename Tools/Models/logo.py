"""The Hellfeather logo as a voxel recipe, built like the buildings in buildings.py.

A riveted bronze ring with a stitched groove, a black feather standing through
it with red-burnt tips, and the name across the front in raised, bevelled
bronze letters over a swash. Every part is drawn from kit.py's Model with a
small fixed palette, at the buildings' 0.0625 voxel; the front faces +Z.

    python Tools/Models/logo.py              writes Assets/HellfeatherLogo.qvox
    python Tools/Models/logo.py --preview    also renders Tools/Models/Preview/HellfeatherLogo.png
                                             and a lit sheet, HellfeatherLogo.lit.png
    python Tools/Models/logo.py --icon       also writes the window icon, Assets/Hellfeather.ico:
                                             the lit front view on a clear square, 16 to 256 pixels,
                                             with the name left off below 64

The game does not use the model yet; the main menu still spells the name in
plain voxel capitals (HellfeatherMenuArt.Title in Source/Menus.dk).
"""
import argparse
import io
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402
from kit import Model, color, compact, hash2  # noqa: E402

NAME = 'HellfeatherLogo'
# A calligraphic bold italic that ships with Windows. A blackletter face would
# be closer to the concept; any .ttf path works here.
FONT = Path('C:/Windows/Fonts/constanz.ttf')

BRONZE = color('logo bronze', (150, 96, 54), (134, 84, 46), (164, 108, 62), (120, 76, 42))
BRONZE_LIT = color('logo bronze lit', (214, 150, 92), (196, 134, 80), (226, 166, 106))
BRONZE_DARK = color('logo bronze dark', (70, 42, 24), (54, 32, 18), (86, 54, 32))
LETTER = color('logo letter', (206, 140, 80), (192, 128, 72), (218, 154, 92), (182, 120, 66))
RIVET = color('logo rivet', (176, 120, 70), (232, 176, 118))
FEATHER = color('logo feather', (30, 29, 32), (40, 38, 42), (22, 21, 24), (52, 49, 52))
EMBER = color('logo ember', (110, 26, 20), (150, 36, 24), (196, 52, 30), (226, 84, 42))
QUILL = color('logo quill', (96, 92, 88), (78, 74, 70))

WIDTH, HEIGHT, DEPTH = 248, 196, 30
CX, CY = 124, 98
RING_OUTER, RING_INNER = 82, 66
RING_BACK, RING_FRONT = 6, 15
FEATHER_BACK = 9
TEXT_BACK, TEXT_FRONT = 17, 27


def smooth(edge0, edge1, value):
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def column_fill(m, mask2d, back, front, colors):
    """Fills each (x, y) column of mask2d from z = back up to front (a 2D grid
    of last z, inclusive). Colors is a 2D grid of palette indexes or a scalar."""
    front3 = np.asarray(front)[:, :, None] if np.ndim(front) else front
    where = mask2d[:, :, None] & (m.z >= back) & (m.z <= front3)
    if np.ndim(colors) == 0:
        m.fill(where, colors)
    else:
        m.fill(where, np.broadcast_to(np.asarray(colors)[:, :, None], m.grid.shape))


def ring(m):
    x = m.x[:, :, 0] - CX
    y = m.y[:, :, 0] - CY
    r = np.hypot(x, y)
    angle = np.arctan2(y, x)
    band = (r >= RING_INNER) & (r < RING_OUTER)
    middle = (RING_INNER + RING_OUTER) / 2.0
    half = (RING_OUTER - RING_INNER) / 2.0
    # A rounded face, highest along the middle of the band.
    across = (r - middle) / half
    front = np.round(RING_FRONT - 3.0 * across ** 2).astype(int)
    noise = hash2(m.x[:, :, 0] // 2, m.y[:, :, 0] // 2, 41)
    shades = np.where(noise < 0.25, BRONZE[0], np.where(noise < 0.5, BRONZE[1], np.where(noise < 0.75, BRONZE[2], BRONZE[3])))
    # The upper rim catches the light, the lower one falls dark.
    shades = np.where((across < -0.7) & (y < 0), BRONZE_DARK[0], shades)
    shades = np.where((across > 0.7) & (y > 0), BRONZE_LIT[0], shades)
    # Stitched grooves near both rims: dashes, sunk one voxel.
    arc = (angle * r / 3.0).astype(int)
    stitch = ((np.abs(r - (RING_OUTER - 3.5)) < 0.8) | (np.abs(r - (RING_INNER + 3.5)) < 0.8)) & (arc % 2 == 0)
    # Joints where the ring's segments meet, every 45 degrees.
    joint = np.abs(((np.degrees(angle) + 22.5) % 45.0) - 22.5) * np.pi / 180.0 * r < 0.8
    shades = np.where(stitch | joint, BRONZE_DARK[1], shades)
    front = np.where(stitch | joint, front - 1, front)
    column_fill(m, band, RING_BACK, front, shades)
    # Rivets on every joint but the ones the feather and the name cover.
    for degrees in range(0, 360, 45):
        if degrees in (90, 270, 0, 180):
            continue
        a = math.radians(degrees)
        rx, ry = CX + middle * math.cos(a), CY + middle * math.sin(a)
        for side in (-1, 1):
            # A pair astride each joint.
            px = rx - side * 5.0 * math.sin(a)
            py = ry + side * 5.0 * math.cos(a)
            dome = (m.x - px) ** 2 + (m.y - py) ** 2 + ((m.z - RING_FRONT) * 1.3) ** 2 <= 3.2 ** 2
            m.fill(dome & (m.z >= RING_FRONT - 2), RIVET[0])
            top = (m.x - (px - 0.8)) ** 2 + (m.y - (py + 0.8)) ** 2 <= 1.2 ** 2
            m.fill(top & dome & (m.z >= RING_FRONT + 1), RIVET[1])


def feather(m):
    """A long black flight feather leaning a little right, burnt red at both tips."""
    x = m.x[:, :, 0].astype(float)
    y = m.y[:, :, 0].astype(float)
    bottom, top = 2.0, HEIGHT - 4.0
    t = (y - bottom) / (top - bottom)
    inside = (t >= 0.0) & (t <= 1.0)
    tc = np.clip(t, 0.0, 1.0)
    centre = CX - 8.0 + 18.0 * tc + 6.0 * np.sin(np.pi * tc)
    offset = x - centre
    # The vane: widest a little above the middle, pointed at the top, the
    # bottom fraying into down before the bare quill.
    swell = np.sin(np.pi * np.clip((tc - 0.06) / 0.94, 0.0, 1.0)) ** 0.55
    width = 34.0 * swell * (1.0 - 0.4 * tc ** 6)
    width = np.where(offset < 0, width * 0.86, width)
    # Barbs run up and out from the shaft.
    lane = (y - np.abs(offset) * 0.6)
    barb = np.floor(lane / 4.0).astype(int)
    jag = hash2(barb, (offset > 0).astype(int), 7)
    edge = width * (0.66 + 0.34 * jag)
    # A few deep splits between barbs.
    split = (hash2(barb, (offset > 0).astype(int) + 4, 9) < 0.2) & (np.abs(offset) > width * 0.4) & ((lane % 4.0) < 1.0)
    vane = inside & (np.abs(offset) <= edge) & ~split & (tc > 0.04)
    shaft = inside & (np.abs(offset) <= 1.3)
    shape = vane | shaft
    # Colors: alternating barb shades, burning to red at the tips.
    stripe = (np.floor(lane / 2.0).astype(int) + (offset > 0)) % 4
    colors = np.asarray(FEATHER)[stripe]
    heat = np.maximum(smooth(0.74, 0.97, tc), smooth(0.34, 0.06, tc))
    dither = 0.7 * hash2(barb, (offset > 0).astype(int), 13) + 0.3 * hash2(m.x[:, :, 0], m.y[:, :, 0], 14)
    burnt = dither < heat
    level = np.clip((heat * 4.0 + dither).astype(int) - 1, 0, 3)
    colors = np.where(burnt, np.asarray(EMBER)[level], colors)
    colors = np.where(shaft, np.where(heat > 0.5, EMBER[0], QUILL[0]), colors)
    # A gently curved vane with the shaft standing proud.
    across = np.clip(np.abs(offset) / np.maximum(width, 1.0), 0.0, 1.0)
    front = np.round(FEATHER_BACK + 6.0 + 3.0 * (1.0 - across ** 2)).astype(int)
    front = np.where(shaft, front + 1, front)
    column_fill(m, shape, FEATHER_BACK, front, colors)


def lettering():
    """The name and a swash below it, as a 2D mask indexed [x, y] with y up."""
    font = ImageFont.truetype(str(FONT), 10)
    # Size the name to the model's width, less a margin for the bevel.
    for size in range(40, 200):
        font = ImageFont.truetype(str(FONT), size)
        left, upper, right, lower = font.getbbox('Hellfeather')
        if right - left > WIDTH - 10:
            font = ImageFont.truetype(str(FONT), size - 1)
            break
    left, upper, right, lower = font.getbbox('Hellfeather')
    image = Image.new('L', (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(image)
    text_width = right - left
    # The name sits a little below the middle of the ring.
    baseline_top = HEIGHT - CY - (lower - upper) // 2 + 6
    draw.text(((WIDTH - text_width) // 2 - left, baseline_top - upper), 'Hellfeather', font=font, fill=255)
    # The swash: a tapered stroke that dips under the middle of the name.
    under = baseline_top + (lower - upper) + 3
    x0, x1 = WIDTH * 0.22, WIDTH * 0.86
    steps = 220
    for i in range(steps + 1):
        s = i / steps
        px = x0 + (x1 - x0) * s
        py = under + 2.0 - 7.0 * math.sin(math.pi * s) + 3.0 * math.sin(2.0 * math.pi * s)
        r = 0.6 + 2.6 * math.sin(math.pi * s) ** 0.8
        draw.ellipse((px - r, py - r, px + r, py + r), fill=255)
    mask = np.asarray(image) > 127
    return mask.T[:, ::-1]


def distance_inside(mask, most):
    """How many steps each cell of a 2D mask is from its edge, up to most."""
    distance = np.zeros(mask.shape, dtype=int)
    current = mask.copy()
    for step in range(most):
        padded = np.pad(current, 1)
        eroded = current & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
        distance += eroded
        current = eroded
    return distance


def letters(m):
    mask = lettering()
    inner = distance_inside(mask, 3)
    # Bevelled: the rim one step back, the face full height.
    front = TEXT_FRONT - np.maximum(0, 2 - inner)
    padded = np.pad(mask, 1)
    open_above = mask & ~padded[1:-1, 2:]
    open_below = mask & ~padded[1:-1, :-2]
    noise = hash2(m.x[:, :, 0], m.y[:, :, 0], 23)
    colors = np.asarray(LETTER)[np.minimum((noise * 4).astype(int), 3)]
    near_top = np.zeros_like(mask)
    near_bottom = np.zeros_like(mask)
    for k in range(2):
        near_top |= np.roll(open_above, -k, axis=1) & mask
    near_bottom |= open_below
    colors = np.where(near_top, BRONZE_LIT[1], colors)
    colors = np.where(near_bottom, BRONZE_DARK[2], colors)
    # Fine scratches across the faces.
    scratch = ((m.x[:, :, 0] * 3 + m.y[:, :, 0] * 5) % 29 == 0) & (inner >= 2)
    colors = np.where(scratch, BRONZE[3], colors)
    # A dark lip around the letters parts them from the feather behind.
    lip = mask.copy()
    for axis in (0, 1):
        for shift in (-1, 1):
            lip |= np.roll(mask, shift, axis=axis)
    column_fill(m, lip & ~mask, TEXT_BACK - 1, np.full(mask.shape, TEXT_BACK + 3), BRONZE_DARK[1])
    column_fill(m, mask, TEXT_BACK - 1, front, colors)


def hellfeather_logo(named=True):
    m = Model(WIDTH, HEIGHT, DEPTH)
    ring(m)
    feather(m)
    if named:
        letters(m)
    return m


def lit_view(grid, palette, yaw, pitch, scale, clear=False):
    """The model from the front, turned by yaw and looked down on by pitch
    (degrees), lit from the upper left, each surface voxel a shaded square."""
    solid = grid >= 0
    padded = np.pad(solid, 1)
    normal = np.zeros(solid.shape + (3,))
    exposed = np.zeros(solid.shape, dtype=bool)
    for axis in range(3):
        for sign in (-1, 1):
            neighbor = np.roll(padded, -sign, axis=axis)[1:-1, 1:-1, 1:-1]
            open_side = solid & ~neighbor
            exposed |= open_side
            normal[..., axis] += open_side * sign
    xs, ys, zs = np.nonzero(exposed)
    w, h, d = solid.shape
    points = np.stack([xs - w / 2 + 0.5, ys - h / 2 + 0.5, zs - d / 2 + 0.5], axis=1)
    normals = normal[xs, ys, zs]
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(length, 1e-6)
    a, p = math.radians(yaw), math.radians(pitch)
    turn = np.array([[math.cos(a), 0.0, math.sin(a)], [0.0, 1.0, 0.0], [-math.sin(a), 0.0, math.cos(a)]])
    tilt = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(p), -math.sin(p)], [0.0, math.sin(p), math.cos(p)]])
    rotate = tilt @ turn
    points = points @ rotate.T
    normals = normals @ rotate.T
    light = np.array([-0.45, 0.7, 0.55]) / np.linalg.norm([-0.45, 0.7, 0.55])
    rim = np.array([0.6, -0.2, -0.3]) / np.linalg.norm([0.6, -0.2, -0.3])
    shade = 0.32 + 0.78 * np.clip(normals @ light, 0.0, 1.0)
    colors = palette[grid[xs, ys, zs]].astype(float) * shade[:, None]
    # A faint red rim light from behind right, as from fire.
    colors += np.clip(normals @ rim, 0.0, 1.0)[:, None] * np.array([70.0, 18.0, 8.0])
    sx, sy, near = points[:, 0], points[:, 1], points[:, 2]
    order = np.argsort(near)
    left, top = sx.min(), sy.max()
    size = (int((sx.max() - left) * scale) + 8, int((top - sy.min()) * scale) + 8)
    image = Image.new('RGBA', size, (0, 0, 0, 0)) if clear else Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(image)
    half = max(0.5, scale * 0.6)
    for i in order:
        cx = (sx[i] - left) * scale + 4
        cy = (top - sy[i]) * scale + 4
        fill = tuple(int(min(255, c)) for c in colors[i])
        draw.rectangle((cx - half, cy - half, cx + half, cy + half), fill=fill + (255,) if clear else fill)
    return image


def lit_sheet(grid, palette, path):
    views = [lit_view(grid, palette, 0.0, 0.0, 3.0), lit_view(grid, palette, -22.0, 6.0, 3.0), lit_view(grid, palette, 0.0, 55.0, 3.0)]
    width = sum(v.width for v in views) + 40 * (len(views) + 1)
    height = max(v.height for v in views) + 80
    sheet = Image.new('RGB', (width, height), (0, 0, 0))
    x = 40
    for v in views:
        sheet.paste(v, (x, (height - v.height) // 2))
        x += v.width + 40
    sheet.save(path)


# Below 64 pixels the name is only noise, so the small sizes show the ring
# and feather alone.
ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]
EMBLEM_BELOW = 64


def icon_square(grid, palette):
    """The lit front view, cut to its bounds and centered on a clear square."""
    view = lit_view(grid, palette, 0.0, 0.0, 4.0, clear=True)
    view = view.crop(view.getbbox())
    side = int(max(view.width, view.height) * 1.04)
    square = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    square.paste(view, ((side - view.width) // 2, (side - view.height) // 2), view)
    return square


def write_ico(path, images):
    """An .ico holding one PNG per size, as Windows Vista and later read them."""
    blobs = []
    for image in images:
        out = io.BytesIO()
        image.save(out, format='PNG')
        blobs.append(out.getvalue())
    data = bytearray(struct.pack('<HHH', 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    for image, blob in zip(images, blobs):
        side = image.width % 256
        data += struct.pack('<BBBBHHII', side, side, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    for blob in blobs:
        data += blob
    path.write_bytes(bytes(data))


def write_icon(grid, palette):
    named = icon_square(grid, palette)
    (emblem_grid,), emblem_palette = compact([hellfeather_logo(named=False).trimmed()])
    emblem = icon_square(emblem_grid, emblem_palette)
    images = [(emblem if size < EMBLEM_BELOW else named).resize((size, size), Image.LANCZOS) for size in ICON_SIZES]
    write_ico(act1.ASSETS / 'Hellfeather.ico', images)
    act1.PREVIEW.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGBA', (sum(ICON_SIZES) + 16 * (len(ICON_SIZES) + 1), 272), (90, 96, 110, 255))
    x = 16
    for image in reversed(images):
        sheet.paste(image, (x, 8), image)
        x += image.width + 16
    sheet.save(act1.PREVIEW / f'{NAME}.icon.png')


def build(preview, icon=False):
    model = hellfeather_logo()
    (grid,), palette = compact([model.trimmed()])
    act1.write(act1.ASSETS / f'{NAME}.qvox', palette, grid, [])
    if preview:
        act1.save_preview(NAME, palette, grid, [])
        lit_sheet(grid, palette, act1.PREVIEW / f'{NAME}.lit.png')
    if icon:
        write_icon(grid, palette)
    w, h, d = grid.shape
    print(f'{NAME}: {w} x {h} x {d}, {int((grid >= 0).sum())} voxels, {len(palette)} colors')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--icon', action='store_true')
    args = parser.parse_args()
    build(args.preview, args.icon)


if __name__ == '__main__':
    main()
