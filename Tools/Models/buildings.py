"""Builds Act I buildings and props from recipes made of kit.py parts.

Each recipe is a function that returns a kit.Model. Proportions are measured
off the concept sheet in Act1-refs: the sheet's dimension panel gives the
footprint and height in world units, and buildings use 0.0625-unit voxels, so
one unit is 16 voxels. act1.MODELS still lists each building with its sheet
crops, marked recipe=True, so inspect_models.py can score it against the sheet
and act1.py leaves it alone.

    python Tools/Models/buildings.py                     build every recipe
    python Tools/Models/buildings.py RookeryTower        build some of them
    python Tools/Models/inspect_models.py RookeryTower   compare with the sheet
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402
from kit import (BRASS, BURLAP, CANDLE, CLOTH_GREY, CLOTH_PALE, CLOTH_RED, FRAME, GLOW, GUANO, IRON, IVY,  # noqa: E402
                 MOSS, PAPER, PLASTER, RAVEN, SOOT, STONE, WATER, WOOD, WOOD_DARK, WOOD_LIT, Model, hash2,
                 compact, octagon_corners, octagon_distance, pick, planks, raven, shingles, stone_courses)
from house import (Gable, barrel, chimney, door, face_layer, falling_water, hanging_sign, lantern,  # noqa: E402
                   pent, plank_block, sack, stair, stone_block, timber_block, water_wheel, window)


def wrap(angle):
    """An angle difference folded into -pi..pi."""
    return np.angle(np.exp(1j * angle))


def rookery_tower():
    """Edda's Rookery Tower: a tapering round stone tower, white with droppings,
    rings of raven perches, an open timber loft under a steep octagonal shingle
    roof, and Edda's hut leaning on its front-left foot. 10 x 10 x 11 units.

    Heights in voxels, read off the sheet's front view (11 units = 176):
    shaft to 106, corbels to 114, loft floor to 117, loft to 141, roof to 170,
    finial to 176."""
    m = Model(118, 176, 110)
    cx, cz = 72.0, 52.0
    shaft_top, corbel_top, floor_top, loft_top, roof_top = 106, 114, 117, 141, 170
    base_r, top_r = 38.0, 26.5
    dx, dz = m.x - cx, m.z - cz
    dist = np.hypot(dx, dz)
    theta = np.arctan2(dz, dx)
    y = m.y
    yf = y.astype(float)

    def shaft_radius(h):
        return base_r - (h - 8) * ((base_r - top_r) / (shaft_top - 8))

    # The shaft: a flared plinth, a long taper, then corbels out to the loft.
    radius = np.where(y < 8, base_r + 3.5 - y * 0.44,
             np.where(y < shaft_top, shaft_radius(yf), top_r + (y - shaft_top) * 0.65))
    along = theta * 30.0
    colors, mortar, (row, col) = stone_courses(along, yf, course=4, block=7)
    # Blocks stand proud of the mortar and of each other, so the wall has relief.
    jitter = (hash2(row, col, 9) - 0.5) * 1.6
    shaft = (y < corbel_top) & (dist <= radius + jitter - mortar * 1.0)

    # Droppings run down from every perch ring and from the loft, thick at the
    # top and thinning out, so the wall reads streaked white as on the sheet.
    column = np.floor(along / 1.5).astype(int)
    streak = np.zeros_like(shaft)
    fade = np.zeros(shaft.shape)
    for top in (corbel_top, 96, 76, 56, 36):
        length = 6 + hash2(column, top, 4) * 34
        here = (hash2(column, top, 5) < 0.3) & (y <= top) & (y > top - length)
        streak |= here
        fade = np.where(here, (top - yf) / length, fade)
    streak_color = np.where(fade < 0.5, pick(GUANO[:2], hash2(column, y // 3, 6)), pick(GUANO[2:], hash2(column, y // 3, 6)))
    colors = np.where(streak & ~mortar, streak_color, colors)
    # Moss creeps up from the ground and sits in the mortar low down.
    moss = ((hash2(column // 2, y // 2, 7) * 18.0 > y + 1) | (mortar & (hash2(column, y, 10) * 30 > y))) & (y < 18)
    colors = np.where(moss, pick(MOSS, hash2(column, y, 8)), colors)
    m.fill(shaft, colors)

    # Buttresses around the foot, stepped back as they rise.
    for k, angle in enumerate((-35, 25, 95, 160, 215, 285)):
        a = math.radians(angle)
        across = np.abs(wrap(theta - a)) * dist
        reach = np.where(y < 10, 7.0, np.where(y < 22, 4.5, 2.0)) * (y < 34)
        buttress = (across <= 4.0) & (dist <= shaft_radius(np.minimum(yf, shaft_top)) + reach) & (np.abs(wrap(theta - a)) < 0.6) & (y < 34)
        bcol = stone_courses(across * 2.0 + k * 3, yf, course=4, block=6, seed=30 + k)[0]
        cap = (y >= 32) | ((y >= 20) & (y < 22)) | ((y >= 8) & (y < 10))
        m.fill(buttress & ~(m.grid >= 0), np.where(cap, STONE[3], np.where(moss, pick(MOSS, hash2(m.x, y, 31)), bcol)))

    # Scattered stones around the foot.
    rubble = (y < 3) & (dist > 38) & (dist < 47) & (hash2(np.floor(along / 4).astype(int), np.floor(dist / 3).astype(int), 11) < 0.35 - y * 0.1)
    m.fill(rubble, pick(STONE + MOSS, hash2(m.x, m.z, 12)))

    def arc_opening(angle, y0, height, width, fill_colors, depth=2.5):
        """Cuts an arched opening into the shaft and fills its back with fill_colors."""
        a = math.radians(angle)
        turn = wrap(theta - a)
        offset = turn * radius
        top = y0 + height
        half = np.where(y >= top - 2, np.maximum(0.6, width / 2.0 - (y - (top - 2)) * 0.9), width / 2.0)
        facing = np.abs(turn) < 1.0
        opening = (np.abs(offset) <= half) & (y >= y0) & (y < top) & (dist > radius - depth - 2) & facing
        m.clear(opening & (dist > radius - depth))
        m.fill(opening & (dist <= radius - depth), fill_colors)
        # A pale stone surround and a sill.
        surround = (np.abs(offset) <= half + 1.2) & (y >= y0 - 1) & (y < top + 1) & ~opening & shaft & facing
        m.fill(surround, STONE[3])

    glow = np.where(hash2(m.x // 2, m.y // 2, 13) < 0.5, GLOW[0], GLOW[1])
    for angle, y0, height in ((70, 26, 10), (40, 48, 10), (100, 68, 10), (60, 88, 9), (10, 32, 9),
                              (150, 58, 9), (200, 40, 9), (255, 78, 9), (320, 92, 9), (-20, 70, 9)):
        arc_opening(angle, y0, height, 3.4, glow)
    door = planks(theta * 30.0, yf, width=2, shades=WOOD[:3])
    door = np.where((y == 6) | (y == 12), FRAME[0], door)
    arc_opening(52, 2, 17, 9.0, door, depth=1.5)

    # Perch rings: beams out of the wall on brackets, ravens on most of them.
    for ring, py in enumerate((36, 56, 76, 96)):
        r = shaft_radius(py)
        for k in range(7):
            a = math.radians(k * (360 / 7) + ring * 26 + 12)
            ca, sa = math.cos(a), math.sin(a)
            m.beam((cx + ca * (r - 2), py, cz + sa * (r - 2)), (cx + ca * (r + 8), py, cz + sa * (r + 8)), 2, WOOD[:3])
            m.beam((cx + ca * (r - 1), py - 5, cz + sa * (r - 1)), (cx + ca * (r + 4), py - 1, cz + sa * (r + 4)), 1, [WOOD_DARK[0]])
            if hash2(ring, k, 14) < 0.65:
                raven(m, (cx + ca * (r + 6), py + 1, cz + sa * (r + 6)), a + (hash2(ring, k, 15) - 0.5) * 2.0)

    # The loft floor, a plank octagon on the corbels, with joist ends showing.
    octo = octagon_distance(dx, dz)
    floor = (y >= corbel_top) & (y < floor_top) & (octo <= 33)
    joists = (np.abs(wrap(theta * 8)) < 0.5) & (octo > 31)
    m.fill(floor, np.where(octo > 31.5, np.where(joists, WOOD[3], WOOD_DARK[0]), planks(theta * 22.0, yf, width=3)))
    # Inside the loft, the tower's lit core: warm boards and lamps.
    core = (y >= floor_top) & (y < loft_top) & (dist <= 21)
    lit = planks(theta * 21.0, yf, width=3, shades=WOOD_LIT)
    lamps = np.zeros_like(core)
    for k in range(5):
        a = math.radians(k * 72 + 20)
        lamps |= (np.abs(wrap(theta - a)) * 21 < 1.6) & (y >= floor_top + 8) & (y < floor_top + 13)
    m.fill(core, np.where(lamps, GLOW[0], lit))

    # Posts, rails and balusters around the octagon, knee braces up to the wall plate.
    corners = octagon_corners((cx, cz), 30.0)
    rail = floor_top + 8
    for k in range(8):
        (ax, az), (bx, bz) = corners[k], corners[(k + 1) % 8]
        m.beam((ax, floor_top, az), (ax, loft_top, az), 3, [WOOD_DARK[0]])
        m.beam((ax, rail, az), (bx, rail, bz), 2, WOOD[:2])
        m.beam((ax, loft_top - 1, az), (bx, loft_top - 1, bz), 3, [WOOD_DARK[1]])
        steps = int(math.hypot(bx - ax, bz - az) // 3)
        for s in range(1, steps):
            t = s / steps
            px, pz = ax + (bx - ax) * t, az + (bz - az) * t
            m.beam((px, floor_top, pz), (px, rail - 1, pz), 1, [WOOD[1]])
        for (sx, sz), (ex, ez) in (((ax, az), (bx, bz)), ((bx, bz), (ax, az))):
            ux, uz = (ex - sx), (ez - sz)
            n = math.hypot(ux, uz)
            m.beam((sx, loft_top - 9, sz), (sx + ux / n * 7, loft_top - 2, sz + uz / n * 7), 1, [WOOD[2]])
        if hash2(k, 0, 16) < 0.55:
            mx, mz = (ax + bx) / 2, (az + bz) / 2
            raven(m, (mx, rail + 1, mz), math.atan2(mz - cz, mx - cx))
    # The bell, hung under the plate on the front face.
    (ax, az), (bx, bz) = corners[1], corners[2]
    bx_, bz_ = (ax + bx) / 2 - 3, (az + bz) / 2 - 3
    m.beam((bx_, loft_top - 6, bz_), (bx_, loft_top - 1, bz_), 1, [WOOD_DARK[0]])
    m.ellipsoid((bx_, loft_top - 9, bz_), (2.4, 3.0, 2.4), BRASS[0])

    # The steep octagonal roof: overlapping shingle rows, a dark fascia under
    # the eave and a slight flare at the bottom, then the finial.
    roof_h = roof_top - loft_top
    t = np.clip((yf - loft_top) / roof_h, 0.0, 1.0)
    roof_r = 39.0 * (1.0 - t) ** 1.25
    row_y = (yf - loft_top) / 2.5
    lip = (1.0 - (row_y - np.floor(row_y))) * 1.2
    roof = (y >= loft_top) & (y < roof_top) & (octo <= roof_r + lip)
    roof_colors = shingles(theta * 26.0, row_y)
    roof_colors = np.where((y < loft_top + 2) & (octo > roof_r - 1.5), WOOD_DARK[0], roof_colors)
    # Hips: the eight ridges where the faces meet are darker capping.
    hip = np.abs(wrap(theta * 8 - math.pi)) < 0.45
    roof_colors = np.where(hip & (y >= loft_top + 2), WOOD_DARK[1], roof_colors)
    m.fill(roof, roof_colors)
    m.beam((cx, roof_top - 3, cz), (cx, 175, cz), 2, [WOOD_DARK[0]])
    m.ellipsoid((cx, 174, cz), (1.6, 1.4, 1.6), BRASS[1])

    # Edda's hut, gable to the front, against the tower's front-left foot.
    hut(m, x0=4, x1=46, z0=68, z1=104)
    return m


def hut(m, x0, x1, z0, z1):
    """A stone-footed plank hut with a steep mossy roof, chimney and lit windows."""
    xc = (x0 + x1) / 2.0
    half = (x1 - x0) / 2.0
    eave, rise, over = 20, 22.0, 3.0
    x, y, z = m.x, m.y, m.z
    xf, yf, zf = x.astype(float), y.astype(float), z.astype(float)
    off = np.abs(xf - xc)
    roof_line = eave + (half + over - off) * rise / (half + over)
    body = (off <= half) & (z >= z0) & (z < z1) & ((y < eave) | (yf < roof_line - 1.5))
    side = off >= half - 0.5
    walls = planks(np.where(side, zf, xf), yf, width=3)
    footing = stone_courses(xf + zf, yf, course=3, block=6, seed=21)[0]
    colors = np.where(y < 7, footing, walls)
    # Dark frame timbers: corner posts, sill, plate and a mid rail.
    frame = (y == 7) | (y == eave - 1) | (y == 14) | ((off >= half - 1.5) & ((z < z0 + 2) | (z >= z1 - 2)))
    colors = np.where(frame & (y >= 7), WOOD_DARK[0], colors)
    m.fill(body, colors)

    roof = (off <= half + over) & (z >= z0 - 2) & (z < z1 + 3) & (yf >= roof_line - 1.5) & (yf < roof_line + 1.5)
    roof_colors = shingles(zf, (half + over - off) / 2.2, width=3, seed=23)
    roof_colors = np.where(off < 1.2, WOOD_DARK[1], roof_colors)
    m.fill(roof, roof_colors)
    # Barge boards along the front gable.
    m.fill(roof & (z >= z1 + 1), WOOD_DARK[0])

    front = z1 - 1
    door = (z == front) & (xf >= xc + 6) & (xf < xc + 13) & (y >= 7) & (y < 20)
    m.fill(door, planks(xf, yf, width=2, shades=WOOD[1:3]))
    window = (z == front) & (xf >= xc - 13) & (xf < xc - 4) & (y >= 9) & (y < 17)
    mullion = (np.abs(xf - (xc - 8.5)) < 0.6) | (y == 13)
    m.fill(window, np.where(mullion, FRAME[0], np.where(hash2(x, y, 24) < 0.5, GLOW[0], GLOW[1])))
    m.fill((z == front) & (np.abs(xf - xc) < 2.6) & (y >= 25) & (y < 31), GLOW[1])
    m.fill((x == x0) & (z >= z0 + 12) & (z < z0 + 20) & (y >= 9) & (y < 16), GLOW[0])

    # Chimney on the back slope, sooty at the top.
    chim = (xf >= xc + 5) & (xf < xc + 11) & (z >= z0 + 4) & (z < z0 + 10) & (y < 52)
    m.fill(chim, np.where(y >= 49, SOOT[0], stone_courses(xf + zf, yf, course=3, block=5, seed=25)[0]))
    m.clear((xf >= xc + 6) & (xf < xc + 10) & (z >= z0 + 5) & (z < z0 + 9) & (y >= 49))

    # A woodpile by the door.
    pile = (z >= z1) & (z < z1 + 4) & (x >= x0 + 1) & (x < x0 + 13) & (y < 7 - (x - x0) // 6)
    ring = ((x % 3) - 1) ** 2 + ((y % 3) - 1) ** 2 == 0
    m.fill(pile, np.where(ring, WOOD[2], WOOD[3]))


def ridge_ravens(m, roof, spots, axis='x', facing=None):
    """Ravens on a gable's ridge at the given positions along it."""
    w, h, d = m.grid.shape
    for at in spots:
        if axis == 'x':
            col = roof.line[int(at), 0, :]
            z = int(np.argmax(col))
            raven(m, (at, int(col[z]) - 1, z), facing if facing is not None else math.pi / 2 * (1 if hash2(int(at), 1, 3) < 0.5 else -1))
        else:
            col = roof.line[:, 0, int(at)]
            x = int(np.argmax(col))
            raven(m, (x, int(col[x]) - 1, at), facing if facing is not None else (0.0 if hash2(int(at), 1, 3) < 0.5 else math.pi))


def raven_icon(u, v):
    """A hunched raven with a bent neck, for signs and banners."""
    body = ((u - 0.5) / 0.3) ** 2 + ((v - 0.55) / 0.2) ** 2 < 1.0
    head = ((u - 0.75) / 0.12) ** 2 + ((v - 0.72) / 0.12) ** 2 < 1.0
    return body or head


def crooked_raven():
    """The Crooked Raven: a two-storey timber-framed tavern on a stone plinth,
    jettied upper floor, sagging main roof along x with a front cross gable,
    a leaning chimney, the raven sign and ravens on the ridge. 6.5 x 6.5 x 7.5."""
    m = Model(100, 122, 90)
    stone_block(m, 10, 88, 0, 8, 10, 70, course=3, block=6, seed=41)
    timber_block(m, 10, 88, 8, 44, 10, 70, bay=12, rails=(26,), seed=51)
    timber_block(m, 8, 90, 44, 76, 8, 74, bay=12, rails=(60,), seed=52)
    # Joist ends under the jetty.
    for x in range(10, 88, 4):
        m.grid[x, 43, 70:74] = WOOD_DARK[0]
    main = Gable(m, 8, 90, 8, 74, eave=76, rise=34, axis='x', over=3, sag=3.0, seed=71)
    main.build(lambda mask: timber_block(m, 8, 90, 74, 112, 8, 74, bay=12, rails=(92,), seed=53, where=mask))
    cross = Gable(m, 34, 64, 40, 77, eave=70, rise=26, axis='z', over=3, seed=72)
    cross.build(lambda mask: timber_block(m, 34, 64, 68, 100, 40, 77, bay=10, rails=(84,), seed=54, where=mask))
    chimney(m, 14, 22, 22, 30, 60, 120, lean=2.0)

    # The front: arched door, lattice windows, the cross gable's bay.
    door(m, '+z', 69, 43, 55, 8, 31, arch=6)
    for u0 in (16, 64):
        window(m, '+z', 69, u0, u0 + 12, 15, 31)
    for u0 in (14, 74):
        window(m, '+z', 73, u0, u0 + 11, 50, 66)
    window(m, '+z', 76, 41, 57, 72, 86)
    window(m, '+z', 76, 46, 52, 89, 95)
    # The right side, which the camera sees, and a few at the back and left.
    for u0 in (22, 46):
        window(m, '+x', 87, u0, u0 + 10, 15, 30)
        window(m, '+x', 89, u0 - 2, u0 + 8, 50, 66)
    window(m, '+x', 89, 36, 46, 82, 94)
    for u0 in (24, 60):
        window(m, '-z', 10, u0, u0 + 10, 15, 30)
        window(m, '-z', 8, u0, u0 + 10, 50, 64)
    window(m, '-x', 10, 30, 40, 15, 30)
    window(m, '-x', 8, 30, 40, 50, 64)

    hanging_sign(m, 90, 64, 72, 'x', 1, raven_icon)
    lantern(m, 40, 20, 71)
    lantern(m, 58, 20, 71)
    for bx, bz in ((80, 77), (85, 81), (80, 83)):
        barrel(m, bx, bz)
    ridge_ravens(m, main, (24, 58, 78))
    return m


def banner(m, z, u0, y_top, width=9, length=18):
    """A raven-sigil banner hung flat on a +z wall: pale cloth, red border, a
    swallowtail foot and the black raven."""
    for u in range(width):
        for j in range(length):
            tail = j >= length - 3 and abs(u - (width - 1) / 2) < (j - (length - 4))
            if tail:
                continue
            edge = u in (0, width - 1) or j in (0, 1) or j >= length - 4
            fig = raven_icon(u / (width - 1), 1.0 - (j - 2) / (length - 6))
            m.grid[u0 + u, y_top - j, z] = CLOTH_RED[0] if edge else (RAVEN[0] if fig else CLOTH_PALE[j % 2])
    m.beam((u0 - 1, y_top + 1, z), (u0 + width, y_top + 1, z), 1, [WOOD_DARK[0]])



def candle_icon(u, v):
    return (abs(u - 0.5) < 0.12 and 0.15 < v < 0.65) or (abs(u - 0.5) < 0.06 and 0.65 <= v < 0.8)


def needle_icon(u, v):
    return abs((u - 0.5) - (v - 0.5)) < 0.09 and 0.12 < u < 0.88


def moth_icon(u, v):
    wings = ((abs(u - 0.5) - 0.2) / 0.18) ** 2 + ((v - 0.55) / 0.25) ** 2 < 1.0
    return wings or (abs(u - 0.5) < 0.05 and 0.25 < v < 0.8)


def reeves_hall():
    """Reeve's Hall: a sturdy two-gabled stone hall with raven banners, a
    bounty board by the arched door and barred lower windows. 6.5 x 6.5 x 5.5."""
    m = Model(100, 90, 92)
    x0, x1, z0, z1 = 10, 88, 10, 78
    stone_block(m, x0, x1, 0, 48, z0, z1, course=4, block=7, seed=42)
    # A string course under the eaves.
    band = m.box(x0 - 1, 46, z0 - 1, x1 + 1, 48, z1 + 1) & ~m.box(x0, 46, z0, x1, 48, z1)
    m.fill(band, STONE[3])
    stone_under = lambda mask: stone_block(m, x0, x1, 46, 90, z0, z1, course=4, block=7, seed=43, quoins=False, where=mask)  # noqa: E731
    front = Gable(m, x0, x1, z0, z1, eave=48, rise=30, axis='z', over=3, seed=73).build(stone_under)
    Gable(m, x0, x1, 30, 58, eave=48, rise=26, axis='x', over=3, seed=74).build(stone_under)
    chimney(m, 14, 22, 14, 22, 50, 88)
    chimney(m, 76, 84, 66, 74, 50, 86)

    door(m, '+z', z1, 40, 56, 0, 30, arch=8, frame=STONE[3])
    banner(m, z1 + 1, 24, 42)
    banner(m, z1 + 1, 64, 42)
    # The bounty board, papers pinned on it, left of the door.
    m.grid[12:28, 6:22, z1 + 1] = WOOD_DARK[0]
    m.grid[13:27, 7:21, z1 + 1] = WOOD[1]
    for px, py in ((14, 13), (19, 9), (22, 15), (15, 8)):
        m.grid[px:px + 4, py:py + 5, z1 + 2] = PAPER[(px + py) % 2]
    m.grid[23, 9, z1 + 3] = CLOTH_RED[0]
    lantern(m, 34, 22, z1 + 2)
    lantern(m, 62, 22, z1 + 2)
    window(m, '+z', z1, 66, 74, 10, 22, style='bars', arch=3)
    window(m, '+z', z1 - 1, 44, 52, 54, 64, arch=4)
    for side, at in (('+x', x1), ('-x', x0 - 1)):
        for u0 in (18, 38, 58):
            window(m, side, at, u0, u0 + 8, 10, 22, style='bars', arch=3)
        window(m, side, at - (1 if side == '+x' else -1), 40, 48, 54, 64, arch=4)
    for u0 in (22, 46, 66):
        window(m, '-z', z0 - 1, u0, u0 + 8, 10, 22, style='bars', arch=3)
    ridge_ravens(m, front, (30, 56), axis='z')
    return m


def pells_chandlery():
    """Pell's Chandlery: a narrow timber candle shop with candles in the
    window, a crooked chimney and an outside stair up the right side to
    Jessa's garret. 6 x 6 x 6.5."""
    m = Model(74, 106, 76)
    stone_block(m, 12, 54, 0, 6, 8, 58, course=3, block=6, seed=44)
    timber_block(m, 12, 54, 6, 40, 8, 58, bay=10, rails=(22,), seed=55)
    timber_block(m, 11, 55, 40, 66, 7, 60, bay=11, rails=(53,), seed=56)
    roof = Gable(m, 11, 55, 7, 60, eave=66, rise=32, axis='z', over=3, seed=75)
    roof.build(lambda mask: timber_block(m, 11, 55, 64, 100, 7, 60, bay=11, rails=(80,), seed=57, where=mask))
    chimney(m, 44, 50, 14, 20, 50, 104, lean=-3.0)

    window(m, '+z', 57, 15, 37, 10, 31, style='candles')
    pent(m, 13, 40, 58, 36, 5, 3)
    door(m, '+z', 57, 40, 48, 6, 30)
    for u0 in (16, 34):
        window(m, '+z', 59, u0, u0 + 8, 45, 57)
    window(m, '+z', 59, 29, 37, 72, 82)
    hanging_sign(m, 46, 48, 60, 'z', 1, candle_icon)
    lantern(m, 51, 22, 59)
    # The outside stair up the right wall to the garret door, and its landing.
    stair(m, 'z', 12, 46, 55, 64, 6, 40, base='stone', rail_side=63)
    stone_block(m, 55, 64, 0, 6, 10, 58, course=3, block=6, seed=45, quoins=False)
    m.fill(m.box(55, 38, 46, 65, 40, 59), planks(m.z.astype(float), m.y.astype(float), width=3))
    for z in range(46, 59, 4):
        m.beam((64, 40, z), (64, 47, z), 1, [WOOD_DARK[0]])
    m.beam((64, 47, 46), (64, 47, 58), 1, [WOOD[2]])
    door(m, '+x', 54, 48, 56, 40, 55)
    window(m, '+x', 54, 22, 28, 46, 54)
    window(m, '+x', 53, 30, 38, 14, 26)
    for u0 in (20, 36):
        window(m, '-z', 7, u0, u0 + 8, 45, 57)
    window(m, '-x', 11, 30, 38, 45, 57)
    barrel(m, 16, 63)
    ridge_ravens(m, roof, (22, 44), axis='z')
    return m


def senns_needlehouse():
    """Senn's Needlehouse: a timber tailor's shop on a stone footing, bolts of
    grey cloth in the window under an awning, a dress form on the step and a
    needle-and-thread sign. 6.5 x 6.5 x 6."""
    m = Model(74, 98, 76)
    stone_block(m, 8, 60, 0, 10, 10, 60, course=3, block=6, seed=46)
    timber_block(m, 8, 60, 10, 36, 10, 60, bay=10, rails=(), seed=58)
    timber_block(m, 7, 61, 36, 60, 9, 62, bay=11, rails=(48,), seed=59)
    roof = Gable(m, 7, 61, 9, 62, eave=60, rise=30, axis='z', over=3, seed=76)
    roof.build(lambda mask: timber_block(m, 7, 61, 58, 92, 9, 62, bay=11, rails=(74,), seed=60, where=mask))
    chimney(m, 48, 55, 16, 23, 50, 96, lean=1.0)

    window(m, '+z', 59, 12, 32, 15, 32, style='cloth')
    pent(m, 10, 35, 60, 37, 6, 4, colors=[CLOTH_PALE[0], CLOTH_PALE[1]])
    door(m, '+z', 59, 40, 50, 10, 31, arch=4)
    # Two stone steps up to the door, and the dress form beside them.
    stone_block(m, 38, 52, 0, 7, 60, 63, course=3, block=5, seed=47, quoins=False, moss_below=4)
    stone_block(m, 38, 52, 0, 3, 63, 66, course=3, block=5, seed=48, quoins=False, moss_below=3)
    m.beam((35, 0, 65), (35, 8, 65), 1, [WOOD_DARK[0]])
    m.ellipsoid((35, 12, 65), (2.4, 3.6, 1.8), CLOTH_PALE[0])
    m.ellipsoid((35, 16.5, 65), (1.0, 1.0, 1.0), WOOD[1])
    window(m, '+z', 61, 24, 36, 41, 54)
    window(m, '+z', 61, 31, 37, 66, 76)
    hanging_sign(m, 61, 46, 58, 'x', 1, needle_icon)
    lantern(m, 38, 22, 61)
    window(m, '+x', 60, 26, 34, 41, 54)
    window(m, '+x', 59, 30, 38, 16, 28)
    window(m, '-z', 9, 28, 36, 41, 54)
    window(m, '-x', 7, 26, 34, 41, 54)
    barrel(m, 12, 64)
    barrel(m, 17, 66)
    ridge_ravens(m, roof, (26,), axis='z')
    return m


def lantern_and_moth():
    """The Lantern & Moth: a timber shop over a heavy stone cellar storey, a
    stair up the front to the shop door, the cellar door under it, the moth
    sign with a shuttered lantern hung beneath. 5.5 x 5.5 x 5.5."""
    m = Model(70, 90, 70)
    stone_block(m, 8, 54, 0, 30, 6, 52, course=5, block=8, seed=49)
    timber_block(m, 7, 55, 30, 56, 5, 54, bay=12, rails=(43,), seed=61)
    roof = Gable(m, 7, 55, 5, 54, eave=56, rise=26, axis='z', over=3, seed=77)
    roof.build(lambda mask: timber_block(m, 7, 55, 54, 84, 5, 54, bay=12, rails=(68,), seed=62, where=mask))
    chimney(m, 42, 48, 12, 18, 46, 88, lean=1.0)

    door(m, '+z', 52, 16, 30, 0, 20, arch=7, frame=STONE[3])
    stair(m, 'z', 66, 53, 38, 50, 0, 30, base='stone', rail_side=37)
    door(m, '+z', 53, 40, 48, 30, 48)
    window(m, '+z', 53, 11, 34, 33, 50)
    pent(m, 9, 36, 54, 54, 4, 3)
    window(m, '+z', 53, 27, 35, 60, 70)
    hanging_sign(m, 52, 52, 54, 'z', 1, moth_icon)
    lantern(m, 52, 38, 64, hang=5)
    lantern(m, 56, 36, 30)
    window(m, '+x', 54, 24, 32, 35, 48)
    window(m, '+x', 54, 20, 28, 8, 15, style='bars')
    window(m, '-z', 5, 22, 30, 35, 48)
    window(m, '-x', 7, 22, 30, 35, 48)
    ridge_ravens(m, roof, (18,), axis='z')
    return m


def orras_hospice():
    """Saint Orra's Hospice: a long grey stone ward hall with lancet windows
    between buttresses, a gabled porch with the Orran Eye over the arched
    gate, a bell cote on the porch, and the low south wing with its chained
    doors. 10 x 10 x 11 on the sheet, sized to the hill's clearing here."""
    m = Model(138, 104, 112)
    nx0, nx1, nz0, nz1 = 10, 112, 24, 70
    stone_block(m, nx0, nx1, 0, 44, nz0, nz1, course=4, block=8, seed=80)
    nave = Gable(m, nx0, nx1, nz0, nz1, eave=44, rise=28, axis='x', over=3, seed=81)
    nave.build(lambda mask: stone_block(m, nx0, nx1, 40, 80, nz0, nz1, seed=82, quoins=False, where=mask))
    # Lancet windows between buttresses, front and back.
    for c in (18, 29, 40, 84, 95, 106):
        window(m, '+z', nz1, c - 3, c + 3, 12, 36, arch=5)
        window(m, '-z', nz0 - 1, c - 3, c + 3, 12, 36, arch=5)
    for b in (11, 23, 34, 78, 89, 100, 110):
        # Each buttress steps back halfway up.
        for low, high in (((nz1, nz1 + 4), (nz1, nz1 + 2)), ((nz0 - 4, nz0), (nz0 - 2, nz0))):
            stone_block(m, b - 1, b + 3, 0, 30, low[0], low[1], course=4, block=5, seed=83 + b, quoins=False)
            stone_block(m, b - 1, b + 3, 30, 48, high[0], high[1], course=4, block=5, seed=84 + b, quoins=False, moss_below=0)

    # The porch, gable to the front, with the Orran Eye and the gate.
    px0, px1, pz0, pz1 = 46, 76, 60, 90
    stone_block(m, px0, px1, 0, 54, pz0, pz1, course=4, block=7, seed=85)
    porch = Gable(m, px0, px1, pz0, pz1, eave=54, rise=22, axis='z', over=2, seed=86)
    porch.build(lambda mask: stone_block(m, px0, px1, 50, 80, pz0, pz1, seed=87, quoins=False, where=mask))
    door(m, '+z', pz1, 53, 69, 2, 34, arch=8, frame=STONE[3])
    m.fill(m.box(48, 0, pz1 + 1, 74, 2, pz1 + 5), STONE[3])
    m.fill(m.box(50, 0, pz1 + 5, 72, 1, pz1 + 9), STONE[1])
    # The Eye: an almond outline, the pupil, and the bar through it.
    ex, ey = 61.0, 64.0
    u, v = m.x - ex, m.y - ey
    almond = np.abs(np.abs(u / 8.0) ** 2 + np.abs(v / (3.8 * (1 - (u / 8.0) ** 2) + 0.3)) ** 2 - 1.0) < 0.35
    eye = ((almond & (np.abs(u) <= 8)) | (np.hypot(u, v) < 1.8) | ((np.abs(u) < 0.8) & (np.abs(v) < 8))) & (m.z == pz1)
    m.fill(m.box(51, 54, pz1, 72, 74, pz1 + 1) & (m.grid >= 0), STONE[2])
    m.fill(eye, PLASTER[2])
    # The bell cote on the porch's ridge, open through, with its bell and a cross.
    stone_block(m, 55, 67, 70, 90, 78, 88, course=3, block=5, seed=88, quoins=False, moss_below=0)
    m.clear(m.box(58, 76, 76, 64, 86, 90))
    m.ellipsoid((61, 80.5, 83), (2.4, 3.0, 2.4), BRASS[0])
    m.beam((61, 84, 83), (61, 86, 83), 1, [WOOD_DARK[0]])
    Gable(m, 54, 68, 77, 89, eave=90, rise=7, axis='z', over=1, seed=89).build()
    m.beam((61, 95, 83), (61, 99, 83), 1, [STONE[3]])
    m.beam((59, 97, 83), (63, 97, 83), 1, [STONE[3]])
    lantern(m, 50, 22, pz1 + 2)
    lantern(m, 72, 22, pz1 + 2)

    # The south wing, lower, its doors chained shut until Act II.
    wx0, wx1, wz0, wz1 = 112, 132, 30, 66
    stone_block(m, wx0, wx1, 0, 32, wz0, wz1, course=4, block=7, seed=90)
    Gable(m, wx0, wx1, wz0, wz1, eave=32, rise=20, axis='x', over=3, seed=91).build(
        lambda mask: stone_block(m, wx0, wx1, 30, 60, wz0, wz1, seed=92, quoins=False, where=mask))
    door(m, '+x', wx1, 40, 56, 0, 24, arch=7, chained=True, frame=STONE[3])
    window(m, '+z', wz1, 118, 124, 10, 24, style='bars', arch=3)
    # A rose window high in the west gable.
    rose = (m.x == nx0 - 1) & (np.hypot(m.z - 47, m.y - 54) < 5)
    m.fill(rose & (np.hypot(m.z - 47, m.y - 54) < 4), GLOW[0])
    m.fill(rose & ((np.abs(m.z - 47) < 0.6) | (np.abs(m.y - 54) < 0.6)), FRAME[0])

    # Red ivy climbing the front walls.
    column = m.x + m.y // 40
    reach = hash2(m.x // 3, 0, 93) * 40
    ivy = (m.grid >= 0) & (m.z >= nz1 - 1) & (m.z <= pz1 + 1) & (m.y < reach) & (hash2(m.x // 3, 1, 94) < 0.18) & (hash2(column, m.y, 95) < 0.45)
    # Only the outermost voxel of a wall carries ivy.
    ivy &= np.roll(m.grid, -1, axis=2) < 0
    ivy &= ~np.isin(m.grid, GLOW + [FRAME[0]] + WOOD + WOOD_DARK + IRON)
    m.fill(ivy, pick(IVY, hash2(m.x, m.y, 96)))
    ridge_ravens(m, nave, (24, 96))
    return m


def hobbs_mill():
    """Hobb's Mill: a stone-and-timber watermill, its undershot wheel on the
    river side (+x), an outside stair up the front where Lise stands, flour
    sacks, and the iron-banded millrace door low at the front. 5 x 5 x 6."""
    m = Model(82, 98, 80)
    stone_block(m, 10, 54, 0, 34, 14, 58, course=4, block=6, seed=100)
    timber_block(m, 9, 55, 34, 58, 13, 60, bay=11, rails=(46,), seed=101)
    roof = Gable(m, 9, 55, 13, 60, eave=58, rise=28, axis='z', over=3, seed=102)
    roof.build(lambda mask: timber_block(m, 9, 55, 56, 90, 13, 60, bay=11, rails=(72,), seed=103, where=mask))
    chimney(m, 40, 46, 18, 24, 50, 96)

    water_wheel(m, 26, 36, 23, 59, 67)
    m.fill(m.box(54, 24, 34, 59, 29, 39), WOOD_DARK[0])
    falling_water(m, 59, 67, 30, 42, 1, 9)
    # The stair along the front, up to the landing and the upper door.
    stair(m, 'x', 6, 34, 60, 68, 0, 34, base='stone', rail_side=67)
    m.fill(m.box(34, 32, 60, 50, 34, 69), planks(m.x.astype(float), m.y.astype(float), width=3))
    for x in range(34, 51, 4):
        m.beam((x, 34, 68), (x, 41, 68), 1, [WOOD_DARK[0]])
    m.beam((34, 41, 68), (50, 41, 68), 1, [WOOD[2]])
    pent(m, 32, 52, 60, 54, 8, 5)
    door(m, '+z', 59, 38, 46, 34, 50)
    door(m, '+z', 58, 40, 50, 0, 14)
    window(m, '+z', 59, 14, 24, 39, 52)
    window(m, '+z', 59, 28, 36, 64, 74)
    window(m, '+x', 54, 24, 32, 39, 52)
    window(m, '+x', 54, 46, 52, 12, 20, style='bars')
    window(m, '-z', 13, 24, 32, 39, 52)
    window(m, '-x', 9, 30, 38, 39, 52)
    window(m, '-x', 9, 22, 28, 12, 20, style='bars')
    for sx, sz in ((40, 72), (45, 73), (50, 71), (43, 76)):
        sack(m, sx, sz, lean=0.6)
    ridge_ravens(m, roof, (30,), axis='z')
    return m


RECIPES = {
    'RookeryTower': rookery_tower,
    'CrookedRaven': crooked_raven,
    'ReevesHall': reeves_hall,
    'PellsChandlery': pells_chandlery,
    'SennsNeedlehouse': senns_needlehouse,
    'LanternAndMoth': lantern_and_moth,
    'OrrasHospice': orras_hospice,
    'HobbsMill': hobbs_mill,
}


def build(name, preview):
    (grid,), palette = compact([RECIPES[name]().trimmed()])
    act1.write(act1.ASSETS / f'{name}.qvox', palette, grid, [])
    if preview:
        act1.save_preview(name, palette, grid, [])
    w, h, d = grid.shape
    print(f'{name}: {w} x {h} x {d}, {int((grid >= 0).sum())} voxels, {len(palette)} colors')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    for name in args.names or RECIPES:
        build(name, args.preview)


if __name__ == '__main__':
    main()
