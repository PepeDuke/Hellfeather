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
                 DYE_RED, BURLAP, Model, hash2, pick, planks)
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


RECIPES = {
    'PilgrimShrine': pilgrim_shrine,
    'FeatherFire': feather_fire,
    'WrensTent': wrens_tent,
    'PilgrimTent': pilgrim_tent,
    'PilgrimTentB': pilgrim_tent_b,
    'ChalkCircle': chalk_circle,
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
