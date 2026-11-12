"""A voxel kit for buildings and props: shapes built from parts, colored by materials.

act1.py cuts models out of two concept views. That works for figures, but a
building made that way is a box: two outlines cannot make a round tower round,
the sheet's painted light is baked into every voxel, and the back, which no view
shows, is a smear. Here a model is instead a recipe (see buildings.py): parts
such as a tapered round shaft, an octagonal roof or a plank wall, placed with
proportions measured off the sheet. Each part paints its voxels from a small
fixed palette of materials, with a pattern (stone courses, planks, shingles)
laid out at voxel scale, so the model reads cleanly from every side.

Grids are int arrays indexed [x, y, z] holding palette indexes, -1 for empty.
"""
import math

import numpy as np

# The shared palette, in sRGB. act1.write converts it to linear light.
COLORS = {}
PALETTE = []


def color(name, *shades):
    """Registers a material's shades. Returns their palette indexes."""
    if name not in COLORS:
        COLORS[name] = []
        for rgb in shades:
            COLORS[name].append(len(PALETTE))
            PALETTE.append(rgb)
    return COLORS[name]


STONE = color('stone', (104, 97, 87), (90, 84, 76), (78, 74, 68), (116, 108, 96), (86, 83, 78), (70, 66, 60))
MORTAR = color('mortar', (58, 55, 51))
GUANO = color('guano', (178, 174, 164), (204, 200, 190), (150, 146, 136), (128, 124, 116))
MOSS = color('moss', (78, 86, 54), (62, 70, 44), (92, 98, 62))
WOOD = color('wood', (96, 69, 46), (80, 57, 37), (66, 46, 30), (110, 82, 56))
WOOD_DARK = color('wood dark', (46, 33, 24), (36, 26, 19))
WOOD_LIT = color('wood lit', (150, 98, 52), (128, 82, 44))
SHINGLE = color('shingle', (74, 66, 60), (60, 54, 49), (88, 78, 68), (50, 45, 41))
GLOW = color('glow', (255, 184, 82), (236, 140, 50), (170, 92, 36))
FRAME = color('frame', (34, 27, 21))
RAVEN = color('raven', (24, 24, 29), (38, 38, 46), (58, 56, 52))
BRASS = color('brass', (150, 116, 58), (112, 84, 40))
SOOT = color('soot', (42, 40, 38))
PLASTER = color('plaster', (132, 122, 108), (120, 111, 98), (142, 132, 116), (108, 101, 91))
IRON = color('iron', (58, 58, 62), (82, 80, 80))
PAPER = color('paper', (206, 194, 166), (184, 172, 146))
CLOTH_RED = color('cloth red', (128, 34, 30), (100, 26, 24))
CLOTH_PALE = color('cloth pale', (196, 186, 164), (170, 162, 144))
CLOTH_GREY = color('cloth grey', (104, 104, 106), (84, 84, 88))
CANDLE = color('candle', (232, 218, 182))
BURLAP = color('burlap', (162, 136, 98), (140, 116, 82))
WATER = color('water', (150, 176, 186), (200, 216, 220), (88, 110, 120))
IVY = color('ivy', (122, 34, 26), (92, 28, 22), (66, 72, 38))


def hash2(a, b, seed=0):
    """A repeatable pseudo-random value in [0, 1) per integer cell, elementwise."""
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    h = (a * 374761393 + b * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65536.0


def pick(shades, value):
    """One of a material's shades for each value in [0, 1)."""
    shades = np.asarray(shades)
    return shades[np.minimum((np.asarray(value) * len(shades)).astype(int), len(shades) - 1)]


class Model:
    def __init__(self, width, height, depth):
        self.grid = np.full((width, height, depth), -1, dtype=np.int32)
        self.x, self.y, self.z = np.meshgrid(np.arange(width), np.arange(height), np.arange(depth), indexing='ij')

    def fill(self, where, colors):
        """Sets voxels where `where` holds; colors is an index or a full grid of them."""
        if np.isscalar(colors) or np.ndim(colors) == 0:
            self.grid[where] = int(colors)
        else:
            self.grid[where] = colors[where]

    def clear(self, where):
        self.grid[where] = -1

    def box(self, x0, y0, z0, x1, y1, z1):
        """A mask of the box from (x0, y0, z0) up to but not including (x1, y1, z1)."""
        return (self.x >= x0) & (self.x < x1) & (self.y >= y0) & (self.y < y1) & (self.z >= z0) & (self.z < z1)

    def beam(self, start, end, thickness, colors):
        """A straight timber or perch: stamps a cube of `thickness` along the line."""
        start, end = np.array(start, float), np.array(end, float)
        steps = int(np.ceil(np.abs(end - start).max())) + 1
        half = thickness / 2.0
        w, h, d = self.grid.shape
        for t in np.linspace(0.0, 1.0, steps):
            p = start + (end - start) * t
            lo = np.floor(p - half + 0.5).astype(int)
            hi = lo + thickness
            lo = np.maximum(lo, 0)
            hi = np.minimum(hi, (w, h, d))
            if np.any(hi <= lo):
                continue
            shade = colors[int(t * 7.0) % len(colors)] if len(colors) > 1 else colors[0]
            self.grid[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = shade

    def ellipsoid(self, center, radii, colors):
        cx, cy, cz = center
        rx, ry, rz = radii
        mask = ((self.x - cx) / rx) ** 2 + ((self.y - cy) / ry) ** 2 + ((self.z - cz) / rz) ** 2 <= 1.0
        self.fill(mask, colors)
        return mask

    def trimmed(self):
        """The grid cut to its solid bounds."""
        xs, ys, zs = np.nonzero(self.grid >= 0)
        return self.grid[xs.min():xs.max() + 1, :ys.max() + 1, zs.min():zs.max() + 1]


# Patterns. Each returns a grid of palette indexes for the given coordinates,
# to be applied with Model.fill under a shape's mask.

def stone_courses(along, y, course=4, block=8, seed=1, shades=STONE):
    """Ashlar courses: rows `course` high, blocks `block` long, staggered.
    `along` is the distance along the wall. Returns (colors, mortar, block id)."""
    row = np.floor(y / course).astype(int)
    shifted = along + (row % 2) * (block / 2.0)
    col = np.floor(shifted / block).astype(int)
    mortar = (y % course == course - 1) | ((shifted % block) < 1.0)
    colors = pick(shades, hash2(row, col, seed))
    colors = np.where(mortar, MORTAR[0], colors)
    return colors, mortar, (row, col)


def planks(along, y, width=3, seed=2, shades=WOOD, vertical=True):
    """Boards `width` wide; vertical boards run up, horizontal ones run along."""
    lane = np.floor((along if vertical else y) / width).astype(int)
    grain = hash2(lane, np.floor((y if vertical else along) / 9).astype(int), seed)
    colors = pick(shades, hash2(lane, 0, seed) * 0.7 + grain * 0.3)
    seam = (along if vertical else y) % width < 0.6
    return np.where(seam, WOOD_DARK[0], colors)


def shingles(along, row_y, width=4, seed=3):
    """Roof shingles in rows, each row's lower edge in shadow, with moss patches."""
    row = np.floor(row_y).astype(int)
    col = np.floor((along + (row % 2) * width / 2.0) / width).astype(int)
    colors = pick(SHINGLE[:3], hash2(row, col, seed))
    edge = (row_y - row) < 0.34
    colors = np.where(edge, SHINGLE[3], colors)
    moss = hash2(row // 2, col // 3, seed + 7) < 0.22
    return np.where(moss & ~edge, pick(MOSS, hash2(row, col, seed + 1)), colors)


def octagon_distance(dx, dz):
    """Distance to the center in the octagon metric (the octagon's apothem)."""
    a = np.abs(dx)
    b = np.abs(dz)
    return np.maximum(np.maximum(a, b), (a + b) / math.sqrt(2.0))


def octagon_corners(center, radius, turn=0.0):
    """The corners of an octagon with the given apothem, as (x, z) pairs."""
    cx, cz = center
    corner = radius / math.cos(math.pi / 8.0)
    return [(cx + corner * math.cos(turn + math.pi / 8.0 + k * math.pi / 4.0),
             cz + corner * math.sin(turn + math.pi / 8.0 + k * math.pi / 4.0)) for k in range(8)]


def raven(model, at, facing, sitting=True):
    """A perched raven, about 7 voxels tall, at the point its feet stand on.
    facing is the angle in the xz plane it looks toward."""
    x, y, z = at
    fx, fz = math.cos(facing), math.sin(facing)
    model.ellipsoid((x - fx * 0.5, y + 2.6, z - fz * 0.5), (2.0, 2.4, 2.0), RAVEN[0])
    model.ellipsoid((x + fx * 1.2, y + 5.0, z + fz * 1.2), (1.3, 1.3, 1.3), RAVEN[1])
    # Tail and beak.
    model.beam((x - fx * 2.4, y + 2.0, z - fz * 2.4), (x - fx * 3.6, y + 1.0, z - fz * 3.6), 1, [RAVEN[0]])
    model.beam((x + fx * 2.2, y + 5.0, z + fz * 2.2), (x + fx * 3.0, y + 4.6, z + fz * 3.0), 1, [RAVEN[2]])
