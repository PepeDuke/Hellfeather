"""Builds Act I enemies from figure.py rigs, with the five clips the game plays
(EnemyMoves.dk): idle and walk loop; attack, hit and death play once.

The attack clip lands its blow on the kind's StrikeFrame (EnemyData.dk). The
game slows the clip so the frames before the strike last as long as the move's
wind-up, assuming they add up to 0.27 s at full speed (EnemyMoves.WindUp), so
keep the wind-up frames' milliseconds summing to 270.

VoxelSize in EnemyData.dk must match what this builds, and Height must be the
model's box height, the middle number the build prints ("W x H x D"), not the
creature's own height: the spawner stands a model by half its Height, so a box
taller than Height (raised wings, a lifted weapon) sinks into the ground.

    python Tools/Models/enemies.py                    build every enemy
    python Tools/Models/enemies.py PilgrimPenitent    build some of them
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure import Rig, build, capsule, column, ellipsoid, fit, minus, union, where  # noqa: E402
from kit import (BALD, BILL, BILL_DARK, BLOOD, BRASS, BURLAP, CLOTH_PALE, CLOTH_RED, EYE_WHITE, FACE_DARK,  # noqa: E402
                 FEATHER_BROWN, FEATHER_GREY, FEATHER_PALE, FEET, MALLARD, CHESTNUT, FLOUR, GLOW, HABIT, HAIR_DARK, HAIR_GREY,
                 GAMBESON, HONEY, IRON, LEATHER, LEECH_MOUTH, MUD, RAVEN, ROPE, SCARF, SHIELD, SILVER, SKIN,
                 SKIN_PALE, SMOCK, STRAW, TROUSERS, WIMPLE, WOOD, WOOD_DARK, WOOL, hash2, pick)
from people import Body, dusted, flat, speckled  # noqa: E402


def legs(b, material, foot, gap=3.8, hip=34, knee=18, thigh=(3.2, 2.7), shin=(2.6, 2.0)):
    """Walking legs: thigh and shin on their own bones, feet forward. thigh and
    shin are the radii at their top and bottom."""
    for side, name in ((-gap, 'r'), (gap, 'l')):
        b.rig.bone(f'{name}_hip', (side, hip, 0), 'root')
        b.rig.bone(f'{name}_knee', (side, knee, 0.4), f'{name}_hip')
        b.part(f'{name}_hip', capsule((side, hip, 0), (side, knee, 0.4), *thigh), material)
        b.part(f'{name}_knee', capsule((side, knee, 0.4), (side, 3, 0), *shin), material)
        b.part(f'{name}_knee', union(ellipsoid((side, 1.5, 1.8), (2.2, 1.5, 3.4)), capsule((side, 3, 0), (side, 1.2, 0.5), 1.9)), foot)


def ragged(shape, hem, seed, depth=4.0, holes=0.04):
    """Tatters a garment: a torn hem `depth` deep above `hem`, and moth holes."""
    def cut(x, y, z):
        lane = np.floor(np.arctan2(z, x) * 9).astype(int)
        torn = y < hem + hash2(lane, 0, seed) * depth
        hole = hash2(np.floor(x).astype(int) * 7 + np.floor(z).astype(int), np.floor(y).astype(int), seed + 1) < holes
        return ~(torn | hole)
    return where(shape, cut)


def pilgrim_penitent():
    """The Pilgrim Penitent: a gaunt pilgrim in ragged grey robes and hood,
    barefoot, black feathers tied into his long grey hair and beard, carrying
    a tall shrine pole hung with feathers in his left hand. His one move is a
    slow overhead pole swing with a long wind-up (HellfeatherMove.PoleSwing).

    Authored with the man 70 tall and the shrine's cross at 97, scaled so the
    whole is 72 voxels, as EnemyData.dk loads it (VoxelSize 0.0306)."""
    b = Body(scale=72 / 97.5, shoulder=9.4, waist=7.6, depth=5.6)
    robe = speckled([SMOCK[1], WOOL[1], SMOCK[0]], 120, 2, 4)

    def stained(x, y, z, pose):
        out = robe(x, y, z, pose)
        dirt = (y < 20) & (hash2(np.floor(x / 2).astype(int) * 5 + np.floor(z / 2).astype(int), np.floor(y / 3).astype(int), 121) < (20 - y) / 30)
        return np.where(dirt, FACE_DARK[0], out)
    legs(b, speckled([WOOL[2], WOOL[1]], 122), speckled(SKIN[1:], 123, 1, 1))
    body, rx, rz = b.skirt(stained, hem=7, flare=3.4, wave=0.0)
    # The skirt from Body is whole; swap it for a tattered one.
    b.rig.parts.pop()
    b.part('root', ragged(column(7, 39, rx, rz, flat(0.3)), 7, 124, depth=5.0), stained)
    b.torso(robe)
    # A rope belt with a hanging end.
    b.belt(ROPE[0], y=37.5, buckle=None, height=1.6)
    b.part('root', capsule((2.5, 37, b.depth + 0.8), (3.5, 24, b.depth + 2.4), 0.7), ROPE[1])
    # The hood, fallen back over the shoulders as a heavy cowl.
    cowl = minus(ellipsoid((0, 55.5, -1.0), (9.0, 4.4, 8.0)), ellipsoid((0, 57, 0.6), (4.6, 6, 4.8)))
    b.part('chest', ragged(cowl, 51.5, 125, depth=2.0, holes=0.0), speckled([HABIT[1], WOOL[1]], 126, 2, 2))
    b.part('chest', ellipsoid((0, 57.5, -6.5), (5.0, 4.5, 2.6)), speckled([HABIT[1], WOOL[1]], 127, 2, 2))
    # Arms in wide ragged sleeves. The left hand holds the pole at the chest;
    # the right hangs loose.
    b.arm(-1, (-9.4, 53, 0), (-11.2, 42, 0.5), (-11.0, 32.5, 2.4), robe, robe, SKIN[1], r=3.0, flare=1.4)
    b.arm(1, (9.4, 53, 0), (11.6, 43, 1.0), (12.4, 40, 6.2), robe, robe, SKIN[1], r=3.0, flare=1.2)
    # The face, gaunt and weathered, with long grey hair and a long beard.
    b.head(SKIN, beard=HAIR_GREY[:2])
    b.hair([HAIR_GREY[1], HAIR_GREY[0], WOOL[0]], 'wavy')
    b.part('head', ellipsoid((0, 55.0, 3.6), (3.8, 4.8, 2.6)), speckled(HAIR_GREY[:2], 128, 1, 1))
    for k, (x, y, z, dx) in enumerate(((-4.4, 61, 1.0, -0.6), (4.6, 61.5, 0.5, 0.6), (-5.0, 59, -2, -0.3), (1.2, 52.5, 5.0, 0.4), (-1.6, 52.0, 5.0, -0.3), (5.2, 58.5, -2.0, 0.4))):
        b.part('head', capsule((x, y, z), (x + dx, y - 6 - k % 2 * 2, z + 0.3), 0.6, 0.3), RAVEN[k % 2])

    # The shrine pole: a staff from the ground to a small gabled shrine with a
    # cross, black feathers hung under it. It turns about his left hand.
    hand = (13.0, 41.0, 8.0)
    b.rig.bone('pole', hand, 'l_elbow')
    px, pz = 13.0, 8.0
    b.part('pole', capsule((px, 0.5, pz), (px, 77, pz), 1.1), speckled(WOOD[:3], 129, 1, 3))
    b.part('pole', capsule((px - 6.5, 76, pz), (px + 6.5, 76, pz), 1.3), WOOD_DARK[0])

    def shrine(x, y, z, pose):
        front = (z > pz + 3.2) & (np.abs(x - px) < 3.0) & (y > 79) & (y < 87)
        bird = front & (((x - px) / 1.8) ** 2 + ((y - 82.6) / 1.4) ** 2 < 1.0)
        out = np.where(front, CLOTH_PALE[1], pick(WOOD[:3], hash2(np.floor(y).astype(int), 0, 130)))
        return np.where(bird, FACE_DARK[0], out)
    box = lambda x, y, z: (np.abs(x - px) < 4.4) & (np.abs(z - pz) < 3.8)  # noqa: E731
    b.part('pole', where(ellipsoid((px, 83, pz), (4.8, 6.0, 4.2)), box), shrine)
    roof = lambda x, y, z: (y >= 88.5) & (y < 94) & (np.abs(x - px) < 5.8 - (y - 88.5)) & (np.abs(z - pz) < 4.8)  # noqa: E731
    b.part('pole', where(ellipsoid((px, 91, pz), (6.0, 3.2, 5.0)), roof), WOOD_DARK[1])
    b.part('pole', capsule((px, 93, pz), (px, 97, pz), 1.0), WOOD_DARK[0])
    b.part('pole', capsule((px - 2.0, 95.0, pz), (px + 2.0, 95.0, pz), 1.0), WOOD_DARK[0])
    for k in range(9):
        fx = px - 6.4 + k * 1.6
        b.part('pole', capsule((fx, 75.5, pz + (k % 2) - 0.5), (fx + (k - 4) * 0.4, 63 - (k % 3) * 2.5, pz + (k % 2) - 0.5), 0.7, 0.3), RAVEN[k % 2])

    def swing(chest, shoulder, pole_world, head=0, right=None, offset=None):
        """A pose for the swing: chest and left shoulder pitch, and the pole's
        pitch in the world (0 upright, 90 pointing ahead, beyond that down)."""
        pose = {'chest': (chest, 0, 0), 'l_shoulder': (shoulder, 0, 0), 'head': (head, 0, 0),
                'pole': (pole_world - chest - shoulder, 0, 0)}
        # Both hands on the staff while it swings.
        pose['r_shoulder'] = right if right is not None else (shoulder, 0, 18)
        pose['r_elbow'] = (0, 0, 0)
        if offset:
            pose['offset'] = offset
        return pose

    idle = [
        ({}, 600),
        ({'chest': (2, 0, 0), 'head': (4, 6, 0)}, 600),
        ({'chest': (3, 0, 0), 'head': (6, 2, 0), 'pole': (2, 0, 0)}, 600),
        ({'chest': (1, 0, 0), 'head': (2, -5, 0)}, 600),
    ]
    walk = []
    for k, phase in enumerate((1, 0, -1, 0)):
        walk.append(({'r_hip': (-22 * phase, 0, 0), 'l_hip': (22 * phase, 0, 0),
                      'r_knee': (18 if phase < 0 else 4, 0, 0), 'l_knee': (18 if phase > 0 else 4, 0, 0),
                      'chest': (8, 0, 2 * phase), 'head': (6, 0, 0), 'r_shoulder': (18 * phase, 0, 0),
                      'pole': (4 * phase, 0, 0), 'offset': (0, -1.0 if phase else 0.0, 0)}, 140))
    attack = [
        # The long wind-up: 270 ms at full speed, which the game stretches.
        (swing(-4, -45, -10), 60),
        (swing(-10, -110, -35, head=-6), 70),
        (swing(-16, -150, -55, head=-10), 70),
        (swing(-18, -162, -62, head=-12), 70),
        # The blow (StrikeFrame 4), the staff on the ground, the slow recovery.
        (swing(28, -62, 104, head=10), 80),
        (swing(36, -32, 124, head=14), 200),
        (swing(20, -20, 70, head=8), 220),
        (swing(6, -8, 20, head=2), 220),
    ]
    hit = [
        ({'chest': (-14, 0, -4), 'head': (-12, 0, 0), 'pole': (10, 0, 0)}, 110),
        ({'chest': (-6, 0, -2), 'head': (-4, 0, 0), 'pole': (4, 0, 0)}, 110),
    ]
    kneel = {'r_hip': (0, 0, 0), 'l_hip': (0, 0, 0), 'r_knee': (90, 0, 0), 'l_knee': (90, 0, 0)}
    death = [
        ({'chest': (14, 0, 0), 'head': (10, 0, 0), 'pole': (30, 0, 0), 'offset': (0, -4, 0)}, 140),
        (dict(kneel, chest=(28, 0, 0), head=(16, 0, 0), pole=(70, 0, 0), l_shoulder=(-20, 0, 0), offset=(0, -15, 0)), 160),
        (dict(kneel, chest=(58, 0, 0), head=(22, 0, 0), pole=(100, 0, 0), l_shoulder=(-50, 0, 0), offset=(0, -16, 0)), 160),
        (dict(kneel, chest=(84, 0, 0), head=(10, 0, 0), pole=(96, 0, 0), l_shoulder=(-80, 0, 0), offset=(0, -17, 0)), 500),
    ]
    clips = [('idle', True, idle), ('walk', True, walk), ('attack', False, attack), ('hit', False, hit), ('death', False, death)]
    return b.rig, clips


# Shared clip makers. Every attack but the Pilgrim's lands on frame 2, the
# EnemySpawner default, after two wind-up frames of 130 and 140 ms.

def merged(*poses):
    """Poses laid over each other: rotations of the same bone add up."""
    out = {}
    for p in poses:
        for k, v in p.items():
            if isinstance(v, tuple) and isinstance(out.get(k), tuple):
                out[k] = tuple(a + b for a, b in zip(out[k], v))
            else:
                out[k] = v
    return out


def attack_clip(base, windup1, windup2, strike, follow, recover, times=(130, 140, 80, 140, 110)):
    return ('attack', False, [(merged(base, p), ms) for p, ms in zip((windup1, windup2, strike, follow, recover), times)])


def human_clips(base, attack, lean=6, swing=18, stride=22, idle=None, hit=None, death=None, walk=None):
    """idle, walk, attack, hit and death for a figure with legs() and arms.
    attack is the five poses of attack_clip."""
    idle = idle or [{}, {'chest': (2, 0, 0), 'head': (3, 6, 0)}, {'chest': (3, 0, 0), 'head': (5, 2, 0)}, {'chest': (1, 0, 0), 'head': (1, -5, 0)}]
    clips = [('idle', True, [(merged(base, p), 560) for p in idle])]
    steps = []
    for phase in (1, 0, -1, 0):
        steps.append(merged(base, {'r_hip': (-stride * phase, 0, 0), 'l_hip': (stride * phase, 0, 0),
                                   'r_knee': (20 if phase < 0 else 4, 0, 0), 'l_knee': (20 if phase > 0 else 4, 0, 0),
                                   'chest': (lean, 0, 2 * phase), 'r_shoulder': (swing * phase, 0, 0),
                                   'offset': (0, -1.0 if phase else 0.0, 0)}, walk or {}))
    clips.append(('walk', True, [(p, 140) for p in steps]))
    clips.append(attack_clip(base, *attack))
    hit = hit or [{'chest': (-14, 0, -4), 'head': (-12, 0, 0)}, {'chest': (-6, 0, -2), 'head': (-4, 0, 0)}]
    clips.append(('hit', False, [(merged(base, p), 110) for p in hit]))
    kneel = {'r_hip': (0, 0, 0), 'l_hip': (0, 0, 0), 'r_knee': (90, 0, 0), 'l_knee': (90, 0, 0)}
    death = death or [
        {'chest': (14, 0, 0), 'head': (10, 0, 0), 'offset': (0, -4, 0)},
        dict(kneel, chest=(28, 0, 0), head=(16, 0, 0), r_shoulder=(-10, 0, -10), l_shoulder=(-10, 0, 10), offset=(0, -15, 0)),
        dict(kneel, chest=(58, 0, 0), head=(22, 0, 0), r_shoulder=(-40, 0, -10), l_shoulder=(-40, 0, 10), offset=(0, -16, 0)),
        dict(kneel, chest=(84, 0, 0), head=(10, 0, 0), r_shoulder=(-70, 0, -10), l_shoulder=(-70, 0, 10), offset=(0, -17, 0)),
    ]
    clips.append(('death', False, [(p, 140 if i < 3 else 500) for i, p in enumerate(death)]))
    return clips


# Faces and fabrics the fighters share.

def quilted(shades, seed, step=4):
    """Diamond-quilted gambeson cloth with a stud at each crossing."""
    def material(x, y, z, pose):
        u = np.floor(x + z).astype(int)
        v = np.floor(y).astype(int)
        seam = ((u + v) % step == 0) | ((u - v) % step == 0)
        stud = ((u + v) % step == 0) & ((u - v) % step == 0)
        out = pick(shades[:2], hash2(u // step, v // step, seed))
        out = np.where(seam, shades[1], out)
        return np.where(stud, BRASS[1], out)
    return material


def kettle_helmet(b, band=None):
    """A round iron helmet with a broad brim, as the Red Cuffs wear."""
    b.part('head', where(ellipsoid((0, 65.0, 0.8), (5.4, 5.2, 5.6)), lambda x, y, z: y > 64.0), speckled(IRON, 140, 1, 2))
    b.part('head', where(ellipsoid((0, 64.4, 0.8), (8.0, 1.6, 8.2)), lambda x, y, z: y < 65.0), IRON[0])
    if band is not None:
        b.part('head', where(ellipsoid((0, 65.0, 0.8), (5.6, 5.3, 5.8)), lambda x, y, z: (y > 64.3) & (y < 66.0)), band)


def sword(b, bone, hilt, tip):
    """An arming sword from the hilt in the hand to the tip."""
    h, t = np.array(hilt, float), np.array(tip, float)
    d = (t - h) / np.linalg.norm(t - h)
    b.part(bone, capsule(tuple(h - d * 3), tuple(h + d * 0.5), 0.8), LEATHER[2])
    side = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0])
    side = side / np.linalg.norm(side)
    b.part(bone, capsule(tuple(h + side * 2.6), tuple(h - side * 2.6), 0.6), IRON[0])
    b.part(bone, capsule(tuple(h + d * 0.8), tuple(t), 0.8, 0.35), lambda x, y, z, pose: np.full(np.shape(x), SILVER[1]))


def kite_shield(b, bone, center, emblem):
    """A kite shield held on the arm, its face to +Z, with an emblem function
    (u, v) -> palette index, or -1 where the plain face shows."""
    cx, cy, cz = center

    def shape(x, y, z):
        u, v = x - cx, y - cy
        top = v > 4
        width = np.where(top, 7.0, 7.0 * np.clip((v + 13) / 17, 0, 1) ** 0.8)
        return (np.abs(u) < width) & (v > -13) & (v < 10 - np.abs(u) * 0.15) & (np.abs(z - cz) < 0.9)
    shape.box = (np.array([cx - 7.5, cy - 13, cz - 1]), np.array([cx + 7.5, cy + 10.5, cz + 1]))

    def paint(x, y, z, pose):
        u, v = x - cx, y - cy
        out = pick(SHIELD, hash2(np.floor(u).astype(int), np.floor(v / 3).astype(int), 141))
        rim = ~shape(cx + u * 1.1, cy + v * 1.05 + 0.4, z)
        out = np.where(rim, WOOD_DARK[0], out)
        mark = emblem(u, v)
        return np.where(mark >= 0, mark, out)
    b.part(bone, shape, paint)


def cuff_ribbon(u, v):
    """The Red Cuff's tied ribbon: a band across with knotted tails."""
    band = (np.abs(v - 0.5) < 1.6) & (np.abs(u) < 6.2)
    knot = (np.abs(u) < 1.6) & (np.abs(v - 0.5) < 2.4)
    tails = (np.abs(np.abs(u) - (1.2 - v * 0.3)) < 0.9) & (v < -1) & (v > -7)
    return np.where(band | knot | tails, CLOTH_RED[0], -1)


def red_cross(u, v):
    """Ottar's shield: deep red with a pale cross."""
    cross = ((np.abs(u) < 0.9) & (v > -9) & (v < 7)) | ((np.abs(v - 1) < 0.9) & (np.abs(u) < 5))
    return np.where(cross, CLOTH_PALE[0], CLOTH_RED[1])


# The fighters.

def tithe_stray():
    """The Tithe Stray: a thin, stooped bearer in wet, torn sackcloth with a
    hood, grey lips, bare feet and a tin tithe bracelet. A weak, slow slap."""
    b = Body(scale=72 / 68, shoulder=8.6, waist=6.6, depth=4.6)
    sack = dusted(speckled([BURLAP[1], MUD[0], SMOCK[1]], 150, 2, 3), [MUD[1]], 0.1, 151)
    legs(b, speckled(SKIN_PALE[1:], 152, 1, 2), SKIN_PALE[2])
    body, rx, rz = b.skirt(sack, hem=18, flare=2.4, wave=0.0)
    b.rig.parts.pop()
    b.part('root', ragged(column(18, 39, rx, rz, flat(0.3)), 18, 153, depth=6.0, holes=0.05), sack)
    b.torso(sack)
    b.belt(ROPE[1], y=37, buckle=None, height=1.2)
    b.part('chest', ragged(minus(ellipsoid((0, 55.5, -1.0), (7.6, 4.0, 7.0)), ellipsoid((0, 57, 0.6), (4.4, 6, 4.6))), 52.0, 154, 2.0, 0.0), sack)
    for side, sx in ((-1, -8.6), (1, 8.6)):
        b.arm(side, (sx, 53, 0), (sx * 1.1, 42, 1.0), (sx * 1.05, 31.5, 3.0), sack, SKIN_PALE, SKIN_PALE[2], r=2.5)
    b.part('l_elbow', capsule((9.0, 34.5, 2.6), (9.0, 33.0, 2.8), 2.2), SILVER[1])
    b.head(SKIN_PALE, lips=HABIT[1])
    b.hair(HAIR_DARK, 'wavy')
    base = {'chest': (14, 0, 0), 'head': (-10, 0, 0), 'r_shoulder': (-6, 0, 0), 'l_shoulder': (-6, 0, 0)}
    attack = ({'r_shoulder': (-30, 0, -20), 'chest': (-4, -10, 0)}, {'r_shoulder': (-55, 0, -30), 'r_elbow': (-30, 0, 0), 'chest': (-6, -18, 0)},
              {'r_shoulder': (-80, 0, 0), 'r_elbow': (-5, 0, 0), 'chest': (6, 14, 0)}, {'r_shoulder': (-60, 0, 10), 'chest': (8, 18, 0)},
              {'r_shoulder': (-20, 0, 0), 'chest': (2, 4, 0)})
    fit(b.rig, 72)
    return b.rig, human_clips(base, attack, lean=4, stride=14, swing=6)


def black_honey_fiend():
    """The Black Honey Fiend: a gaunt addict in a torn hooded smock, crouched
    and quick, eyes too bright, mouth black with the honey, a kitchen knife.
    Sprints in and slashes twice."""
    b = Body(scale=1.0, shoulder=8.8, waist=6.6, depth=4.6)
    rag = speckled([SMOCK[1], MUD[0], WOOL[1]], 160, 2, 3)
    legs(b, speckled(SKIN[1:], 161, 1, 2), SKIN[2])
    b.part('r_hip', ragged(capsule((-3.8, 34, 0), (-3.9, 24, 0.4), 3.6), 24, 162, 3.0, 0.0), speckled([TROUSERS[0], MUD[1]], 163))
    b.part('l_hip', ragged(capsule((3.8, 34, 0), (3.9, 24, 0.4), 3.6), 24, 164, 3.0, 0.0), speckled([TROUSERS[0], MUD[1]], 163))
    body, rx, rz = b.skirt(rag, hem=24, flare=2.0, wave=0.0)
    b.rig.parts.pop()
    b.part('root', ragged(column(24, 39, rx, rz, flat(0.3)), 24, 165, depth=5.0, holes=0.05), rag)
    b.torso(rag)
    b.part('chest', ragged(minus(ellipsoid((0, 54.5, -2.2), (9.4, 5.0, 8.4)), ellipsoid((0, 57, 0.6), (4.4, 6, 4.6))), 50.0, 166, 3.0, 0.03), rag)
    b.arm(-1, (-8.8, 53, 0), (-10.4, 42, 2.0), (-10.4, 32.5, 5.0), rag, SKIN, BLOOD[1], r=2.5)
    b.arm(1, (8.8, 53, 0), (10.4, 42, 1.0), (10.4, 32.5, 3.0), rag, SKIN, BLOOD[1], r=2.5)
    b.part('r_elbow', capsule((-10.4, 29.5, 6.0), (-10.4, 29.0, 9.0), 0.8), WOOD[2])
    b.part('r_elbow', capsule((-10.4, 29.0, 9.0), (-10.2, 27.5, 17.0), 1.2, 0.3), SILVER[1])
    b.head(SKIN, lips=HONEY[0], eyes=GLOW[0], beard=[HONEY[0], HONEY[1]])
    b.hair(HAIR_DARK, 'wavy')
    crouch = {'chest': (18, 0, 0), 'head': (-16, 0, 0), 'r_hip': (-24, 0, 0), 'l_hip': (-16, 0, 0), 'r_knee': (34, 0, 0), 'l_knee': (28, 0, 0),
              'offset': (0, -4, 0), 'r_shoulder': (-30, 0, -6), 'r_elbow': (-30, 0, 0)}
    attack = ({'r_shoulder': (-60, 0, -40), 'r_elbow': (-40, 0, 0), 'chest': (0, -14, 0)}, {'r_shoulder': (-110, 0, -50), 'r_elbow': (-30, 0, 0), 'chest': (-4, -24, 0)},
              {'r_shoulder': (-70, 0, 30), 'r_elbow': (-10, 0, 0), 'chest': (10, 22, 0)}, {'r_shoulder': (-100, 0, -40), 'chest': (0, -16, 0)},
              {'r_shoulder': (-60, 0, 35), 'chest': (14, 24, 0)})
    death = None
    fit(b.rig, 70)
    return b.rig, human_clips(crouch, attack, lean=10, stride=30, swing=10, death=death,
                              walk={'chest': (10, 0, 0)})


def millhand_thrall():
    """The Millhand Thrall: a flour-caked mill worker with a headband, torn
    smock and apron, bare feet, a full flour sack held low in both hands
    as his weapon. A slow, heavy sack swing."""
    b = Body(scale=72 / 70, shoulder=9.8, waist=8.2, depth=5.6)
    smock = dusted(speckled(SMOCK, 170, 2, 3), FLOUR, 0.12, 171)
    legs(b, speckled([TROUSERS[0], SMOCK[1]], 172), SKIN[2])
    body, rx, rz = b.skirt(smock, hem=24, flare=2.2, wave=0.0)
    b.rig.parts.pop()
    b.part('root', ragged(column(24, 39, rx, rz, flat(0.3)), 24, 173, 4.0, 0.03), smock)
    b.torso(smock)
    b.apron(dusted(speckled([CLOTH_PALE[1], SMOCK[2]], 174), FLOUR, 0.15, 175), hem=22, low_half=7.0, bib_half=0)
    b.belt(ROPE[1], y=38, buckle=None, height=1.4)
    for side, sx in ((-1, -9.8), (1, 9.8)):
        b.arm(side, (sx, 53, 0), (sx * 1.05, 42, 3.0), (sx * 0.55, 31, 7.5), smock, SKIN, SKIN[1], r=2.8)
    b.rig.bone('sack', (0, 28, 9.0), 'l_elbow')
    b.part('sack', ellipsoid((0, 23, 9.5), (7.0, 7.4, 4.8)), dusted(speckled([CLOTH_PALE[1], BURLAP[0]], 176, 2, 2), FLOUR, 0.2, 177))
    b.part('sack', capsule((-2.5, 29.5, 9.5), (2.5, 29.5, 9.5), 1.6), BURLAP[1])
    b.head(SKIN, beard=HAIR_GREY[:2], eyes=EYE_WHITE[0])
    b.hair(HAIR_GREY, 'short')
    b.part('head', where(ellipsoid((0, 64.5, 0.8), (5.8, 5.6, 6.0)), lambda x, y, z: (y > 64.6) & (y < 67)), CLOTH_PALE[1])
    stance = {'chest': (14, 0, 0), 'head': (-12, 0, 0), 'r_hip': (-8, 0, -8), 'l_hip': (-8, 0, 8), 'r_knee': (14, 0, 0), 'l_knee': (14, 0, 0), 'offset': (0, -2, 0)}
    both = lambda p, e=0: {'r_shoulder': (p, 0, 0), 'l_shoulder': (p, 0, 0), 'r_elbow': (e, 0, 0), 'l_elbow': (e, 0, 0)}  # noqa: E731
    attack = (merged(both(-60, -20), {'chest': (-6, 0, 0), 'sack': (40, 0, 0)}), merged(both(-150, -30), {'chest': (-20, 0, 0), 'head': (-6, 0, 0), 'sack': (120, 0, 0)}),
              merged(both(-40, 0), {'chest': (34, 0, 0), 'sack': (30, 0, 0)}), merged(both(-10, 0), {'chest': (40, 0, 0)}), merged(both(0, 0), {'chest': (16, 0, 0)}))
    fit(b.rig, 72)
    return b.rig, human_clips(stance, attack, lean=6, stride=16, swing=0)


def red_cuff(sergeant=False, arbalist=False):
    """A Red Cuff soldier: quilted grey gambeson, red at the cuffs and collar,
    dark trousers and tall boots. Cuffman: kettle helmet, sword and kite
    shield. The Arbalist: a longer coat with a red sash, a bladelock carried
    level. Sergeant Ottar: bareheaded and grey-bearded, a red sash and belt,
    a bladelock on his back, a red shield with a pale cross."""
    b = Body(scale=72 / 70, shoulder=10.0, waist=8.6, depth=6.0, belly=0.6 if sergeant else 0.0)
    gam = quilted(GAMBESON, 180)
    legs(b, speckled(TROUSERS, 181), FACE_DARK[0])
    for name, sx in (('r_knee', -3.8), ('l_knee', 3.8)):
        b.part(name, capsule((sx, 17, 0.4), (sx, 3, 0), 2.9, 2.4), speckled(LEATHER[1:3], 182, 1, 2))
    hem = 16 if arbalist else 22
    b.skirt(gam, hem=hem, flare=2.6, wave=0.0, front_cut=lambda y: 0.6 + 0 * y)
    b.torso(gam)
    b.belt(LEATHER[2] if not sergeant else CLOTH_RED[0], y=37, buckle=BRASS[0], height=2.2)
    b.part('chest', shell_collar(), CLOTH_RED[0])
    sleeve = gam
    b.arm(-1, (-10.0, 53, 0), (-11.6, 42, 1.0), (-11.0, 32, 4.0), sleeve, sleeve, SKIN[1], r=3.1, cuff=CLOTH_RED[0])
    if arbalist:
        b.arm(1, (10.0, 53, 0), (11.6, 43, 2.0), (4.0, 39, 8.0), sleeve, sleeve, SKIN[1], r=3.1, cuff=CLOTH_RED[0])
        b.part('chest', capsule((-5, 56, 6.4), (5, 30, 7.6), 1.6), CLOTH_RED[1])
        b.part('root', capsule((0, 38, 8.4), (0.5, 18, 9.6), 2.2, 2.6), CLOTH_RED[1])
        # The bladelock: a crossbow with a blade nested under its stock.
        b.rig.bone('bow', (-11.0, 30, 7.0), 'r_elbow')
        b.part('bow', capsule((-12, 30, 1), (-6, 33, 18), 1.3), WOOD[1])
        b.part('bow', capsule((-14, 33.5, 16), (2, 34.5, 16), 0.9), IRON[0])
        b.part('bow', capsule((-10, 31.4, 9), (-5, 32.0, 23), 0.8, 0.2), SILVER[1])
        b.part('bow', capsule((-11, 32.5, 12), (-6.5, 33.3, 19), 0.5), WOOD_DARK[0])
    else:
        b.arm(1, (10.0, 53, 0), (12.0, 43, 3.0), (10.5, 41, 9.0), sleeve, sleeve, SKIN[1], r=3.1, cuff=CLOTH_RED[0])
        kite_shield(b, 'l_elbow', (11.5, 40, 11.5), red_cross if sergeant else cuff_ribbon)
        sword(b, 'r_elbow', (-11.0, 29, 5.5), (-13.0, 6, 16.0))
    if sergeant:
        b.part('chest', capsule((8, 55, 5.8), (-7, 38, 7.6), 1.8), CLOTH_RED[0])
        b.part('root', capsule((-3, 36, 8.8), (-3.5, 22, 9.6), 1.4, 1.8), CLOTH_RED[0])
        b.part('chest', ellipsoid((6.8, 52, 6.8), (1.7, 1.7, 0.7)), BRASS[0])
        b.part('chest', capsule((-8, 58, -7.4), (7, 40, -7.6), 1.2), WOOD[1])
        b.part('chest', capsule((-9, 57, -8.0), (-5, 59, -8.4), 0.8), IRON[0])
        b.head(SKIN, beard=HAIR_GREY[:2])
        b.hair([HAIR_GREY[1], HAIR_DARK[1], HABIT[1]], 'wavy')
    else:
        b.head(SKIN, beard=HAIR_DARK[:2])
        kettle_helmet(b, CLOTH_RED[0] if arbalist else None)
    fit(b.rig, 72)
    if arbalist:
        aim = {'r_shoulder': (-70, 0, 10), 'r_elbow': (-20, 0, 0), 'l_shoulder': (-60, 0, -14), 'chest': (-2, 0, 0), 'head': (6, 0, 0)}
        attack = (merged(aim, {'r_shoulder': (25, 0, 0)}), aim, merged(aim, {'chest': (-6, 0, 0), 'r_shoulder': (-6, 0, 0)}), merged(aim, {'r_shoulder': (20, 0, 0)}), {'r_shoulder': (-10, 0, 0)})
        return b.rig, human_clips({}, attack, lean=4, stride=20, swing=0)
    guard = {'l_shoulder': (-8, 0, 0)}
    if sergeant:
        attack = ({'r_shoulder': (-90, 0, -20), 'r_elbow': (-40, 0, 0), 'chest': (-6, -10, 0)}, {'r_shoulder': (-170, 0, -10), 'r_elbow': (-30, 0, 0), 'chest': (-10, -16, 0)},
                  {'r_shoulder': (-80, 0, 10), 'r_elbow': (0, 0, 0), 'chest': (16, 14, 0)}, {'r_shoulder': (-40, 0, 14), 'chest': (20, 16, 0)}, {'r_shoulder': (-14, 0, 0), 'chest': (4, 0, 0)})
    else:
        attack = ({'r_shoulder': (-70, 0, -40), 'r_elbow': (-60, 0, 0), 'chest': (-4, -14, 0)}, {'r_shoulder': (-130, 0, -40), 'r_elbow': (-50, 0, 0), 'chest': (-8, -24, 0)},
                  {'r_shoulder': (-70, 0, 20), 'r_elbow': (0, 0, 0), 'chest': (14, 20, 0)}, {'r_shoulder': (-40, 0, 30), 'chest': (18, 26, 0)}, {'r_shoulder': (-14, 0, 0), 'chest': (4, 0, 0)})
    return b.rig, human_clips(guard, attack, lean=5, stride=22, swing=10)


def shell_collar():
    """A red stand-up collar at the throat."""
    return minus(column(53, 57.5, flat(4.6), flat(4.4), flat(0.6)), column(52, 58, flat(3.0), flat(2.8), flat(0.6)))


def hollowed_bearer():
    """The Hollowed Bearer: a hollow-eyed bearer chained upright in an iron
    frame, gripping its bars, silver wire bracelets on both wrists, milk-white
    eyes, a torn shift. Speed 0: it swipes out from inside the frame."""
    b = Body(shoulder=8.8, waist=6.8, depth=4.8)
    shift = speckled([SMOCK[1], MUD[0], BURLAP[1]], 190, 2, 3)
    legs(b, speckled(SKIN_PALE[1:], 191, 1, 2), SKIN_PALE[2])
    body, rx, rz = b.skirt(shift, hem=16, flare=2.0, wave=0.0)
    b.rig.parts.pop()
    b.part('root', ragged(column(16, 39, rx, rz, flat(0.3)), 16, 192, 7.0, 0.05), shift)
    b.torso(shift)
    for side, sx in ((-1, -8.8), (1, 8.8)):
        b.arm(side, (sx, 53, 0), (sx * 1.3, 46, 1.0), (sx * 1.25, 55, 2.4), shift, SKIN_PALE, SKIN_PALE[1], r=2.5)
        for k in range(3):
            b.part(f'{"r" if side < 0 else "l"}_elbow', capsule((sx * 1.25, 52 + k * 0.9, 2.2), (sx * 1.25, 52.4 + k * 0.9, 2.2), 2.0), SILVER[k % 2])
    b.head(SKIN_PALE, eyes=EYE_WHITE[0], lips=FACE_DARK[0])
    b.hair(HAIR_DARK, 'wavy')
    # The frame: four posts, cross bars, an arched top with a ring.
    frame = speckled([IRON[0], LEATHER[2], IRON[1]], 193, 1, 2)
    for x in (-13, 13):
        for z in (-8, 8):
            b.part('root', capsule((x, 0, z), (x, 80, z), 1.4), frame)
    for y in (2, 30, 50, 80):
        for z in (-8, 8):
            b.part('root', capsule((-13, y, z), (13, y, z), 1.2), frame)
        for x in (-13, 13):
            b.part('root', capsule((x, y, -8), (x, y, 8), 1.2), frame)
    b.part('root', minus(ellipsoid((0, 80, 0), (13.5, 9, 1.5)), ellipsoid((0, 80, 0), (11.5, 7.5, 3))), frame)
    b.part('root', minus(ellipsoid((0, 91, 0), (3, 3, 0.9)), ellipsoid((0, 91, 0), (1.8, 1.8, 2))), frame)
    for k in range(5):
        b.part('root', capsule((13, 50 - k * 4, 8.5), (13, 47 - k * 4, 9.5), 0.8), IRON[1])
    attack = ({'r_shoulder': (-20, 0, 0), 'r_elbow': (40, 0, 0), 'chest': (-4, -10, 0)}, {'r_shoulder': (-30, 0, -20), 'r_elbow': (60, 0, 0), 'chest': (-6, -20, 0), 'head': (-10, 0, 0)},
              {'r_shoulder': (-80, 0, 10), 'r_elbow': (-60, 0, 0), 'chest': (16, 16, 0), 'head': (8, 0, 0)}, {'r_shoulder': (-70, 0, 20), 'r_elbow': (-60, 0, 0), 'chest': (18, 20, 0)},
              {'r_shoulder': (-20, 0, 0), 'chest': (4, 0, 0)})
    death = [{'chest': (10, 0, 0), 'head': (20, 0, 0), 'r_shoulder': (30, 0, 0), 'l_shoulder': (30, 0, 0)},
             {'chest': (24, 0, 6), 'head': (34, 0, 0), 'r_shoulder': (40, 0, 0), 'l_shoulder': (40, 0, 0), 'offset': (0, -3, 0)},
             {'chest': (34, 0, 8), 'head': (40, 0, 0), 'r_shoulder': (50, 0, 0), 'l_shoulder': (50, 0, 0), 'offset': (0, -6, 0)},
             {'chest': (40, 0, 10), 'head': (44, 0, 0), 'r_shoulder': (55, 0, 0), 'l_shoulder': (55, 0, 0), 'offset': (0, -8, 0)}]
    clips = human_clips({'head': (-10, 0, 0)}, attack, death=death)
    clips[1] = ('walk', True, clips[0][2])
    fit(b.rig, 72)
    return b.rig, clips


def ring_keeper_warden():
    """The Ring-Keeper Warden, Mardra's foreman: a big man in a bloodied
    leather apron over a pale shirt with rolled sleeves, long dark hair and a
    beard, a grey ring glowing on his left thumb, a meat cleaver in his right
    hand. A slow overhead chop."""
    b = Body(scale=72 / 70, shoulder=12.2, waist=11.0, depth=8.0, belly=3.0)
    shirt = speckled([CLOTH_PALE[1], SMOCK[2], SCARF[2]], 200, 2, 3)
    legs(b, speckled(TROUSERS, 201), FACE_DARK[0], gap=4.4)
    for name, sx in (('r_knee', -4.4), ('l_knee', 4.4)):
        b.part(name, capsule((sx, 12, 0.3), (sx, 3, 0), 3.0, 2.6), LEATHER[2])
    b.torso(shirt)

    def bloodied(x, y, z, pose):
        out = pick(LEATHER[:3], hash2(np.floor(x / 2).astype(int), np.floor(y / 5).astype(int), 202))
        splash = hash2(np.floor(x / 3).astype(int), np.floor(y / 3).astype(int), 203) < 0.08
        return np.where(splash, BLOOD[0], out)
    b.apron(bloodied, hem=12, low_half=11.0, bib_half=7.6, straps=LEATHER[2], skirt_top=39, flare=1.6, grow=1.4)
    b.belt(LEATHER[2], y=37, buckle=IRON[1])
    b.arm(-1, (-12.2, 53, 0), (-13.6, 42, 1.0), (-13.2, 32, 3.5), shirt, SKIN, SKIN[1], r=3.6)
    b.arm(1, (12.2, 53, 0), (13.6, 42, 1.0), (13.2, 32, 3.0), shirt, SKIN, SKIN[1], r=3.6)
    b.part('l_elbow', minus(ellipsoid((12.0, 30, 5.6), (1.4, 1.4, 1.4)), ellipsoid((12.0, 30, 5.6), (0.6, 2, 0.6))), lambda x, y, z, pose: np.full(np.shape(x), SILVER[2] if pose.get('ring') else HABIT[1]))
    # The cleaver, blade down and forward.
    b.part('r_elbow', capsule((-13.2, 28, 6), (-13.2, 26, 9), 0.9), WOOD[2])
    b.part('r_elbow', where(ellipsoid((-13.2, 20.5, 11), (0.7, 7, 4.2)), lambda x, y, z: (np.abs(z - 11) < 3.6) & (y < 26)),
           lambda x, y, z, pose: np.where(hash2(np.floor(y).astype(int), np.floor(z).astype(int), 205) < 0.3, BLOOD[0], SILVER[1]))
    b.head(SKIN, beard=HAIR_DARK[:2])
    b.hair(HAIR_DARK, 'wavy')
    b.part('head', ellipsoid((0, 59, -4.2), (4.2, 5.6, 2.4)), speckled(HAIR_DARK, 206, 1, 2))
    both = lambda p, e=0: {'r_shoulder': (p, 0, 8), 'l_shoulder': (p, 0, -8), 'r_elbow': (e, 0, 0), 'l_elbow': (e, 0, 0)}  # noqa: E731
    attack = (merged(both(-90, -50), {'chest': (-6, 0, 0)}), merged(both(-170, -60), {'chest': (-14, 0, 0), 'head': (-8, 0, 0), 'ring': 1}),
              merged(both(-70, 0), {'chest': (26, 0, 0)}), merged(both(-30, 0), {'chest': (34, 0, 0)}), merged(both(-8, 0), {'chest': (10, 0, 0)}))
    fit(b.rig, 72)
    return b.rig, human_clips({}, attack, lean=4, stride=16, swing=10)


# The birds.

class Bird:
    """A bird standing on two legs, facing +Z, authored about 100 tall to the
    crown: legs, a body with folded wings and a tail, a neck with a head, a
    bill with a jaw that opens. Its rig: root, body, tail, l_wing, r_wing,
    neck, head, jaw, l_leg, r_leg."""

    def __init__(self, feathers, wings, leg=28, body=(16, 15, 24), neck=((0, 56, 14), (0, 80, 18)), neck_r=(7.0, 5.0),
                 head=(7.0, 7.4, 8.6), bill=('duck', 15), bill_color=BILL, feet=FEET, gap=7, webbed=True, eye=FACE_DARK[0], eye_r=1.2, seed=210):
        self.rig = Rig()
        r = self.rig
        bx, by, bz = body
        cy = leg + by - 3
        self.cy, self.body = cy, body
        r.bone('root', (0, 0, 0))
        for side, name in ((-gap, 'r'), (gap, 'l')):
            r.bone(f'{name}_leg', (side, leg + 2, 0), 'root')
            r.part(f'{name}_leg', capsule((side, leg + 4, 0), (side, 3, 1.5), 2.2, 1.4), feet[1])
            if webbed:
                foot = where(ellipsoid((side, 1.2, 6), (5.0, 1.3, 6.4)), lambda x, y, z: z > 0)
            else:
                foot = union(*[capsule((side, 1.2, 1.5), (side + dx, 0.8, 1.5 + dz), 0.8) for dx, dz in ((-3, 6), (0, 7), (3, 6), (0, -4))])
            r.part(f'{name}_leg', foot, feet[0])
        r.bone('body', (0, leg, 0), 'root')
        r.part('body', ellipsoid((0, cy, -2), (bx, by, bz)), feathers)
        r.part('body', ellipsoid((0, cy + 3, bz * 0.42), (bx * 0.86, by * 0.86, bz * 0.55)), feathers)
        r.bone('tail', (0, cy, -bz + 4), 'body')
        r.part('tail', ellipsoid((0, cy + by * 0.35, -bz - 3), (bx * 0.55, by * 0.22, 9)), wings)
        for side, name in ((-1, 'r'), (1, 'l')):
            r.bone(f'{name}_wing', (side * bx * 0.8, cy + by * 0.55, bz * 0.35), 'body')

            def wing(x, y, z, pose, side=side):
                tip = (z < -bz * 0.6) & ((np.floor(y) + np.floor(z)) % 3 == 0)
                return np.where(tip, RAVEN[1], wings(x, y, z, pose) if callable(wings) else wings)
            r.part(f'{name}_wing', ellipsoid((side * (bx + 0.6), cy + by * 0.12, -bz * 0.3), (2.4, by * 0.78, bz * 0.98)), wing)
        (nx0, ny0, nz0), (nx1, ny1, nz1) = neck
        r.bone('neck', (nx0, ny0, nz0), 'body')
        r.part('neck', capsule((nx0, ny0, nz0), (nx1, ny1, nz1), neck_r[0], neck_r[1]), feathers)
        r.bone('head', (nx1, ny1, nz1), 'neck')
        hx, hy, hz = head
        self.head_at = (nx1, ny1 + hy * 0.5, nz1 + hz * 0.25)
        cx_, cy_, cz_ = self.head_at
        r.part('head', ellipsoid(self.head_at, head), feathers)
        for side in (-1, 1):
            r.part('head', ellipsoid((side * hx * 0.8, cy_ + hy * 0.15, cz_ + hz * 0.32), (eye_r, eye_r * 1.1, eye_r * 1.1)), eye)
        kind, length = bill
        front = cz_ + hz * 0.85
        r.bone('jaw', (0, cy_ - hy * 0.25, front - 1), 'head')
        if kind == 'duck':
            r.part('head', ellipsoid((0, cy_ - hy * 0.12, front + length * 0.45), (hx * 0.62, 2.0, length * 0.55)), bill_color[0])
            r.part('jaw', ellipsoid((0, cy_ - hy * 0.32, front + length * 0.4), (hx * 0.55, 1.2, length * 0.5)), bill_color[1])
        else:
            r.part('head', capsule((0, cy_, front - 1), (0, cy_ - hy * 0.25, front + length), hy * 0.32, 0.4), bill_color[0])
            r.part('jaw', capsule((0, cy_ - hy * 0.3, front - 1), (0, cy_ - hy * 0.38, front + length * 0.85), hy * 0.2, 0.3), bill_color[1])

    def part(self, bone, shape, material, when=None):
        self.rig.part(bone, shape, material, when)

    def quills(self, count, seed, length=7.0, color=RAVEN[0]):
        """Black quills bristling from the back of the neck and the crown."""
        r = self.rig
        (nx0, ny0, nz0), (nx1, ny1, nz1) = [r.bones['neck'][0], r.bones['head'][0]]
        for k in range(count):
            t = k / max(1, count - 1)
            y = ny0 + (ny1 - ny0) * t
            z = nz0 + (nz1 - nz0) * t
            sx = (hash2(k, 0, seed) - 0.5) * 6
            r.part('neck', capsule((sx, y, z - 3), (sx * 1.6, y + length * 0.5, z - 3 - length), 1.4, 0.7), color)

    def patches(self, shades, seed, amount=0.12, bone='body'):
        """Bald moult patches: blotches of bare skin on the body."""
        bx, by, bz = self.body
        for k in range(int(amount * 30)):
            a = hash2(k, 1, seed) * 2 * math.pi
            y = self.cy + (hash2(k, 2, seed) - 0.5) * by
            z = (hash2(k, 3, seed) - 0.5) * bz * 1.4
            x = math.cos(a) * bx * 0.98
            self.rig.part(bone, ellipsoid((x, y, z), (1.2, 2.6, 3.0)), shades[k % len(shades)])


def bird_clips(kind, base=None, flight=False):
    """idle, walk, attack, hit and death for a Bird. kind picks the attack:
    peck, hop, charge, wingslam, spit or dive."""
    base = base or {}
    clips = [('idle', True, [(merged(base, p), 420) for p in (
        {}, {'neck': (-4, 0, 0), 'head': (0, 20, 0)}, {'neck': (-2, 0, 0), 'head': (4, 12, 0), 'tail': (0, 10, 0)}, {'head': (0, -16, 0), 'tail': (0, -8, 0)})])]
    if flight:
        walk = [merged(base, {'l_wing': (0, 0, 90 + a), 'r_wing': (0, 0, -90 - a), 'l_leg': (-60, 0, 0), 'r_leg': (-60, 0, 0),
                              'body': (12, 0, 0), 'offset': (0, 10 + a * 0.08, 0)}) for a in (50, 10, -30, 10)]
    else:
        walk = [merged(base, {'l_leg': (24 * p, 0, 0), 'r_leg': (-24 * p, 0, 0), 'body': (4, 0, 6 * p), 'neck': (6 + 4 * abs(p), 0, 0),
                              'tail': (0, 10 * p, 0)}) for p in (1, 0, -1, 0)]
    clips.append(('walk', True, [(p, 130) for p in walk]))
    if kind == 'peck':
        attack = ({'neck': (-24, 0, 0), 'body': (-6, 0, 0)}, {'neck': (-36, 0, 0), 'body': (-10, 0, 0), 'mouth': 1},
                  {'neck': (55, 0, 0), 'head': (25, 0, 0), 'body': (24, 0, 0)}, {'neck': (50, 0, 0), 'head': (20, 0, 0), 'body': (18, 0, 0)}, {'neck': (10, 0, 0), 'body': (4, 0, 0)})
    elif kind == 'hop':
        attack = ({'l_leg': (-20, 0, 0), 'r_leg': (-20, 0, 0), 'body': (10, 0, 0), 'offset': (0, -2, 0)}, {'neck': (-20, 0, 0), 'offset': (0, 8, 8), 'l_wing': (0, 0, 40), 'r_wing': (0, 0, -40)},
                  {'neck': (60, 0, 0), 'head': (25, 0, 0), 'body': (26, 0, 0), 'offset': (0, 0, 12)}, {'neck': (40, 0, 0), 'body': (14, 0, 0), 'offset': (0, 4, 6)}, {'offset': (0, 0, 0)})
    elif kind == 'charge':
        puff = {'l_wing': (0, 0, 18), 'r_wing': (0, 0, -18), 'tail': (-20, 0, 0)}
        attack = (merged(puff, {'neck': (-10, 0, 0), 'mouth': 1}), merged(puff, {'neck': (45, 0, 0), 'body': (14, 0, 0), 'l_leg': (-10, 0, 0), 'r_leg': (-10, 0, 0)}),
                  {'neck': (60, 0, 0), 'body': (26, 0, 0), 'l_leg': (30, 0, 0), 'r_leg': (-30, 0, 0), 'offset': (0, -2, 14)}, {'neck': (50, 0, 0), 'body': (20, 0, 0), 'offset': (0, -1, 8)}, {'neck': (10, 0, 0)})
    elif kind == 'wingslam':
        attack = ({'neck': (-26, 0, 0), 'l_wing': (0, 0, 60), 'r_wing': (0, 0, -60), 'mouth': 1}, {'neck': (-40, 0, 0), 'body': (-12, 0, 0), 'l_wing': (-20, 0, 120), 'r_wing': (-20, 0, -120), 'mouth': 1},
                  {'neck': (40, 0, 0), 'body': (24, 0, 0), 'l_wing': (40, 30, 60), 'r_wing': (40, -30, -60)}, {'neck': (50, 0, 0), 'body': (28, 0, 0), 'l_wing': (50, 40, 30), 'r_wing': (50, -40, -30)},
                  {'neck': (10, 0, 0), 'l_wing': (0, 0, 10), 'r_wing': (0, 0, -10)})
    elif kind == 'spit':
        attack = ({'neck': (-24, 0, 0), 'l_wing': (0, 0, 20), 'r_wing': (0, 0, -20)}, {'neck': (-42, 0, 0), 'body': (-12, 0, 0), 'head': (-20, 0, 0), 'l_wing': (0, 0, 35), 'r_wing': (0, 0, -35), 'mouth': 1},
                  {'neck': (30, 0, 0), 'head': (-10, 0, 0), 'body': (8, 0, 0), 'mouth': 1, 'bolt': 1}, {'neck': (20, 0, 0), 'mouth': 1}, {'neck': (4, 0, 0)})
    else:  # dive
        attack = ({'l_wing': (0, 0, 130), 'r_wing': (0, 0, -130), 'offset': (0, 14, 0), 'l_leg': (-60, 0, 0), 'r_leg': (-60, 0, 0)},
                  {'l_wing': (-30, 0, 70), 'r_wing': (-30, 0, -70), 'body': (30, 0, 0), 'offset': (0, 16, 0), 'l_leg': (-70, 0, 0), 'r_leg': (-70, 0, 0), 'mouth': 1},
                  {'l_wing': (-40, 0, 30), 'r_wing': (-40, 0, -30), 'body': (40, 0, 0), 'neck': (20, 0, 0), 'offset': (0, 6, 12), 'l_leg': (-80, 0, 0), 'r_leg': (-80, 0, 0), 'mouth': 1},
                  {'l_wing': (0, 0, 90), 'r_wing': (0, 0, -90), 'body': (10, 0, 0), 'offset': (0, 10, 8), 'l_leg': (-60, 0, 0), 'r_leg': (-60, 0, 0)}, {'l_wing': (0, 0, 20), 'r_wing': (0, 0, -20)})
    attack = [dict(p) for p in attack]
    for p in attack:
        if p.get('mouth'):
            p['jaw'] = (24, 0, 0)
    clips.append(attack_clip(base, *attack))
    clips.append(('hit', False, [(merged(base, p), 110) for p in ({'body': (-14, 0, 0), 'neck': (-20, 0, 0), 'l_wing': (0, 0, 30), 'r_wing': (0, 0, -30)}, {'body': (-6, 0, 0), 'neck': (-8, 0, 0)})]))
    death = [
        {'body': (-10, 0, 0), 'neck': (-30, 0, 0), 'l_wing': (0, 0, 50), 'r_wing': (0, 0, -50), 'jaw': (24, 0, 0)},
        {'root': (0, 0, 30), 'neck': (30, 0, 0), 'head': (20, 0, 0), 'l_wing': (0, 0, 40), 'r_wing': (0, 0, -20), 'offset': (0, -2, 0)},
        {'root': (0, 0, 60), 'neck': (60, 0, 20), 'head': (30, 0, 0), 'l_wing': (0, 0, 30), 'r_wing': (0, 0, -10), 'l_leg': (-30, 0, 0), 'offset': (0, -2, 0)},
        {'root': (0, 0, 80), 'neck': (70, 0, 30), 'head': (30, 0, 0), 'l_wing': (0, 0, 20), 'l_leg': (-40, 0, 0), 'r_leg': (-20, 0, 0), 'offset': (0, -1, 0)},
    ]
    clips.append(('death', False, [(merged(base, p), 140 if i < 3 else 500) for i, p in enumerate(death)]))
    return clips


def feathered(shades, seed, scale=1.0):
    """Layered feathers: rows of scalloped shades running down the body."""
    def material(x, y, z, pose):
        row = np.floor(y / (2.2 * scale)).astype(int)
        col = np.floor((x + z + (row % 2) * 1.5) / (3.0 * scale)).astype(int)
        edge = ((y / (2.2 * scale)) % 1.0) < 0.3
        out = pick(shades, hash2(row, col, seed) ** 1.4)
        return np.where(edge, shades[1], out)
    return material


def evil_duck():
    """The Evil Duck, the Ford Road's plain foe: a mallard gone wrong. Glossy
    dark-green head, a white collar, a chestnut breast over a grey-brown body,
    black-tipped wing feathers, red-rimmed eyes, a chipped yellow bill, and
    loose black pinfeathers trailing behind. Waddle-runs in flocks; a fast peck."""
    def body(x, y, z, pose):
        out = feathered([FEATHER_GREY[1], FEATHER_BROWN[2], FEATHER_GREY[0]], 330)(x, y, z, pose)
        breast = (z > 8) & (y > 38)
        return np.where(breast, pick(CHESTNUT, hash2(np.floor(x / 3).astype(int), np.floor(y / 2).astype(int), 331)), out)

    def head(x, y, z, pose):
        out = pick(MALLARD, hash2(np.floor(x / 2).astype(int) * 7 + np.floor(z / 2).astype(int), np.floor(y / 2).astype(int), 332) ** 1.5)
        return np.where(y < 59.5, CLOTH_PALE[0], out)
    b = Bird(body, feathered([FEATHER_BROWN[0], FEATHER_GREY[1], FEATHER_BROWN[1]], 333), leg=22,
             body=(16, 15, 24), neck=((0, 50, 15), (0, 66, 18)), neck_r=(7.5, 6.5), head=(7.6, 7.8, 8.8),
             bill=('duck', 14), eye=BLOOD[0], eye_r=1.9)
    # The head and neck in mallard green over a white ring; the body's colour
    # stays on the neck below the ring.
    hx, hy, hz = b.head_at
    b.part('head', ellipsoid(b.head_at, (7.7, 7.9, 8.9)), head)
    b.part('neck', where(capsule((0, 50, 15), (0, 66, 18), 7.6, 6.6), lambda x, y, z: (y > 56) & (y < 59)), CLOTH_PALE[0])
    b.part('neck', where(capsule((0, 50, 15), (0, 66, 18), 7.6, 6.6), lambda x, y, z: y >= 59), MALLARD[1])
    for side in (-1, 1):
        b.part('head', ellipsoid((side * 6.4, hy + 1.2, hz + 2.8), (1.6, 2.2, 2.2)), BLOOD[0])
        b.part('head', ellipsoid((side * 7.0, hy + 1.2, hz + 3.0), (1.1, 1.2, 1.2)), FACE_DARK[0])
    # The chipped bill: a notch out of its tip.
    b.part('head', ellipsoid((2.6, hy - 1.0, hz + 19.5), (1.6, 2.4, 1.8)), FACE_DARK[1])
    # Black-tipped wings, and loose pinfeathers trailing off the tail.
    for side, name in ((-1, 'r'), (1, 'l')):
        b.part(f'{name}_wing', ellipsoid((side * 16.8, 38, -20), (2.2, 6, 6)), RAVEN[0])
    for k in range(5):
        x = (k - 2) * 2.4
        b.part('tail', capsule((x, 46 - abs(k - 2), -30), (x * 1.6, 44 + (k % 2) * 3, -38 - k % 3 * 2), 1.4, 0.8), RAVEN[k % 2])
    fit(b.rig, 66)
    return b.rig, bird_clips('peck')


def road_drake():
    """The Road Drake: a duck the size of a sheepdog, dark grey-brown, with
    bald pink moult patches and a thick neck bristling with black quills.
    Puffs up, then charges with its head low."""
    b = Bird(feathered(FEATHER_BROWN, 220), feathered([FEATHER_BROWN[1], RAVEN[1], FEATHER_BROWN[0]], 221), leg=30,
             body=(15, 15, 25), neck=((0, 56, 14), (0, 78, 19)), neck_r=(8.0, 6.0))
    b.quills(14, 222, 9.0)
    b.patches(BALD, 223, 0.25)
    fit(b.rig, 72)
    return b.rig, bird_clips('charge')


def carrion_rook():
    """The Carrion Rook: a small scruffy crow, black with rusty patches, one
    eye filmed white. Hops in, pecks once, hops back."""
    b = Bird(feathered([RAVEN[0], RAVEN[1], FEATHER_BROWN[1]], 230), feathered([RAVEN[1], RAVEN[0], FEATHER_BROWN[2]], 231), leg=26,
             body=(13, 14, 24), neck=((0, 58, 14), (0, 72, 17)), neck_r=(8.5, 7.0), head=(7.4, 7.6, 8.4), bill=('crow', 11),
             bill_color=BILL_DARK, feet=[RAVEN[0], RAVEN[1]], gap=5, webbed=False, eye=FACE_DARK[1], eye_r=1.8)
    hx, hy, hz = b.head_at
    b.part('head', ellipsoid((6.2, hy + 1, hz + 2.6), (1.8, 2.2, 2.2)), EYE_WHITE[0])
    fit(b.rig, 40)
    return b.rig, bird_clips('hop')


def reed_duck():
    """The Reed Duck: a duck slick with fen mud, dead reeds tangled on its back. Peck."""
    b = Bird(feathered([MUD[0], FEATHER_BROWN[0], MUD[1]], 240), feathered([MUD[1], FEATHER_BROWN[1], MUD[0]], 241), leg=24,
             body=(15, 14, 24), neck=((0, 52, 15), (0, 72, 18)), neck_r=(7.0, 5.5), bill_color=[BILL[1], BILL_DARK[0]])
    cy = b.cy
    for k in range(10):
        x = (hash2(k, 0, 242) - 0.5) * 18
        b.part('body', capsule((x, cy + 12, 14 - k * 2), (x * 1.4 + (hash2(k, 1, 242) - 0.5) * 8, cy + 16 - (k % 3) * 3, -18 - k * 1.5), 0.8, 0.5), STRAW[k % 2])
    fit(b.rig, 62)
    return b.rig, bird_clips('peck')


def duckling():
    """A Duckling: grey fluff with black pinfeathers, oversized feet. A tiny peck."""
    b = Bird(speckled(FEATHER_GREY[:2] + [FEATHER_BROWN[2]], 250, 1, 1), feathered([FEATHER_GREY[1], RAVEN[1], FEATHER_GREY[0]], 251), leg=26,
             body=(16, 16, 20), neck=((0, 58, 10), (0, 70, 12)), neck_r=(9.0, 8.0), head=(10.0, 10.0, 10.0), bill=('duck', 11), gap=8, eye_r=2.4)
    for leg in ('l_leg', 'r_leg'):
        sx = 8 if leg == 'l_leg' else -8
        b.part(leg, where(ellipsoid((sx, 1.4, 6), (6.5, 1.5, 8.0)), lambda x, y, z: z > -1), FEET[0])
    fit(b.rig, 26)
    return b.rig, bird_clips('peck')


def goose(name, height, plume=False, scars=False):
    """A long-necked goose: grey, half bald, black quills down the neck, bill
    open and hissing. Old Greyneck is paler and scarred, with one long quill
    standing from its crown like a plume. Rears back, then a wing slam."""
    shades = FEATHER_PALE if plume else FEATHER_GREY
    b = Bird(feathered(shades, 260), feathered([shades[1], shades[0], FEATHER_GREY[1]], 261), leg=30,
             body=(17, 16, 27), neck=((0, 60, 16), (0, 98, 22)), neck_r=(6.0, 4.6), head=(6.0, 6.6, 8.6), bill=('duck', 15), gap=7)
    b.quills(18, 262, 6.0)
    b.patches(BALD, 263, 0.3)
    if scars:
        for k in range(4):
            b.part('neck', capsule((3.5, 70 + k * 6, 20), (4.5, 66 + k * 6, 18), 0.8), BLOOD[1])
    if plume:
        hx, hy, hz = b.head_at
        b.part('head', capsule((0, hy + 5, hz - 2), (0, hy + 22, hz - 9), 1.6, 1.1), RAVEN[1])
        b.part('head', capsule((0, hy + 22, hz - 9), (0, hy + 25, hz - 16), 1.1, 0.9), RAVEN[1])
    fit(b.rig, height)
    return b.rig, bird_clips('wingslam', base={'jaw': (14, 0, 0)})


def gallows_rook():
    """The Gallows Rook: a corvid with a raw rope-burn ring of bare skin round
    its neck, beak gaping. Walks by flying, wings spread; a straight dive."""
    b = Bird(feathered([RAVEN[0], RAVEN[1], FEATHER_BROWN[0]], 270), feathered([RAVEN[1], RAVEN[0], RAVEN[2]], 271), leg=24,
             body=(13, 14, 25), neck=((0, 58, 14), (0, 74, 18)), neck_r=(8.0, 6.6), head=(7.2, 7.6, 8.4), bill=('crow', 13),
             bill_color=BILL_DARK, feet=[RAVEN[0], RAVEN[1]], gap=5, webbed=False, eye_r=1.8)
    b.part('neck', where(capsule((0, 60, 14.4), (0, 72, 17.4), 8.0, 6.8), lambda x, y, z: (y > 64.5) & (y < 67.5)), BALD[0])
    fit(b.rig, 44)
    return b.rig, bird_clips('dive', flight=True)


def pond_drake():
    """The Pond Drake: a dark wet duck whose throat glows silver, silver drops
    falling from its bill. Rears back and spits a glowing water bolt."""
    b = Bird(feathered([FEATHER_BROWN[1], MUD[1], FEATHER_BROWN[0]], 280), feathered([FEATHER_BROWN[0], RAVEN[1], MUD[0]], 281), leg=26,
             body=(15, 14, 25), neck=((0, 54, 15), (0, 80, 19)), neck_r=(7.0, 5.4), bill_color=[BILL_DARK[0], BILL_DARK[1]])
    b.part('neck', where(capsule((0, 54, 15.4), (0, 78, 19.4), 7.1, 5.5), lambda x, y, z: (z > 15 + (y - 54) * 0.16 + 3.6) & (np.abs(x) < 3.6)), SILVER[1])
    hx, hy, hz = b.head_at
    for k in range(3):
        b.part('head', capsule((k - 1, hy - 4, hz + 12 + k * 2), (k - 1, hy - 9 - k * 2, hz + 12 + k * 2), 0.5), SILVER[2])
    # The spat bolt, there only on the strike frame.
    b.part('head', capsule((0, hy - 2, hz + 20), (0, hy - 3, hz + 46), 2.4, 1.2), SILVER[2], when=lambda pose: pose.get('bolt'))
    fit(b.rig, 70)
    return b.rig, bird_clips('spit')


def brood_drake():
    """The Brood Drake: an oversized, always-wet duck, grey feathers plastered
    thin over silver veins, milk-white eyes, water running off it. A short leap-peck."""
    def wet(x, y, z, pose):
        out = feathered([FEATHER_GREY[1], FEATHER_BROWN[2], FEATHER_GREY[0]], 290)(x, y, z, pose)
        vein = (np.abs(np.sin(x * 0.35 + y * 0.15) + np.sin(z * 0.25 - y * 0.1)) < 0.02)
        drip = hash2(np.floor(x / 2).astype(int) * 3 + np.floor(z / 2).astype(int), np.floor(y / 6).astype(int), 291) < 0.015
        return np.where(vein | drip, SILVER[0], out)
    b = Bird(wet, feathered([FEATHER_GREY[1], FEATHER_GREY[0], FEATHER_BROWN[2]], 292), leg=30,
             body=(15, 15, 25), neck=((0, 56, 14), (0, 84, 19)), neck_r=(7.0, 5.0), bill_color=[BILL_DARK[0], BILL_DARK[1]], eye=EYE_WHITE[0])
    fit(b.rig, 72)
    return b.rig, bird_clips('hop')


# The leech and the Brood-Mother.

def black_honey_leech():
    """The Black Honey Leech: a fat glossy black leech the length of a forearm,
    an amber sheen running up its back, a ringed pink mouth. Crawls by
    humping, lunges to bite; its death is a black splash."""
    r = Rig()
    r.bone('root', (0, 0, 0))
    segs, step = 7, 6.5
    # The chain runs from the tail (s6) to the head (s0), so turning a
    # segment lifts only what lies ahead of it.
    prev = 'root'
    for k in reversed(range(segs)):
        z = 20 - k * step
        r.bone(f's{k}', (0, 8, z - step / 2), prev)
        prev = f's{k}'

    def skin(x, y, z, pose):
        ring = (np.floor(z * 0.9).astype(int) % 3) == 0
        sheen = (np.abs(x - np.sin(z * 0.18) * 3) < 1.4) & (y > 10.5)
        out = np.where(ring, HONEY[0], HONEY[1])
        return np.where(sheen, HONEY[2], out)
    for k in range(segs):
        z = 20 - k * step
        t = k / (segs - 1)
        width = 7.6 * (1.0 - 0.55 * abs(t - 0.35) ** 1.3)
        r.part(f's{k}', ellipsoid((0, 8.5, z), (width, width * 0.9, step * 0.8)), skin)
    r.part('s0', minus(ellipsoid((0, 9, 25), (4.4, 4.4, 1.8)), ellipsoid((0, 9, 26), (2.2, 2.2, 2.4))), LEECH_MOUTH[0])
    r.part('s0', ellipsoid((0, 9, 24.6), (2.4, 2.4, 1.2)), LEECH_MOUTH[1])
    r.part('root', where(ellipsoid((0, 8.5, 0), (20, 2, 22)), lambda x, y, z: hash2(np.floor(x / 2).astype(int), np.floor(z / 2).astype(int), 300) < 0.7),
           HONEY[0], when=lambda pose: pose.get('splash'))
    fit(r, 14)

    def wave(amount, shift):
        return {f's{k}': (amount * math.sin(k * 1.2 + shift), 0, 0) for k in range(segs)}
    clips = [('idle', True, [(wave(4, a), 300) for a in (0, 1.6, 3.2, 4.8)])]
    clips.append(('walk', True, [(wave(14, a), 140) for a in (0, 1.6, 3.2, 4.8)]))
    clips.append(attack_clip({}, {'s0': (-30, 0, 0), 's1': (-20, 0, 0), 's2': (10, 0, 0)}, {'s0': (-40, 0, 0), 's1': (-35, 0, 0), 's2': (20, 0, 0)},
                             {'s0': (30, 0, 0), 's1': (20, 0, 0), 's2': (-5, 0, 0), 'offset': (0, 0, 8)}, {'s0': (24, 0, 0), 's1': (10, 0, 0), 'offset': (0, 0, 5)}, {}))
    clips.append(('hit', False, [({'s0': (-20, 0, 0), 's1': (-10, 0, 0)}, 110), ({'s0': (-8, 0, 0)}, 110)]))
    # It sinks into its own black splash: the splash sits 8 up so it lands on
    # the ground once the body has dropped by 8.
    clips.append(('death', False, [({'s0': (-30, 0, 0), 's6': (-30, 0, 0)}, 140), ({'offset': (0, -6, 0), 's0': (10, 0, 0)}, 140),
                                   ({'offset': (0, -8, 0), 'splash': 1}, 140), ({'offset': (0, -9.5, 0), 'splash': 1}, 500)]))
    return r, clips


def mardra():
    """Goodwife Mardra Hobb, Brood-Mother of the Millpond, the Act I boss:
    half woman, half moulting fowl. A goodwife's dress and apron split at the
    back by great grey wings shedding black feathers, scaled bird legs and
    taloned feet, a long scaly neck, a woman's face going to beak under a cap,
    a large grey ring fused round her right hand. A wing buffet."""
    b = Body(shoulder=9.4, waist=7.6, depth=5.6, bust=1.2)
    r = b.rig
    dress = speckled([SMOCK[1], SMOCK[0], BURLAP[1]], 310, 2, 3)
    scaly = lambda x, y, z, pose: np.where((np.floor(y) + np.floor(x + z)) % 3 == 0, BALD[1], pick(SKIN[1:], hash2(np.floor(x).astype(int), np.floor(y).astype(int), 311)))  # noqa: E731
    for side, name in ((-3.6, 'r'), (3.6, 'l')):
        r.bone(f'{name}_hip', (side, 30, 0), 'root')
        r.bone(f'{name}_knee', (side, 14, -2), f'{name}_hip')
        r.part(f'{name}_hip', capsule((side, 30, 0), (side, 14, -2), 2.6, 2.0), scaly)
        r.part(f'{name}_knee', capsule((side, 14, -2), (side, 2.5, 0.5), 1.8, 1.4), scaly)
        r.part(f'{name}_knee', union(*[capsule((side, 1.5, 0.5), (side + dx, 0.6, 0.5 + dz), 0.8, 0.4) for dx, dz in ((-3, 6), (0, 7), (3, 6), (0, -4))]), BILL_DARK[0])
    body, rx, rz = b.skirt(dress, hem=22, flare=4.0, wave=0.0)
    b.rig.parts.pop()
    b.part('root', ragged(column(22, 39, rx, rz, flat(0.3)), 22, 312, 5.0, 0.04), dress)
    b.torso(dress)

    def stained(x, y, z, pose):
        out = pick([CLOTH_PALE[1], STRAW[1]], hash2(np.floor(x / 2).astype(int), np.floor(y / 5).astype(int), 313))
        return np.where(hash2(np.floor(x / 2.5).astype(int), np.floor(y / 2.5).astype(int), 314) < 0.12, BLOOD[0], out)
    b.apron(stained, hem=20, low_half=7.6, bib_half=5.6, straps=LEATHER[2], flare=4.0)
    b.belt(LEATHER[2], y=37.5, buckle=None, height=1.6)
    b.arm(-1, (-9.4, 53, 0), (-11.2, 42, 2.0), (-10.8, 33, 6.0), dress, SKIN, SKIN[1], r=2.8, cuff=CLOTH_PALE[1])
    b.arm(1, (9.4, 53, 0), (11.2, 42, 1.0), (11.0, 32, 3.0), dress, SKIN, SKIN[1], r=2.8, cuff=CLOTH_PALE[1])
    b.part('r_elbow', minus(ellipsoid((-10.7, 31.5, 7.5), (3.2, 2.0, 3.2)), ellipsoid((-10.7, 31.5, 7.5), (2.0, 3, 2.0))),
           lambda x, y, z, pose: np.full(np.shape(x), SILVER[2] if pose.get('ring') else SILVER[1]))
    # The long scaly neck, the face going to beak, a goodwife's cap.
    b.part('chest', capsule((0, 54, 0.5), (0, 66, 2.5), 3.2, 2.6), scaly)
    b.part('head', ellipsoid((0, 70, 2.4), (4.2, 5.0, 4.6)), lambda x, y, z, pose: np.where((z > 5.0) & (np.abs(np.abs(x) - 1.7) < 0.7) & (np.abs(y - 70.6) < 0.6), EYE_WHITE[0], pick(SKIN[:2], hash2(np.floor(x).astype(int), np.floor(y).astype(int), 315))))
    b.part('head', capsule((0, 68.8, 6.0), (0, 66.4, 11.5), 1.8, 0.4), BILL[1])
    b.part('head', where(ellipsoid((0, 71.6, 1.6), (5.2, 4.6, 5.6)), lambda x, y, z: y > 71.0), CLOTH_PALE[1])
    b.part('head', ellipsoid((0, 68.4, -2.8), (3.6, 4.2, 2.0)), speckled(HAIR_GREY, 316, 1, 1))
    # The wings, folded down her back almost to the ground: flat, layered
    # dark-grey feathers with ragged black tips, shedding.
    def plumage(x, y, z, pose):
        row = np.floor(y / 2.6).astype(int)
        col = np.floor((z + (row % 2) * 1.6) / 3.2).astype(int)
        out = pick([FEATHER_GREY[1], FEATHER_BROWN[0], FEATHER_GREY[0]], hash2(row, col, 318) ** 1.6)
        out = np.where(((y / 2.6) % 1.0) < 0.3, FEATHER_BROWN[1], out)
        return np.where(y < 26, RAVEN[1], out)
    for side, name in ((-1, 'r'), (1, 'l')):
        r.bone(f'{name}_wing', (side * 5, 54, -5), 'chest')
        wing = union(ellipsoid((side * 8.5, 40, -9.5), (2.8, 20, 9)), ellipsoid((side * 7.5, 52, -7), (4.0, 6, 6)))
        ragged_tips = lambda x, y, z: (y > 21 + hash2(np.floor(z / 2).astype(int), 0, 319) * 6) | (hash2(np.floor(z).astype(int), np.floor(y).astype(int), 320) < 0.5)  # noqa: E731
        b.part(f'{name}_wing', where(wing, ragged_tips), plumage)
    fit(r, 72)
    attack = ({'l_wing': (0, 0, 50), 'r_wing': (0, 0, -50), 'chest': (-6, 0, 0), 'head': (-10, 0, 0)},
              {'l_wing': (-20, 0, 110), 'r_wing': (-20, 0, -110), 'chest': (-12, 0, 0), 'head': (-16, 0, 0), 'ring': 1},
              {'l_wing': (40, 70, 80), 'r_wing': (40, -70, -80), 'chest': (20, 0, 0), 'head': (10, 0, 0)},
              {'l_wing': (40, 80, 50), 'r_wing': (40, -80, -50), 'chest': (24, 0, 0)}, {'l_wing': (0, 0, 10), 'r_wing': (0, 0, -10), 'chest': (6, 0, 0)})
    idle = [{}, {'l_wing': (0, 0, 8), 'r_wing': (0, 0, -8), 'head': (4, 10, 0)}, {'head': (2, 4, 0), 'ring': 1}, {'l_wing': (0, 0, 4), 'r_wing': (0, 0, -4), 'head': (0, -8, 0)}]
    return r, human_clips({}, attack, lean=6, stride=16, swing=8, idle=idle)


ENEMIES = {
    'PilgrimPenitent': (pilgrim_penitent, (72, 96, 120)),
    'TitheStray': (tithe_stray, (60, 90, 90)),
    'BlackHoneyFiend': (black_honey_fiend, (64, 90, 100)),
    'MillhandThrall': (millhand_thrall, (64, 100, 100)),
    'Cuffman': (red_cuff, (64, 100, 100)),
    'BladelockArbalist': (lambda: red_cuff(arbalist=True), (64, 90, 100)),
    'SergeantOttar': (lambda: red_cuff(sergeant=True), (64, 100, 100)),
    'HollowedBearer': (hollowed_bearer, (64, 90, 90)),
    'RingKeeperWarden': (ring_keeper_warden, (70, 100, 100)),
    'EvilDuck': (evil_duck, (90, 80, 100)),
    'RoadDrake': (road_drake, (100, 90, 110)),
    'CarrionRook': (carrion_rook, (60, 60, 70)),
    'ReedDuck': (reed_duck, (90, 80, 100)),
    'Duckling': (duckling, (40, 36, 44)),
    'MoultedGander': (lambda: goose('MoultedGander', 72), (110, 90, 100)),
    'OldGreyneck': (lambda: goose('OldGreyneck', 72, plume=True, scars=True), (110, 90, 100)),
    'GallowsRook': (gallows_rook, (100, 80, 80)),
    'PondDrake': (pond_drake, (90, 84, 110)),
    'BroodDrake': (brood_drake, (90, 96, 100)),
    'BlackHoneyLeech': (black_honey_leech, (44, 40, 60)),
    'Mardra': (mardra, (100, 90, 100)),
}



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    for name in args.names or ENEMIES:
        make, size = ENEMIES[name]
        rig, clips = make()
        build(name, rig, clips, size, args.preview)


if __name__ == '__main__':
    main()
