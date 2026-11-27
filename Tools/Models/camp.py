"""Act II's Pilgrims' Encampment: camp parts and the recipes built from them.

Like buildings.py, each recipe is a function returning a kit.Model at 0.0625-unit
voxels (16 to a unit), +Z the front the camera sees. Proportions are measured off
the Act II sheets (act2.py crops them into Assets/Reference/Act2): the sheets have
no dimension panel, so the height comes from Act2Models.md and the footprint from
the ratio of the front and side views to it. act2.MODELS lists each recipe, so
inspect_models.py scores it against its sheet.

The parts here are what house.py has no answer for: canvas with sag, stains and
patches, bell and ridge tents, guy ropes and pegs, pennants, spoked wheels, wattle.

    python Tools/Models/camp.py                       build every recipe
    python Tools/Models/camp.py PilgrimTent --preview  build some, with renders
    python Tools/Models/inspect_models.py PilgrimTent  compare with the sheet
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buildings  # noqa: E402
from kit import (CANDLE, CANVAS, CANVAS_OILED, CLOTH_GREY, CLOTH_PALE, EMBER, FEATHER_PALE, FELT, FRAME, GLOW,  # noqa: E402
                 IRON, MOSS, MUD, QUILL_ASH, QUILL_BLACK, ROPE, SOOT, STONE, STRAW, TIN, WICKER, WOOD, WOOD_DARK,
                 DYE_RED, DYE_BLUE, DYE_YELLOW, BURLAP, LEATHER, WATER, WOOD_LIT, Model, hash2, pick, planks)
from house import barrel, stone_block  # noqa: E402


# Canvas.

def canvas_colors(m, along, shades, seed, ground=0, peak=None, patches=0.0, patch_shades=None):
    """Cloth shades for every voxel: sewn panels 6 wide along `along`, each a
    shade of its own with a darker seam, a little speckle, a thin mud stain at
    `ground`, soot darkening toward `peak`, and square patches sewn on where
    hash says so (patches is the share of patch cells). The last shade is the
    darkest and is used for seams and soot."""
    yf = m.y.astype(float)
    lane = np.floor(along / 6.0).astype(int)
    colors = pick(shades[:3], hash2(lane, 0, seed) * 0.8 + hash2(lane, m.y // 12, seed + 1) * 0.2)
    colors = np.where(hash2(np.floor(along).astype(int), m.y, seed + 8) < 0.07, shades[1], colors)
    colors = np.where((along % 6.0) < 0.8, shades[-1], colors)
    mud = (yf - ground) < (1.0 + hash2(np.floor(along / 2.0).astype(int), 0, seed + 2) * 2.5)
    colors = np.where(mud, pick(MUD, hash2(lane, m.y, seed + 3)), colors)
    if peak is not None:
        soot = (peak - yf) < (2.0 + hash2(lane, 1, seed + 4) * 4.0)
        colors = np.where(soot, shades[-1], colors)
    if patches:
        cell_u = np.floor(along / 7.0).astype(int)
        cell_v = (m.y // 7).astype(int)
        patch = hash2(cell_u, cell_v, seed + 5) < patches
        inset_u = (along % 7.0 >= 1.0) & (along % 7.0 < 6.0)
        inset_v = (m.y % 7 >= 1) & (m.y % 7 < 6)
        stitch = patch & inset_u & inset_v & (((along % 7.0) < 2.0) | ((m.y % 7) == 1))
        fill = patch & inset_u & inset_v
        colors = np.where(fill, pick(patch_shades or shades, hash2(cell_u, cell_v, seed + 6)), colors)
        colors = np.where(stitch & (hash2(m.x + m.z, m.y, seed + 7) < 0.5), ROPE[1], colors)
    return colors


def bell_tent(m, cx, cz, radius, wall, peak, shades, seed, door=True, door_half=7.0, door_top=None,
              concave=1.25, sag=0.0, valance=True, patches=0.0, patch_shades=None, band=None, emblem=None):
    """A bell tent: a short round wall `wall` high, then a cone to `peak` at the
    centre pole. concave > 1 hollows the cone like canvas pulled down by its
    ropes; sag adds slack between the ropes. The door is a triangular opening on
    the +Z side, dark inside. band is a stripe colour near the hem, emblem a
    colour for a cross on four sides. Returns the solid mask."""
    dx, dz = m.x - cx, m.z - cz
    dist = np.hypot(dx, dz)
    theta = np.arctan2(dz, dx)
    yf = m.y.astype(float)
    # Slack between eight ropes: the canvas bellies in between them.
    slack = sag * np.abs(np.sin(theta * 4.0))
    t = np.clip((yf - wall) / (peak - wall), 0.0, 1.0)
    target = np.where(yf < wall, radius - slack * 0.5, (radius - slack) * (1.0 - t) ** concave)
    along = (theta + math.pi) * radius
    colors = canvas_colors(m, along, shades, seed, ground=0, peak=peak, patches=patches, patch_shades=patch_shades)
    if band is not None:
        colors = np.where((yf >= 2) & (yf < 4), band, colors)
    shell = (yf < peak) & (dist <= target + 0.5) & (dist > target - 1.6)
    # The inner layer is shadow, so an open door shows a dark inside.
    inner = dist < target - 0.6
    colors = np.where(inner, SOOT[0], colors)
    if door:
        top = door_top if door_top is not None else wall + (peak - wall) * 0.55
        half = door_half * np.clip((top - yf) / top, 0.0, 1.0)
        opening = (dz > 0) & (np.abs(dx) < half) & (yf < top)
        # Flap edges, folded back, show the band colour if there is one.
        edge = (dz > 0) & (np.abs(np.abs(dx) - half) < 1.2) & (yf < top)
        shell &= ~opening
        colors = np.where(edge & shell, band if band is not None else shades[-1], colors)
        m.fill(m.box(int(cx - radius + 3), 0, int(cz - radius + 3), int(cx + radius - 3), 1, int(cz + radius - 3)) & (dist < radius - 3), FRAME[0])
    if emblem is not None:
        for angle in (0.0, math.pi / 2.0, math.pi, -math.pi / 2.0):
            if door and angle == math.pi / 2.0:
                continue
            turn = np.angle(np.exp(1j * (theta - angle))) * radius
            cy = wall * 0.6 + 1.0
            cross = ((np.abs(turn) < 0.8) & (np.abs(yf - cy) < 3.0)) | ((np.abs(turn) < 2.5) & (np.abs(yf - cy - 0.5) < 0.8))
            colors = np.where(cross & (dist > target - 0.6), emblem, colors)
    m.fill(shell, colors)
    if valance:
        hem = (np.abs(yf - wall) < 1.5) & (dist <= radius + 1.0) & (dist > radius - 0.8) & ~((dz > 0) & (np.abs(dx) < door_half * 0.5 if door else False))
        m.fill(hem, shades[3] if len(shades) > 3 else shades[1])
    # The centre pole, standing proud of the peak.
    m.beam((cx, 0, cz), (cx, peak + 3, cz), 2, [WOOD_DARK[0], WOOD[2]])
    return shell


def guy_rope(m, start, end, peg=True):
    """A rope from a point on the canvas to a peg in the ground."""
    m.beam(start, end, 1, [ROPE[0], ROPE[1]])
    if peg:
        x, _, z = end
        m.beam((x, 0, z), (x, 2, z), 1, [WOOD_DARK[0]])


def rope_ring(m, cx, cz, radius, height, reach, count=8, turn=0.0):
    """count guy ropes around a round tent, from `height` on its wall out to
    pegs `reach` beyond it."""
    for k in range(count):
        a = turn + k * 2.0 * math.pi / count
        ca, sa = math.cos(a), math.sin(a)
        guy_rope(m, (cx + ca * radius, height, cz + sa * radius), (cx + ca * (radius + reach), 0, cz + sa * (radius + reach)))


def pennant(m, top, length, colors, tails=1, droop=0.35):
    """A cloth pennant flying toward +X from a pole top, drooping as it goes."""
    x, y, z = top
    for k in range(tails):
        dz = (k - (tails - 1) / 2.0) * 2.0
        for i in range(length):
            yy = y - i * droop - (k * 0.6)
            for j in range(2):
                xi, yi, zi = int(round(x + i)), int(round(yy - j)), int(round(z + dz))
                if 0 <= xi < m.grid.shape[0] and 0 <= yi < m.grid.shape[1] and 0 <= zi < m.grid.shape[2]:
                    m.grid[xi, yi, zi] = colors[(i // 3 + j) % len(colors)]


def wheel(m, center, radius, axis='x', thick=2, spokes=8, colors=None):
    """A spoked wheel turning about `axis`: rim, spokes and an iron hub."""
    colors = colors or [WOOD[1], WOOD[0]]
    cx, cy, cz = center
    if axis == 'x':
        u, v, w = m.z - cz, m.y - cy, m.x - cx
    else:
        u, v, w = m.x - cx, m.y - cy, m.z - cz
    r = np.hypot(u, v)
    band = np.abs(w) < thick / 2.0
    m.fill(band & (r <= radius) & (r > radius - 1.6), pick(colors, hash2(np.floor(np.arctan2(v, u) * 4).astype(int), 0, 140)))
    for k in range(spokes):
        a = k * 2.0 * math.pi / spokes
        du, dv = math.cos(a) * (radius - 1), math.sin(a) * (radius - 1)
        end = (cx, cy + dv, cz + du) if axis == 'x' else (cx + du, cy + dv, cz)
        m.beam(center, end, 1, [WOOD[3]])
    m.fill((np.abs(w) < thick / 2.0 + 1) & (r <= 1.6), IRON[0])


def wattle(m, x0, x1, y0, y1, z0, z1, seed=150):
    """A woven wattle hurdle filling the box: rods over and under upright stakes."""
    box = m.box(x0, y0, z0, x1, y1, z1)
    along = np.where((x1 - x0) >= (z1 - z0), m.x, m.z)
    stake = (along % 6) == 0
    weave = ((m.y // 2 + along // 6) % 2 == 0)
    colors = np.where(stake, WOOD_DARK[0], np.where(weave, pick(WICKER, hash2(along // 3, m.y, seed)), WICKER[2]))
    m.fill(box, colors)


def candle(m, x, y, z, height):
    """A tallow stub `height` tall with a lit wick, and wax run down its foot."""
    m.beam((x, y, z), (x, y + height - 1, z), 1, [CANDLE[0]])
    if 0 <= y + height < m.grid.shape[1]:
        m.grid[x, y + height, z] = GLOW[0]
    m.grid[x, y, max(0, z - 1):z + 2] = np.where(m.grid[x, y, max(0, z - 1):z + 2] >= 0, CANDLE[0], m.grid[x, y, max(0, z - 1):z + 2])


def badge(m, x, y, z, face='+z'):
    """A tin pilgrim's badge, 3 wide and 4 tall, with a red seal, on a wall face."""
    for i in range(3):
        for j in range(4):
            c = DYE_RED[0] if (i == 1 and j in (1, 2)) else TIN[0] if j < 3 else TIN[2]
            if face[1] == 'z':
                m.grid[x + i - 1, y - j, z] = c
            else:
                m.grid[x, y - j, z + i - 1] = c


def feather(m, at, direction, length=6):
    """A pale offering feather wedged into a crack, pointing along `direction`."""
    x, y, z = at
    dx, dy, dz = direction
    m.beam((x, y, z), (x + dx * length, y + dy * length, z + dz * length), 1, [FEATHER_PALE[0], FEATHER_PALE[2]])


def ribbon(m, x, y, z, length, color, sway=0.0):
    """A cloth strip hanging straight down from (x, y, z)."""
    for i in range(length):
        xi = int(round(x + math.sin(i * 0.5) * sway))
        if 0 <= y - i < m.grid.shape[1]:
            m.grid[xi, y - i, z] = color


# Recipes.

def pilgrim_shrine():
    """The Pilgrim Shrine of Orra: a roofless chapel front of mossy fieldstone with
    a pointed niche holding Orra, a stone bar across her eyes; three steps of
    candle stubs; ribbons, tin badges and feathers in every crack; and on the +X
    side, where the wall fell, a wattle-and-canvas patch on posts. The sheet's
    front, side and height ratios give 106 x 112 x 86 voxels (6.6 x 7 x 5.4 units)."""
    m = Model(108, 116, 90)
    yf = m.y.astype(float)
    apex_x, apex = 46, 108

    # The plinth under everything, and the steps up to the niche.
    stone_block(m, 4, 102, 0, 6, 16, 66, course=3, block=6, seed=200, moss_below=5)
    stone_block(m, 14, 80, 0, 4, 66, 88, course=4, block=8, seed=201, quoins=False, moss_below=1)
    stone_block(m, 18, 76, 4, 8, 66, 82, course=4, block=8, seed=202, quoins=False, moss_below=0)
    stone_block(m, 22, 72, 8, 12, 60, 76, course=4, block=8, seed=203, quoins=False, moss_below=0)

    # The chapel front: a gable wall whose right shoulder has fallen away.
    gable_top = 72 + (38 - np.abs(m.x - apex_x)) * (apex - 72) / 38.0
    ruin = (m.x > apex_x + 6) * (hash2(m.x // 4, 0, 204) * 10.0 + (m.x - apex_x - 6) * 0.3)
    # Behind the front wall (z 34 on) the side walls have fallen: their tops
    # step down toward the back, as the sheet's side view shows.
    back_top = np.where(m.z >= 34, 999.0, 46.0 + np.floor((m.z - 22) / 3.0) * 10.0 + hash2(m.z // 3, m.x // 6, 220) * 8.0)
    stone_block(m, 8, 84, 6, apex, 22, 58, course=4, block=7, seed=205, where=(yf < gable_top - ruin) & (yf < back_top))
    # Coping along the gable's left edge, which still stands.
    coping = (m.x <= apex_x + 6) & (yf >= gable_top - 3) & (yf < gable_top) & (m.z >= 34) & (m.z < 59) & (m.x >= 8)
    m.fill(coping, STONE[3])
    m.fill(m.box(apex_x - 3, apex - 2, 46, apex_x + 3, apex + 4, 56), STONE[3])

    # Pilasters either side of the niche, with capitals.
    for x0 in (8, 72):
        stone_block(m, x0, x0 + 12, 6, 76, 56, 64, course=4, block=5, seed=206 + x0, moss_below=12)
        m.fill(m.box(x0 - 1, 72, 55, x0 + 13, 77, 65), STONE[3])

    # The pointed niche, cut deep into the front, darker at the back.
    half = np.where(yf < 74, 18.0, 18.0 * np.clip(1.0 - np.clip((yf - 74) / 22.0, 0.0, None) ** 1.6, 0.0, 1.0))
    niche = (np.abs(m.x - apex_x) < half) & (yf >= 12) & (yf < 96) & (m.z >= 38)
    m.clear(niche & (m.z < 66))
    back = (np.abs(m.x - apex_x) < half) & (yf >= 12) & (yf < 96) & (m.z >= 34) & (m.z < 38)
    m.fill(back, pick([STONE[5], SOOT[0], STONE[5]], hash2(m.x // 3, m.y // 3, 207)))
    surround = (np.abs(m.x - apex_x) < half + 2.5) & ~(np.abs(m.x - apex_x) < half) & (yf >= 12) & (yf < 98) & (m.z >= 56) & (m.z < 59)
    m.fill(surround & (m.grid >= 0), np.where((m.y // 4) % 2 == 0, STONE[3], STONE[0]))
    m.fill(m.box(apex_x - 18, 6, 38, apex_x + 18, 12, 60), STONE[3])

    # Orra: a robed figure, hands folded, a flat stone bar across her eyes.
    sx, sz = apex_x, 46
    robe_r = np.where(yf < 56, 9.0 - (yf - 12) * 0.08, 6.5)
    statue = (np.hypot((m.x - sx) * 1.0, (m.z - sz) * 1.3) <= robe_r) & (yf >= 12) & (yf < 60)
    folds = (np.abs(np.sin((m.x - sx) * 0.9)) < 0.25) & (yf < 50)
    m.fill(statue, np.where(folds, STONE[0], pick([STONE[3], CLOTH_GREY[0]], hash2(m.x, m.y // 3, 208))))
    m.ellipsoid((sx, 64, sz + 1), (4.5, 5.0, 4.5), STONE[3])
    m.ellipsoid((sx, 40, sz + 7), (3.0, 3.0, 2.0), STONE[0])
    # Hair falling to the shoulders behind the face.
    m.fill((np.hypot(m.x - sx, m.z - sz + 1.5) <= 5.5) & (yf >= 56) & (yf < 68) & (m.z < sz + 1), STONE[1])
    # The bar: a wide flat brim at the eyes, an eye carved on its face.
    bar = (np.hypot(m.x - sx, (m.z - sz - 1) * 1.6) <= 9.5) & (yf >= 64) & (yf < 66)
    m.fill(bar, STONE[3])
    m.fill(m.box(sx - 2, 64, sz + 6, sx + 3, 66, sz + 8), FRAME[0])
    m.fill(m.box(sx - 9, 66, sz - 3, sx + 10, 67, sz + 5) & (np.hypot(m.x - sx, (m.z - sz - 1) * 1.6) <= 9.5), STONE[0])

    # The fallen +X side, patched: posts, a wattle hurdle along the side and the
    # front, a canvas cloth over the front with the Orran diamond, rags below.
    stone_block(m, 84, 102, 6, 18, 22, 58, course=4, block=6, seed=209, where=yf < 12 + hash2(m.z // 5, 0, 210) * 8)
    for px, pz in ((84, 64), (101, 64), (101, 22)):
        m.beam((px, 0, pz), (px, 66, pz), 2, [WOOD[1], WOOD[2]])
        m.fill(m.box(px - 1, 50, pz - 1, px + 2, 53, pz + 2), ROPE[0])
    wattle(m, 85, 101, 6, 50, 62, 64, seed=211)
    wattle(m, 99, 101, 6, 50, 24, 62, seed=212)
    cloth = m.box(85, 36, 65, 101, 62, 66) & (yf > 36 + hash2(m.x, 0, 213) * 6.0)
    diamond = (np.abs(m.x - 93) + np.abs(yf - 50))
    m.fill(cloth, np.where((diamond >= 4) & (diamond < 6.5), DYE_RED[0], np.where(diamond < 2, DYE_RED[1], pick(CLOTH_PALE, hash2(m.x // 2, m.y, 214)))))
    side_cloth = m.box(101, 36, 26, 103, 62, 60) & (yf > 36 + hash2(m.z, 1, 215) * 6.0)
    side_diamond = np.abs(m.z - 43) + np.abs(yf - 50)
    m.fill(side_cloth, np.where((side_diamond >= 5) & (side_diamond < 8), DYE_RED[0], pick(CLOTH_PALE, hash2(m.z // 2, m.y, 216))))
    for k, x in enumerate(range(87, 100, 3)):
        ribbon(m, x, 34, 66, 8 + k % 3 * 3, DYE_RED[1] if k % 2 else CLOTH_GREY[0])

    # Offerings: ribbons from the apex and the capitals, badges and feathers on
    # the front, candle stubs on every step.
    for x, color, length in ((apex_x - 2, DYE_RED[0], 22), (apex_x, CLOTH_PALE[0], 18), (apex_x + 2, DYE_RED[1], 24)):
        ribbon(m, x, apex - 2, 59, length, color, sway=0.6)
    for x, y in ((12, 70), (14, 56), (12, 40), (78, 70), (76, 52), (80, 38), (30, 88), (62, 86), (66, 30)):
        badge(m, x, y, 64 if x < 20 or x > 70 else 59)
        feather(m, (x + (3 if x < apex_x else -3), y + 2, 64 if x < 20 or x > 70 else 59), (0.6 if x < apex_x else -0.6, 0.8, 0.0))
    for k in range(26):
        x = 16 + int(hash2(k, 0, 217) * 60)
        z = 62 + int(hash2(k, 1, 218) * 24)
        if abs(x - apex_x) < 6 and z < 76:
            continue
        top = 0
        while top < 20 and m.grid[x, top, z] >= 0:
            top += 1
        if top < 2:
            continue
        candle(m, x, top, z, 2 + int(hash2(k, 2, 219) * 4))
    # The back: badges and ribbons hung on the bare wall.
    for x, y in ((24, 60), (40, 76), (58, 64), (70, 40), (32, 36)):
        m.grid[x - 1:x + 2, y - 3:y + 1, 21] = TIN[1]
        m.grid[x, y - 2, 21] = DYE_RED[0]
    return m


def feather_fire():
    """The Feather Fire: a wide iron basket on a square stone plinth, heaped with
    half-burnt black quills glowing through its bars, a rake leaning on it and a
    sack of gathered feathers beside it. The flame is the game's (Fires.dk).
    40 x 30 x 31 voxels; the sheet's flame is left out of the height."""
    m = Model(44, 34, 34)
    yf = m.y.astype(float)
    cx, cz = 21.0, 16.0
    # The plinth, with a cloth hung on its front showing a pale feather.
    stone_block(m, 11, 31, 0, 12, 8, 25, course=3, block=5, seed=230, moss_below=4)
    m.fill(m.box(10, 11, 7, 32, 13, 26), STONE[3])
    cloth = m.box(16, 2, 25, 26, 11, 26)
    quill = (np.abs((m.x - 21) - (yf - 6.5) * 0.4) < 0.8) & (yf >= 3) & (yf < 10)
    m.fill(cloth, np.where(quill, CLOTH_PALE[0], np.asarray(DYE_RED)[np.minimum((m.y % 3), 1)]))
    # The basket: a flared iron bowl of bars and bands, embers glowing between.
    dx, dz = (m.x - cx) / 1.0, (m.z - cz) / 0.78
    dist = np.hypot(dx, dz)
    theta = np.arctan2(dz, dx)
    radius = 12.5 + (yf - 13) * 0.45
    bowl = (yf >= 13) & (yf < 22) & (dist <= radius) & (dist > radius - 1.6)
    bars = (np.abs(np.sin(theta * 9.0)) < 0.9) | (yf < 15) | (yf >= 19)
    m.fill(bowl & bars, np.where(yf >= 20, IRON[1], IRON[0]))
    m.fill(bowl & ~bars, pick(EMBER, hash2(m.x, m.y + m.z, 231) * 0.8 + 0.1))
    m.fill((yf >= 13) & (yf < 15) & (dist <= radius - 1.6), EMBER[2])
    # Rivets on the top band.
    m.fill(bowl & (yf == 20) & (np.abs(np.sin(theta * 9.0 + 0.6)) < 0.2), IRON[0])
    # Legs from the bowl to the plinth.
    for a in (0.6, 2.5, 3.8, 5.6):
        m.beam((cx + math.cos(a) * 9, 12, cz + math.sin(a) * 7), (cx + math.cos(a) * 12, 16, cz + math.sin(a) * 9.4), 2, [IRON[0]])
    # The heap of quills: a mound with quill-tips sticking out, embers inside.
    heap_top = 21 + 4.5 * np.clip(1.0 - (dist / 14.0) ** 2, 0.0, 1.0) + (hash2(m.x // 2, m.z // 2, 232) - 0.5) * 3.0
    heap = (yf >= 15) & (dist <= radius - 1.4) & (yf < heap_top)
    glowing = hash2(m.x, m.y * 7 + m.z, 233) < 0.08
    m.fill(heap, np.where(glowing & (yf < heap_top - 1), pick(EMBER[:2], hash2(m.x, m.z, 234)), pick(QUILL_BLACK, hash2(m.x // 2, m.y + m.z, 235))))
    for k in range(10):
        a = hash2(k, 0, 236) * math.tau
        r = 4 + hash2(k, 1, 237) * 8
        x0, z0 = cx + math.cos(a) * r, cz + math.sin(a) * r * 0.78
        m.beam((x0, 23, z0), (x0 + math.cos(a) * 4, 26 + hash2(k, 2, 238) * 2, z0 + math.sin(a) * 3), 1, [QUILL_BLACK[2], QUILL_BLACK[0]])
    # Quill-ash spilled on the plinth top.
    m.fill(m.box(10, 13, 7, 32, 14, 26) & (hash2(m.x, m.z, 239) < 0.3) & (m.grid < 0), pick(QUILL_ASH, hash2(m.x, m.z, 240)))
    # A rake leaning on the left, a sack of black feathers on the right.
    m.beam((4, 0, 20), (10, 24, 17), 1, [WOOD[1], WOOD[2]])
    m.beam((1, 1, 22), (7, 1, 22), 1, [IRON[0]])
    for x in (1, 3, 5, 7):
        m.beam((x, 0, 22), (x, 1, 22), 1, [IRON[0]])
    m.ellipsoid((37, 4.5, 20), (5.0, 5.0, 4.5), CANVAS_OILED[0])
    m.ellipsoid((37, 9, 20), (3.4, 2.4, 3.0), CANVAS_OILED[3])
    for k in range(6):
        a = k * 1.05
        m.beam((37 + math.cos(a), 10, 20 + math.sin(a)), (37 + math.cos(a) * 3, 14, 20 + math.sin(a) * 3), 1, [QUILL_BLACK[1], QUILL_BLACK[2]])
    return m


def wrens_tent():
    """Wren's tent, her Act II residence: an oiled, patched ridge tent on two poles,
    the ridge running front to back, the door flaps tied back on the +Z end over
    a dark inside with a cot. Guy ropes fore and aft, a grindstone on its frame and
    a bucket by the door. 64 x 48 x 66 voxels (4 x 3 x 4 units)."""
    m = Model(68, 52, 70)
    yf = m.y.astype(float)
    cx, z0, z1, ridge, half = 33.0, 12, 56, 44.0, 24.0
    sag = 2.0 * np.sin(np.clip((m.z - z0) / (z1 - z0), 0, 1) * math.pi)
    ridge_here = ridge - sag
    # The sides bow outward, the canvas full rather than stretched flat.
    target = np.where(yf < 6, half, half * (1.0 - np.clip((yf - 6) / (ridge_here - 6), 0.0, 1.0) ** 1.35))
    across = np.abs(m.x - cx)
    inside_len = (m.z >= z0) & (m.z < z1)
    slope = inside_len & (yf < ridge_here) & (across <= target + 0.5) & (across > target - 1.6)
    colors = canvas_colors(m, m.z.astype(float) * 1.0 + (m.x > cx) * 40.0, [CANVAS[1], CANVAS[3], CANVAS[0], CANVAS_OILED[3]], 250, ground=0, peak=ridge,
                           patches=0.14, patch_shades=[CANVAS_OILED[0], DYE_RED[2], CANVAS_OILED[3]])
    colors = np.where(across < target - 0.6, SOOT[0], colors)
    m.fill(slope, colors)
    # The back end, closed.
    m.fill((m.z == z0) & (across <= target) & (yf < ridge_here), canvas_colors(m, m.x.astype(float), [CANVAS[1], CANVAS[3], CANVAS[0], CANVAS_OILED[3]], 251, peak=ridge, patches=0.1, patch_shades=[DYE_RED[2], CANVAS_OILED[0]]))
    m.fill((m.z == z0 + 1) & (across < target - 1) & (yf < ridge_here - 1), SOOT[0])
    # The front: flaps drawn aside and tied, a dark inside, and a cot.
    # Bunched flaps: pulled in to a tie at y 18, loose above and below it.
    pinch = 0.12 + 0.4 * np.clip(1.0 - np.abs(yf - 14) / 16.0, 0.0, 1.0)
    bulge = 1.0 + 1.5 * np.clip(1.0 - np.abs(yf - 18) / 8.0, 0.0, 1.0)
    flap = (m.z >= z1 - 1) & (m.z < z1 + bulge) & (yf < ridge_here) & (across <= target + 0.5) & (across > target * pinch)
    folds = (np.sin(m.x * 1.4 + yf * 0.15) > 0.35)
    m.fill(flap, np.where(folds, CANVAS_OILED[3], pick(CANVAS[:2], hash2(m.x, m.y // 5, 254))))
    for side in (-1, 1):
        m.beam((cx + side * 10, 18, z1 + 1), (cx + side * 14, 18, z1 + 1), 1, [ROPE[0]])
    m.fill(m.box(int(cx - half + 3), 0, z0 + 1, int(cx + half - 3), 1, z1), STRAW[1])
    m.fill(m.box(int(cx) - 8, 1, z0 + 8, int(cx) + 8, 5, z1 - 10), WOOD[1])
    m.fill(m.box(int(cx) - 7, 5, z0 + 9, int(cx) + 7, 7, z1 - 11), pick(CLOTH_GREY + FELT[:2], hash2(m.x // 2, m.z // 3, 252)))
    # Poles and guy ropes.
    for z in (z0, z1 - 1):
        m.beam((cx, 0, z), (cx, ridge + 3, z), 2, [WOOD_DARK[0], WOOD[2]])
    guy_rope(m, (cx, ridge + 2, z1), (cx, 0, 68))
    guy_rope(m, (cx, ridge + 2, z0), (cx, 0, 1))
    for z, far in ((z0 + 2, 1), (z1 - 2, 68)):
        for side in (-1, 1):
            guy_rope(m, (cx + side * 6, 34, z), (cx + side * 31, 0, far if far < 30 else 66))
    # Grindstone on a little frame at the front left, a bucket at the front right.
    m.fill(m.box(3, 0, 58, 14, 5, 62), WOOD[0])
    wheel(m, (8.5, 9.0, 60.0), 5.0, axis='z', thick=2, spokes=0, colors=[STONE[2], STONE[1]])
    m.fill((np.hypot(m.x - 8.5, m.y - 9.0) <= 5.0) & (np.abs(m.z - 60) < 1.5), pick(STONE[:3], hash2(m.x, m.y, 253)))
    m.beam((8.5, 9, 57), (8.5, 9, 64), 1, [IRON[0]])
    barrel(m, 54, 61, r=3.2, h=7)
    return m


def pilgrim_tent():
    """A pilgrims' bell tent of pale wool canvas: a low wall under a hollowed cone,
    a red stripe at the hem and a red cross on each side, the door open on +Z,
    eight guy ropes, and a ribbon flying from the pole. 51 x 46 x 49 voxels."""
    m = Model(58, 50, 56)
    cx, cz = 26.0, 26.0
    bell_tent(m, cx, cz, 22.0, 11.0, 41.0, CANVAS, 260, door=True, door_half=8.0, concave=1.35,
              band=DYE_RED[0], emblem=DYE_RED[1])
    rope_ring(m, cx, cz, 21.0, 10.0, 4.0, count=8, turn=math.pi / 8.0)
    pennant(m, (cx + 1, 46, cz), 9, [CLOTH_PALE[0], DYE_RED[0], CLOTH_PALE[1]], tails=1)
    return m


def pilgrim_tent_b():
    """A second pilgrims' tent so the ring doesn't repeat: grey wool felt gone
    dark and slumped, slack between its ropes, patched in faded red, a forked
    red pennant. 52 x 42 x 48 voxels."""
    m = Model(58, 46, 56)
    cx, cz = 26.0, 26.0
    bell_tent(m, cx, cz, 23.0, 17.0, 37.0, [FELT[1], FELT[3], FELT[0], FELT[3]], 270, door=True, door_half=8.0,
              door_top=22.0, concave=1.25, sag=2.5, valance=True, patches=0.06, patch_shades=[DYE_RED[2], CANVAS_OILED[3]])
    rope_ring(m, cx, cz, 22.0, 15.0, 3.0, count=8)
    pennant(m, (cx + 1, 42, cz), 10, [DYE_RED[0], DYE_RED[1]], tails=2)
    return m


def chalk_circle():
    """The Orran chalk circle drawn on a floor: a double ring with ticks and the
    branching mark in the middle, one voxel proud of the ground so it can be
    walked over. The Novice Weaver's Hold Mark and the inscription tutorial use
    it. 36 x 2 x 36 voxels (2.25 units across)."""
    m = Model(38, 3, 38)
    c = 18.5
    dist = np.hypot(m.x - c, m.z - c)
    theta = np.arctan2(m.z - c, m.x - c)
    floor = m.y == 0
    chalk = pick(CLOTH_PALE, hash2(m.x, m.z, 300) * 0.9)
    ring = ((np.abs(dist - 17.0) < 0.8) | (np.abs(dist - 14.0) < 0.6)) & floor
    ticks = (dist > 14.0) & (dist < 17.0) & (np.abs(np.sin(theta * 6.0)) < 0.12) & floor
    # The branching mark: a stem and three pairs of branches.
    u, v = m.x - c, m.z - c
    stem = (np.abs(u) < 0.7) & (np.abs(v) < 10.0)
    branches = np.zeros(m.grid.shape, dtype=bool)
    for k, at in enumerate((-6.0, -1.0, 4.0)):
        reach = 7.0 - k * 1.5
        along = v - at
        branches |= (np.abs(np.abs(u) - along * 0.9) < 0.75) & (along > 0) & (np.abs(u) < reach)
    smudged = hash2(m.x, m.z, 301) < 0.12
    m.fill((ring | ticks | ((stem | branches) & floor)) & ~smudged, chalk)
    return m


# Camp furniture: parts the wagons, carts, tables and small props share.

def plank_box(m, x0, x1, y0, y1, z0, z1, seed, run='x', across='z', width=3):
    """A solid block of boards: each board runs along `run` and they lie side
    by side along `across`, with dark seams between them. A table top runs
    'x' across 'z'; a wagon side runs 'z' across 'y'."""
    axes = {'x': m.x, 'y': m.y, 'z': m.z}
    colors = planks(axes[across].astype(float), axes[run].astype(float), width=width, seed=seed, vertical=True)
    m.fill(m.box(x0, y0, z0, x1, y1, z1), colors)


def studs(m, points):
    """Iron nail heads or rivets at the given voxels."""
    w, h, d = m.grid.shape
    for x, y, z in points:
        x, y, z = int(round(x)), int(round(y)), int(round(z))
        if 0 <= x < w and 0 <= y < h and 0 <= z < d:
            m.grid[x, y, z] = IRON[1]


def staved_barrel(m, cx, cz, y0, radius, height, seed, hoops=(2, None, -3), water=True, moss=True):
    """A big cask of dark staves bellied in the middle, iron hoops standing
    proud with rivets, open at the top with water in it, green at the foot.
    A hoop at None sits halfway up; a negative one counts from the top."""
    yy = (m.y - y0).astype(float)
    dx, dz = m.x - cx, m.z - cz
    ring = np.hypot(dx, dz)
    theta = np.arctan2(dz, dx)
    bulge = radius + 0.9 * np.sin(np.clip(yy / height, 0.0, 1.0) * math.pi)
    inside = (yy >= 0) & (yy < height)
    body = inside & (ring <= bulge) & (ring > bulge - 1.8)
    u = (theta + math.pi) * radius / 2.2
    stave = np.floor(u).astype(int)
    colors = pick([WOOD[1], WOOD[2], WOOD[0], WOOD[3]], hash2(stave, 0, seed) * 0.85 + hash2(stave, m.y // 5, seed + 1) * 0.15)
    colors = np.where(u % 1.0 < 0.22, WOOD_DARK[1], colors)
    if moss:
        colors = np.where(yy < 1.5 + hash2(stave, 1, seed + 2) * 3.0, pick(MOSS[:2], hash2(stave, m.y, seed + 3)), colors)
    m.fill(body | (inside & (yy < 1) & (ring <= bulge)), colors)
    for at in hoops:
        hy = height // 2 if at is None else (at if at >= 0 else height + at)
        hoop = (np.abs(yy - hy) < 1.0) & (ring <= bulge + 0.7) & (ring > bulge - 1.8) & inside
        rivet = hoop & (np.abs(np.sin(theta * 6.0)) < 0.2) & (np.abs(yy - hy) < 0.5)
        m.fill(hoop, np.where(rivet, IRON[1], IRON[0]))
    if water:
        m.fill((np.abs(yy - (height - 2)) < 0.5) & (ring <= bulge - 1.6), pick([WATER[2], WATER[2], WATER[0]], hash2(m.x, m.z, seed + 4)))


def bowl(m, x, y, z, r=2.0, food=None):
    """A wooden bowl, with food heaped in it if colours are given."""
    d = np.hypot(m.x - x, m.z - z)
    m.fill((d <= r) & (m.y == y), WOOD[2])
    m.fill((d <= r + 0.6) & (d > r - 0.8) & (m.y == y + 1), WOOD[1])
    if food:
        m.fill((d <= r - 0.6) & (m.y == y + 1), pick(food, hash2(m.x, m.z, 400)))


def cloth_drape(m, u0, u1, w, y_top, length, shades, seed, axis='x', fringe=True, mark=None):
    """A cloth hanging straight down from y_top in the plane z = w (x = w for
    axis 'z'), u0 to u1 wide, its hem ragged and fringed. mark is a colour for
    an Orran cross sewn in the middle."""
    u = m.x if axis == 'x' else m.z
    plane = m.z if axis == 'x' else m.x
    hem = y_top - length + hash2(u, 0, seed) * 2.0
    cloth = (u >= u0) & (u < u1) & (plane == w) & (m.y <= y_top) & (m.y > hem)
    colors = pick(shades[:-1] if len(shades) > 1 else shades, hash2((u - u0) // 2, m.y // 3, seed + 1))
    colors = np.where((u - u0) % 5 == 4, shades[-1], colors)
    if fringe:
        colors = np.where(m.y < hem + 1.5, shades[-1], colors)
    if mark is not None:
        mu, my = (u0 + u1 - 1) / 2.0, y_top - length * 0.45
        cross = ((np.abs(u - mu) < 0.6) & (np.abs(m.y - my) < 2.6)) | ((np.abs(m.y - my - 0.5) < 0.6) & (np.abs(u - mu) < 2.0))
        colors = np.where(cross, mark, colors)
    m.fill(cloth, colors)


def hooped_cover(m, cx, half, z0, z1, y0, y_mid, top, seed, hoops=4, hem=0):
    """A wagon's canvas over hoops from z0 to z1: straight sides from y0 to
    y_mid, then a round top to `top`, sagging between the hoops, patched and
    stained, hanging ragged up to `hem` below y0. Returns the canvas mask."""
    yf = m.y.astype(float)
    across = np.abs(m.x - cx)
    hoop_at = [z0 + (z1 - 1 - z0) * k / (hoops - 1) for k in range(hoops)]
    spacing = (z1 - z0) / (hoops - 1)
    nearest = np.min([np.abs(m.z - h) for h in hoop_at], axis=0)
    sag = 0.8 * np.sin(np.clip(nearest / spacing, 0, 0.5) * math.pi)
    t = np.clip((yf - y_mid) / (top - y_mid), 0.0, 1.0)
    shape = np.where(yf < y_mid, half, half * np.sqrt(np.clip(1.0 - t ** 2, 0.0, 1.0)))
    target = shape - sag * 0.7
    low = y0 - hem * hash2(m.z // 2, (m.x > cx).astype(int), seed)
    along = m.z.astype(float) + (m.x > cx) * 50.0 + np.where(yf > y_mid, 0.0, 0.0)
    colors = canvas_colors(m, along, [CANVAS[2], CANVAS[0], CANVAS[2], CANVAS[3]], seed, ground=-99, patches=0.08,
                           patch_shades=[CANVAS_OILED[0], DYE_RED[2], CANVAS[1]])
    # Shade the canvas darker low on the sides, where it is dirtier.
    colors = np.where((yf < y0 + 3) & (hash2(m.z, m.y, seed + 9) < 0.5), CANVAS[1], colors)
    colors = np.where((across < target - 0.8) & (yf < top - sag - 1.0), SOOT[0], colors)
    span = (m.z >= z0) & (m.z < z1)
    ceiling = top - sag
    outer = (yf >= low) & (yf < ceiling + 0.5) & (across <= np.maximum(target, 0.0) + 0.5)
    inner = (yf < ceiling - 1.5) & (across <= target - 1.4)
    canvas = span & outer & ~inner
    m.fill(canvas, colors)
    # The hoops: dark bent wood a voxel proud of the canvas.
    for h in hoop_at:
        hz = int(round(h))
        ring = (m.z == hz) & (yf >= y0) & (across <= shape + 1.4) & (across > shape - 0.6) & (yf < top + 1.4)
        m.fill(ring, WOOD_DARK[0])
    return canvas


def iron_lantern(m, x, y, z, hang=0):
    """A lantern a little bigger than house.lantern's: a cap, a glowing body
    behind four corner bars, and a chain to hang it by."""
    if hang:
        m.beam((x, y + 5, z), (x, y + 5 + hang, z), 1, [IRON[0]])
    m.grid[x - 1:x + 2, y, z - 1:z + 2] = IRON[0]
    m.grid[x - 1:x + 2, y + 1:y + 4, z - 1:z + 2] = GLOW[1]
    m.grid[x, y + 1:y + 4, z] = GLOW[0]
    for dx in (-1, 1):
        for dz in (-1, 1):
            m.grid[x + dx, y + 1:y + 4, z + dz] = IRON[0]
    m.grid[x - 1:x + 2, y + 4, z - 1:z + 2] = IRON[0]


def bottle(m, x, y, z, color, tall=3):
    """A bottle or jar standing at (x, y, z): a body of `color`, wide when
    tall enough, with a dark neck and a cork."""
    m.grid[x, y:y + tall, z] = color
    if tall > 2:
        m.grid[max(0, x - 1):x + 2, y:y + tall - 1, z] = color
    m.grid[x, y + tall, z] = FRAME[0]
    if y + tall + 1 < m.grid.shape[1]:
        m.grid[x, y + tall + 1, z] = WOOD[3]


def herbs(m, x, y, z, length, shades):
    """A bundle of drying herbs hung head down from (x, y, z)."""
    m.grid[x, y, z] = ROPE[0]
    for i in range(1, length):
        spread = 0 if i < 3 else 1
        for dx in range(-spread, spread + 1):
            if hash2(x + dx, y - i, z) < 0.8:
                m.grid[x + dx, y - i, z] = shades[(i + dx) % len(shades)]


def hesks_wagon():
    """Hesk's wagon: a covered wagon whose tailboard is let down at the +Z end
    as a counter under a red cloth, the canvas open over shelves of bottles,
    herbs and a lantern hung in the opening. Four spoked wheels, big behind,
    the shafts resting on the ground at -Z, a pot and pans and a badge cloth
    on the side. 42 x 56 x 76 voxels (2.6 x 3.5 x 4.75 units)."""
    m = Model(44, 60, 78)
    yf = m.y.astype(float)
    cx = 21.0
    bed_y0, bed_y1 = 13, 20
    z0, z1 = 10, 66
    # The chassis: two beams under the bed and an axle under each pair of wheels.
    for x in (12, 30):
        m.beam((x, 11, z0 - 2), (x, 11, z1), 2, [WOOD_DARK[0], WOOD[2]])
    for z in (20, 56):
        m.beam((4, 10, z), (38, 10, z), 2, [WOOD_DARK[0]])
    # The bed: boards along z, plank sides stacked in y, a rail on top.
    plank_box(m, 6, 37, bed_y0, bed_y0 + 2, z0, z1, 500, run='z', across='x')
    for xa, xb in ((5, 7), (36, 38)):
        plank_box(m, xa, xb, bed_y0, bed_y1, z0, z1, 501 + xa, run='z', across='y')
        m.fill(m.box(xa, bed_y1, z0, xb, bed_y1 + 1, z1), WOOD[3])
    plank_box(m, 5, 38, bed_y0, bed_y1 + 3, z0 - 1, z0 + 1, 503, run='x', across='y')
    studs(m, [(x, y, z) for x in (4, 38) for y in (bed_y0 + 1, bed_y1 - 1) for z in range(z0 + 4, z1, 8)])
    # Wheels outside the bed: big at the back of the sheet's side view, small in front.
    for x in (2, 40):
        wheel(m, (x, 10.0, 54.0), 10.0, axis='x', thick=2, spokes=10)
        wheel(m, (x, 8.0, 20.0), 8.0, axis='x', thick=2, spokes=8)
    # The cover on five hoops, its hem hanging ragged over the bed's sides.
    hooped_cover(m, cx, 19.5, z0, z1, bed_y1 - 2, 34.0, 55.0, 504, hoops=5, hem=3)
    across = np.abs(m.x - cx)
    t = np.clip((yf - 34.0) / 21.0, 0.0, 1.0)
    face = np.where(yf < 34.0, 19.5, 19.5 * np.sqrt(np.clip(1.0 - t ** 2, 0.0, 1.0)))
    # The closed -Z end: canvas drawn in to a dark puckered hole.
    back = (m.z == z0) & (across < face) & (yf >= bed_y1) & (yf < 55)
    pucker = np.hypot(m.x - cx, (yf - 37.0) * 1.3) < 3.0
    gathers = np.sin(np.arctan2(yf - 37.0, m.x - cx) * 9.0) > 0.3
    m.fill(back & ~pucker, np.where(gathers, CANVAS[3], CANVAS[0]))
    m.fill(back & pucker, SOOT[0])
    # The open +Z end: a dark inside, three shelves of bottles and jars.
    m.fill((m.z == z1 - 7) & (across < face - 1) & (yf >= bed_y1) & (yf < 54), pick([WOOD_DARK[1], SOOT[0]], hash2(m.x // 3, m.y // 4, 505)))
    for y in (25, 33, 41):
        m.fill(m.box(int(cx) - 15, y - 1, z1 - 6, int(cx) + 16, y, z1 - 2), WOOD[1])
        for k, x in enumerate(range(int(cx) - 14, int(cx) + 15, 3)):
            c = [TIN[1], DYE_RED[0], CLOTH_PALE[1], MOSS[2], BURLAP[0], DYE_BLUE[0], WICKER[0]][int(hash2(x, y, 506) * 7)]
            bottle(m, x, y, z1 - 4 + (k % 2), c, tall=2 + int(hash2(x, y, 507) * 3))
    # Herbs and a lantern hung under the front hoop.
    for k, x in enumerate((int(cx) - 13, int(cx) - 9, int(cx) + 9, int(cx) + 13)):
        herbs(m, x, 50 - (k % 2) * 3, z1 - 2, 8, [MOSS[1], MOSS[0], DYE_RED[2], STRAW[1]])
    iron_lantern(m, int(cx), 44, z1 - 2, hang=6)
    # The tailboard let down on chains as a counter, a red cloth with a pale cross over it.
    plank_box(m, 6, 37, bed_y1 - 1, bed_y1 + 1, z1, z1 + 7, 508, run='x', across='z')
    for x in (7, 35):
        m.beam((x, bed_y1 + 1, z1 + 6), (x, 30, z1 - 1), 1, [IRON[0], IRON[1]])
    m.fill(m.box(12, bed_y1 + 1, z1, 31, bed_y1 + 2, z1 + 8), DYE_RED[0])
    cloth_drape(m, 12, 31, z1 + 7, bed_y1 + 1, 10, DYE_RED, 509, mark=CLOTH_PALE[0])
    for x, color in ((9, TIN[0]), (15, BURLAP[0]), (20, CLOTH_PALE[1]), (28, DYE_RED[1]), (33, MOSS[2])):
        bottle(m, x, bed_y1 + (2 if 12 <= x < 31 else 1), z1 + 3, color, tall=2 + (x % 3))
    m.fill(m.box(22, bed_y1 + 2, z1 + 2, 25, bed_y1 + 5, z1 + 5), WICKER[0])
    # The shafts at the back, resting on the ground, with a crossbar.
    for x in (15, 27):
        m.beam((x, 12, z0), (x + (2 if x > cx else -2), 1, 1), 2, [WOOD[1], WOOD[2]])
    m.beam((13, 2, 2), (29, 2, 2), 1, [WOOD_DARK[0]])
    # The +X side: a pot and two pans hung on the bed rail, a red cloth with
    # tin badges pinned on the canvas, a coil of rope.
    for k, z in enumerate((26, 32, 38)):
        m.beam((40, bed_y1 + 1, z), (40, bed_y1 - 2, z), 1, [IRON[0]])
        r = 2.6 if k else 3.4
        m.fill((np.hypot(m.z - z, m.y - (bed_y1 - 5)) <= r) & (np.abs(m.x - 40) < 1.0), IRON[0] if k else SOOT[0])
    patch = (m.x >= 39) & (m.x < 42) & (m.z >= 42) & (m.z < 53) & (yf >= 25) & (yf < 37) & (m.grid >= 0)
    m.fill(patch, np.where((np.abs(m.z - 47) + np.abs(yf - 31)) < 2.5, CLOTH_PALE[0], DYE_RED[1]))
    for z, y in ((43, 35), (51, 35), (43, 26), (51, 26)):
        for x in range(43, 38, -1):
            if m.grid[x, y, z] >= 0:
                m.grid[x, y, z] = TIN[0]
                break
    # The -X side, so the wagon does not read bare from the left.
    for z in (28, 44):
        m.fill((np.hypot(m.z - z, m.y - (bed_y1 - 4)) <= 2.6) & (np.abs(m.x - 3) < 1.0), IRON[0])
        m.beam((3, bed_y1 + 1, z), (3, bed_y1 - 2, z), 1, [IRON[0]])
    return m


def tinkers_cart():
    """Tolly's cart: a two-wheeled handcart under a striped awning of madder,
    bone and woad, coats hung along a rail, shelves of tins behind them, a
    grinding wheel on a frame in front, a sign with a hammer and spanner on a
    post above, the handles resting on a stand at the back (-Z).
    34 x 47 x 38 voxels (2.1 x 2.9 x 2.4 units)."""
    m = Model(36, 48, 40)
    yf = m.y.astype(float)
    x0, x1, z0, z1 = 4, 30, 9, 27
    bed = 11
    # The cart: a plank box on an axle, a spoked wheel either side.
    plank_box(m, x0, x1, bed, bed + 2, z0, z1, 520, run='z', across='x')
    for xa, xb in ((x0, x0 + 1), (x1 - 1, x1)):
        plank_box(m, xa, xb, bed, bed + 5, z0, z1, 521 + xa, run='z', across='y', width=2)
    plank_box(m, x0, x1, bed, bed + 5, z1 - 1, z1, 523, run='x', across='y', width=2)
    m.beam((1, 8, 18), (33, 8, 18), 2, [WOOD_DARK[0]])
    for x in (2, 32):
        wheel(m, (x, 8.0, 18.0), 8.0, axis='x', thick=2, spokes=8)
    # Corner posts up to the awning, a dark back wall with shelves of tins.
    for x in (x0, x1 - 1):
        for z in (z0, z1 - 1):
            m.beam((x, bed, z), (x, 36, z), 1, [WOOD[1], WOOD[2]])
    m.fill(m.box(x0 + 1, bed + 2, z0, x1 - 1, 35, z0 + 1), pick([WOOD_DARK[0], WOOD_DARK[1]], hash2(m.x // 3, m.y // 4, 526)))
    for y in (19, 26):
        m.fill(m.box(x0 + 1, y, z0 + 1, x1 - 1, y + 1, z0 + 5), WOOD[1])
        for x in range(x0 + 2, x1 - 2, 3):
            c = [TIN[0], TIN[2], BURLAP[1], DYE_RED[2], LEATHER[1]][int(hash2(x, y, 524) * 5)]
            m.fill(m.box(x, y + 1, z0 + 2, x + 2, y + 2 + int(hash2(x, y, 525) * 3), z0 + 4), c)
    # A rail across the front and coats hung from it, each a dulled colour.
    m.beam((x0, 32, z1 - 3), (x1 - 1, 32, z1 - 3), 1, [WOOD_DARK[0]])
    coats = [MOSS[1], DYE_BLUE[0], DYE_RED[1], FELT[0], DYE_YELLOW[2], CANVAS_OILED[0]]
    for k, xc in enumerate(range(x0 + 3, x1 - 1, 4)):
        body, trim = coats[k % len(coats)], coats[(k + 3) % len(coats)]
        top = 31
        length = 11 + int(hash2(k, 0, 527) * 5)
        coat = (np.abs(m.x - xc) <= 1.2 + (top - yf) * 0.1) & (yf <= top) & (yf > top - length) & (m.z >= z1 - 5) & (m.z < z1 - 1)
        m.fill(coat & (m.grid < 0), np.where((np.abs(m.x - xc) < 0.5) | (yf > top - 1.5), trim, body))
        m.grid[xc, top + 1, z1 - 3] = IRON[0]
    # The striped awning, sloping down to the front, with a scalloped edge.
    over_z1 = z1 + 6
    slope = 37 + (z1 - m.z) * 0.18
    awning = (m.x >= x0 - 2) & (m.x < x1 + 2) & (m.z >= z0 - 1) & (m.z < over_z1) & (yf >= slope) & (yf < slope + 1.5)
    stripe = ((m.x - x0 + 2) // 3) % 3
    stripe_colors = np.where(stripe == 0, DYE_RED[0], np.where(stripe == 1, CLOTH_PALE[1], DYE_BLUE[1]))
    m.fill(awning, stripe_colors)
    scallop = (m.z == over_z1 - 1) & (m.x >= x0 - 2) & (m.x < x1 + 2) & (yf < slope) & (yf >= slope - 2 - ((m.x % 3) == 1))
    m.fill(scallop, stripe_colors)
    for x in (x0 - 2, x1 + 1):
        m.beam((x, 36, over_z1 - 1), (x, bed + 3, z1 + 1), 1, [WOOD_DARK[0]])
    # The sign above: a hammer crossed with a spanner, pale on dark wood.
    xc = (x0 + x1) // 2
    m.beam((xc, 38, z0 + 6), (xc, 47, z0 + 6), 1, [WOOD_DARK[0]])
    m.beam((xc - 6, 47, z0 + 6), (xc + 6, 47, z0 + 6), 1, [WOOD_DARK[0]])
    for x in (xc - 5, xc + 5):
        m.beam((x, 47, z0 + 6), (x, 45, z0 + 6), 1, [IRON[0]])
    board = m.box(xc - 5, 39, z0 + 7, xc + 6, 45, z0 + 8)
    u, v = (m.x - xc).astype(float), yf - 42
    icon = ((np.abs(u - v) < 0.8) & (np.abs(u) < 3)) | ((np.abs(u + v) < 0.8) & (np.abs(u) < 3)) | ((np.abs(v - 2) < 0.8) & (np.abs(u + 2) < 1.6))
    m.fill(board, np.where(icon, TIN[0], np.where((m.x == xc - 5) | (m.x == xc + 5) | (m.y == 39) | (m.y == 44), WOOD_DARK[0], WOOD[2])))
    # The grinding wheel on a little frame at the front left, facing the camera.
    gx, gy, gz = 10.0, 9.0, z1 + 4
    m.fill(m.box(6, 0, z1 + 2, 15, 4, z1 + 6), WOOD[0])
    m.fill((np.hypot(m.x - gx, m.y - gy) <= 4.6) & (np.abs(m.z - gz) < 1.5), pick(STONE[:3], hash2(m.x, m.y, 528)))
    m.fill((np.hypot(m.x - gx, m.y - gy) <= 1.2) & (np.abs(m.z - gz) < 2.5), IRON[0])
    m.beam((gx + 1, gy, gz + 2), (gx + 4, gy - 3, gz + 2), 1, [WOOD[3]])
    # A bucket and a crate of scrap at the front right.
    barrel(m, 25, z1 + 4, r=2.4, h=5)
    m.fill(m.box(17, 0, z1 + 2, 22, 4, z1 + 6), WOOD[2])
    m.fill(m.box(18, 4, z1 + 3, 21, 5, z1 + 5), IRON[1])
    # The handles at the back, down to a stand.
    for x in (8, 26):
        m.beam((x, bed + 2, z0), (x, 6, 1), 1, [WOOD[1], WOOD[3]])
        m.beam((x, 6, 2), (x, 0, 2), 1, [WOOD_DARK[0]])
    return m


def long_table():
    """The long table by the cookfire: a trestle table of dark boards with a
    bench either side, iron-bound at the ends, a red cloth over each end and a
    grey runner with a red Orran cross hanging down the front, bowls of stew
    and apples, a loaf and a lidded black pot on it. 40 x 19 x 26 voxels."""
    m = Model(42, 22, 26)
    x0, x1 = 2, 40
    top = 12
    # The trestles: an A of two legs at each end, a stretcher between them.
    for x in (6, 35):
        for dz in (-1, 1):
            m.beam((x, 0, 12 + dz * 4), (x, top, 12 + dz * 1.5), 2, [WOOD[1], WOOD[2]])
        m.beam((x, 4, 8), (x, 4, 16), 1, [WOOD_DARK[0]])
    m.beam((6, 5, 12), (35, 5, 12), 2, [WOOD[2], WOOD_DARK[0]])
    plank_box(m, x0, x1, top, top + 2, 6, 19, 530, run='x', across='z')
    m.fill(m.box(x0, top, 6, x1, top + 2, 19) & ((m.x == x0) | (m.x == x1 - 1)), IRON[0])
    studs(m, [(x, top + 1, z) for x in (x0, x1 - 1) for z in (8, 16)])
    # A bench either side.
    for z0, z1 in ((0, 4), (22, 26)):
        plank_box(m, x0 + 1, x1 - 1, 6, 8, z0, z1, 531 + z0, run='x', across='z', width=2)
        for x in (5, 36):
            m.fill(m.box(x - 1, 0, z0 + 1, x + 1, 6, z1 - 1), WOOD[2])
        studs(m, [(x0 + 1, 7, (z0 + z1) // 2), (x1 - 2, 7, (z0 + z1) // 2)])
    # Red cloths over both ends, a grey runner down the middle and over the front.
    for xa, xb in ((x0, x0 + 6), (x1 - 6, x1)):
        m.fill(m.box(xa, top + 2, 6, xb, top + 3, 19), DYE_RED[0])
        cloth_drape(m, xa, xb, 19, top + 2, 5, DYE_RED, 532 + xa)
        cloth_drape(m, xa, xb, 5, top + 2, 4, DYE_RED, 534 + xa)
    m.fill(m.box(15, top + 2, 6, 26, top + 3, 19), CLOTH_GREY[0])
    cloth_drape(m, 15, 26, 19, top + 2, 8, [CLOTH_GREY[0], FELT[2], CLOTH_GREY[1]], 536, mark=DYE_RED[0])
    # The meal: bowls, a loaf, apples and the lidded pot.
    y = top + 3
    bowl(m, 6, y, 12, 2.2, [DYE_RED[0], DYE_RED[1]])
    bowl(m, 12, y, 10, 2.2, [STRAW[0], MOSS[2]])
    bowl(m, 31, y, 14, 2.2, [STRAW[1], WOOD_LIT[1]])
    bowl(m, 35, y, 10, 2.0, [MOSS[2], STRAW[0]])
    m.ellipsoid((19.0, y + 0.6, 13.0), (3.4, 1.6, 2.2), WOOD_LIT[0])
    m.fill(m.box(17, y + 1, 12, 22, y + 3, 14) & (m.grid >= 0) & (hash2(m.x, m.z, 537) < 0.5), STRAW[0])
    m.ellipsoid((26.0, y + 2.2, 11.0), (3.0, 2.6, 3.0), SOOT[0])
    m.fill(m.box(23, y + 4, 8, 30, y + 5, 15) & (np.hypot(m.x - 26, m.z - 11) <= 2.6), IRON[0])
    m.grid[26, y + 5, 11] = IRON[1]
    return m


def water_barrels():
    """A water butt on two skids: a big staved cask with three iron hoops,
    open and full, a striped towel over its rim on the left and a ladle on a
    peg at the front. 18 x 21 x 19 voxels."""
    m = Model(20, 24, 22)
    yf = m.y.astype(float)
    cx, cz = 9.5, 9.5
    for x in (5, 14):
        m.fill(m.box(x - 1, 0, 3, x + 1, 3, 17), WOOD_DARK[0])
    staved_barrel(m, cx, cz, 3, 6.6, 18, 540, hoops=(2, None, -3))
    # The towel: over the rim at the back left and down the left side.
    ring = np.hypot(m.x - cx, m.z - cz)
    stripes = (m.z % 4 == 0)
    towel_color = np.where(stripes, DYE_RED[1], pick([CLOTH_GREY[0], FELT[2], CLOTH_GREY[1]], hash2(m.z, m.y // 2, 542)))
    side = (m.x < cx - 3) & (m.z >= 5) & (m.z < 12) & (np.abs(ring - 8.4) < 0.8) & (yf > 9 + hash2(m.z, 0, 541) * 3) & (yf < 21)
    m.fill(side, towel_color)
    m.fill((m.x < cx - 2) & (m.z >= 5) & (m.z < 12) & (ring > 5.5) & (ring < 9.2) & (m.y == 21), towel_color)
    # The ladle: a peg at the front, the handle down, the cup at the bottom.
    front = 18
    m.grid[13, 16, front - 1] = WOOD_DARK[0]
    m.beam((13, 16, front), (13, 7, front), 1, [WOOD[3], WOOD_LIT[1]])
    m.fill(m.box(12, 4, front - 1, 15, 7, front + 2) & ~m.box(13, 6, front, 14, 7, front + 1), IRON[1])
    m.beam((13, 13, front), (13, 14, front), 1, [ROPE[0]])
    return m


def torch_pole(lit=True):
    """A torch pole from the ring round the camp: a staff in a cairn of
    stones, bound with rope, a ragged madder cloth with a pale cross hung
    below an iron basket. Lit, the basket is full of glowing coals, under the
    flame Fires.dk plays; cold, of black char and quills. 10 x 51 x 11
    voxels (48 cold)."""
    height = 52 if lit else 48
    m = Model(14, height + 2, 14)
    cx, cz = 7, 7
    yf = m.y.astype(float)
    ring = np.hypot(m.x - cx, m.z - cz)
    for k in range(7):
        a = k * 0.9
        m.ellipsoid((cx + math.cos(a) * 3.4, 1.0, cz + math.sin(a) * 3.4), (1.8, 1.4, 1.8), STONE[k % 4])
    top = height - 9
    m.beam((cx, 0, cz), (cx, top, cz), 2, [WOOD[1], WOOD[2], WOOD[0]])
    for y in (top - 3, top - 2, 21, 22):
        m.fill((ring < 1.9) & (m.y == y), ROPE[y % 2])
    # The cloth, hung from the binding on the front.
    seed = 550 if lit else 551
    cloth = (m.z == cz + 1) & (np.abs(m.x - cx + 0.5) < 2.0) & (yf <= top - 4) & (yf > top - 22 + hash2(m.x, 0, seed) * 4)
    mark = ((np.abs(m.x - cx + 0.5) < 0.6) & (np.abs(yf - (top - 11)) < 2.4)) | ((np.abs(yf - (top - 10)) < 0.6) & (np.abs(m.x - cx + 0.5) < 1.6))
    m.fill(cloth, np.where(mark, CLOTH_PALE[0], pick(DYE_RED, hash2(m.x, m.y // 3, 552))))
    m.beam((cx + 2, top - 4, cz + 1), (cx + 3, top - 14, cz + 2), 1, [DYE_RED[2]])
    # The basket: four bars flaring from a collar, a band round the top.
    base = top
    for k in range(4):
        a = k * math.pi / 2.0 + math.pi / 4.0
        m.beam((cx, base, cz), (cx + math.cos(a) * 3.6, base + 7, cz + math.sin(a) * 3.6), 1, [IRON[0]])
    m.fill((np.abs(ring - 3.6) < 0.8) & (m.y == base + 6), IRON[0])
    load = (ring < 1.2 + (yf - base) * 0.4) & (yf > base) & (yf < base + 6) & (m.grid < 0)
    if lit:
        # Glowing coals only: the flame, its smoke and its light are the
        # game's (Fires.dk), which knows the torch by its volume.
        m.fill(load, pick([EMBER[1], EMBER[0], GLOW[1], EMBER[2]], hash2(m.x, m.y + m.z, 553)))
    else:
        m.fill(load, pick([SOOT[0], QUILL_BLACK[0], QUILL_ASH[2]], hash2(m.x, m.y + m.z, 554)))
        for k in range(5):
            a = hash2(k, 0, 555) * math.tau
            m.beam((cx, base + 5, cz), (cx + math.cos(a) * 2.5, base + 8, cz + math.sin(a) * 2.5), 1, [QUILL_BLACK[1]])
    return m


def feather_sack():
    """A sack of gathered black feathers waiting for the Feather Fire: patched
    burlap tied at the neck with rope, its mouth rolled down and black quills
    spilling over the top. 16 x 18 x 14 voxels."""
    m = Model(18, 19, 16)
    cx, cz = 8.5, 7.5
    yf = m.y.astype(float)
    dist = np.hypot(m.x - cx, (m.z - cz) * 1.15)
    # The body: wide and slumped at the foot, narrowing to the neck at 10.
    radius = np.where(yf < 9, 7.6 - (yf - 4.5) ** 2 * 0.07, 5.0 + (yf - 9) * 0.5)
    sack = (dist <= radius) & (yf < 13)
    weave = pick([CANVAS_OILED[0], BURLAP[1], CANVAS[1], CANVAS_OILED[3]], hash2(m.x + m.z * 3, m.y, 560) * 0.7 + 0.3 * hash2(m.x // 3, m.y // 3, 561))
    m.fill(sack, weave)
    # The rolled rim, the rope round the neck, its knot and tassel.
    m.fill((dist <= radius + 0.8) & (dist > radius - 1.0) & (yf >= 12) & (yf < 13.5), CANVAS[1])
    m.fill((dist <= radius + 0.7) & (dist > radius - 0.5) & (yf >= 9) & (yf < 10), ROPE[0])
    m.fill(m.box(8, 8, 13, 10, 10, 15) & (m.grid < 0), ROPE[1])
    m.beam((9, 8, 14), (8, 3, 15), 1, [ROPE[0], ROPE[1]])
    # Patches: woad on the front right, madder on the left, a darned hole.
    front = (m.z > cz + 2) & sack
    m.fill(front & (np.abs(m.x - 12) < 2.2) & (np.abs(yf - 4) < 2.0), DYE_BLUE[1])
    m.fill(front & (np.abs(m.x - 4) < 1.8) & (np.abs(yf - 6) < 1.6), DYE_RED[1])
    m.fill(front & (np.abs(m.x - 7) < 0.6) & (np.abs(yf - 3) < 0.6), SOOT[0])
    # The feathers: a heap in the mouth and quills fanning out of it.
    m.fill((dist <= 5.0) & (yf >= 12) & (yf < 14 + hash2(m.x, m.z, 562) * 2), pick(QUILL_BLACK, hash2(m.x, m.z, 563)))
    for k in range(9):
        a = k * math.tau / 9 + hash2(k, 0, 564)
        r = 1.0 + hash2(k, 1, 565) * 3.0
        fx, fz = cx + math.cos(a) * r, cz + math.sin(a) * r
        m.beam((fx, 13, fz), (fx + math.cos(a) * 2.5, 17 + hash2(k, 2, 566) * 1.5, fz + math.sin(a) * 2.0), 1, [QUILL_BLACK[0], QUILL_BLACK[2]])
    return m


def raven_cage():
    """The raven cage Edda's bird is posted from: a wicker cage with a domed
    top on a stout post, its little door open to the front, a sack of
    feathers tied to the post. 18 x 46 x 22 voxels."""
    m = Model(22, 48, 24)
    cx, cz = 10.5, 9.0
    yf = m.y.astype(float)
    # The post on a cross of feet.
    m.beam((cx, 0, cz), (cx, 27, cz), 2, [WOOD[1], WOOD[2], WOOD[0]])
    m.beam((cx - 4, 0, cz), (cx + 4, 0, cz), 1, [WOOD_DARK[0]])
    m.beam((cx, 0, cz - 4), (cx, 0, cz + 4), 1, [WOOD_DARK[0]])
    # The cage: wicker walls with rounded corners and a dome.
    y0, y1 = 26, 38
    dx, dz = np.abs(m.x - cx), np.abs(m.z - cz)
    half_x, half_z = 7.5, 6.5
    dome = np.where(yf < y1, 1.0, np.sqrt(np.clip(1.0 - ((yf - y1) / 6.5) ** 2, 0.0, 1.0)))
    edge = (dx / (half_x * dome + 0.01)) ** 3 + (dz / (half_z * dome + 0.01)) ** 3
    walls = (yf >= y0) & (yf < y1 + 7) & (edge <= 1.0) & (edge > 0.62)
    # Uprights every third voxel round the walls, bands every fourth course,
    # and the dome woven closed.
    around = np.where(dx * half_z > dz * half_x, m.z, m.x)
    bars = (around % 3 == 0) | ((m.y - y0) % 4 == 0) | (yf >= y1 + 3)
    m.fill(walls & bars, pick(WICKER, hash2(m.x + m.z, m.y // 2, 570)))
    m.fill((m.y == y0) & (edge <= 1.0), WOOD[2])
    # The door on the front, swung open to the camera's right.
    front = int(cz + half_z)
    door_x0, door_x1 = int(cx) - 3, int(cx) + 3
    m.clear(m.box(door_x0, y0 + 2, front - 2, door_x1, y1, front + 2) & (m.z > cz))
    m.fill(m.box(door_x0 - 1, y0 + 1, front - 1, door_x0, y1 + 1, front + 1), WOOD[1])
    m.fill(m.box(door_x1, y0 + 1, front - 1, door_x1 + 1, y1 + 1, front + 1), WOOD[1])
    door = (m.x == door_x1 + 1) & (m.z >= front + 1) & (m.z < front + 7) & (yf >= y0 + 2) & (yf < y1)
    m.fill(door & (((m.z + m.y) % 2 == 0) | (m.y == y0 + 2) | (m.y == y1 - 1) | (m.z == front + 6)), WICKER[0])
    # A ring on top to hang it by.
    m.fill((np.abs(np.hypot(m.x - cx, m.y - (y1 + 8.0)) - 1.6) < 0.7) & (m.z == int(cz)), IRON[0])
    # The sack of feathers tied to the post at the front, a red rag on it.
    m.ellipsoid((cx, 13.0, cz + 2.8), (2.6, 4.0, 1.8), BURLAP[0])
    m.fill(m.box(int(cx) - 1, 17, int(cz) + 1, int(cx) + 2, 19, int(cz) + 4), ROPE[1])
    for k in range(4):
        m.beam((cx - 1.5 + k, 16, cz + 3), (cx - 2.5 + k * 1.6, 20 + k % 2, cz + 4), 1, [QUILL_BLACK[1], QUILL_BLACK[0]])
    m.fill(m.box(int(cx) - 1, 9, int(cz) + 4, int(cx) + 2, 12, int(cz) + 5), DYE_RED[1])
    return m


def cook_pot():
    """The cook pot: a black cauldron of stew hung on a chain from two poles
    crossed and lashed over it, rags tied at the crossing, on a ring of
    stones round embers and split logs, a ladle in the stew.
    26 x 27 x 14 voxels."""
    m = Model(26, 28, 18)
    cx, cz = 12.5, 8.5
    yf = m.y.astype(float)
    # The fire ring: stones round embers and two logs.
    for k in range(10):
        a = k * math.tau / 10
        m.ellipsoid((cx + math.cos(a) * 7.0, 1.0, cz + math.sin(a) * 5.6), (1.8, 1.4, 1.6), STONE[k % 5])
    m.fill((np.hypot(m.x - cx, (m.z - cz) * 1.2) < 5.4) & (m.y == 0), pick([EMBER[2], SOOT[0], EMBER[1], QUILL_ASH[2]], hash2(m.x, m.z, 580)))
    m.beam((cx - 4, 1, cz - 1), (cx + 4, 1, cz + 1), 2, [WOOD_DARK[0], WOOD_DARK[1]])
    m.beam((cx - 3, 1, cz + 2), (cx + 3, 2, cz - 2), 2, [WOOD_DARK[1], EMBER[2]])
    m.fill((np.hypot(m.x - cx, m.z - cz) < 3.0) & (m.y == 3) & (hash2(m.x, m.z, 581) < 0.5) & (m.grid < 0), EMBER[0])
    # The poles, crossed and lashed at the top, rags tied there.
    apex = 24
    m.beam((1, 0, cz), (cx + 3, apex + 2, cz), 2, [WOOD[1], WOOD[2]])
    m.beam((24, 0, cz), (cx - 3, apex + 2, cz), 2, [WOOD[1], WOOD[2]])
    m.fill(m.box(int(cx) - 1, apex - 1, int(cz) - 1, int(cx) + 2, apex + 2, int(cz) + 2), ROPE[0])
    for x, length, color in ((cx - 2, 6, DYE_RED[1]), (cx + 2, 4, CLOTH_GREY[1])):
        m.beam((x, apex, cz + 1), (x - 0.5, apex - length, cz + 1.5), 1, [color])
    # The chain, the bail and the cauldron.
    m.beam((cx, apex - 1, cz), (cx, 15, cz), 1, [IRON[0], IRON[1]])
    m.fill((np.abs(np.hypot(m.x - cx, m.y - 12.0) - 4.6) < 0.6) & (m.z == int(cz)) & (m.y > 12), IRON[0])
    r = np.hypot(m.x - cx, (m.z - cz) * 1.05)
    pot = (r <= 5.6 - np.clip(7.0 - yf, 0, None) * 0.45) & (yf >= 4) & (yf < 12)
    m.fill(pot, pick([SOOT[0], IRON[0]], hash2(m.x, m.y // 2, 582) * 0.4))
    m.fill((r <= 6.2) & (r > 4.4) & (m.y == 12), IRON[0])
    m.fill((r <= 4.4) & (m.y == 11), pick([WOOD_LIT[1], DYE_YELLOW[2], MUD[0]], hash2(m.x, m.z, 583)))
    m.beam((cx + 2, 11, cz), (cx + 6, 17, cz + 2), 1, [WOOD[3]])
    return m


RECIPES = {
    'PilgrimShrine': pilgrim_shrine,
    'FeatherFire': feather_fire,
    'WrensTent': wrens_tent,
    'PilgrimTent': pilgrim_tent,
    'PilgrimTentB': pilgrim_tent_b,
    'ChalkCircle': chalk_circle,
    'HesksWagon': hesks_wagon,
    'TinkersCart': tinkers_cart,
    'LongTable': long_table,
    'WaterBarrels': water_barrels,
    'TorchPole': torch_pole,
    'TorchPoleCold': lambda: torch_pole(lit=False),
    'FeatherSack': feather_sack,
    'RavenCage': raven_cage,
    'CookPot': cook_pot,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    for name in args.names or RECIPES:
        buildings.build(name, args.preview, RECIPES)


if __name__ == '__main__':
    main()
