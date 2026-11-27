"""Act II's Hospice Road and Thornmere props: recipes built from kit.py, house.py
and camp.py parts, as buildings.py's are. 0.0625-unit voxels, +Z toward the
camera. act2.MODELS lists each one, so inspect_models.py scores it against its
sheet in Assets/Reference/Act2.

    python Tools/Models/road.py                        build every recipe
    python Tools/Models/road.py RoadGibbet --preview   build some, with renders
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buildings  # noqa: E402
from camp import cloth_drape, hooped_cover, iron_lantern, plank_box, studs, wheel  # noqa: E402
from kit import (CLOTH_GREY, CLOTH_PALE, DYE_RED, FELT, IRON, MOSS, MUD, ROPE, SOOT, STONE, WATER, WOOD,  # noqa: E402
                 WOOD_DARK, CANVAS, CANVAS_OILED, Model, hash2, pick)
from house import stone_block  # noqa: E402


def timber(m, x0, x1, y0, y1, z0, z1, seed):
    """A squared beam: dark grain running along its longest side, iron-dark
    checks where it has split."""
    size = (x1 - x0, y1 - y0, z1 - z0)
    run = 'xyz'[int(np.argmax(size))]
    across = 'y' if run != 'y' else 'x'
    plank_box(m, x0, x1, y0, y1, z0, z1, seed, run=run, across=across, width=2)
    axes = {'x': m.x, 'y': m.y, 'z': m.z}
    split = m.box(x0, y0, z0, x1, y1, z1) & (hash2(axes[run] // 5, axes[across], seed + 1) < 0.06)
    m.fill(split, WOOD_DARK[1])


def iron_band(m, x0, x1, y0, y1, z0, z1):
    """An iron strap round a beam, a voxel proud, with rivet heads."""
    band = m.box(x0 - 1, y0, z0 - 1, x1 + 1, y1, z1 + 1) & ~m.box(x0, y0, z0, x1, y1, z1)
    m.fill(band, np.where(hash2(m.x + m.z, m.y, 600) < 0.2, IRON[1], IRON[0]))


def post(m, cx, cz, top, half=2, seed=610, bands=(14, 40)):
    """An upright gallows post on a foot of fieldstone, braced by four
    diagonal struts, iron bands round it."""
    stone_block(m, cx - half - 4, cx + half + 5, 0, 5, cz - half - 3, cz + half + 4, course=2, block=4, seed=seed, moss_below=3)
    timber(m, cx - half, cx + half + 1, 4, top, cz - half, cz + half + 1, seed + 1)
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        m.beam((cx + dx * 6, 5, cz + dz * 4), (cx + dx * (half + 0.5), 15, cz + dz * (half + 0.5)), 2, [WOOD[1], WOOD[2]])
    for y in bands:
        iron_band(m, cx - half, cx + half + 1, y, y + 2, cz - half, cz + half + 1)


def banner(m, x, top, z, length, seed):
    """A ragged madder banner with a pale cross hung from a beam."""
    cloth_drape(m, x - 2, x + 3, z, top, length, DYE_RED, seed, mark=CLOTH_PALE[1])


def noose(m, x, top, z, drop):
    """A rope from a beam to a loop."""
    m.beam((x, top, z), (x, top - drop, z), 1, [ROPE[0], ROPE[1]])
    m.fill((np.abs(np.hypot(m.x - x, m.y - (top - drop - 2.5)) - 2.0) < 0.7) & (m.z == z), ROPE[1])
    m.fill(m.box(x - 1, top - drop, z - 1, x + 2, top - drop + 2, z + 2), ROPE[0])


def hanged(m, x, top, z, seed):
    """A hooded body in grey pilgrim wool hung from a rope, head lolled to
    one side, a red tithe cloth at the waist, bare grey feet."""
    yf = m.y.astype(float)
    m.beam((x, top, z - 4), (x, top - 3, z), 1, [ROPE[0], ROPE[1]])
    m.beam((x, top - 3, z), (x, top - 6, z), 1, [ROPE[0], ROPE[1]])
    head_y = top - 9
    m.ellipsoid((x + 0.8, head_y, z), (2.6, 3.0, 2.6), FELT[1])
    m.fill((np.hypot(m.x - x - 1.2, m.z - z - 1.6) < 1.6) & (np.abs(yf - head_y + 0.5) < 1.6), SOOT[0])
    robe_r = 2.8 + np.clip(head_y - 3 - yf, 0, None) * 0.12
    body = (np.hypot(m.x - x, (m.z - z) * 1.25) <= robe_r) & (yf < head_y - 2) & (yf > head_y - 25 + hash2(m.x, m.z, seed) * 3)
    m.fill(body, pick([CLOTH_GREY[1], FELT[1], CLOTH_GREY[0]], hash2(m.x, m.y // 3, seed + 1)))
    m.fill(body & (np.abs(yf - (head_y - 12)) < 1.0), ROPE[1])
    m.fill(body & (yf < head_y - 13) & (yf > head_y - 20) & (m.z > z) & (np.abs(m.x - x) < 1.5), DYE_RED[1])
    for dx in (-1, 1):
        m.beam((x + dx, head_y - 25, z), (x + dx, head_y - 28, z + 0.5), 1, [CLOTH_PALE[1]])


def road_gibbet():
    """A gibbet by the Hospice Road: a stout post on a stone foot, braced, a
    beam across its top with a hooded pilgrim hanged in front of the post and a
    madder banner with a pale cross from each end. 36 x 61 x 14 voxels."""
    m = Model(38, 66, 20)
    cx, cz = 18, 9
    post(m, cx, cz, 58, seed=620, bands=(16, 44))
    timber(m, 1, 37, 56, 60, cz - 1, cz + 2, 621)
    for side in (-1, 1):
        m.beam((cx + side * 1, 46, cz), (cx + side * 9, 56, cz), 2, [WOOD[1], WOOD[2]])
        iron_band(m, cx + side * 12, cx + side * 12 + 2, 56, 60, cz - 1, cz + 2) if side > 0 else iron_band(m, cx - 13, cx - 11, 56, 60, cz - 1, cz + 2)
    iron_band(m, cx - 2, cx + 3, 55, 61, cz - 1, cz + 2)
    banner(m, 3, 55, cz + 2, 18, 622)
    banner(m, 34, 55, cz + 2, 15, 623)
    hanged(m, cx, 55, cz + 6, 624)
    return m


def road_gibbet_empty():
    """An empty gibbet: two braced posts and a beam across them, two nooses
    hanging, torn madder rags wound round the posts. 58 x 61 x 13 voxels."""
    m = Model(58, 66, 20)
    cz = 9
    for cx in (6, 51):
        post(m, cx, cz, 58, seed=630 + cx, bands=(14, 40))
        for y in (22, 41):
            m.fill(m.box(cx - 3, y, cz - 3, cx + 4, y + 3 + int(hash2(cx, y, 631) * 3), cz + 4) & ~m.box(cx - 2, 0, cz - 2, cx + 3, 99, cz + 3) & (hash2(m.x, m.y + m.z, 632) < 0.8),
                   pick(DYE_RED + [CLOTH_GREY[1]], hash2(m.x + m.z, m.y, 633)))
    timber(m, 1, 57, 56, 60, cz - 1, cz + 2, 634)
    for cx, side in ((6, 1), (51, -1)):
        m.beam((cx + side * 2, 46, cz), (cx + side * 10, 56, cz), 2, [WOOD[1], WOOD[2]])
        iron_band(m, cx - 2, cx + 3, 55, 61, cz - 1, cz + 2)
    noose(m, 22, 55, cz + 2, 12)
    noose(m, 36, 55, cz + 2, 16)
    cloth_drape(m, 13, 17, cz + 2, 55, 9, DYE_RED, 635)
    return m


def tilted(src, pitch, roll, drop):
    """src's grid turned `pitch` degrees about x (its +Z end down) and `roll`
    about z, then sunk `drop` voxels, as a cart nose-down in the shallows."""
    w, h, d = src.grid.shape
    # Room above for the end that rises.
    out = Model(w, h + int(d * math.sin(math.radians(abs(pitch))) * 0.6) + 2, d)
    c = np.array([w / 2.0, 0.0, d / 2.0])
    a, b = math.radians(pitch), math.radians(roll)
    rx = np.array([[1, 0, 0], [0, math.cos(a), math.sin(a)], [0, -math.sin(a), math.cos(a)]])
    rz = np.array([[math.cos(b), -math.sin(b), 0], [math.sin(b), math.cos(b), 0], [0, 0, 1]])
    turn = rz @ rx
    p = np.stack([out.x, out.y + drop, out.z], axis=-1).astype(float) + 0.5 - c
    back = p @ turn + c
    i, j, k = (np.floor(back[..., n]).astype(int) for n in range(3))
    ok = (i >= 0) & (i < w) & (j >= 0) & (j < h) & (k >= 0) & (k < d)
    out.grid[ok] = src.grid[i[ok], j[ok], k[ok]]
    return out


def drowned_cart():
    """A pilgrims' cart gone off the road into the shallows: a hooded cart
    nose-down and listing, its canvas sagging and stained with a red cross
    over the opening, a front wheel broken off and lying against it, rags
    hanging, moss and mud up its sides, a lantern still hung inside, mud
    pushed up round its nose. 34 x 32 x 44 voxels."""
    src = Model(34, 36, 44)
    cx = 16.0
    z0, z1 = 6, 38
    bed = 8
    plank_box(src, 5, 28, bed, bed + 2, z0, z1, 640, run='z', across='x')
    for xa, xb in ((4, 6), (27, 29)):
        plank_box(src, xa, xb, bed, bed + 6, z0, z1, 641 + xa, run='z', across='y', width=2)
    plank_box(src, 4, 29, bed, bed + 12, z0, z0 + 2, 643, run='x', across='y', width=2)
    hooped_cover(src, cx, 13.0, z0 + 1, z1, bed + 4, 20.0, 31.0, 644, hoops=4, hem=3)
    yf = src.y.astype(float)
    # A canvas valance over the front opening, a red cross on it, its hem torn.
    t = np.clip((yf - 20.0) / 11.0, 0.0, 1.0)
    arch = np.where(yf < 20.0, 13.0, 13.0 * np.sqrt(np.clip(1.0 - t ** 2, 0.0, 1.0)))
    valance = (src.z == z1 - 1) & (np.abs(src.x - cx) < arch) & (yf > 19 + hash2(src.x, 0, 650) * 3) & (yf < 31)
    cross = ((np.abs(src.x - cx) < 1.0) & (np.abs(yf - 25.5) < 3.5)) | ((np.abs(yf - 26.5) < 1.0) & (np.abs(src.x - cx) < 3))
    src.fill(valance, np.where(cross, DYE_RED[0], pick([CANVAS[2], CANVAS[0], CANVAS[1]], hash2(src.x // 2, src.y // 3, 651))))
    # Inside: dark, a chest, a lantern hung from the front hoop.
    src.fill(src.box(int(cx) - 4, bed + 2, z1 - 12, int(cx) + 4, bed + 7, z1 - 6), WOOD[2])
    src.fill(src.box(int(cx) - 4, bed + 5, z1 - 12, int(cx) + 4, bed + 6, z1 - 6), IRON[0])
    iron_lantern(src, int(cx) + 6, 18, z1 - 2, hang=6)
    # The back wheels still on their axle.
    # The big back wheels stand up past the canvas once the nose goes down.
    src.beam((1, 10, 10), (32, 10, 10), 2, [WOOD_DARK[0]])
    for x in (1, 32):
        wheel(src, (x, 10.0, 10.0), 10.0, axis='x', thick=2, spokes=8)
    studs(src, [(x, bed + 3, z) for x in (3, 29) for z in range(z0 + 3, z1, 7)])
    # Rags hanging off the sides.
    for k, z in enumerate((14, 22, 30)):
        cloth_drape(src, z, z + 3, 3 if k % 2 else 30, bed + 8, 7 + k, DYE_RED if k != 1 else [CLOTH_PALE[1], CANVAS[3]], 645 + k, axis='z')
    m = tilted(src, -22.0, -5.0, 3)
    yf = m.y.astype(float)
    # Mud and moss where the water has been: the lowest rows of everything.
    low = (m.grid >= 0) & (yf < 3 + hash2(m.x // 2, m.z // 2, 646) * 3)
    m.fill(low, np.where(hash2(m.x, m.y + m.z, 647) < 0.5, MOSS[1], MUD[0]))
    # The broken front wheel lying against the +X side.
    wheel(m, (31.0, 8.0, 30.0), 7.0, axis='x', thick=2, spokes=8, colors=[WOOD[2], WOOD_DARK[0]])
    m.fill(m.box(29, 0, 28, 33, 2, 33) & (m.grid < 0), MUD[1])
    # Mud pushed up round its nose where it ploughed in.
    ridge = (m.y == 0) & (m.grid < 0) & (np.abs(np.hypot((m.x - 16) / 16.0, (m.z - 30) / 12.0) - 1.0) < 0.15) & (hash2(m.x, m.z, 648) < 0.7)
    m.fill(ridge, pick([MUD[0], MUD[1], MOSS[1]], hash2(m.x, m.z, 649)))
    return m


RECIPES = {
    'RoadGibbet': road_gibbet,
    'RoadGibbetEmpty': road_gibbet_empty,
    'DrownedCart': drowned_cart,
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
