"""House parts for buildings.py: walls, gable roofs, openings, chimneys, stairs
and dressing. All sizes are in voxels (a sixteenth of a unit); +Z is the front,
which the camera sees together with +X and the roofs.

Openings and signs go on a face, named '+z', '-z', '+x' or '-x', at the
face's outermost layer `at`. Along a face, u runs along x for z faces and
along z for x faces.
"""
import math

import numpy as np

from kit import (BRASS, BURLAP, CANDLE, CLOTH_GREY, FRAME, GLOW, IRON, MORTAR, MOSS, PAPER, PLASTER, SHINGLE, SOOT, STONE,
                 WATER, WOOD, WOOD_DARK, hash2, pick, planks, shingles, stone_courses)


def face_layer(m, side, at, inset=0):
    """The 2D slice of one face layer, indexed [u, y]: a view that can be assigned."""
    step = -1 if side[0] == '+' else 1
    layer = at + step * inset
    if side[1] == 'z':
        return m.grid[:, :, layer]
    return m.grid[layer, :, :].T


def local(u0, u1, y0, y1):
    return np.meshgrid(np.arange(u0, u1), np.arange(y0, y1), indexing='ij')


# Walls.

def wall_along(m, x0, x1, z0, z1):
    """For each voxel, its distance along whichever wall face is nearest."""
    near_x = np.minimum(np.abs(m.x - x0), np.abs(m.x - (x1 - 1)))
    near_z = np.minimum(np.abs(m.z - z0), np.abs(m.z - (z1 - 1)))
    return np.where(near_z <= near_x, m.x, m.z).astype(float), near_z <= near_x


def stone_block(m, x0, x1, y0, y1, z0, z1, course=4, block=7, seed=40, quoins=True, moss_below=10, where=None):
    """A solid stone mass with relief: about half the blocks stand a voxel proud."""
    along, _ = wall_along(m, x0, x1, z0, z1)
    colors, mortar, (row, col) = stone_courses(along, m.y.astype(float), course, block, seed)
    core = m.box(x0, y0, z0, x1, y1, z1)
    shell = m.box(x0 - 1, y0, z0 - 1, x1 + 1, y1, z1 + 1) & ~core
    proud = shell & ~mortar & (hash2(row, col, seed + 1) < 0.5)
    if quoins:
        corner = (np.minimum(np.abs(m.x - x0), np.abs(m.x - (x1 - 1))) < 3) & (np.minimum(np.abs(m.z - z0), np.abs(m.z - (z1 - 1))) < 3)
        big = (row % 2 == 0)
        colors = np.where(corner & ~mortar & big, STONE[3], colors)
    low = (m.y < y0 + moss_below) & (hash2(col, row, seed + 2) * moss_below > (m.y - y0))
    colors = np.where(low, pick(MOSS, hash2(row, col, seed + 3)), colors)
    mask = core | proud
    if where is not None:
        mask &= where
    m.fill(mask, colors)


def timber_block(m, x0, x1, y0, y1, z0, z1, bay=12, rails=(), seed=50, where=None):
    """A timber-framed mass: plaster panels between dark posts, with a rail at
    each height in rails and a brace across every other panel."""
    along, z_face = wall_along(m, x0, x1, z0, z1)
    yf = m.y.astype(float)
    plaster = pick(PLASTER, hash2(np.floor(along / 3).astype(int), m.y // 3, seed) * 0.6 + hash2(m.x // 7, m.z // 7, seed + 1) * 0.4)
    along = along - np.where(z_face, x0, z0)
    post = along % bay < 2
    corner = (np.minimum(np.abs(m.x - x0), np.abs(m.x - (x1 - 1))) < 2) & (np.minimum(np.abs(m.z - z0), np.abs(m.z - (z1 - 1))) < 2)
    edges = (yf < y0 + 2) | (yf >= y1 - 2)
    for r in rails:
        edges |= (yf >= r) & (yf < r + 2)
    # Braces: one diagonal per panel, alternating, across the panel's own height.
    panel = np.floor(along / bay).astype(int)
    pu = (along % bay) / bay
    tops = [y0] + sorted(rails) + [y1]
    brace = np.zeros(m.grid.shape, dtype=bool)
    for lo, hi in zip(tops[:-1], tops[1:]):
        pv = (yf - lo) / max(1.0, hi - lo)
        inside = (yf >= lo) & (yf < hi)
        line = np.where(panel % 2 == 0, pu, 1.0 - pu)
        brace |= inside & (np.abs(line - pv) * bay < 1.1) & (hash2(panel, int(lo), seed + 2) < 0.55)
    frame = post | corner | edges | brace
    colors = np.where(frame, np.where(hash2(panel, m.y // 9, seed + 3) < 0.5, WOOD_DARK[0], WOOD[2]), plaster)
    mask = m.box(x0, y0, z0, x1, y1, z1)
    if where is not None:
        mask &= where
    m.fill(mask, colors)


def plank_block(m, x0, x1, y0, y1, z0, z1, seed=60, where=None):
    along, _ = wall_along(m, x0, x1, z0, z1)
    mask = m.box(x0, y0, z0, x1, y1, z1)
    if where is not None:
        mask &= where
    m.fill(mask, planks(along, m.y.astype(float), width=3, seed=seed))


# Roofs.

class Gable:
    """A gable roof over the box x0..x1, z0..z1 whose eaves sit at `eave` and
    ridge `rise` higher, running along `axis` ('x' or 'z'). `over` is the
    overhang and `sag` drops the middle of the ridge."""

    def __init__(self, m, x0, x1, z0, z1, eave, rise, axis='x', over=3, sag=0.0, thick=2.5, seed=70):
        self.m = m
        if axis == 'x':
            across, a0, a1, along, b0, b1 = m.z, z0, z1, m.x, x0, x1
        else:
            across, a0, a1, along, b0, b1 = m.x, x0, x1, m.z, z0, z1
        mid = (a0 + a1 - 1) / 2.0
        half = (a1 - a0) / 2.0
        self.off = np.abs(across - mid)
        t = np.clip((along - b0) / max(1, b1 - b0 - 1), 0.0, 1.0)
        up = np.clip((half + over - self.off) / (half + over), 0.0, 1.0)
        self.line = eave + up * rise - sag * np.sin(math.pi * t) * up
        reach = (self.off <= half + over) & (along >= b0 - over) & (along < b1 + over)
        yf = m.y.astype(float)
        self.shell = reach & (yf >= self.line - thick) & (yf < self.line)
        self.under = (self.off < half) & (along >= b0) & (along < b1) & (yf >= eave - 1) & (yf < self.line - thick + 0.5)
        colors = shingles(along.astype(float), (half + over - self.off) / 2.2, width=3, seed=seed)
        colors = np.where(self.off < 1.3, WOOD_DARK[1], colors)
        ends = (along < b0 - over + 1) | (along >= b1 + over - 1)
        colors = np.where(ends, WOOD_DARK[0], colors)
        self.colors = colors

    def build(self, under=None):
        """Fills the gable ends and attic with `under` (a function taking a mask),
        then lays the roof over them."""
        if under is not None:
            under(self.under)
        self.m.fill(self.shell, self.colors)
        return self


# Openings.

def window(m, side, at, u0, u1, y0, y1, style='lattice', arch=0, frame=FRAME[0]):
    """A lit window recessed one voxel, framed. style is lattice, bars, panes,
    candles (a shop window of hanging candles) or dark."""
    u, y = local(u0, u1, y0, y1)
    shape = np.ones(u.shape, dtype=bool)
    if arch:
        mid = (u0 + u1 - 1) / 2.0
        half = (u1 - u0) / 2.0
        top = y1 - arch
        shape = (y < top) | (np.abs(u - mid) <= half * np.sqrt(np.clip(1 - ((y - top + 0.5) / arch) ** 2, 0, 1)))
    glow = np.where(hash2(u, y // 2, 81) < 0.55, GLOW[0], GLOW[1])
    if style == 'lattice':
        bars = ((u + y) % 5 == 0) | ((u - y) % 5 == 0)
    elif style == 'bars':
        bars = (u - u0) % 3 == 1
    elif style == 'panes':
        bars = ((u - u0) % 4 == 3) | ((y - y0) % 5 == 4)
    elif style == 'cloth':
        # Bolts of grey cloth stacked in the lower half, lamplight above.
        bars = np.zeros(u.shape, dtype=bool)
        low = y < y0 + (y1 - y0) * 0.55
        glow = np.where(low, np.where((y - y0) % 3 == 2, FRAME[0], np.where((u // 5) % 2 == 0, CLOTH_GREY[0], CLOTH_GREY[1])), glow)
    elif style == 'candles':
        bars = np.zeros(u.shape, dtype=bool)
        hanging = ((u - u0) % 3 == 1) & (y >= y0 + 2) & (y < y1 - 2) & (hash2(u, 0, 82) * (y1 - y0) < (y1 - y) + 2)
        glow = np.where(hanging, CANDLE[0], glow)
    else:
        bars = np.zeros(u.shape, dtype=bool)
        glow = np.full(u.shape, FRAME[0])
    outer = face_layer(m, side, at)
    inner = face_layer(m, side, at, 1)
    border_u, border_y = local(u0 - 1, u1 + 1, y0 - 1, y1 + 1)
    ring = np.ones(border_u.shape, dtype=bool)
    ring[1:-1, 1:-1] = ~shape
    region = outer[u0 - 1:u1 + 1, y0 - 1:y1 + 1]
    region[ring & (region >= 0)] = frame
    region[ring & (border_y == y0 - 1)] = frame
    o = outer[u0:u1, y0:y1]
    # Only bars stand in the outer layer, so the glow behind shows at an angle.
    o[shape] = np.where(bars & (style == 'bars'), frame, -1)[shape]
    i = inner[u0:u1, y0:y1]
    i[shape] = np.where(bars & (style != 'bars'), frame, glow)[shape]


def door(m, side, at, u0, u1, y0, y1, arch=0, bands=True, chained=False, frame=FRAME[0]):
    """A plank door set back one voxel under an optional round arch, with iron bands."""
    u, y = local(u0, u1, y0, y1)
    shape = np.ones(u.shape, dtype=bool)
    if arch:
        mid = (u0 + u1 - 1) / 2.0
        half = (u1 - u0) / 2.0
        top = y1 - arch
        shape = (y < top) | (np.abs(u - mid) <= half * np.sqrt(np.clip(1 - ((y - top + 0.5) / arch) ** 2, 0, 1)))
    boards = np.where((u - u0) % 3 == 0, WOOD_DARK[0], np.where(hash2(u, 0, 83) < 0.5, WOOD[1], WOOD[2]))
    if bands:
        boards = np.where(((y - y0) % 7 == 3), IRON[0], boards)
    if chained:
        mid = (u0 + u1 - 1) / 2.0
        chain = (np.abs(np.abs(u - mid) - (y - y0) * 0.6 + (y1 - y0) * 0.25) < 0.8) & (y > y0 + 3)
        boards = np.where(chain & ((u + y) % 2 == 0), IRON[1], boards)
        boards = np.where(chain & ((u + y) % 2 == 1), IRON[0], boards)
    outer = face_layer(m, side, at)
    inner = face_layer(m, side, at, 1)
    o = outer[u0:u1, y0:y1]
    o[shape] = -1
    i = inner[u0:u1, y0:y1]
    i[shape] = boards[shape]
    if chained:
        o[shape & chain] = IRON[0]
        lock = (np.abs(u - (u0 + u1 - 1) / 2.0) < 1.5) & (np.abs(y - (y0 + (y1 - y0) * 0.45)) < 1.5)
        o[lock] = BRASS[1]
    # Frame around the sides and top.
    region = outer[u0 - 1:u1 + 1, y0:y1 + 1]
    bu, by = local(u0 - 1, u1 + 1, y0, y1 + 1)
    edge = np.ones(bu.shape, dtype=bool)
    edge[1:-1, :-1] = ~shape
    region[edge & (region >= 0)] = frame


def chimney(m, x0, x1, z0, z1, y0, y1, lean=0.0, seed=90):
    """A stone stack, open at the top with a sooty cap; lean shifts it along x."""
    yf = m.y.astype(float)
    shift = np.round(np.clip(yf - y0, 0, None) / max(1, y1 - y0) * lean)
    xs = m.x - shift
    colors = stone_courses((xs + m.z).astype(float), yf, course=3, block=5, seed=seed)[0]
    body = (xs >= x0) & (xs < x1) & (m.z >= z0) & (m.z < z1) & (m.y >= y0) & (m.y < y1)
    cap = (xs >= x0 - 1) & (xs < x1 + 1) & (m.z >= z0 - 1) & (m.z < z1 + 1) & (m.y >= y1 - 3) & (m.y < y1 - 1)
    m.fill(body, np.where(m.y >= y1 - 4, SOOT[0], colors))
    m.fill(cap, STONE[3])
    m.fill((xs > x0) & (xs < x1 - 1) & (m.z > z0) & (m.z < z1 - 1) & (m.y >= y1 - 4) & (m.y < y1), -1)


def stair(m, axis, a_start, a_end, b0, b1, y_bottom, y_top, base='stone', rail_side=None, seed=95):
    """A straight outside stair climbing along `axis` from a_start (at y_bottom)
    to a_end (at y_top), b0..b1 wide across. base fills under the treads with
    stone or leaves wooden stringers. rail_side is the across edge for a rail."""
    along, across = (m.x, m.z) if axis == 'x' else (m.z, m.x)
    lo, hi = min(a_start, a_end), max(a_start, a_end)
    t = np.clip((along - a_start) / (a_end - a_start), 0.0, 1.0)
    step = y_bottom + np.floor(t * (y_top - y_bottom) / 2.0 + 1.0) * 2.0
    inside = (along >= lo) & (along < hi) & (across >= b0) & (across < b1)
    yf = m.y.astype(float)
    treads = inside & (yf < step) & (yf >= step - 2)
    m.fill(treads, np.where(hash2(along // 3, across // 4, seed) < 0.5, WOOD[0], WOOD[3]) if base == 'wood' else STONE[3])
    if base == 'stone':
        below = inside & (yf < step - 2) & (yf >= y_bottom)
        m.fill(below, stone_courses((along + across).astype(float), yf, course=3, block=5, seed=seed)[0])
    else:
        stringer = inside & ((across == b0) | (across == b1 - 1)) & (yf < step) & (yf >= step - 5)
        m.fill(stringer, WOOD_DARK[0])
    if rail_side is not None:
        n = int(abs(a_end - a_start))
        for s in range(0, n + 1, 4):
            a = a_start + (s if a_end > a_start else -s)
            h = y_bottom + (s / n) * (y_top - y_bottom) + 1
            p = (a, rail_side) if axis == 'x' else (rail_side, a)
            m.beam((p[0], h, p[1]), (p[0], h + 7, p[1]), 1, [WOOD_DARK[0]])
        if axis == 'x':
            m.beam((a_start, y_bottom + 8, rail_side), (a_end, y_top + 8, rail_side), 1, [WOOD[2]])
        else:
            m.beam((rail_side, y_bottom + 8, a_start), (rail_side, y_top + 8, a_end), 1, [WOOD[2]])


def pent(m, x0, x1, z_wall, y_top, depth, drop, colors=None):
    """A lean-to roof strip off the +z wall along x: from y_top at the wall down
    by drop over depth voxels. colors defaults to shingles."""
    for x in range(x0, x1):
        shade = colors[(x // 3) % len(colors)] if colors else SHINGLE[(x // 3 + x // 7) % 3]
        m.beam((x, y_top, z_wall), (x, y_top - drop, z_wall + depth), 1, [shade])
        m.grid[x, int(y_top - drop) - 1, z_wall + depth] = WOOD_DARK[0]


# Dressing.

def hanging_sign(m, x, y, z, out_axis, out_sign, icon):
    """A bracket from the wall at (x, y, z) reaching out along out_axis, with a
    board hung from it by two chains. icon is a function (u, v) -> mask in
    board coordinates 0..1 for the pale painted figure."""
    d = np.array([1.0, 0.0, 0.0]) if out_axis == 'x' else np.array([0.0, 0.0, 1.0])
    d *= out_sign
    start = np.array([x, y, z], float)
    end = start + d * 13
    m.beam(start, end, 2, [WOOD_DARK[0]])
    m.beam(start + d * 2 - np.array([0, 6, 0]), start + d * 8, 1, [WOOD_DARK[0]])
    for k in (5, 11):
        p = start + d * k
        m.beam(p - np.array([0, 2, 0]), p - np.array([0, 1, 0]), 1, [IRON[0]])
    # The board stands in the plane of the bracket, 9 wide and 8 tall.
    top = y - 3
    for i in range(9):
        for j in range(8):
            p = start + d * (3.5 + i)
            v = j / 7.0
            u = i / 8.0
            edge = i in (0, 8) or j in (0, 7)
            c = WOOD_DARK[0] if edge else (PAPER[1] if icon(u, v) else WOOD[1])
            xi, yi, zi = int(round(p[0])), int(top - j), int(round(p[2]))
            if 0 <= xi < m.grid.shape[0] and 0 <= zi < m.grid.shape[2]:
                m.grid[xi, yi, zi] = c


def lantern(m, x, y, z, hang=0):
    """A small iron lantern, 3 wide and 4 tall, glowing, optionally hung below a chain."""
    if hang:
        m.beam((x, y + 4, z), (x, y + 4 + hang, z), 1, [IRON[0]])
    m.grid[x - 1:x + 2, y:y + 4, z - 1:z + 2] = IRON[0]
    m.grid[x - 1:x + 2, y + 1:y + 3, z - 1:z + 2] = GLOW[0]
    m.grid[x, y + 1:y + 3, z] = GLOW[1]


def barrel(m, x, z, y=0, r=2.6, h=7):
    yy = m.y - y
    ring = np.hypot(m.x - x, m.z - z)
    bulge = r + 0.5 * np.sin(np.clip(yy / h, 0, 1) * math.pi)
    body = (ring <= bulge) & (yy >= 0) & (yy < h)
    m.fill(body, np.where((yy == 1) | (yy == h - 2), IRON[0], np.where(hash2(np.floor(np.arctan2(m.z - z, m.x - x) * 3).astype(int), 0, 97) < 0.5, WOOD[0], WOOD[1])))


def sack(m, x, z, y=0, lean=0.0):
    m.ellipsoid((x, y + 2.5, z), (2.8, 3.0, 2.4), BURLAP[0])
    m.ellipsoid((x + lean, y + 5.6, z), (1.2, 1.2, 1.0), BURLAP[1])


def water_wheel(m, cy, cz, radius, x0, x1, spokes=8):
    """An undershot wheel turning on an axle along x, between x0 and x1."""
    dy, dz = m.y - cy, m.z - cz
    r = np.hypot(dy, dz)
    ang = np.arctan2(dy, dz)
    band = (m.x >= x0) & (m.x < x1)
    rim = band & (((m.x == x0) | (m.x == x1 - 1)) & (r <= radius) & (r > radius - 2.5))
    m.fill(rim, np.where(hash2(np.floor(ang * 6).astype(int), 0, 98) < 0.5, WOOD[1], WOOD[0]))
    paddles = band & (r <= radius + 2) & (r > radius - 4) & (np.abs(np.angle(np.exp(1j * (ang * 16)))) < 0.35)
    m.fill(paddles, WOOD[2])
    for k in range(spokes):
        a = k * 2 * math.pi / spokes
        for xx in (x0, x1 - 1):
            m.beam((xx, cy, cz), (xx, cy + math.sin(a) * (radius - 1), cz + math.cos(a) * (radius - 1)), 1, [WOOD[3]])
    hub = (m.x >= x0 - 3) & (m.x < x1 + 1) & (r <= 2.6)
    m.fill(hub, IRON[0])
    m.fill(band & (r <= 4) & ((m.x == x0) | (m.x == x1 - 1)), WOOD_DARK[0])


def falling_water(m, x0, x1, z0, z1, y0, y1, seed=99):
    """Sparse pale streaks of water pouring down, and a splash at the foot."""
    streak = m.box(x0, y0, z0, x1, y1, z1) & (hash2(m.x, m.z, seed) < 0.45) & (hash2(m.x * 7 + m.z, m.y // 3, seed + 1) < 0.8)
    m.fill(streak, pick(WATER[:2], hash2(m.x, m.y, seed + 2)))
    m.fill(m.box(x0 - 3, 0, z0 - 4, x1 + 3, 1, z1 + 4), pick(WATER, hash2(m.x, m.z, seed + 3)))
