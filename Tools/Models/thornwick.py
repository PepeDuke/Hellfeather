"""Thornwick's buildings as recipes: the gate, the Tithe-House, the Clothiers'
Guildhall (and its burnt state), two dyers' houses and the Cloister of Looms.

Like buildings.py, each recipe returns a kit.Model at 0.0625-unit voxels, +Z the
front the camera sees, built from house.py's parts with proportions measured off
the Act II sheets (Assets/Reference/Act2). Thornwick is a dye town, so its
plaster runs with madder red under the windows, cloth hangs from every jetty,
and the Red Cuffs' red is on the gate and the Tithe-House. The gate and the
Cloister are a little smaller than the sheets so the town's clearing can hold
them. act2.MODELS lists them as recipes, so inspect_models.py scores them.

    python Tools/Models/thornwick.py                       build every recipe
    python Tools/Models/thornwick.py TitheHouse --preview   build some, with renders
    python Tools/Models/inspect_models.py TitheHouse        compare with the sheet
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buildings  # noqa: E402
from kit import (BRASS, CANDLE, CLOTH_GREY, CLOTH_PALE, DYE_BLUE, DYE_RED, DYE_YELLOW, FRAME, GLOW, IRON, MORTAR, MOSS,  # noqa: E402
                 PAPER, PLASTER, RAVEN, ROPE, SHINGLE, SILVER, SOOT, STONE, WATER, WICKER, WOOD, WOOD_DARK, Model, hash2, pick, planks)
from house import (Gable, barrel, chimney, door, lantern, pent, stair, stone_block, timber_block, window)  # noqa: E402

DYES = [DYE_RED, DYE_BLUE, DYE_YELLOW, CLOTH_PALE, CLOTH_GREY]


# Thornwick's own dressing.

def recolor(m, where, old, new):
    """Swaps the shades of one material for another's, inside a mask."""
    for k, shade in enumerate(old):
        m.fill(where & (m.grid == shade), new[k % len(new)])


def red_roof(m, where):
    """The Red Cuffs' tiles: the roof's shingles under the mask turned madder."""
    recolor(m, where, SHINGLE[:3], [DYE_RED[2], DYE_RED[1], DYE_RED[2]])
    recolor(m, where, SHINGLE[3:], [FRAME[0]])


def dye_runs(m, face_z, x0, x1, y_top, seed, colors=None):
    """Dye run down a plastered +z wall from y_top: streaks of madder, now and
    then woad, a voxel proud of nothing, painted on the face layer."""
    colors = colors or [DYE_RED[0], DYE_RED[1], DYE_RED[2], DYE_BLUE[2]]
    for x in range(x0, x1, 2):
        if hash2(x, 0, seed) > 0.7:
            continue
        length = 8 + int(hash2(x, 1, seed) * 18)
        color = colors[int(hash2(x // 3, 2, seed) * len(colors)) % len(colors)]
        for w in range(2):
            # The second voxel of a run stops a little sooner, so it tapers.
            for j in range(length - w * int(hash2(x, 3, seed) * 6)):
                y = y_top - j
                if y < 0 or x + w >= m.grid.shape[0] or m.grid[x + w, y, face_z] < 0:
                    continue
                if int(m.grid[x + w, y, face_z]) in PLASTER:
                    m.grid[x + w, y, face_z] = color


def cloth_hang(m, z, x0, x1, y_top, seed, step=5, short=6, long=16):
    """Bolts of dyed cloth hung from a jetty or a line, one every few voxels,
    their lengths ragged."""
    for k, x in enumerate(range(x0, x1, step)):
        color = DYES[int(hash2(k, 0, seed) * len(DYES)) % len(DYES)]
        length = short + int(hash2(k, 1, seed) * (long - short))
        for w in range(min(3, x1 - x)):
            for j in range(length - (1 if w == 1 and hash2(k, j, seed) < 0.3 else 0)):
                y = y_top - j
                if y >= 0:
                    m.grid[x + w, y, z] = color[(j // 4 + w) % len(color)]


def cloth_line(m, start, end, seed, sag=4.0):
    """A rope between two posts, sagging, with rags hung along it."""
    (xa, ya, za), (xb, yb, zb) = start, end
    steps = int(max(abs(xb - xa), abs(zb - za))) + 1
    for i in range(steps):
        t = i / max(1, steps - 1)
        x = xa + (xb - xa) * t
        z = za + (zb - za) * t
        y = ya + (yb - ya) * t - sag * math.sin(math.pi * t)
        xi, yi, zi = int(round(x)), int(round(y)), int(round(z))
        m.grid[xi, yi, zi] = WOOD_DARK[0]
        if i % 5 == 2:
            color = DYES[int(hash2(i, 3, seed) * len(DYES)) % len(DYES)]
            for j in range(1, 6 + int(hash2(i, 4, seed) * 6)):
                if yi - j >= 0:
                    m.grid[xi, yi - j, zi] = color[j % len(color)]
                    if i + 1 < steps:
                        m.grid[min(m.grid.shape[0] - 1, xi + 1), yi - j, zi] = color[(j + 1) % len(color)]


def eye_mark(m, cx, cy, z, half=5, barred=True):
    """The Barred Eye (closed by a bar across it) or the Orran Eye (a bar
    upright through it), carved in pale stone on a +z face."""
    for dx in range(-half, half + 1):
        for dy in range(-half, half + 1):
            lid = abs(dy) <= (half - abs(dx)) * 0.55 + 0.4
            edge = lid and abs(dy) > (half - abs(dx)) * 0.55 - 0.8
            pupil = dx * dx + dy * dy <= 2
            bar = (abs(dy) <= 0 and abs(dx) <= half) if barred else (abs(dx) <= 0 and abs(dy) <= half)
            if edge or pupil or bar:
                m.grid[cx + dx, cy + dy, z] = FRAME[0] if (pupil and not bar) else STONE[3]


def eye_banner(m, z, u0, y_top, width=10, length=22, barred=True):
    """A red banner hung flat on a +z wall with a pale eye on it, swallowtailed."""
    for u in range(width):
        for j in range(length):
            if j >= length - 3 and abs(u - (width - 1) / 2) < (j - (length - 4)):
                continue
            m.grid[u0 + u, y_top - j, z] = DYE_RED[0] if (u in (0, width - 1) or j < 2) else DYE_RED[1]
    eye_mark(m, u0 + width // 2, y_top - length // 2, z + 1, half=3, barred=barred)
    m.beam((u0 - 1, y_top + 1, z), (u0 + width, y_top + 1, z), 1, [WOOD_DARK[0]])


def hip_roof(m, x0, x1, z0, z1, y0, rise, colors_seed, red=False):
    """A pyramid roof over a square tower, overhanging a little, tiled."""
    cx, cz = (x0 + x1 - 1) / 2.0, (z0 + z1 - 1) / 2.0
    half = max(x1 - x0, z1 - z0) / 2.0 + 2.0
    yf = m.y.astype(float)
    t = (yf - y0) / rise
    reach = half * (1.0 - t)
    d = np.maximum(np.abs(m.x - cx), np.abs(m.z - cz))
    shell = (yf >= y0) & (yf < y0 + rise) & (d <= reach) & (d > reach - 2.2)
    row = np.floor((half - d) / 2.0).astype(int)
    colors = pick(SHINGLE[:3], hash2(row, (m.x + m.z) // 3, colors_seed))
    colors = np.where(((half - d) % 2.0) < 0.6, SHINGLE[3], colors)
    m.fill(shell, colors)
    if red:
        red_roof(m, shell)
    m.beam((cx, y0 + rise - 2, cz), (cx, y0 + rise + 3, cz), 1, [IRON[0]])


def pennant(m, x, y, z, length=8):
    m.beam((x, y, z), (x, y + 10, z), 1, [IRON[0]])
    for i in range(length):
        for j in range(3 - (1 if i > length - 3 else 0)):
            m.grid[x + 1 + i, y + 9 - j - i // 4, z] = DYE_RED[(i + j) % 2]


def merlons(m, x0, x1, z0, z1, y, seed):
    """Crenellations along the top of a wall: teeth every other four voxels."""
    stone_block(m, x0, x1, y, y + 4, z0, z1, course=4, block=4, seed=seed, quoins=False,
                where=((m.x - x0) // 4) % 2 == 0)


# Recipes.

def thornwick_gate():
    """Thornwick's gatehouse, where the Red Cuffs hold the road: two square
    towers under red pyramid roofs with pennants, a crenellated wall across a
    great arch, the portcullis up, the Barred Eye over the arch, red banners,
    a chain across the road for the shakedown and a toll booth at the side.
    144 x 128 x 64 voxels (9 x 8 x 4 units)."""
    m = Model(150, 136, 70)
    yf = m.y.astype(float)
    z0, z1 = 18, 52
    # The wall between the towers, with the arch through it.
    stone_block(m, 34, 112, 0, 74, z0 + 4, z1 - 4, course=4, block=7, seed=500)
    merlons(m, 34, 112, z0 + 4, z1 - 4, 74, 501)
    span = (np.abs(m.x - 73) < 30) & (yf < 46 + 18 * np.sqrt(np.clip(1 - ((m.x - 73) / 30.0) ** 2, 0, 1)))
    m.clear(span & (m.z >= z0) & (m.z < z1))
    # The arch's voussoirs, and the portcullis raised into its top.
    ring = (np.abs(m.x - 73) < 33) & ~span & (yf < 49 + 19 * np.sqrt(np.clip(1 - ((m.x - 73) / 33.0) ** 2, 0, 1))) & (m.z >= z1 - 5) & (m.z < z1 - 3)
    m.fill(ring & (m.grid >= 0), np.where((m.x // 4) % 2 == 0, STONE[3], STONE[0]))
    for x in range(46, 101, 4):
        top = 46 + int(18 * math.sqrt(max(0.0, 1 - ((x - 73) / 30.0) ** 2)))
        m.beam((x, top - 9, z1 - 6), (x, top, z1 - 6), 1, [IRON[0]])
    m.beam((44, 54, z1 - 6), (102, 54, z1 - 6), 1, [IRON[1]])
    eye_mark(m, 73, 66, z1 - 3, half=5)
    # The towers, with arrow-slit windows lit inside and red roofs.
    for x0 in (2, 112):
        stone_block(m, x0, x0 + 34, 0, 100, z0, z1, course=4, block=6, seed=510 + x0, moss_below=14)
        band = m.box(x0 - 1, 96, z0 - 1, x0 + 35, 100, z1 + 1) & ~m.box(x0, 96, z0, x0 + 34, 100, z1)
        m.fill(band, STONE[3])
        hip_roof(m, x0, x0 + 34, z0, z1, 100, 26, 520 + x0, red=True)
        pennant(m, x0 + 17, 120, (z0 + z1) // 2)
        for y0 in (30, 62, 82):
            window(m, '+z', z1 - 1, x0 + 15, x0 + 19, y0, y0 + 8, style='lattice', arch=2)
        window(m, '+x' if x0 > 50 else '-x', x0 + 33 if x0 > 50 else x0, 20, 24, 70, 78, arch=2)
        eye_banner(m, z1, x0 + 12, 58, width=10, length=26)
    # Lanterns at the arch, the chain across the road, the toll booth.
    lantern(m, 40, 30, z1)
    lantern(m, 106, 30, z1)
    for x in range(36, 111):
        sag = 6.0 * math.sin(math.pi * (x - 36) / 74.0)
        y = int(round(12 - sag))
        m.grid[x, y, z1 + 2] = IRON[(x // 2) % 2]
    m.fill(m.box(70, 3, z1 + 2, 77, 9, z1 + 3), DYE_RED[0])
    # The toll booth: a plank hut with a red-tiled pent roof, at the front right.
    booth = (118, 146, 52, 66)
    m.fill(m.box(booth[0], 0, booth[2], booth[1], 26, booth[3]), planks(m.x.astype(float), yf, width=3))
    window(m, '+z', booth[3] - 1, 124, 136, 10, 20, style='lattice')
    roof = Gable(m, booth[0], booth[1], booth[2], booth[3], eave=26, rise=8, axis='x', over=2, seed=530).build()
    red_roof(m, roof.shell)
    barrel(m, 112, 62)
    return m


def tithe_house():
    """The Thornwick Tithe-House: a tall, narrow stone counting-house under a
    steep front gable with pinnacles, a glowing bay in the gable, the Barred
    Eye carved over the arched door, barred ground windows, red-tiled wings
    either side for the Red Cuff barracks, and chimneys. 80 x 128 x 52."""
    m = Model(86, 132, 58)
    x0, x1, z0, z1 = 16, 66, 8, 48
    stone_block(m, x0, x1, 0, 86, z0, z1, course=4, block=6, seed=540, moss_below=12)
    band = m.box(x0 - 1, 50, z0 - 1, x1 + 1, 53, z1 + 1) & ~m.box(x0, 50, z0, x1, 53, z1)
    m.fill(band, STONE[3])
    under = lambda mask: stone_block(m, x0, x1, 84, 130, z0, z1, course=4, block=6, seed=541, quoins=False, where=mask)  # noqa: E731
    roof = Gable(m, x0, x1, z0, z1, eave=86, rise=36, axis='z', over=2, seed=542).build(under)
    # Pinnacles at the gable's foot and peak.
    for px in (x0 - 1, x1 - 2):
        stone_block(m, px, px + 4, 84, 96, z1 - 4, z1, course=3, block=4, seed=543, quoins=False)
    m.fill(m.box(39, 120, z1 - 3, 43, 128, z1), STONE[3])
    chimney(m, x0 + 4, x0 + 10, z0 + 4, z0 + 10, 90, 130)
    chimney(m, x1 - 10, x1 - 4, z0 + 4, z0 + 10, 90, 126)
    # Wings for the barracks, lower, red-tiled.
    for wx0, wx1, side in ((2, 16, -1), (66, 80, 1)):
        stone_block(m, wx0, wx1, 0, 44, z0 + 8, z1 - 2, course=4, block=6, seed=545 + wx0, moss_below=10)
        wing = Gable(m, wx0, wx1, z0 + 8, z1 - 2, eave=44, rise=12, axis='z', over=2, seed=546 + wx0).build(
            lambda mask, a=wx0, b=wx1: stone_block(m, a, b, 42, 60, z0 + 8, z1 - 2, course=4, block=6, seed=547, quoins=False, where=mask))
        red_roof(m, wing.shell)
        window(m, '+z', z1 - 3, wx0 + 4, wx1 - 4, 12, 22, style='bars', arch=2)
    # The front: steps, the arched door under the Barred Eye, barred windows,
    # the glowing bay in the gable, the counting-room windows.
    stone_block(m, 30, 52, 0, 3, z1, z1 + 5, course=3, block=6, seed=548, quoins=False, moss_below=0)
    door(m, '+z', z1 - 1, 35, 47, 2, 26, arch=6, frame=STONE[3])
    eye_mark(m, 41, 33, z1, half=5)
    for u0 in (21, 53):
        window(m, '+z', z1 - 1, u0, u0 + 7, 10, 22, style='bars', arch=2)
        window(m, '+z', z1 - 1, u0, u0 + 7, 58, 72, arch=3)
    m.fill(m.box(31, 56, z1, 51, 58, z1 + 3), STONE[3])
    window(m, '+z', z1 - 1, 32, 50, 60, 84, style='panes', arch=6)
    window(m, '+z', z1 - 1, 37, 45, 94, 106, arch=4)
    eye_banner(m, z1, 4, 40, width=8, length=20)
    lantern(m, 30, 18, z1)
    high = m.y > 10
    m.fill(high & np.isin(m.grid, MOSS) & (m.y < 84), pick(STONE[:3], hash2(m.x // 3, m.y // 3, 549)))
    slate = np.isin(m.grid, SHINGLE + MOSS) & (m.y >= 84)
    m.fill(slate, pick([RAVEN[2], SOOT[0], DYE_BLUE[2]], hash2(m.x // 3, m.z // 3, 550)))
    for side, at in (('+x', x1 - 1), ('-x', x0)):
        for y0 in (12, 60):
            window(m, side, at, 22, 28, y0, y0 + 11, style='bars' if y0 < 30 else 'lattice', arch=2)
    return m


def guildhall(burnt=False):
    """The Clothiers' Guildhall, with Journeyman & Vale, Factors above it: a
    stone ground floor under two jettied timber floors, a long roof with a
    front cross gable, bolts of dyed cloth hung from the jetties, the firm's
    old sign, and an outside stair up the right side to its door. Burnt, after
    the Burning Archive: the upper floors charred, the roof fallen in to its
    rafters, the windows black. 112 x 140 x 72."""
    m = Model(118, 146, 80)
    x0, x1, z0, z1 = 12, 100, 10, 60
    stone_block(m, x0, x1, 0, 36, z0, z1, course=4, block=6, seed=560, moss_below=10)
    timber_block(m, x0 - 2, x1 + 2, 36, 68, z0 - 2, z1 + 2, bay=11, rails=(52,), seed=561)
    timber_block(m, x0 - 4, x1 + 4, 68, 94, z0 - 4, z1 + 4, bay=11, rails=(81,), seed=562)
    for x in range(x0 - 2, x1 + 2, 4):
        m.grid[x, 35, z1:z1 + 2] = WOOD_DARK[0]
        m.grid[x, 67, z1 + 2:z1 + 4] = WOOD_DARK[0]
    main = Gable(m, x0 - 4, x1 + 4, z0 - 4, z1 + 4, eave=94, rise=34, axis='x', over=3, sag=2.0, seed=563)
    main.build(lambda mask: timber_block(m, x0 - 4, x1 + 4, 92, 132, z0 - 4, z1 + 4, bay=11, rails=(110,), seed=564, where=mask))
    cross = Gable(m, 62, 96, 34, z1 + 7, eave=88, rise=30, axis='z', over=3, seed=565)
    cross.build(lambda mask: timber_block(m, 62, 96, 86, 120, 34, z1 + 7, bay=10, rails=(102,), seed=566, where=mask))
    chimney(m, x0 + 4, x0 + 11, z0 + 6, z0 + 13, 100, 144, lean=1.5)
    chimney(m, x1 - 12, x1 - 5, z0 + 4, z0 + 11, 100, 140)
    # Ground floor: the guild's door, barred windows, a bench of folded bolts.
    door(m, '+z', z1 - 1, 30, 44, 0, 26, arch=7, frame=STONE[3])
    for u0 in (16, 52, 76):
        window(m, '+z', z1 - 1, u0, u0 + 8, 10, 22, style='bars', arch=3)
    lantern(m, 26, 20, z1)
    lantern(m, 48, 20, z1)
    # Upper floors: lit windows; the cross gable's tall one.
    for u0 in (12, 30, 48):
        window(m, '+z', z1 + 1, u0, u0 + 10, 41, 52)
        window(m, '+z', z1 + 3, u0, u0 + 10, 72, 84)
    window(m, '+z', z1 + 3, 70, 88, 72, 84, style='panes')
    window(m, '+z', z1 + 6, 72, 86, 94, 108, arch=4)
    for side, at in (('+x', x1 + 1), ('-x', x0 - 2)):
        for u0 in (20, 40):
            window(m, side, at, u0, u0 + 9, 41, 52)
    # Dyed cloth under both jetties, and dye run down the plaster.
    cloth_hang(m, z1 + 2, x0, x1, 35, 567, step=5, short=6, long=14)
    cloth_hang(m, z1 + 4, x0 - 2, x1 + 2, 67, 568, step=6, short=8, long=18)
    dye_runs(m, z1 + 1, x0 - 2, x1 + 2, 50, 569)
    dye_runs(m, z1 + 3, x0 - 4, x1 + 4, 80, 570)
    # The firm's sign: an old board, its paint older than the guild's.
    m.fill(m.box(76, 40, z1 + 2, 98, 56, z1 + 3), WOOD_DARK[0])
    m.fill(m.box(77, 41, z1 + 3, 97, 55, z1 + 4), PAPER[1])
    for y in (44, 48, 52):
        m.fill(m.box(79, y, z1 + 4, 95, y + 1, z1 + 5) & (hash2(m.x, y, 571) < 0.7), RAVEN[0])
    # The outside stair up the right side to the factors' door.
    stair(m, 'z', z1 + 2, z0 + 18, x1 + 2, x1 + 10, 0, 36, base='wood', rail_side=x1 + 9)
    m.fill(m.box(x1 + 2, 34, z0 + 10, x1 + 11, 36, z0 + 19), planks(m.z.astype(float), m.y.astype(float), width=3))
    door(m, '+x', x1 + 1, z0 + 10, z0 + 18, 36, 56)
    barrel(m, 8, 66)
    barrel(m, 14, 69)
    if burnt:
        char(m, 36, 573, (x0 + 1, x1 - 1, z0 + 1, z1 - 1))
    return m


def char(m, above, seed, inner):
    """Fire's work above a floor line: the rooms burnt out behind their walls,
    the frame black, the plaster scorched and broken through in places, the
    windows dark, and the roof's red tiles fallen in between its rafters."""
    x0, x1, z0, z1 = inner
    roof = np.isin(m.grid, SHINGLE)
    # Hollow the upper floors, so what fell in shows a gutted room below.
    # The chimneys stand, being stone.
    gut = m.box(x0, above + 2, z0, x1, m.grid.shape[1], z1) & ~roof & ~np.isin(m.grid, STONE + SOOT + MORTAR)
    m.fill(gut & (m.y == above + 2), pick([SOOT[0], FRAME[0], WOOD_DARK[1]], hash2(m.x, m.z, seed + 9)))
    m.clear(gut & (m.y > above + 2))
    upper = m.y >= above
    plaster = upper & np.isin(m.grid, PLASTER)
    scorch = hash2(m.x // 2, m.y // 3, seed)
    m.fill(plaster, np.where(scorch < 0.45, SOOT[0], np.where(scorch < 0.7, PLASTER[3], PLASTER[1])))
    # Panels burnt through.
    m.clear(plaster & (hash2(m.x // 6, m.y // 7, seed + 4) < 0.22))
    m.fill(upper & np.isin(m.grid, WOOD + WOOD_DARK), pick([FRAME[0], WOOD_DARK[1], SOOT[0]], hash2(m.x, m.y // 5, seed + 1)))
    m.fill(upper & np.isin(m.grid, GLOW + CANDLE), FRAME[0])
    rafter = (m.x % 9) < 2
    fallen = roof & ~rafter & (hash2(m.x // 4, m.z // 4, seed + 2) < 0.45)
    m.clear(fallen)
    m.fill(roof & rafter, FRAME[0])
    left = roof & ~rafter & ~fallen
    m.fill(left, pick([DYE_RED[2], DYE_RED[1], DYE_RED[2], SOOT[0]], hash2(m.x // 2, m.z // 2, seed + 3)))


def dyers_house(variant):
    """A dyer's house on Thornwick's lanes: timber and plaster, dye run red down
    the walls, cloth drying on a line, and a lean-to over the vats. Variant 0
    turns its gable to the street with the dye yard on its left; variant 1
    turns its long side to the street, a dark slate roof, the lean-to on its
    right. 112 x 110 x 88."""
    m = Model(118, 116, 102)
    yf = m.y.astype(float)
    if variant == 0:
        x0, x1, z0, z1 = 44, 100, 18, 74
        stone_block(m, x0, x1, 0, 6, z0, z1, course=3, block=6, seed=580, quoins=False, moss_below=4)
        timber_block(m, x0, x1, 6, 36, z0, z1, bay=10, rails=(20,), seed=581)
        timber_block(m, x0 - 2, x1 + 2, 36, 62, z0 - 2, z1 + 2, bay=10, rails=(49,), seed=582)
        roof = Gable(m, x0 - 2, x1 + 2, z0 - 2, z1 + 2, eave=62, rise=34, axis='z', over=3, sag=1.5, seed=583)
        roof.build(lambda mask: timber_block(m, x0 - 2, x1 + 2, 60, 100, z0 - 2, z1 + 2, bay=10, rails=(76,), seed=584, where=mask))
        chimney(m, x1 - 12, x1 - 5, z0 + 6, z0 + 13, 70, 112)
        door(m, '+z', z1 - 1, 66, 76, 6, 28)
        for u0 in (50, 84):
            window(m, '+z', z1 - 1, u0, u0 + 9, 14, 26)
        for u0 in (50, 66, 84):
            window(m, '+z', z1 + 1, u0, u0 + 9, 42, 54)
        window(m, '+z', z1 + 3, 66, 76, 72, 84)
        window(m, '+x', x1 - 1, 30, 40, 14, 26)
        window(m, '+x', x1 + 1, 30, 40, 42, 54)
        dye_runs(m, z1 - 1, x0, x1, 30, 585)
        dye_runs(m, z1 + 1, x0 - 2, x1 + 2, 58, 586)
        lantern(m, 80, 18, z1)
        # The dye yard on the left: a lean-to on posts over vats, a fence.
        yard = (4, 44, 40, 82)
        for px, pz in ((5, 41), (5, 80), (24, 80)):
            m.beam((px, 0, pz), (px, 32, pz), 2, [WOOD_DARK[0]])
        lean_to(m, yard[1], yard[0] - 1, 40, 30, yard[2], yard[3] + 2, 588)
        cloth_hang(m, yard[3] + 1, yard[0] + 2, yard[1] - 4, 28, 589, step=5, short=5, long=10)
        vats(m, [(14, 60, DYE_RED), (30, 66, DYE_BLUE), (16, 74, DYE_RED)])
        fence(m, 2, 44, 84)
        cloth_line(m, (3, 52, 30), (44, 56, 30), 587)
    else:
        x0, x1, z0, z1 = 8, 80, 24, 78
        stone_block(m, x0, x1, 0, 8, z0, z1, course=3, block=6, seed=590, quoins=False, moss_below=5)
        timber_block(m, x0, x1, 8, 40, z0, z1, bay=12, rails=(24,), seed=591)
        timber_block(m, x0 - 2, x1 + 2, 40, 64, z0 - 2, z1 + 2, bay=12, rails=(52,), seed=592)
        roof = Gable(m, x0 - 2, x1 + 2, z0 - 2, z1 + 2, eave=64, rise=32, axis='x', over=3, seed=593)
        roof.build(lambda mask: timber_block(m, x0 - 2, x1 + 2, 62, 100, z0 - 2, z1 + 2, bay=12, rails=(80,), seed=594, where=mask))
        recolor(m, roof.shell, SHINGLE[:3], [SOOT[0], SHINGLE[3], RAVEN[2]])
        chimney(m, 40, 47, 44, 51, 70, 112)
        door(m, '+z', z1 - 1, 14, 24, 8, 32)
        for u0 in (32, 50):
            window(m, '+z', z1 - 1, u0, u0 + 10, 16, 28, style='lattice')
        for u0 in (14, 34, 56):
            window(m, '+z', z1 + 1, u0, u0 + 10, 44, 56)
        window(m, '-x', x0 - 2, 40, 50, 44, 56)
        dye_runs(m, z1 - 1, x0, x1, 34, 595)
        dye_runs(m, z1 + 1, x0 - 2, x1 + 2, 60, 596)
        lantern(m, 28, 22, z1)
        # The lean-to on the right over the vats, cloth hung from its eave.
        for px, pz in ((110, 50), (110, 96), (82, 96)):
            m.beam((px, 0, pz), (px, 30, pz), 2, [WOOD_DARK[0]])
        lean_to(m, 80, 113, 44, 30, 46, 99, 598)
        vats(m, [(92, 70, DYE_RED), (100, 86, DYE_BLUE)])
        cloth_hang(m, 98, 84, 112, 30, 597, step=4, short=6, long=14)
        fence(m, 80, 114, 97)
    return m


def lean_to(m, x_high, x_low, y_high, y_low, z0, z1, seed):
    """A lean-to roof of shingles on boards, two voxels thick, falling from
    y_high at x_high to y_low at x_low, with a dark eave board along its foot."""
    lo, hi = min(x_high, x_low), max(x_high, x_low)
    t = (m.x - x_high) / float(x_low - x_high)
    line = y_high + (y_low - y_high) * t
    slab = (m.x >= lo) & (m.x <= hi) & (m.z >= z0) & (m.z < z1) & (m.y <= line + 0.5) & (m.y > line - 2.5)
    row = np.floor((m.x - x_high) * np.sign(x_low - x_high) / 3.0).astype(int)
    colors = pick(SHINGLE[:3], hash2(row, m.z // 4, seed))
    colors = np.where(m.y < line - 1.2, WOOD_DARK[0], colors)
    m.fill(slab, colors)
    eave = (np.abs(m.x - x_low) < 1) & (m.z >= z0) & (m.z < z1) & (m.y <= y_low) & (m.y > y_low - 3)
    m.fill(eave, WOOD_DARK[0])


def vats(m, spots):
    """Round wooden vats, each full of its dye."""
    for x, z, dye in spots:
        dist = np.hypot(m.x - x, m.z - z)
        tub = (dist <= 5.5) & (m.y < 13)
        m.fill(tub & (dist > 4.3), np.where(m.y % 4 == 1, IRON[0], WOOD[1]))
        m.fill(tub & (dist <= 4.3) & (m.y == 11), dye[0])
        m.fill(tub & (dist <= 4.3) & (m.y < 11), dye[2])
        # Dye slopped down the staves.
        m.fill(tub & (dist > 4.3) & (hash2(m.x, m.z, 610) < 0.35) & (m.y > 6), dye[1])


def fence(m, x0, x1, z):
    """A low plank fence along the front of a yard."""
    for x in range(x0, x1):
        top = 8 if x % 6 else 10
        m.fill(m.box(x, 0, z, x + 1, top, z + 1), WOOD[(x // 3) % 3] if x % 6 else WOOD_DARK[0])
    m.beam((x0, 5, z), (x1 - 1, 5, z), 1, [WOOD_DARK[0]])


def cloister_of_looms():
    """The Cloister of Looms: a grey stone weaving school around a bell tower
    whose belfry holds a bell under a slate spire and a shuttle weathervane;
    a long practice hall of pointed windows on the left, a chapel wing with a
    great window on the right, and along the front a cloister walk of arches.
    The Orran Eye is carved over the doors. 176 x 160 x 120."""
    m = Model(184, 166, 128)
    yf = m.y.astype(float)
    # The practice hall, the left wing: its roof runs along x.
    hall = (8, 76, 26, 92)
    stone_block(m, hall[0], hall[1], 0, 62, hall[2], hall[3], course=4, block=7, seed=600, moss_below=12)
    Gable(m, hall[0] - 2, hall[1] + 2, hall[2] - 2, hall[3] + 2, eave=62, rise=30, axis='x', over=3, seed=601).build(
        lambda mask: stone_block(m, hall[0], hall[1], 60, 96, hall[2], hall[3], course=4, block=7, seed=602, quoins=False, where=mask))
    for u0 in (14, 30, 46, 60):
        window(m, '+z', hall[3] - 1, u0, u0 + 9, 34, 56, style='panes', arch=5)
    # The chapel wing on the right, its gable to the front with a great window.
    chapel = (112, 172, 26, 92)
    stone_block(m, chapel[0], chapel[1], 0, 68, chapel[2], chapel[3], course=4, block=7, seed=605, moss_below=12)
    Gable(m, chapel[0] - 2, chapel[1] + 2, chapel[2] - 2, chapel[3] + 2, eave=68, rise=40, axis='z', over=3, seed=606).build(
        lambda mask: stone_block(m, chapel[0], chapel[1], 66, 112, chapel[2], chapel[3], course=4, block=7, seed=607, quoins=False, where=mask))
    window(m, '+z', chapel[3] - 1, 130, 154, 34, 88, style='panes', arch=12)
    for px in (chapel[0] - 1, chapel[1] - 3):
        stone_block(m, px, px + 4, 0, 76, chapel[3] - 3, chapel[3] + 2, course=4, block=4, seed=608, quoins=False)
        m.fill(m.box(px, 76, chapel[3] - 3, px + 4, 84, chapel[3] + 2) & ((m.y - 76) < 8 - np.abs(m.x - px - 1.5) * 2), STONE[3])
    # The bell tower between them.
    tower = (76, 112, 44, 84)
    stone_block(m, tower[0], tower[1], 0, 122, tower[2], tower[3], course=4, block=6, seed=610, moss_below=14)
    band = m.box(tower[0] - 1, 104, tower[2] - 1, tower[1] + 1, 107, tower[3] + 1) & ~m.box(*tower[:1], 104, tower[2], tower[1], 107, tower[3])
    m.fill(band, STONE[3])
    # The belfry, open on each side, and its bell.
    cx, cz = (tower[0] + tower[1]) / 2.0, (tower[2] + tower[3]) / 2.0
    belfry = (yf >= 108) & (yf < 122) & ((np.abs(m.x - cx) < 6) | (np.abs(m.z - cz) < 6))
    m.clear(belfry & m.box(tower[0], 108, tower[2], tower[1], 122, tower[3]))
    m.fill(m.box(tower[0] + 2, 107, tower[2] + 2, tower[1] - 2, 108, tower[3] - 2), WOOD_DARK[0])
    bell = (np.hypot(m.x - cx, m.z - cz) <= 1.5 + (120 - yf) * 0.35) & (yf >= 110) & (yf < 120)
    m.fill(bell, BRASS[0])
    hip_roof(m, tower[0], tower[1], tower[2], tower[3], 122, 30, 611)
    # The shuttle weathervane on the spire.
    m.beam((cx, 150, cz), (cx, 160, cz), 1, [IRON[0]])
    m.beam((cx - 6, 158, cz), (cx + 6, 158, cz), 1, [BRASS[0], BRASS[1]])
    m.beam((cx - 4, 159, cz), (cx + 4, 159, cz), 1, [BRASS[1]])
    # The front of the tower: the doors under a pointed arch, the Orran Eye,
    # the hall's red banners.
    # The porch before the tower, out past the cloister walk, with the doors
    # under a pointed arch and the Orran Eye over them.
    porch = (80, 108, 84, 112)
    stone_block(m, porch[0], porch[1], 0, 52, porch[2], porch[3], course=4, block=6, seed=612, moss_below=4)
    Gable(m, porch[0] - 1, porch[1] + 1, porch[2], porch[3] + 1, eave=52, rise=14, axis='z', over=2, seed=613).build(
        lambda mask: stone_block(m, porch[0], porch[1], 50, 70, porch[2], porch[3], course=4, block=6, seed=614, quoins=False, where=mask))
    door(m, '+z', porch[3] - 1, 86, 102, 0, 36, arch=9, frame=STONE[3])
    eye_mark(m, 94, 44, porch[3], half=5, barred=False)
    window(m, '+z', tower[3] - 1, 89, 99, 72, 98, arch=5)
    eye_banner(m, porch[3], 81, 46, width=5, length=22, barred=False)
    eye_banner(m, porch[3], 102, 46, width=5, length=22, barred=False)
    # The cloister walk either side of the porch: a lean-to on open arches,
    # banners hung in the arches as on the sheet.
    walk = (92, 110)
    for x0, x1 in ((8, 80), (108, 172)):
        for x in range(x0, x1):
            m.beam((x, 40, walk[0]), (x, 32, walk[1] - 1), 2, [SHINGLE[(x // 3 + x // 7) % 3]])
        piers = m.box(x0, 0, walk[1] - 4, x1, 32, walk[1])
        local = (m.x - x0) % 12
        arch_gap = (local >= 3) & (yf < 16 + 7 * np.sqrt(np.clip(1 - ((local - 7.5) / 4.5) ** 2, 0, 1)))
        stone_block(m, x0, x1, 0, 32, walk[1] - 4, walk[1], course=4, block=4, seed=615 + x0, quoins=False, moss_below=3, where=piers & ~arch_gap)
        m.fill(m.box(x0, 0, walk[0], x1, 1, walk[1] - 4), STONE[4])
        for x in range(x0 + 7, x1 - 3, 12):
            m.fill(m.box(x - 2, 8, walk[0] + 2, x + 2, 20, walk[0] + 3), DYE_RED[1])
            m.grid[x - 1:x + 1, 14, walk[0] + 3] = CLOTH_PALE[0]
            lantern(m, x, 24, walk[0] + 1)
    # The sheet's Cloister is pale dressed stone under dark slate.
    roofs = np.isin(m.grid, SHINGLE + MOSS) & (m.y > 30)
    m.fill(roofs & (hash2(m.x // 3, m.z // 3, 616) < 0.5), DYE_BLUE[2])
    m.fill(roofs & np.isin(m.grid, MOSS), SOOT[0])
    m.fill(roofs & np.isin(m.grid, SHINGLE[:3]), RAVEN[2])
    walls = np.isin(m.grid, STONE[:3] + MOSS) & ~roofs
    m.fill(walls, pick([STONE[3], STONE[0], STONE[3], STONE[4]], hash2(m.x // 3, m.y // 3, 617)))
    return m


def inscription_loom():
    """The Inscription Loom, Thornwick's crafting station: a great upright loom
    of dark wood whose warp is silver thread, under an open timber shelter on
    stone feet with a mossy slate roof. Rune-stones are slotted along its top
    beam, a cloth roll of red-patterned weave sits at its foot, a red banner
    with the branching mark hangs in the gable, a candle table stands on the
    left, a basket of spools on the right, and Agnet's chalk circle under the
    shelter's front edge. 48 x 64 x 28 voxels (3 x 4 x 1.75 units). It is an
    open frame where the sheet's dark shelter reads as solid, so its outlines
    score lower than a closed building's."""
    m = Model(52, 68, 44)
    yf = m.y.astype(float)
    x0, x1, z0, z1 = 3, 47, 3, 27
    # The shelter: four posts on stone feet, lashed braces, plates on top.
    for px in (x0, x1 - 3):
        for pz in (z0, z1 - 3):
            stone_block(m, px - 1, px + 4, 0, 4, pz - 1, pz + 4, course=2, block=3, seed=620, quoins=False, moss_below=2)
            m.fill(m.box(px, 4, pz, px + 3, 46, pz + 3), np.where((m.y % 7) == 0, WOOD_DARK[0], WOOD[2]))
            for y in (14, 34):
                m.fill(m.box(px - 1, y, pz - 1, px + 4, y + 2, pz + 4) & ((m.x + m.y + m.z) % 2 == 0), ROPE[0])
    for pz in (z0, z1 - 3):
        m.fill(m.box(x0 - 1, 44, pz, x1 + 1, 47, pz + 3), WOOD_DARK[0])
    for px in (x0, x1 - 3):
        m.fill(m.box(px, 44, z0, px + 3, 47, z1), WOOD_DARK[0])
    for side in (0, 1):
        x = x0 + 1 if side == 0 else x1 - 2
        step = 1 if side == 0 else -1
        m.beam((x, 32, z1 - 1), (x + step * 9, 44, z1 - 1), 2, [WOOD[1]])
    # The roof: slate on a gable to the front, open beneath, a truss and the
    # banner in it.
    # Boarded gable ends front and back, dark between the truss timbers.
    roof = Gable(m, x0 - 1, x1 + 1, z0 - 1, z1 + 1, eave=46, rise=16, axis='z', over=3, seed=621).build(
        lambda mask: m.fill(mask & ((m.z <= z0) | (m.z >= z1 - 1)), np.where(m.x % 4 == 0, WOOD_DARK[1], WOOD_DARK[0])))
    m.fill(roof.shell & np.isin(m.grid, SHINGLE[:3]), pick([RAVEN[2], SOOT[0], STONE[1]], hash2(m.x // 3, m.z // 3, 622)))
    m.beam((25, 46, z1), (25, 60, z1), 2, [WOOD_DARK[0]])
    m.beam((x0, 47, z1), (x1 - 1, 47, z1), 2, [WOOD_DARK[0]])
    for u in range(8):
        for j in range(14):
            if j >= 11 and abs(u - 3.5) < (j - 10):
                continue
            glyph = (abs(u - 3.5) < 0.6 and 2 < j < 11) or (abs(abs(u - 3.5) - (j - 3) * 0.45) < 0.6 and 3 < j < 9)
            m.grid[21 + u, 59 - j, z1] = CLOTH_PALE[0] if glyph else DYE_RED[0 if u in (0, 7) else 1]
    # The loom: two uprights, the top beam with its rune-stones, the breast
    # beam, the silver warp and the cloth roll at its foot.
    lz = 13
    # Its side frames are deep, braced panels; a cog wheel turns on the right.
    for ux in (10, 38):
        side = m.box(ux, 0, lz - 6, ux + 3, 40, lz + 9)
        brace = (np.abs((m.z - (lz - 6)) - (m.y * 15.0 / 40.0)) < 1.2) | (m.y < 3) | (np.abs(m.y - 24) < 1.5) | (m.z == lz - 6) | (m.z == lz + 8) | ((m.z >= lz) & (m.z < lz + 4))
        m.fill(side & brace, np.where(m.y % 9 == 0, WOOD_DARK[1], WOOD_DARK[0]))
    wheel = (np.hypot(m.y - 26, m.z - (lz + 2)) <= 6.0) & (m.x >= 41) & (m.x < 43)
    m.fill(wheel & ((np.hypot(m.y - 26, m.z - (lz + 2)) > 4.4) | (np.abs(np.sin(np.arctan2(m.y - 26, m.z - lz - 2) * 4)) < 0.25)), WOOD[0])
    m.fill((np.hypot(m.y - 26, m.z - (lz + 2)) <= 1.5) & (m.x >= 41) & (m.x < 44), IRON[0])
    m.fill(m.box(9, 36, lz, 42, 40, lz + 4), WOOD[0])
    m.fill(m.box(10, 20, lz + 1, 41, 22, lz + 4), WOOD[1])
    for k, rx in enumerate(range(12, 38, 5)):
        stone = m.box(rx, 40, lz + 1, rx + 4, 45, lz + 3)
        m.fill(stone, STONE[3])
        m.fill(stone & (m.z == lz + 2) & ((m.x == rx + 1 + k % 2) | (m.y == 42 + k % 2)), CLOTH_PALE[0])
    warp = (m.x >= 14) & (m.x < 37) & (m.x % 2 == 0) & (m.y >= 8) & (m.y < 36) & (m.z == lz + 2)
    m.fill(warp, np.where((m.y + m.x) % 5 == 0, SILVER[2], SILVER[1]))
    # A band already woven above the roll: grey with a red border.
    woven = (m.x >= 14) & (m.x < 37) & (m.y >= 11) & (m.y < 16) & (m.z == lz + 2)
    m.fill(woven, np.where((m.y == 11) | (m.y == 15), DYE_RED[1], CLOTH_GREY[0]))
    roll = (np.hypot(m.y - 7, m.z - (lz + 6)) <= 3.4) & (m.x >= 13) & (m.x < 38)
    m.fill(roll, np.where(np.abs(m.x - 25) < 3, DYE_RED[0], np.where((m.x % 6) == 0, DYE_RED[1], CLOTH_PALE[1])))
    # The candle table on the left, with books, and the basket of spools on the right.
    m.fill(m.box(1, 0, z1 - 5, 9, 12, z1 + 1) & ((m.y == 11) | (((m.x == 1) | (m.x == 8)) & ((m.z == z1 - 5) | (m.z == z1)))), WOOD[1])
    m.fill(m.box(2, 12, z1 - 4, 8, 15, z1), pick([DYE_RED[2], DYE_BLUE[2], WOOD_DARK[0]], hash2(m.y, m.x // 3, 623)))
    for cx in (3, 6):
        m.fill(m.box(cx, 15, z1 - 2, cx + 1, 19, z1 - 1), CANDLE[0])
        m.grid[cx, 19, z1 - 2] = GLOW[0]
    basket = (np.hypot(m.x - 44, m.z - (z1 - 2)) <= 4.0) & (m.y < 9)
    m.fill(basket & (np.hypot(m.x - 44, m.z - (z1 - 2)) > 3.0), WICKER[(0)])
    for k, (sx, sz) in enumerate(((43, z1 - 3), (45, z1 - 1), (44, z1 - 2))):
        m.fill(m.box(sx, 8, sz, sx + 2, 13, sz + 2), DYES[k % len(DYES)][0])
    # Agnet's chalk circle on the floor under the shelter's front edge.
    d = np.hypot(m.x - 25, m.z - (z1 - 2))
    chalk = ((np.abs(d - 5.0) < 0.6) | ((d < 4.2) & ((np.abs(m.x - 25) < 0.6) | (np.abs(np.abs(m.x - 25) - (m.z - z1 + 5) * 0.8) < 0.6)))) & (m.y == 0) & (m.z < z1 + 2)
    m.fill(chalk & (m.grid < 0) & (hash2(m.x, m.z, 624) < 0.85), CLOTH_PALE[0])
    return m


RECIPES = {
    'ThornwickGate': thornwick_gate,
    'TitheHouse': tithe_house,
    'ClothiersGuildhall': guildhall,
    'ClothiersGuildhallBurnt': lambda: guildhall(burnt=True),
    'ClothiersRow': lambda: dyers_house(0),
    'ClothiersRowB': lambda: dyers_house(1),
    'CloisterOfLooms': cloister_of_looms,
    'InscriptionLoom': inscription_loom,
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
