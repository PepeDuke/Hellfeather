"""Builds the furniture of Act I's interiors from recipes, as buildings.py builds
the buildings.

Each prop is a function that returns a kit.Model, put together from parts:
planked boards with dark seams and edges, square posts, iron bands and nails,
stone courses, cylinders for barrels, jars and millstones. Proportions are
measured off the three-view concept sheets in Downloads/interior-props, which
--import crops into Assets/Reference/Interiors for comparison. Furniture uses
act1.CELL voxels (0.025 units, 40 to a unit), as people do, so it stands at the
right size beside them. +Z is the front, which faces the camera.

A wall fitting, such as a sconce, is built that many voxels up off an empty
floor (RAISE), so the game can place it like any other prop.

    python Tools/Models/interiors.py --import DIR    crop the sheets' panels for reference
    python Tools/Models/interiors.py                 build every prop
    python Tools/Models/interiors.py Table Chest     build some of them
    python Tools/Models/interiors.py --preview       also save isometric renders to Tools/Models/Preview
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402
from kit import (BRASS, BURLAP, CANDLE, CLOTH_GREY, CLOTH_PALE, CLOTH_RED, FLOUR, GLOW, IRON, MORTAR, PAPER,  # noqa: E402
                 ROPE, SOOT, STONE, STRAW, WOOD, WOOD_DARK, WOOD_LIT, Model, color, compact, hash2, pick)

CROPS = act1.ROOT / 'Assets/Reference/Interiors'

# Materials of the interiors, beside the kit's.
OAK = color('oak', (122, 80, 46), (108, 70, 40), (134, 90, 52), (96, 62, 36))
OAK_DARK = color('oak dark', (58, 38, 24), (44, 29, 19))
CERAMIC = color('ceramic', (214, 204, 182), (192, 182, 162))
GLAZE = color('glaze', (64, 88, 138), (46, 64, 104))
CLAY = color('clay', (150, 78, 48), (126, 62, 38), (168, 96, 60))
JAM = color('jam', (138, 40, 38), (178, 118, 40), (84, 112, 50))
LINEN = color('linen', (204, 194, 170), (184, 174, 152))
BLANKET = color('blanket', (118, 102, 84), (100, 86, 70), (132, 116, 96))
LAVENDER = color('lavender', (128, 98, 152), (104, 78, 128))
HERB = color('herb', (92, 116, 60), (72, 94, 46), (112, 134, 72))
BLOOM = color('bloom', (216, 182, 72), (238, 214, 122))
EMBER = color('ember', (206, 74, 30), (150, 42, 20))
BURLAP_DARK = color('burlap dark', (112, 92, 64))
STRIPE = color('stripe', (150, 52, 44))
SOOT_DEEP = color('soot deep', (20, 18, 17))
# Damp wood, the salt line water leaves as it dries, and the Waterwalkers'
# leather, which keeps a cold blue-grey sheen.
DAMP = color('damp', (52, 36, 24), (44, 30, 20), (60, 42, 28))
TIDE = color('tide', (150, 140, 120), (124, 116, 100))
WALKER = color('walker', (58, 56, 60), (46, 44, 48), (78, 82, 92), (30, 28, 30))
# Black flight feathers, as the feather item: near black with a blue sheen.
FEATHER_BLACK = color('feather black', (20, 21, 27), (14, 14, 18), (31, 43, 82), (96, 100, 106))
LEATHER_BOOK = color('book', (102, 52, 32), (80, 40, 26))
INK = color('ink', (16, 16, 20))


# Parts.

def boards(m, x0, x1, y0, y1, z0, z1, grain='x', width=4, shades=OAK, seed=0, edges=True):
    """A box of boards: grain 'x' or 'z' lays them flat along that axis, side by
    side, and 'y' stands them up. Seams between boards and the box's edges are
    dark, so a piece reads at this size."""
    mask = m.box(x0, y0, z0, x1, y1, z1)
    if grain == 'x':
        lane, along = m.z - z0, m.x
    elif grain == 'z':
        lane, along = m.x - x0, m.z
    else:
        lane, along = (m.x - x0) + (m.z - z0), m.y
    lanes = np.floor(lane / width).astype(int)
    tone = hash2(lanes, seed, seed) * 0.65 + hash2(lanes, np.floor(along / 7).astype(int), seed + 1) * 0.35
    colors = pick(shades, tone)
    seam = (lane % width == 0) & (lane > 0)
    colors = np.where(seam, OAK_DARK[0], colors)
    if edges:
        on = ((m.x == x0) | (m.x == x1 - 1)).astype(int) + ((m.y == y0) | (m.y == y1 - 1)).astype(int) + ((m.z == z0) | (m.z == z1 - 1)).astype(int)
        colors = np.where(on >= 2, OAK_DARK[1], colors)
    m.fill(mask, colors)
    return mask


def post(m, x0, x1, y0, y1, z0, z1, shades=OAK, seed=0):
    """A square post or rail with its edges in shadow."""
    return boards(m, x0, x1, y0, y1, z0, z1, grain='y', width=99, shades=shades, seed=seed)


def dot(m, x, y, z, colors=IRON):
    """A nail or rivet head."""
    w, h, d = m.grid.shape
    if 0 <= x < w and 0 <= y < h and 0 <= z < d:
        m.grid[x, y, z] = colors[0]


def cylinder(m, cx, cz, r, y0, y1, colors, bulge=0.0):
    """Upright, centered on (cx, cz); bulge swells the middle like a barrel's."""
    t = np.clip((m.y - y0) / max(1, y1 - y0 - 1), 0.0, 1.0)
    radius = r + bulge * np.sin(t * math.pi)
    mask = (np.hypot(m.x - cx + 0.5, m.z - cz + 0.5) <= radius) & (m.y >= y0) & (m.y < y1)
    m.fill(mask, colors[0] if isinstance(colors, list) else colors)
    return mask


def disc_z(m, cx, cy, r, z0, z1, colors):
    """A wheel standing in the x-y plane, z0 to z1 thick."""
    mask = (np.hypot(m.x - cx + 0.5, m.y - cy + 0.5) <= r) & (m.z >= z0) & (m.z < z1)
    m.fill(mask, colors)
    return mask


def jar(m, x, z, y, r, h, body, band=None, lid=None, neck=0.7):
    """A pot: a swelling body, a narrower neck, an optional band and lid."""
    t = np.clip((m.y - y) / max(1, h - 1), 0.0, 1.0)
    radius = np.where(t < 0.8, r * (0.8 + 0.3 * np.sin(t / 0.8 * math.pi)), r * neck)
    mask = (np.hypot(m.x - x + 0.5, m.z - z + 0.5) <= radius) & (m.y >= y) & (m.y < y + h)
    colors = np.full(m.grid.shape, body[0])
    colors = np.where(hash2(m.x, m.y, 7) < 0.3, body[-1], colors)
    if band is not None:
        colors = np.where((m.y - y) == int(h * 0.45), band[0], colors)
    m.fill(mask, colors)
    if lid is not None:
        m.fill(m.box(x - int(r * neck), y + h, z - int(r * neck), x + int(r * neck) + 1, y + h + 1, z + int(r * neck) + 1), lid[0])


def flame(m, x, y, z, tall=4):
    """A candle flame: glow narrowing to a bright tip."""
    for k in range(tall):
        m.grid[x, y + k, z] = GLOW[0] if k < tall - 1 else GLOW[1]
    if tall > 2:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m.grid[x + dx, y, z + dz] = GLOW[2]


def candle(m, x, y, z, tall=6):
    m.fill(m.box(x - 1, y, z - 1, x + 2, y + tall, z + 2), CANDLE[0])
    flame(m, x, y + tall, z)


def sack(m, x, y, z, rx, ry, rz, shades=BURLAP, tie=True, lean=0.0):
    """A filled sack, its burlap mottled, tied off at the top."""
    mask = ((m.x - x) / rx) ** 2 + ((m.y - y - ry) / ry) ** 2 + ((m.z - z) / rz) ** 2 <= 1.0
    mask &= m.y >= y
    m.fill(mask, pick(shades + BURLAP_DARK, hash2(m.x // 2, m.y // 2 + m.z, 11)))
    if tie:
        top = y + 2 * ry
        m.ellipsoid((x + lean, top + 1, z), (rx * 0.35, 2.0, rz * 0.35), ROPE[0])
        m.ellipsoid((x + lean, top + 3, z), (rx * 0.45, 2.0, rz * 0.45), shades[1])


def barrel(m, x, z, y, r, h, seed=0):
    """Staves with dark seams, iron hoops near each end and the middle."""
    angle = np.arctan2(m.z - z + 0.5, m.x - x + 0.5)
    stave = np.floor((angle + math.pi) / (2 * math.pi) * 18).astype(int)
    colors = np.where(hash2(stave, seed, 5) < 0.5, OAK[0], OAK[2])
    colors = np.where(((angle + math.pi) / (2 * math.pi) * 18) % 1.0 < 0.12, OAK_DARK[0], colors)
    yy = m.y - y
    hoop = (yy == 2) | (yy == 3) | (yy == h - 3) | (yy == h - 4) | (np.abs(yy - h // 2) <= 0)
    colors = np.where(hoop, IRON[0], colors)
    colors = np.where(yy == h - 1, OAK[3], colors)
    cylinder(m, x, z, r, y, y + h, colors, bulge=r * 0.12)


def blanket_fold(m, x0, x1, y, z0, z1, shades, seed=0):
    """A cloth laid over a surface, hanging a little over the sides with a
    ragged hem."""
    hang = 2 + (hash2(m.x, m.z, seed) * 3).astype(int)
    on = m.box(x0, y, z0, x1, y + 2, z1)
    side = ((m.z == z0 - 1) | (m.z == z1)) & (m.x >= x0) & (m.x < x1) & (m.y < y + 2) & (m.y >= y + 2 - hang)
    colors = pick(shades, hash2(m.x // 3, m.z // 3, seed))
    m.fill(on | side, colors)


# Props. Sizes in the docstrings are in units, then voxels.

def table():
    """A rustic table: a thick top of four boards, square legs, an apron and low
    stretchers. 1.1 by 0.75, 0.78 tall: 44 x 30 x 31."""
    m = Model(46, 32, 32)
    boards(m, 1, 45, 27, 31, 1, 31, grain='x', width=7, seed=1)
    for x in (3, 39):
        for z in (3, 25):
            post(m, x, x + 4, 0, 27, z, z + 4, seed=x + z)
    boards(m, 4, 42, 22, 27, 4, 6, grain='x', width=99, seed=3)
    boards(m, 4, 42, 22, 27, 26, 28, grain='x', width=99, seed=4)
    boards(m, 3, 7, 22, 27, 6, 26, grain='z', width=99, seed=5)
    boards(m, 39, 43, 22, 27, 6, 26, grain='z', width=99, seed=6)
    boards(m, 4, 7, 6, 9, 6, 26, grain='z', width=99, seed=7)
    boards(m, 39, 42, 6, 9, 6, 26, grain='z', width=99, seed=8)
    boards(m, 7, 39, 6, 9, 14, 17, grain='x', width=99, seed=9)
    for x in (4, 41):
        for z in (4, 7, 22, 26):
            dot(m, x, 30, z)
    return m


def bench():
    """A plank bench on splayed trestle legs with a long stretcher. 1.4 by 0.35,
    0.45 tall: 56 x 14 x 18."""
    m = Model(58, 20, 18)
    boards(m, 1, 57, 15, 19, 2, 16, grain='x', width=7, seed=11)
    for x0, lean in ((7, -1), (47, 1)):
        for z in (3, 12):
            m.beam((x0 + 2 + lean * 3, 0, z + 1), (x0 + 2, 14, z + 1), 3, [OAK[1], OAK[3]])
        boards(m, x0, x0 + 5, 11, 15, 3, 15, grain='z', width=99, seed=x0)
    boards(m, 9, 49, 5, 8, 7, 10, grain='x', width=99, seed=12)
    for x in (3, 54):
        dot(m, x, 18, 4)
        dot(m, x, 18, 13)
    return m


def stool():
    """A three-board seat on four splayed legs with rungs. 0.45 square, 0.5
    tall: 18 x 18 x 20."""
    m = Model(22, 22, 22)
    boards(m, 2, 20, 17, 21, 2, 20, grain='x', width=6, seed=21)
    for x, z, dx, dz in ((4, 4, -1, -1), (15, 4, 1, -1), (4, 15, -1, 1), (15, 15, 1, 1)):
        m.beam((x + 1 + dx * 2, 0, z + 1 + dz * 2), (x + 1, 16, z + 1), 3, [OAK[1], OAK[0]])
    boards(m, 5, 17, 6, 8, 4, 6, grain='x', width=99, seed=22)
    boards(m, 5, 17, 6, 8, 16, 18, grain='x', width=99, seed=23)
    return m


def chest():
    """A planked chest under a rounded lid, iron bands over it and at the
    corners, a lock plate at the front. 0.9 by 0.55, 0.6 tall: 36 x 22 x 24."""
    m = Model(38, 26, 24)
    boards(m, 1, 37, 0, 16, 1, 23, grain='x', width=4, shades=OAK, seed=31)
    # The lid: a half barrel along x.
    lid = (np.hypot(m.y - 15.5, (m.z - 11.5) * 0.85) <= 9.5) & (m.y >= 16) & (m.x >= 1) & (m.x < 37) & (m.z >= 1) & (m.z < 23)
    angle = np.arctan2(m.y - 15.5, m.z - 11.5)
    m.fill(lid, np.where(np.floor(angle * 6).astype(int) % 2 == 0, OAK[0], OAK[2]))
    lid_seam = lid & ((angle * 6) % 1.0 < 0.15)
    m.fill(lid_seam, OAK_DARK[0])
    solid = m.grid >= 0
    for x in (4, 5, 32, 33):
        band = solid & (m.x == x)
        m.fill(band & ~ndimage.binary_erosion(solid), IRON[0])
    for x in (1, 36):
        m.fill(solid & (m.x == x) & ((m.z <= 2) | (m.z >= 21)), IRON[0])
    m.fill(m.box(16, 9, 23, 22, 17, 24), IRON[1])
    m.fill(m.box(18, 11, 23, 20, 14, 24), SOOT_DEEP[0])
    for x in (2, 35):
        m.fill(m.box(x - 1 if x == 2 else x, 11, 10, x if x == 2 else x + 1, 13, 14), IRON[0])
    return m


def inside_door():
    """An arched plank door in a dressed stone surround, with strap hinges and a
    ring pull, to stand against a wall. 1.1 wide, 2.3 tall: 44 x 92 x 8."""
    m = Model(46, 94, 10)
    cx = 22.5
    # The stone surround, an arch of voussoirs.
    outer = ((m.y < 72) & (np.abs(m.x - cx) <= 22)) | (np.hypot(m.x - cx, m.y - 72) <= 22)
    inner = ((m.y < 72) & (np.abs(m.x - cx) <= 16)) | (np.hypot(m.x - cx, m.y - 72) <= 16)
    frame = outer & ~inner & (m.z >= 1) & (m.z < 9) & (m.y < 94)
    angle = np.arctan2(m.y - 72, m.x - cx)
    stone_id = np.where(m.y < 72, (m.y // 9) * 2 + (m.x > cx), 100 + np.floor(angle * 4).astype(int))
    colors = pick(STONE, hash2(stone_id, 3, 41))
    joint = np.where(m.y < 72, m.y % 9 == 0, (angle * 4) % 1.0 < 0.12)
    colors = np.where(joint, MORTAR[0], colors)
    m.fill(frame, colors)
    # The door, set back in the surround.
    leaf = inner & (m.z >= 2) & (m.z < 6)
    lane = np.floor((m.x - 6) / 5).astype(int)
    colors = pick(OAK[:3], hash2(lane, 0, 43) * 0.7 + hash2(lane, m.y // 8, 44) * 0.3)
    colors = np.where((m.x - 6) % 5 == 0, OAK_DARK[0], colors)
    for y in (18, 58):
        colors = np.where((m.y >= y) & (m.y < y + 3), IRON[0], colors)
    m.fill(leaf, colors)
    for y in (19, 59):
        for x in range(9, 37, 6):
            dot(m, x, y + 1, 6, IRON[1:])
    # The ring pull.
    ring = (np.abs(np.hypot(m.x - 30, m.y - 42) - 2.5) < 0.9) & (m.z == 6)
    m.fill(ring, IRON[1])
    m.fill(m.box(29, 43, 6, 32, 46, 7), IRON[0])
    return m


RAISE = 56


def sconce():
    """A candle on an iron arm out from a pointed backplate. 0.3 wide, 0.55
    tall, raised to hang at shoulder height: 12 x 22 x 10 above RAISE."""
    m = Model(14, RAISE + 26, 12)
    y = RAISE
    plate = (np.abs(m.x - 6.5) <= 4.5 - np.abs(m.y - y - 10) * 0.18) & (m.y >= y) & (m.y < y + 20) & (m.z >= 0) & (m.z < 2)
    m.fill(plate, np.where(hash2(m.x, m.y, 51) < 0.3, IRON[1], WOOD_DARK[0]))
    m.fill(plate & ((m.y == y) | (m.y == y + 19) | (np.abs(np.abs(m.x - 6.5) - (4.5 - np.abs(m.y - y - 10) * 0.18)) < 0.7)), IRON[0])
    m.beam((6, y + 6, 2), (6, y + 9, 7), 1, [IRON[0]])
    m.fill(m.box(4, y + 9, 5, 10, y + 10, 10), BRASS[1])
    m.fill(m.box(5, y + 10, 6, 9, y + 11, 9), BRASS[0])
    candle(m, 6, y + 11, 7, tall=6)
    return m


def wall_lantern():
    """A lantern hung from an iron bracket on a wall plate. 0.4 wide, 0.85
    tall, raised: 16 x 34 x 18 above RAISE - 6."""
    m = Model(18, RAISE + 34, 20)
    y = RAISE - 6
    m.fill(m.box(7, y + 22, 0, 11, y + 32, 2), WOOD_DARK[0])
    m.beam((9, y + 30, 2), (9, y + 30, 13), 2, [IRON[0]])
    m.beam((9, y + 24, 2), (9, y + 30, 9), 1, [IRON[0]])
    m.beam((9, y + 30, 12), (9, y + 25, 12), 1, [IRON[1]])
    # The lantern: roof, glass sides in iron frames, a base.
    for k in range(4):
        m.fill(m.box(6 + k, y + 21 + k, 9 + k, 13 - k, y + 22 + k, 16 - k), IRON[0])
    m.fill(m.box(6, y + 6, 9, 13, y + 21, 16), GLOW[1])
    m.fill(m.box(7, y + 8, 10, 12, y + 19, 15), GLOW[0])
    frame = m.box(6, y + 6, 9, 13, y + 21, 16) & ((m.x == 6) | (m.x == 12)) & ((m.z == 9) | (m.z == 15))
    m.fill(frame, IRON[0])
    m.fill(m.box(6, y + 6, 9, 13, y + 21, 16) & ((m.y == y + 6) | (m.y == y + 20) | (m.y == y + 13)) & ((m.x == 6) | (m.x == 12) | (m.z == 9) | (m.z == 15)), IRON[0])
    m.fill(m.box(5, y + 3, 8, 14, y + 6, 17), IRON[0])
    m.fill(m.box(8, y, 11, 11, y + 3, 14), IRON[1])
    return m


def jar_shelf():
    """An open shelf against the wall: sides, a planked back and four shelves
    of crocks, pots and jars of preserves. 1.4 wide, 1.75 tall, 0.45 deep:
    56 x 70 x 18."""
    m = Model(58, 72, 20)
    boards(m, 1, 57, 0, 70, 1, 3, grain='y', width=6, seed=61)
    post(m, 1, 4, 0, 71, 1, 19, seed=62)
    post(m, 54, 57, 0, 71, 1, 19, seed=63)
    shelves = (2, 19, 36, 53, 68)
    for y in shelves:
        boards(m, 4, 54, y, y + 2, 3, 19, grain='x', width=99, seed=y)
    boards(m, 1, 57, 0, 2, 1, 19, grain='x', width=99, seed=64)
    stock = [
        [('crock', 9), ('pot', 20), ('jam', 30), ('jam', 37), ('crock', 46)],
        [('pot', 9), ('pot', 19), ('crock', 30), ('jam', 41), ('jam', 48)],
        [('jam', 8), ('jam', 15), ('crock', 25), ('pot', 37), ('pot', 47)],
        [('crock', 10), ('jam', 22), ('pot', 32), ('crock', 45)],
    ]
    for row, items in enumerate(stock):
        base = shelves[row] + 2
        for k, (kind, x) in enumerate(items):
            if kind == 'crock':
                jar(m, x, 11, base, 4.2, 11, CERAMIC, band=GLAZE, lid=CERAMIC)
            elif kind == 'pot':
                jar(m, x, 11, base, 4.6, 9, CLAY, neck=0.85)
            else:
                shade = [JAM[(row + k) % 3]]
                jar(m, x, 12, base, 2.8, 8, shade, lid=CLOTH_PALE, neck=0.95)
    return m


def cot():
    """A plain wooden cot: corner posts, the head taller, a straw mattress in
    pale ticking, a worn blanket and a pillow at the head (+x). 1.9 by 0.8,
    0.75 tall at the head: 76 x 32 x 30."""
    m = Model(78, 32, 34)
    for x, top in ((1, 22), (73, 30)):
        for z in (1, 29):
            post(m, x, x + 4, 0, top, z, z + 4, seed=x + z)
            m.fill(m.box(x, top, z, x + 4, top + 1, z + 4), OAK_DARK[0])
    boards(m, 5, 73, 9, 13, 1, 4, grain='x', width=99, seed=71)
    boards(m, 5, 73, 9, 13, 30, 33, grain='x', width=99, seed=72)
    boards(m, 73, 77, 16, 27, 4, 29, grain='z', width=6, seed=73)
    boards(m, 1, 5, 14, 20, 4, 29, grain='z', width=6, seed=74)
    # The mattress, a little lumpy.
    lump = (hash2(m.x // 6, m.z // 5, 75) * 2).astype(int)
    mattress = m.box(5, 13, 4, 73, 17, 30) & (m.y < 16 + lump)
    m.fill(mattress, pick(LINEN, hash2(m.x // 4, m.z // 4, 76)))
    m.fill(mattress & (m.z % 6 == 0), STRAW[1])
    # The blanket over the foot two thirds, with a ragged edge toward the head.
    edge = 50 + (hash2(m.z, 1, 77) * 5).astype(int)
    over = (m.x >= 5) & (m.x < edge) & (m.z >= 3) & (m.z < 31) & (m.y >= 16) & (m.y < 18)
    side = (m.x >= 5) & (m.x < edge) & ((m.z == 3) | (m.z == 30)) & (m.y >= 11) & (m.y < 18)
    m.fill(over | side, pick(BLANKET, hash2(m.x // 3, m.z // 4, 78)))
    m.ellipsoid((65, 18, 16.5), (6.5, 2.8, 9.5), LINEN[0])
    return m


def screen():
    """A folding screen of three linen panels in wooden frames, the outer two
    turned forward. Each 0.55 wide, 1.7 tall: 66 x 68 x 14."""
    m = Model(68, 70, 18)
    width = 22

    def panel(x0, z0, x1, z1):
        steps = int(max(abs(x1 - x0), abs(z1 - z0))) * 2 + 1
        for t in np.linspace(0.0, 1.0, steps):
            x = int(round(x0 + (x1 - x0) * t))
            z = int(round(z0 + (z1 - z0) * t))
            edge = t < 0.07 or t > 0.93
            for y in range(1, 68):
                frame = edge or y < 6 or y > 63 or y in (34, 35)
                cloth = CLOTH_PALE[0] if hash2(x, y // 3, 81) < 0.6 else CLOTH_PALE[1]
                m.grid[x, y, z] = OAK[1] if frame else cloth
                if frame:
                    m.grid[x, y, min(z + 1, 17)] = OAK_DARK[0] if y in (34, 35) else OAK[3]
            if edge:
                m.grid[x, 0, z] = OAK_DARK[0]

    panel(1, 14, 1 + width - 2, 6)
    panel(1 + width - 1, 6, 1 + 2 * width - 2, 6)
    panel(1 + 2 * width - 1, 6, 66, 14)
    return m


def washstand():
    """A washstand: a planked cabinet on legs with a shelf of folded towels,
    a basin and a blue-banded jug on top, a towel over the side. 0.9 by 0.5,
    0.85 tall to the top: 36 x 20 x 34, the jug to 48."""
    m = Model(40, 50, 22)
    boards(m, 1, 39, 30, 33, 1, 21, grain='x', width=6, seed=91)
    boards(m, 1, 39, 33, 39, 1, 3, grain='x', width=99, seed=92)
    for x in (2, 34):
        for z in (2, 17):
            post(m, x, x + 3, 0, 30, z, z + 3, seed=x + z)
    boards(m, 3, 37, 4, 6, 3, 20, grain='x', width=8, seed=93)
    boards(m, 3, 37, 26, 30, 18, 20, grain='x', width=99, seed=94)
    # Towels folded on the shelf, and one over the side.
    for x in (8, 16):
        m.fill(m.box(x, 6, 7, x + 7, 13, 17), pick(LINEN, hash2(m.y, m.x, 95)))
        m.fill(m.box(x, 9, 7, x + 7, 10, 17), CLOTH_RED[1])
    m.fill(m.box(24, 6, 8, 32, 11, 17), STRAW[0])
    m.fill(m.box(37, 14, 6, 40, 30, 14), pick(LINEN, hash2(m.y // 2, m.z, 96)))
    # The basin and the jug.
    bowl = (np.hypot(m.x - 14 + 0.5, m.z - 11 + 0.5) <= 8.5) & (m.y >= 33) & (m.y < 38)
    hollow = (np.hypot(m.x - 14 + 0.5, m.z - 11 + 0.5) <= 6.5) & (m.y >= 35)
    m.fill(bowl & ~hollow, CERAMIC[0])
    m.fill(bowl & (m.y == 36) & ~hollow, GLAZE[0])
    jar(m, 29, 11, 33, 4.0, 14, CERAMIC, band=GLAZE, neck=0.75)
    m.beam((33, 45, 11), (34, 38, 11), 1, [CERAMIC[1]])
    return m


def herb_rack():
    """Two posts on feet and a crossbar with bundles of drying herbs hung from
    it: lavender, green herbs and yellow flowers. 2.0 wide, 1.5 tall: 80 x 60 x 10."""
    m = Model(82, 62, 14)
    for x in (2, 76):
        post(m, x, x + 4, 0, 58, 5, 9, seed=x)
        boards(m, x - 3, x + 7, 0, 3, 3, 11, grain='x', width=99, seed=x + 1)
    boards(m, 0, 82, 54, 58, 4, 10, grain='x', width=99, seed=101)
    m.beam((6, 44, 7), (12, 54, 7), 2, [OAK[1]])
    m.beam((76, 44, 7), (70, 54, 7), 2, [OAK[1]])
    kinds = [LAVENDER, HERB, BLOOM, HERB, LAVENDER, HERB, BLOOM, HERB]
    for k, shades in enumerate(kinds):
        x = 12 + k * 8
        m.beam((x, 54, 7), (x, 46, 7), 1, [ROPE[0]])
        m.fill(m.box(x - 1, 44, 6, x + 2, 47, 9), ROPE[1])
        for b in range(9):
            bx = x + int(round(math.sin(b * 1.7) * (1 + b * 0.25)))
            bz = 7 + int(round(math.cos(b * 2.3) * 1.5))
            length = 10 + (b * 7) % 6
            m.beam((x, 44, 7), (bx, 44 - length, bz), 1, [HERB[1]] if shades is not HERB else [HERB[0], HERB[2]])
            if shades is not HERB:
                m.ellipsoid((bx, 44 - length, bz), (1.2, 1.6, 1.2), shades[b % len(shades)])
    return m


def hearth():
    """A stone fireplace: an arched opening black with soot, logs burning under
    an iron cauldron on a chain, a wooden mantel with pots on it. 1.9 wide,
    1.9 tall, 0.9 deep: 76 x 76 x 36."""
    m = Model(78, 80, 38)
    cx = 38.5
    body = m.box(2, 0, 2, 76, 58, 34)
    yy = m.y.astype(float)
    row = (m.y // 6)
    shifted = m.x + (row % 2) * 5 + m.z
    stone = pick(STONE, hash2(row, shifted // 10, 111))
    joint = (m.y % 6 == 5) | (shifted % 10 == 0)
    m.fill(body, np.where(joint, MORTAR[0], stone))
    # The opening, an arch, sooted inside.
    opening = ((m.y < 34) & (np.abs(m.x - cx) <= 22)) | (np.hypot(m.x - cx, (yy - 34) * 1.3) <= 22)
    opening &= (m.y >= 4) & (m.z >= 10)
    m.clear(opening & body)
    back = opening & (m.z >= 8) & (m.z < 10)
    m.fill(back, SOOT_DEEP[0])
    inner = ndimage.binary_dilation(opening, iterations=1) & (m.grid >= 0) & body
    m.fill(inner, np.where(hash2(m.x, m.y, 112) < 0.5, SOOT[0], SOOT_DEEP[0]))
    # The hearth floor, the chimney breast above the mantel.
    m.fill(m.box(10, 0, 8, 68, 4, 36), pick(STONE, hash2(m.x // 5, m.z // 5, 113)))
    m.fill(m.box(10, 58, 4, 68, 80, 30), np.where(joint, MORTAR[0], stone))
    boards(m, 0, 78, 56, 61, 0, 38, grain='x', width=99, seed=114)
    # Logs and fire.
    for z, x0, x1 in ((18, 24, 54), (22, 26, 52)):
        m.beam((x0, 6, z), (x1, 7, z + 3), 3, [WOOD_DARK[0], WOOD[2]])
    m.fill(m.box(26, 4, 16, 52, 6, 28), EMBER[1])
    for k in range(14):
        x = 26 + (k * 13) % 26
        z = 17 + (k * 7) % 10
        h = 5 + (k * 5) % 9
        m.beam((x, 8, z), (x + (k % 3) - 1, 8 + h, z), 1, [GLOW[1], GLOW[0], EMBER[0]])
    # The cauldron on its chain.
    m.beam((cx, 48, 22), (cx, 30, 22), 1, [IRON[0], IRON[1]])
    pot = m.ellipsoid((cx, 22, 22), (9.5, 7.5, 8.5), IRON[0])
    m.clear(pot & (m.y > 26))
    m.fill(m.box(29, 26, 14, 49, 28, 31) & (np.hypot(m.x - cx + 0.5, m.z - 22 + 0.5) <= 9.5) & (np.hypot(m.x - cx + 0.5, m.z - 22 + 0.5) > 7.5), IRON[1])
    m.fill(m.box(31, 26, 16, 47, 27, 29) & (np.hypot(m.x - cx + 0.5, m.z - 22 + 0.5) <= 7.5), SOOT_DEEP[0])
    # Pots on the mantel.
    jar(m, 8, 19, 61, 4.5, 9, CLAY)
    jar(m, 20, 20, 61, 3.5, 7, CERAMIC, band=GLAZE)
    jar(m, 64, 19, 61, 4.0, 8, CLAY, neck=0.6)
    # A bucket and a sack beside it.
    cylinder(m, 6, 33, 3.5, 0, 8, np.where(m.y % 4 == 1, IRON[0], OAK[1]))
    sack(m, 72, 0, 32, 4.5, 4.5, 3.5)
    return m


def millstones():
    """The millstones in their wooden case on a heavy frame: the hopper above,
    the spout, the crank wheel at the side, sacks and a tub at the foot. 2.0
    by 1.6, 2.0 tall: 80 x 64 x 80."""
    m = Model(84, 82, 70)
    cx, cz = 40.5, 34.5
    # The frame: four posts, beams under the stones and over them.
    for x in (8, 72):
        for z in (12, 54):
            post(m, x, x + 5, 0, 44, z, z + 5, seed=x + z)
    for z in (12, 54):
        boards(m, 6, 79, 22, 27, z, z + 5, grain='x', width=99, seed=z)
    for x in (8, 72):
        boards(m, x, x + 5, 22, 27, 12, 59, grain='z', width=99, seed=x)
    # The stone case (tun), planked round, and the stones within.
    angle = np.arctan2(m.z - cz, m.x - cx)
    lane = np.floor((angle + math.pi) * 9).astype(int)
    tun = pick(OAK[:3], hash2(lane, 0, 121))
    tun = np.where(((angle + math.pi) * 9) % 1.0 < 0.15, OAK_DARK[0], tun)
    tun = np.where((m.y == 29) | (m.y == 38), IRON[0], tun)
    case = cylinder(m, cx, cz, 23.0, 27, 40, tun)
    m.clear(case & (np.hypot(m.x - cx + 0.5, m.z - cz + 0.5) <= 20.0) & (m.y >= 36))
    top = (np.hypot(m.x - cx + 0.5, m.z - cz + 0.5) <= 20.0) & (m.y >= 34) & (m.y < 37)
    m.fill(top, pick(STONE[:3], hash2(m.x // 3, m.z // 3, 122)))
    m.fill(top & (np.abs(np.sin(np.arctan2(m.z - cz, m.x - cx) * 6)) < 0.18), MORTAR[0])
    m.fill((np.hypot(m.x - cx + 0.5, m.z - cz + 0.5) <= 3.0) & (m.y == 36), SOOT_DEEP[0])
    # The hopper: an upturned pyramid of boards on two posts, the spout below.
    for x in (30, 50):
        post(m, x, x + 3, 36, 64, cz - 1, cz + 2, seed=x)
    for k in range(18):
        y = 58 + k
        half = 4 + k
        ring = m.box(int(cx - half), y, int(cz - half), int(cx + half) + 1, y + 1, int(cz + half) + 1)
        inside = m.box(int(cx - half) + 2, y, int(cz - half) + 2, int(cx + half) - 1, y + 1, int(cz + half) - 1)
        colors = np.where(hash2((m.x + m.z) // 5, k // 4, 123) < 0.5, OAK[0], OAK[2])
        m.fill(ring & ~inside, np.where(k % 6 == 0, OAK_DARK[0], colors))
        # Grain lies low in it, so the boards inside show.
        m.fill(inside & (y == 63), FLOUR[0])
    m.beam((cx, 58, cz), (cx, 44, cz + 6), 3, [OAK[1]])
    m.beam((cx + 2, 30, cz + 23), (cx + 2, 20, cz + 30), 3, [OAK[1]])
    # The crank wheel on the side.
    wheel = (np.abs(np.hypot(m.y - 32, m.z - cz) - 9.0) < 1.6) & (m.x >= 79) & (m.x < 82)
    m.fill(wheel, OAK[1])
    for k in range(6):
        a = k * math.pi / 3
        m.beam((80, 32, cz), (80, 32 + 9 * math.sin(a), cz + 9 * math.cos(a)), 1, [OAK[3]])
    m.beam((77, 32, cz), (82, 32, cz), 2, [IRON[0]])
    m.beam((81, 32 + 9, cz), (83, 32 + 9, cz), 2, [OAK_DARK[0]])
    # At the foot: sacks and a tub of flour.
    sack(m, 10, 0, 64, 6, 7, 5)
    sack(m, 70, 0, 64, 6, 6, 5, lean=1)
    cylinder(m, 44, 64, 5, 0, 8, np.where(m.y % 4 == 1, IRON[0], OAK[1]))
    m.fill(m.box(40, 7, 61, 49, 8, 68) & (np.hypot(m.x - 44 + 0.5, m.z - 64 + 0.5) <= 4), FLOUR[0])
    return m


def mill_gear():
    """The great gear that turns the stones, on its axle out of a stone pier
    in a timber frame: spokes, a toothed rim, iron at the hub. 2.0 by 1.7,
    1.9 tall: 80 x 76 x 30."""
    m = Model(80, 78, 32)
    # The pier behind.
    pier = m.box(6, 0, 1, 74, 70, 12)
    row = m.y // 6
    shifted = m.x + (row % 2) * 5
    m.fill(pier, np.where((m.y % 6 == 5) | (shifted % 10 == 0), MORTAR[0], pick(STONE, hash2(row, shifted // 10, 131))))
    # The frame around the wheel.
    for x in (4, 70):
        post(m, x, x + 6, 0, 76, 10, 16, seed=x)
    boards(m, 2, 78, 70, 76, 9, 17, grain='x', width=99, seed=132)
    boards(m, 2, 78, 0, 5, 9, 18, grain='x', width=99, seed=133)
    # The wheel: rim with teeth on its face, spokes and hub.
    cx, cy = 40.0, 37.0
    r = np.hypot(m.x - cx + 0.5, m.y - cy + 0.5)
    a = np.arctan2(m.y - cy + 0.5, m.x - cx + 0.5)
    rim = (r <= 29) & (r >= 24) & (m.z >= 16) & (m.z < 21)
    m.fill(rim, np.where(np.floor((a + math.pi) * 5).astype(int) % 2 == 0, OAK[0], OAK[2]))
    m.fill(rim & (((a + math.pi) * 5) % 1.0 < 0.12), OAK_DARK[0])
    teeth = (r <= 27.5) & (r >= 25) & (m.z >= 21) & (m.z < 24) & (np.floor((a + math.pi) / (2 * math.pi) * 32).astype(int) % 2 == 0)
    m.fill(teeth, OAK[3])
    for k in range(8):
        ang = k * math.pi / 4
        m.beam((cx, cy, 18), (cx + 25 * math.cos(ang), cy + 25 * math.sin(ang), 18), 3, [OAK[1], OAK[3]])
    disc_z(m, cx, cy, 7, 15, 23, IRON[0])
    disc_z(m, cx, cy, 4, 23, 26, IRON[1])
    m.beam((cx, cy, 10), (cx, cy, 30), 4, [OAK_DARK[0]])
    for k in range(4):
        dot(m, int(cx + 5 * math.cos(k * 1.57 + 0.78)), int(cy + 5 * math.sin(k * 1.57 + 0.78)), 23, IRON[1:])
    return m


def barrels():
    """Two big barrels, a small one in front, and burlap sacks against them, a
    cloth over one. 1.3 by 1.0, 1.0 tall: 52 x 40 x 40."""
    m = Model(56, 42, 44)
    barrel(m, 16, 14, 0, 11, 34, seed=1)
    barrel(m, 37, 13, 0, 10, 30, seed=2)
    barrel(m, 34, 33, 0, 8, 20, seed=3)
    sack(m, 9, 0, 33, 7, 8, 6)
    sack(m, 48, 0, 30, 6, 7, 5, lean=1)
    # A cloth over the big one's lid, hanging down its side.
    lid = (np.hypot(m.x - 16 + 0.5, m.z - 14 + 0.5) <= 11.5) & (m.y >= 34) & (m.y < 36)
    hang = (np.hypot(m.x - 16 + 0.5, m.z - 14 + 0.5) > 10.5) & (np.hypot(m.x - 16 + 0.5, m.z - 14 + 0.5) <= 12.5) & (m.y >= 22 + (hash2(m.x, m.z, 141) * 6).astype(int)) & (m.y < 35) & (m.x < 20) & (m.z > 8)
    m.fill(lid | hang, pick(CLOTH_PALE, hash2(m.x // 2, m.y // 2, 142)))
    m.fill((lid | hang) & ((m.x + m.y) % 7 == 0), CLOTH_RED[0])
    return m


def flour_sacks():
    """Sacks laid flat in a stack, each with a red stripe, and an open one at
    the side full of flour with a scoop. 1.3 by 1.1, 1.0 tall: 52 x 44 x 40."""
    m = Model(56, 44, 46)
    layers = [(4, 14), (4, 30), (4 + 8, 14), (4 + 8, 30), (20, 22)]
    for k, (y, z) in enumerate(layers):
        x = 18
        body = ((m.x - x) / 15.0) ** 2 + ((m.y - y - 4) / 4.6) ** 2 + ((m.z - z) / 8.0) ** 2 <= 1.0
        body &= m.y >= y
        colors = pick(BURLAP + BURLAP_DARK, hash2(m.x // 2, m.z // 2 + m.y, 151 + k))
        colors = np.where(np.abs(m.x - x) <= 1, STRIPE[0], colors)
        colors = np.where((np.abs(m.x - x) == 9) & (hash2(m.z, k, 152) < 0.7), BURLAP_DARK[0], colors)
        m.fill(body, colors)
        m.ellipsoid((x + 15, y + 4, z), (2.0, 2.4, 2.4), ROPE[0])
    # The open sack.
    sack(m, 44, 0, 32, 8, 9, 8, tie=False)
    mouth = (np.hypot(m.x - 44 + 0.5, m.z - 32 + 0.5) <= 6.5) & (m.y >= 16) & (m.y < 19)
    m.clear(mouth)
    m.fill((np.hypot(m.x - 44 + 0.5, m.z - 32 + 0.5) <= 6.5) & (m.y >= 15) & (m.y < 17), FLOUR[0])
    m.ellipsoid((44, 17, 32), (5.0, 1.8, 5.0), FLOUR[1])
    rim = (np.abs(np.hypot(m.x - 44 + 0.5, m.z - 32 + 0.5) - 7.5) < 1.2) & (m.y >= 16) & (m.y < 20)
    m.fill(rim, BURLAP[1])
    m.beam((42, 18, 31), (36, 26, 28), 2, [OAK[0]])
    return m


def workbench():
    """A carpenter's bench: a thick planked top on heavy splayed legs, a vise at
    the front right, a shelf below with a crate and a tub, a tool tray with a
    saw and chisels, a mallet, a cloth over one end, sacks at the left. 2.2 by
    0.8, 0.85 tall at the top: 88 x 32 x 34, the tools to 48."""
    m = Model(96, 50, 40)
    boards(m, 6, 94, 30, 35, 4, 36, grain='x', width=8, seed=161)
    for x in (10, 84):
        for z in (6, 30):
            post(m, x, x + 5, 0, 30, z, z + 4, seed=x + z)
        boards(m, x, x + 5, 6, 10, 8, 30, grain='z', width=99, seed=x)
        m.beam((x + 2, 10, 10), (x + 2, 26, 28), 2, [OAK[1]])
    boards(m, 15, 84, 8, 10, 6, 34, grain='x', width=8, seed=162)
    boards(m, 10, 89, 24, 30, 33, 35, grain='x', width=99, seed=163)
    # On the shelf: a crate and a tub.
    boards(m, 22, 42, 10, 21, 12, 28, grain='x', width=4, seed=164)
    cylinder(m, 60, 20, 8, 10, 21, np.where((m.y == 12) | (m.y == 19), IRON[0], np.where(hash2(np.floor(np.arctan2(m.z - 20, m.x - 60) * 3).astype(int), 0, 165) < 0.5, OAK[0], OAK[2])))
    # The vise at the front right.
    m.fill(m.box(76, 24, 35, 88, 34, 38), OAK[1])
    m.beam((82, 29, 38), (82, 29, 40), 2, [IRON[0]])
    m.beam((78, 29, 39), (86, 29, 39), 1, [IRON[1]])
    # The tool tray and its tools.
    boards(m, 46, 74, 35, 41, 8, 16, grain='x', width=99, seed=166)
    m.clear(m.box(48, 37, 10, 72, 41, 14))
    boards(m, 58, 61, 41, 47, 11, 13, grain='y', width=99, seed=167)
    for x in (50, 53):
        m.beam((x, 38, 12), (x, 46, 12), 1, [OAK_DARK[0]])
        dot(m, x, 47, 12, OAK[3:])
    saw = m.box(64, 38, 12, 73, 49, 13) & ((m.x - 64) <= (m.y - 38) * 1.0 + 1)
    m.fill(saw, np.where(m.x > 70, OAK[1], IRON[1]))
    # A mallet and shavings on the top.
    m.beam((24, 36, 22), (36, 36, 24), 2, [OAK[3]])
    m.fill(m.box(20, 35, 19, 25, 40, 26), IRON[0])
    for k in range(10):
        dot(m, 40 + (k * 7) % 30, 35, 18 + (k * 5) % 14, [WOOD_LIT[0]])
    # A cloth over the left end, and sacks against the legs.
    blanket_fold(m, 6, 26, 35, 4, 36, CLOTH_PALE, seed=168)
    sack(m, 6, 0, 30, 6, 8, 5)
    sack(m, 6, 0, 16, 5, 7, 5, lean=1)
    return m


def trapdoor():
    """A hatch in the floor: planks in a stone curb, two strap hinges at the
    back and a ring pull at the front. 1.4 square: 56 x 3 x 56."""
    m = Model(56, 3, 56)
    curb = m.box(0, 0, 0, 56, 2, 56) & ~m.box(5, 0, 5, 51, 2, 51)
    m.fill(curb, np.where(((m.x // 7 + m.z // 7) % 2 == 0) | (np.minimum(m.x, m.z) % 7 == 0), MORTAR[0], pick(STONE, hash2(m.x // 7, m.z // 7, 171))))
    m.fill(curb & ((m.x % 7 == 0) | (m.z % 7 == 0)), MORTAR[0])
    lane = np.floor((m.x - 5) / 6).astype(int)
    leaf = m.box(5, 0, 5, 51, 2, 51)
    colors = pick(OAK[:3], hash2(lane, 0, 172) * 0.7 + hash2(lane, m.z // 9, 173) * 0.3)
    colors = np.where((m.x - 5) % 6 == 0, OAK_DARK[0], colors)
    colors = np.where(((m.z >= 12) & (m.z < 15)) | ((m.z >= 40) & (m.z < 43)), IRON[0], colors)
    m.fill(leaf, colors)
    for z in (13, 41):
        m.fill(m.box(3, 1, z - 1, 10, 3, z + 2), IRON[0])
        m.fill(m.box(46, 1, z - 1, 53, 3, z + 2), IRON[0])
    ring = (np.abs(np.hypot(m.x - 27.5, m.z - 47) - 3.5) < 1.0) & (m.y == 2)
    m.fill(ring, IRON[1])
    m.fill(m.box(26, 2, 42, 30, 3, 44), IRON[0])
    return m


def jessa_desk():
    """Jessa's writing desk: a planked top on square legs with a drawer, a
    candle in a brass dish, a book on loose papers, an inkwell with a quill,
    a jar, and a small lantern. 1.2 by 0.6, 0.8 tall: 48 x 24 x 32."""
    m = Model(50, 46, 26)
    boards(m, 1, 49, 28, 31, 1, 25, grain='x', width=6, seed=181)
    for x in (2, 44):
        for z in (2, 20):
            post(m, x, x + 4, 0, 28, z, z + 4, seed=x + z)
    boards(m, 6, 44, 22, 28, 22, 24, grain='x', width=99, seed=182)
    boards(m, 28, 42, 22, 27, 24, 25, grain='x', width=99, seed=183)
    m.fill(m.box(34, 24, 25, 37, 25, 26), BRASS[0])
    boards(m, 6, 44, 6, 8, 12, 15, grain='x', width=99, seed=184)
    # Papers, the book, the inkwell and quill.
    m.fill(m.box(9, 31, 6, 24, 32, 18), pick(PAPER, hash2(m.x // 3, m.z // 3, 185)))
    m.fill(m.box(12, 32, 8, 22, 35, 16), LEATHER_BOOK[0])
    m.fill(m.box(12, 32, 8, 22, 34, 16) & (m.z == 15), PAPER[0])
    m.fill(m.box(16, 35, 8, 17, 36, 16), BRASS[1])
    cylinder(m, 27, 10, 1.8, 31, 35, INK)
    m.beam((27, 35, 10), (30, 44, 8), 1, [CLOTH_PALE[0], PAPER[0]])
    # The candle in its dish.
    cylinder(m, 6, 12, 3.5, 31, 32, BRASS)
    candle(m, 6, 32, 12, tall=6)
    # A jar of black honey, cloth-topped.
    jar(m, 34, 13, 31, 2.8, 6, [SOOT_DEEP[0], SOOT[0]], lid=CLOTH_PALE, neck=0.95)
    # The lantern.
    m.fill(m.box(40, 31, 9, 47, 33, 16), IRON[0])
    m.fill(m.box(40, 33, 9, 47, 41, 16), GLOW[1])
    m.fill(m.box(41, 34, 10, 46, 40, 15), GLOW[0])
    m.fill(m.box(40, 33, 9, 47, 41, 16) & (((m.x == 40) | (m.x == 46)) & ((m.z == 9) | (m.z == 15))), IRON[0])
    for k in range(3):
        m.fill(m.box(40 + k, 41 + k, 9 + k, 47 - k, 42 + k, 16 - k), IRON[0])
    return m


def wardrobe():
    """A tall wardrobe: a plinth on bracket feet, a framed carcass with
    battened sides, two planked doors with strap hinges on their outer edges
    and ring pulls at the meeting stiles, under an arched crown with a
    moulding. 1.1 wide, 1.9 tall, 0.6 deep: 44 x 76 x 24."""
    m = Model(48, 80, 26)
    # The plinth and its bracket feet, cut away between them.
    boards(m, 1, 47, 4, 9, 1, 25, grain='x', width=99, seed=191)
    for x0, x1 in ((2, 9), (39, 46)):
        for z0, z1 in ((2, 7), (19, 24)):
            post(m, x0, x1, 0, 4, z0, z1, seed=x0 + z0)
    # The carcass: corner stiles, battened sides, a back.
    post(m, 2, 6, 9, 66, 2, 24, seed=192)
    post(m, 42, 46, 9, 66, 2, 24, seed=193)
    boards(m, 2, 46, 9, 66, 2, 4, grain='y', width=6, seed=194)
    for x0, x1 in ((2, 4), (44, 46)):
        boards(m, x0, x1, 9, 66, 4, 22, grain='y', width=6, seed=x0 + 1)
        for y in (20, 52):
            boards(m, x0 - 1 if x0 == 2 else x1 - 1, x0 if x0 == 2 else x1, y, y + 4, 5, 21, grain='z', width=99, seed=y)
    # The face frame and the two doors, set back a voxel inside it.
    boards(m, 2, 46, 9, 13, 21, 24, grain='x', width=99, seed=195)
    boards(m, 2, 46, 62, 66, 21, 24, grain='x', width=99, seed=196)
    post(m, 2, 7, 9, 66, 21, 24, seed=197)
    post(m, 41, 46, 9, 66, 21, 24, seed=198)
    for x0, x1, seed in ((7, 24, 201), (24, 41, 202)):
        leaf = boards(m, x0, x1, 13, 62, 20, 23, grain='y', width=4, seed=seed)
        # A rail across the top and bottom of each door.
        boards(m, x0, x1, 14, 17, 22, 23, grain='x', width=99, seed=seed + 1)
        boards(m, x0, x1, 57, 60, 22, 23, grain='x', width=99, seed=seed + 2)
    m.fill(m.box(23, 13, 22, 25, 62, 23), OAK_DARK[0])
    # Strap hinges on the outer edges, ring pulls at the middle.
    for y in (19, 53):
        for x0, x1, tip in ((5, 15, 15), (33, 43, 33)):
            m.fill(m.box(x0, y, 23, x1, y + 2, 24), IRON[0])
            m.fill(m.box(tip - 1 if tip == 15 else tip, y - 1, 23, tip + 1 if tip == 15 else tip + 2, y + 3, 24), IRON[0])
            for x in range(x0 + 1, x1, 3):
                dot(m, x, y, 24 if False else 23, IRON[1:])
    for x in (21, 27):
        ring = (np.abs(np.hypot(m.x - x - 0.5, m.y - 35) - 2.0) < 0.8) & (m.z == 23)
        m.fill(ring, IRON[1])
        m.fill(m.box(x, 37, 23, x + 1, 39, 24), IRON[0])
    # The crown: a cornice, then an arch rising to the middle, with a
    # moulding along its edge.
    boards(m, 0, 48, 66, 69, 0, 26, grain='x', width=99, seed=203)
    arch = 69 + np.clip(9.0 * np.cos(np.clip((m.x - 23.5) / 22.0, -1, 1) * math.pi / 2) ** 1.5, 0, 9)
    crown = (m.y >= 69) & (m.y < arch) & (m.x >= 1) & (m.x < 47) & (m.z >= 2) & (m.z < 24)
    m.fill(crown, pick(OAK[:3], hash2((m.x + m.z) // 5, m.y // 3, 204)))
    rim = crown & (m.y >= arch - 2)
    m.fill(rim & ((m.z == 23) | (m.z == 2)), OAK_DARK[0])
    m.fill(crown & (m.z == 23) & (m.y >= arch - 1), OAK[3])
    for x in (2, 45):
        dot(m, x, 67, 25, IRON[1:])
    return m


def loose_feather(m, x, z, angle, length, curl=False):
    """One flight feather lying on the floor: a pale quill, the vane wider on
    one side, black with a blue sheen along the quill. Its tip may lift a
    voxel off the boards."""
    ax, az = math.cos(angle), math.sin(angle)
    nx, nz = -az, ax
    steps = int(length * 2)
    w, _, d = m.grid.shape

    def put(px, py, pz, shade):
        gx, gz = int(round(px)), int(round(pz))
        if 0 <= gx < w and 0 <= gz < d:
            m.grid[gx, py, gz] = shade

    for k in range(steps + 1):
        t = k / steps
        bend = math.sin(t * math.pi) * 1.2
        qx = x + ax * length * t + nx * bend
        qz = z + az * length * t + nz * bend
        y = 1 if curl and t > 0.85 else 0
        put(qx, y, qz, FEATHER_BLACK[3])
        if t < 0.2:
            continue
        u = (t - 0.2) / 0.8
        swell = math.sin(min(1.0, u * 1.4) * math.pi / 2) * (1.0 - u ** 3)
        for side, wide in ((1, 4.4), (-1, 2.8)):
            reach = 0.6
            while reach <= wide * swell:
                bx = qx + (nx * side + ax * 0.4) * reach
                bz = qz + (nz * side + az * 0.4) * reach
                shade = FEATHER_BLACK[2] if reach < 1.3 and side == 1 else FEATHER_BLACK[(k + int(reach)) % 2]
                put(bx, y, bz, shade)
                reach += 0.5


def feather_scatter():
    """Black feathers strewn across the floor, as if they came in on the wind
    and stayed: eight, every way, lying flat so they are walked over. 1.4
    across: 56 x 2 x 56."""
    m = Model(60, 2, 60)
    lay = ((8, 10, 0.3, 20, False), (28, 8, 1.9, 16, True), (50, 26, 3.4, 20, False), (10, 40, -0.6, 18, False),
           (34, 26, 2.4, 14, True), (52, 50, 4.0, 16, False), (8, 52, 0.4, 12, False), (32, 56, -1.2, 18, True))
    for x, z, angle, length, curl in lay:
        loose_feather(m, x, z, angle, length, curl)
    return m


def feather_scatter_small():
    """Three feathers together by the bed. 0.7 across: 28 x 2 x 28."""
    m = Model(32, 2, 32)
    for x, z, angle, length, curl in ((4, 8, 0.4, 18, False), (10, 22, -0.5, 16, True), (20, 4, 1.8, 14, False)):
        loose_feather(m, x, z, angle, length, curl)
    return m


# Where Jessa's boots stand in the water stain, in voxels from its middle:
# each sole's middle across and along. Both recipes use them, so the dry
# outline in the stain fits the boots.
SOLES = ((-4, 0), (4, 1))
SOLE_HALF = (2.6, 5.2)


def water_stain():
    """Water dried on the boards: a dark damp patch with a pale salt line at
    its edge, curving around the dry outline of a pair of boots as if it went
    around them on purpose. It lies one voxel thin, to be walked over. 1.4 by
    1.1: 56 x 1 x 44."""
    w, d = 56, 44
    m = Model(w, 1, d)
    cx, cz = w / 2, d / 2
    angle = np.arctan2(m.z - cz, m.x - cx)
    wobble = 1.0 + 0.16 * np.sin(angle * 3 + 0.7) + 0.09 * np.sin(angle * 7 + 2.1)
    reach = np.hypot((m.x - cx) / 25.0, (m.z - cz) / 19.0) / wobble
    blob = reach < 1.0
    # The dry ground: each sole and a margin, opened toward the back so the
    # water curls round the boots rather than ringing them.
    dry = np.zeros(m.grid.shape, dtype=bool)
    for sx, sz in SOLES:
        dry |= ((m.x - cx - sx) / (SOLE_HALF[0] + 1.6)) ** 2 + ((m.z - cz - sz) / (SOLE_HALF[1] + 1.6)) ** 2 <= 1.0
    dry |= (np.abs(m.x - cx + 2) < 2.5) & (m.z < cz - 3) & (m.z > cz - 22)
    wet = blob & ~dry
    m.fill(wet, pick(DAMP, hash2(m.x // 4, m.z // 2, 211)))
    # The salt line along every edge of the wet, inside and out.
    edge = wet & ~ndimage.binary_erosion(wet, structure=np.ones((3, 1, 3)))
    m.fill(edge, pick(TIDE, hash2(m.x, m.z, 212)))
    # A second, fainter line a little inside, where it dried in stages.
    inner = wet & ~ndimage.binary_erosion(wet, structure=np.ones((3, 1, 3)), iterations=4) & ~edge
    m.fill(inner & (hash2(m.x, m.z, 213) < 0.35), DAMP[2])
    return m


def waterwalkers():
    """Jessa's Waterwalkers standing together: tall boots of dark leather
    with a cold blue-grey sheen, turned-down cuffs, a buckled strap at the
    ankle. 0.45 tall: about 18 x 18 x 12, centered as the stain's soles."""
    w, h, d = 22, 20, 16
    m = Model(w, h, d)
    cx, cz = w / 2, d / 2
    for k, (sx, sz) in enumerate(SOLES):
        bx, bz = cx + sx, cz + sz
        # The sole and foot, longer toward the toe (+z).
        foot = (((m.x - bx + 0.5) / SOLE_HALF[0]) ** 2 + ((m.z - bz + 0.5) / SOLE_HALF[1]) ** 2 <= 1.0) & (m.y < 4)
        foot &= (m.y < 2) | (m.z - bz < 3)
        m.fill(foot, np.where(m.y == 0, WALKER[3], pick(WALKER[:2], hash2(m.x, m.z, 221 + k))))
        # The shaft over the heel, a little wider at the top.
        shaft = (np.hypot(m.x - bx + 0.5, m.z - (bz - 1.5) + 0.5) <= 2.4 + (m.y - 4) * 0.03) & (m.y >= 2) & (m.y < 17)
        sheen = (m.x - bx) > 0.8
        m.fill(shaft, np.where(sheen, WALKER[2], pick(WALKER[:2], hash2(m.y // 3, k, 223))))
        cuff = (np.hypot(m.x - bx + 0.5, m.z - (bz - 1.5) + 0.5) <= 3.0) & (m.y >= 15) & (m.y < 18)
        m.fill(cuff, WALKER[1])
        m.fill(cuff & (np.hypot(m.x - bx + 0.5, m.z - (bz - 1.5) + 0.5) <= 1.6) & (m.y >= 16), -1)
        strap = (np.hypot(m.x - bx + 0.5, m.z - (bz - 1.5) + 0.5) <= 2.7) & (m.y == 5)
        m.fill(strap, WALKER[3])
        dot(m, int(round(bx + 2)), 5, int(round(bz - 1)), BRASS)
    return m


RECIPES = {
    'InsideDoor': inside_door,
    'Sconce': sconce,
    'WallLantern': wall_lantern,
    'Table': table,
    'Bench': bench,
    'Stool': stool,
    'Chest': chest,
    'JarShelf': jar_shelf,
    'Cot': cot,
    'Screen': screen,
    'Washstand': washstand,
    'HerbRack': herb_rack,
    'Hearth': hearth,
    'Millstones': millstones,
    'MillGear': mill_gear,
    'Barrels': barrels,
    'FlourSacks': flour_sacks,
    'Workbench': workbench,
    'Trapdoor': trapdoor,
    'JessaDesk': jessa_desk,
    'Wardrobe': wardrobe,
    'FeatherScatter': feather_scatter,
    'FeatherScatterSmall': feather_scatter_small,
    'WaterStain': water_stain,
    'Waterwalkers': waterwalkers,
}


# Props built a second time turned to face +X, named with East, for the left
# wall: the game cannot turn a placed model, so the turn is in the model.
TURNED = ['Chest', 'Sconce', 'WallLantern', 'Washstand', 'Cot', 'JarShelf', 'Bench']
# And to face -X, named with West, for the right wall.
TURNED_WEST = ['Wardrobe']


def turned(grid):
    """The grid turned a quarter about Y so its front, +Z, faces +X."""
    return np.ascontiguousarray(np.transpose(grid, (2, 1, 0))[:, :, ::-1])


def turned_west(grid):
    """The grid turned a quarter the other way, so its front faces -X."""
    return np.ascontiguousarray(np.transpose(grid, (2, 1, 0))[::-1, :, :])


# Sheets, for reference: the name of each prop's sheet in Downloads/interior-props.
SHEETS = {
    'InsideDoor': 'středověkých dveří', 'Sconce': 'středověký svícen', 'WallLantern': 'lucernový svítidlo',
    'Table': 'rustikální dřevěný stůl', 'Bench': 'Dřevěná lavice', 'Stool': 'Dřevěná stolička',
    'Chest': 'Pixelové truhly', 'JarShelf': 'keramickými nádobami', 'Cot': 'Rustikální dřevěná postel',
    'Screen': 'paraván', 'Washstand': 'umývací stolek', 'HerbRack': 'sušák bylin', 'Hearth': 'středověké ohniště',
    'Millstones': 'obilní mlýn', 'MillGear': 'ozubené kolo', 'Barrels': 'sudy a jutové pytle',
    'FlourSacks': 'pytlů mouky', 'Workbench': 'truhlářský ponk', 'Trapdoor': 'padací poklop',
    'JessaDesk': 'kouzelnými předměty',
}


def import_sheets(directory):
    """Keeps a small copy of each sheet beside the crops of act1's models."""
    CROPS.mkdir(parents=True, exist_ok=True)
    for name, key in SHEETS.items():
        found = [p for p in Path(directory).iterdir() if p.suffix == '.png' and key in p.name]
        if len(found) != 1:
            raise SystemExit(f'{len(found)} sheets match {key!r}')
        sheet = Image.open(found[0]).convert('RGB')
        sheet.thumbnail((1086, 1086))
        sheet.save(CROPS / f'{name}.sheet.png')
    print(f'{len(SHEETS)} sheets saved to {CROPS}')


def iso_preview(grid, palette, path, scale=3):
    """Renders the model as the game's camera sees it, from +x +z above, with the
    tops lit and the +x sides in shade, so a recipe can be judged against its sheet."""
    w, h, d = grid.shape
    cells = np.argwhere(grid >= 0)
    if len(cells) == 0:
        return
    # Each voxel is a 2 x 2 block: u across the screen, v down it.
    u = (cells[:, 0] - cells[:, 2]) * 2
    v = (cells[:, 0] + cells[:, 2]) - cells[:, 1] * 2
    depth = cells[:, 0] + cells[:, 2] + cells[:, 1]
    u -= u.min()
    v -= v.min()
    image = np.zeros((v.max() + 4, u.max() + 4, 3), dtype=np.uint8)
    best = np.full(image.shape[:2], -1, dtype=np.int64)
    solid = grid >= 0

    def empty(x, y, z):
        return not (0 <= x < w and 0 <= y < h and 0 <= z < d) or not solid[x, y, z]

    order = np.argsort(depth)
    for i in order:
        x, y, z = cells[i]
        base = np.array(palette[grid[x, y, z]], dtype=float)
        top = base * 1.15 + 8 if empty(x, y + 1, z) else None
        front = base
        side = base * 0.72
        pu, pv = u[i], v[i]
        # Top face over the upper row, sides below.
        faces = [(0, 0, top if top is not None else front), (1, 0, top if top is not None else side),
                 (0, 1, front), (1, 1, side), (0, 2, front), (1, 2, side)]
        for du, dv, colorv in faces:
            image[pv + dv, pu + du] = np.clip(colorv, 0, 255)
    Image.fromarray(image).resize((image.shape[1] * scale, image.shape[0] * scale), Image.NEAREST).save(path)


def build(name, preview):
    model = RECIPES[name]()
    (grid,), palette = compact([model.trimmed()])
    copies = [(name, grid)]
    if name in TURNED:
        copies.append((name + 'East', turned(grid)))
    if name in TURNED_WEST:
        copies.append((name + 'West', turned_west(grid)))
    for title, shape in copies:
        act1.write(act1.ASSETS / f'{title}.qvox', palette, shape, [])
        if preview:
            act1.PREVIEW.mkdir(parents=True, exist_ok=True)
            iso_preview(shape, palette, act1.PREVIEW / f'{title}.png')
        w, h, d = shape.shape
        print(f'{title}: {w} x {h} x {d}, {int((shape >= 0).sum())} voxels, {len(palette)} colors')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--import', dest='source')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if args.source:
        import_sheets(args.source)
        return
    for name in args.names or RECIPES:
        build(name, args.preview)


if __name__ == '__main__':
    main()
