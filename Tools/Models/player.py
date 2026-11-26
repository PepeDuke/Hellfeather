"""Builds the player, Wren Carrow, from a figure.py rig into Assets/Warrior.qvox.

Wren is a thief-taker and ex-miner: a lean woman in her thirties in a worn
oilcloth coat over a leather jerkin, a miner's leather cap with its lamp pushed
back, a grey scarf over her mouth for the Grey Cough, her right sleeve rolled to
show the Tithe-mark, a silver lattice from wrist to elbow (Story.md).

The game (Warrior.dk, HellfeatherGame.dk) plays idle and walk, pain when the
Tithe-mark takes (its glow rides the `mark` socket), and for her actions
attack, cleave and shout, each with a twin ending in _walk that has the
walk's legs under the same upper body, for acting on the move. Her axe, Assets/BattleAxe.qvox, rides the `hand_r` socket that every
frame carries. The swing lands on frame 3 (HellfeatherGame.AxeStrikeFrame).
HellfeatherWarrior.Height must be the model's box height, the middle number the
build prints, because the game stands her by half of it; VoxelSize stays 0.025.

    python Tools/Models/player.py --preview
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enemies import legs  # noqa: E402
from figure import build_variants, capsule, column, ellipsoid, fit, minus, union, where  # noqa: E402
from kit import (BRASS, CLOTH_RED, FACE_DARK, HAIR_DARK, IRON, LEATHER, MUD, SCARF, SILVER, SKIN, SMOCK,  # noqa: E402
                 TROUSERS, color, hash2, pick)
from people import Body, coat_front, flat, speckled  # noqa: E402

HEIGHT = 78
# WarriorUnmarked and WarriorLeatherArmorUnmarked are the same bodies before
# the Tithe-mark (Quests.TitheMark), with the lattice left off her forearm.
# Oilcloth: a greasy olive-brown, darker in the creases.
OILCLOTH = [MUD[0], MUD[1], SCARF[1]]
VEST = [SMOCK[1], SMOCK[0], SCARF[0]]
SHORTS = [SCARF[1], MUD[0]]
# Scale mail's bronze plates and the dark gaps between their rows.
BRONZE = color('bronze scale', (156, 112, 60), (128, 90, 48), (176, 132, 76))
BRONZE_DARK = color('bronze gap', (62, 44, 28))


def ring_mail(x, y, z, pose):
    """Riveted rings, light and dark in alternate rows and columns, so a
    hauberk reads as mail at one voxel to a ring."""
    row = np.floor(y).astype(int)
    column = np.floor((x + z) * 0.9).astype(int)
    lit = (row + column) % 2 == 0
    return np.where(lit, IRON[1], np.where(hash2(column, row, 451) < 0.25, SILVER[1], IRON[0]))


def scale_mail(x, y, z, pose):
    """Overlapping bronze scales in rows two voxels tall, each row shifted by
    half a scale, with dark gaps under and between them."""
    row = np.floor(y / 2.0).astype(int)
    along = (x + z) * 0.8 + (row % 2) * 1.0
    gap_below = (y - row * 2.0) < 0.55
    gap_side = (np.floor(along).astype(int) % 2 == 0) & ((along % 1.0) < 0.25)
    out = pick(BRONZE, hash2(np.floor(along).astype(int), row, 452))
    return np.where(gap_below | gap_side, BRONZE_DARK[0], out)


def plate_mail(x, y, z, pose):
    """Bands of polished steel, three voxels tall, with dark seams between."""
    band = np.floor(y / 3.0).astype(int)
    out = np.where(band % 2 == 0, SILVER[1], SILVER[0])
    seam = (y - band * 3.0) < 0.6
    return np.where(seam, IRON[0], out)


# The patterns of each body armor's coat, and its trim, over the same coat shape.
ARMOR = {
    'ring': (ring_mail, IRON[0]),
    'scale': (scale_mail, BRONZE_DARK[0]),
    'plate': (plate_mail, IRON[0]),
}


# The head socket sits at the middle of her skull; helmets are built around it
# (Tools/Models/gear.py), in rest rig coordinates before scaling.
HEAD = (0.0, 63.0, 1.2)


def wren(armor=False, marked=True):
    """armor is False, True or 'leather' for the Leather Armor, or 'ring',
    'scale' or 'plate' for the mail coats, which are the same coat in metal."""
    return wren_body(armor, marked)


def wren_body(armor, marked):
    """Wren in her basic attire: a worn sleeveless vest and shorts, barefoot,
    the Tithe-mark on her right forearm, dark hair in a loose bun. With armor,
    the Leather Armor on top: the oilcloth coat over a leather jerkin, a coat
    sleeve rolled above the Tithe-mark, a glove, trousers and boots, and the
    scarf over her mouth for the Grey Cough. Both share bones and sockets.
    Unmarked, she is as she was before Jessa gave her the mark: the same
    forearm without the lattice."""
    b = Body(shoulder=9.0, waist=7.0, depth=5.0, bust=1.0)
    r = b.rig
    skin = speckled(SKIN[:2], 406, 2, 3)
    vest = speckled(VEST, 407, 2, 3)

    # The body as she is: bare legs and feet, shorts, the vest.
    legs(b, skin, SKIN[1], gap=3.4, thigh=(2.9, 2.2), shin=(2.1, 1.5))
    # Coat tails hang from the waist on each side and follow their leg (see
    # COAT_FOLLOW). Both outfits have the bones, so they share clips.
    r.bone('r_coat', (-3.6, 39, 0), 'root')
    r.bone('l_coat', (3.6, 39, 0), 'root')
    for name, sx in (('r_hip', -3.6), ('l_hip', 3.6)):
        b.part(name, capsule((sx * 1.05, 34, 0), (sx, 27.5, 0.2), 3.7, 3.4), speckled(SHORTS, 408, 2, 2))
    b.part('root', column(29, 39, flat(7.6), flat(5.6), flat(0.2)), speckled(SHORTS, 408, 2, 2))

    def top(x, y, z, pose):
        out = vest(x, y, z, pose)
        neck = (z > 0) & (y > 51.5) & (np.abs(x) < 4.0 - (56 - y) * 0.25)
        shoulders = (np.abs(x) > 5.6) & (y > 50.5)
        return np.where(neck | shoulders, SKIN[0], out)
    b.torso(top)
    b.arm(-1, (-9.0, 53, 0), (-10.6, 42, 1.0), (-10.8, 32.5, 3.0), skin, SKIN, SKIN[1], r=2.6, cuff=SKIN[0])
    b.arm(1, (9.0, 53, 0), (10.6, 42, 1.0), (10.6, 32.5, 2.6), skin, SKIN, SKIN[1], r=2.6, cuff=SKIN[0])

    def lattice(x, y, z, pose):
        return np.full(np.shape(x), SILVER[1])

    def woven(x, y, z):
        u = np.arctan2(z - 2.0, x + 10.7) * 2.6
        return (np.abs(((u + y * 0.55) % 2.0) - 1.0) < 0.28) | (np.abs(((u - y * 0.55) % 2.0) - 1.0) < 0.28)
    if marked:
        b.part('r_elbow', where(capsule((-10.65, 40.0, 1.3), (-10.8, 33.5, 2.8), 2.15, 1.85), woven), lattice)
    b.head(SKIN)
    b.hair(HAIR_DARK, 'bun')
    b.part('head', ellipsoid((-4.2, 61.5, 1.0), (1.0, 2.6, 1.4)), HAIR_DARK[1])

    if armor:
        coat = speckled(OILCLOTH, 400, 2, 4)
        jerkin = speckled(LEATHER[1:3], 401, 2, 3)
        trim = MUD[1]
        if armor in ARMOR:
            coat, trim = ARMOR[armor]
            jerkin = coat
        # Trousers over her legs and tall laced boots to the knee.
        for side, hip, knee in ((-3.6, 'r_hip', 'r_knee'), (3.6, 'l_hip', 'l_knee')):
            b.part(hip, capsule((side, 34, 0), (side, 18, 0.4), 3.6, 3.1), speckled(TROUSERS, 402))
            b.part(knee, capsule((side, 17, 0.4), (side, 3, 0), 2.9, 2.4),
                   lambda x, y, z, pose: np.where(np.floor(y) % 4 == 0, LEATHER[2], LEATHER[1]))
            b.part(knee, capsule((side, 17.5, 0.4), (side, 16.0, 0.4), 3.3), LEATHER[3])
            b.part(knee, union(ellipsoid((side, 1.6, 1.9), (2.5, 1.7, 3.6)), capsule((side, 3, 0), (side, 1.2, 0.5), 2.1)), FACE_DARK[0])
        # The long coat, open in front to show the jerkin, to just below the knee.
        # Its tails hang from the coat bones rather than the root, split down the
        # back like a riding coat's vent, so each tail swings with its leg instead
        # of the leg pushing through it.
        opening = coat_front(1.8, 5.0, hem=14)
        tails, _, _ = b.skirt(coat, hem=14, flare=3.6, wave=0.4, front_cut=opening, grow=0.6)
        r.parts.pop()
        b.part('r_coat', where(tails, lambda x, y, z: x < 0.6), coat)
        b.part('l_coat', where(tails, lambda x, y, z: x > -0.6), coat)

        def chest(x, y, z, pose):
            out = coat(x, y, z, pose)
            front = z > 1.8
            inside = front & (np.abs(x) < opening(y))
            lapel = front & (np.abs(x) >= opening(y)) & (np.abs(x) < opening(y) + 1.8) & (y > 44)
            out = np.where(lapel, trim, out)
            out = np.where(inside, jerkin(x, y, z, pose), out)
            strap = inside & ((np.abs(y - 47) < 0.7) | (np.abs(y - 42.5) < 0.7))
            return np.where(strap, LEATHER[2], out)
        b.torso(chest, grow=0.7)
        b.belt(LEATHER[2], y=37, buckle=BRASS[0], height=2.2)
        b.part('chest', capsule((-6.5, 54.5, 4.8), (6.5, 38.5, 7.2), 0.9), LEATHER[2])
        # Pouches on the coat tails, so they ride with the cloth.
        b.part('l_coat', ellipsoid((6.8, 34.0, 6.8), (2.6, 3.0, 1.8)), LEATHER[1])
        b.part('r_coat', ellipsoid((-6.0, 33.6, 7.2), (2.0, 2.4, 1.6)), LEATHER[1])
        # Sleeves: the right rolled above the Tithe-mark, the left full, gloved.
        b.part('r_shoulder', capsule((-9.0, 53, 0), (-10.6, 42, 1.0), 3.3, 3.0), coat)
        b.part('r_elbow', capsule((-10.6, 42.5, 1.0), (-10.65, 40.6, 1.2), 3.4), trim)
        b.part('l_shoulder', capsule((9.0, 53, 0), (10.6, 42, 1.0), 3.3, 3.0), coat)
        b.part('l_elbow', capsule((10.6, 42, 1.0), (10.6, 32.5, 2.6), 2.9, 2.6), coat)
        b.part('l_elbow', capsule((10.6, 34.5, 2.3), (10.6, 32.5, 2.6), 3.1), trim)
        b.part('l_elbow', ellipsoid((10.6, 30.3, 2.9), (2.2, 2.6, 2.2)), LEATHER[2])
        # A red kerchief at the throat, the grey scarf over mouth and nose.
        b.part('chest', ellipsoid((0, 55.4, 0.6), (5.6, 2.0, 5.0)), CLOTH_RED[1])
        scarf = minus(ellipsoid((0, 59.8, 1.4), (5.0, 3.6, 5.4)), lambda x, y, z: (z < -1.0) & (y > 61))
        b.part('head', where(scarf, lambda x, y, z: y < 62.6), speckled(SCARF, 403, 1, 2))

    # Sockets for what she holds and wears. The weapon hangs head-down from her
    # right fist, its haft leaning a little forward and the blade turned back;
    # this turn suits weapons made like the Battle Axe (gear.py). Check it with
    #   python Tools/Models/inspect_models.py WarriorLeatherArmor --gear hand_r=BattleAxe
    # The shield rides her left forearm facing out, the helmet her head.
    r.socket('hand_r', 'r_elbow', (-11.0, 30.6, 3.4), yaw=180, pitch=30, roll=180)
    r.socket('hand_l', 'l_elbow', (13.4, 37.0, 1.8), yaw=90)
    r.socket('head', 'head', HEAD)
    # The middle of the Tithe-mark, where the game puts its glow.
    r.socket('mark', 'r_elbow', (-10.7, 36.8, 3.6))
    return b

# How far each coat tail turns with its leg, as a share of the hip's pitch.
COAT_FOLLOW = 0.8
# One walk cycle: eight frames of 76 milliseconds.
WALK_MS = 8 * 76
LEGS = ('r_hip', 'l_hip', 'r_knee', 'l_knee', 'offset')


def walk_legs(a):
    """Hips, knees and the bob of the walk at phase a, in radians."""
    s = math.sin(a)
    return {'r_hip': (-26 * s, 0, 0), 'l_hip': (26 * s, 0, 0),
            # Each knee bends as its leg swings through.
            'r_knee': (6 + 26 * max(0.0, -math.sin(a - 0.6)), 0, 0),
            'l_knee': (6 + 26 * max(0.0, math.sin(a - 0.6)), 0, 0),
            'offset': (0, -0.8 * (1 - abs(math.cos(a))), 0)}


# Where her feet land in the walk cycle, in milliseconds: each hip swings
# furthest and the bob sits lowest a quarter and three quarters of the way round.
FOOTFALLS = (WALK_MS // 4, 3 * WALK_MS // 4)


def footsteps(clips):
    """A `footstep` call on each frame of the walk, and of the actions' _walk
    twins, during which a foot lands. Their legs keep the walk's timing from
    the clip's start, so the same moments apply."""
    calls = {}
    for name, looping, frames in clips:
        if name != 'walk' and not name.endswith('_walk'):
            continue
        at, marks = 0, {}
        for k, (_, ms) in enumerate(frames):
            if any((t - at) % WALK_MS < ms for t in FOOTFALLS):
                marks[k] = ['footstep']
            at += ms
        calls[name] = marks
    return calls


# The swing's sounds on her attack clips: the grip and creak as she winds up,
# and the whoosh on the downswing, just before the blow lands on frame 3.
SWING_CALLS = {0: ['swing_start'], 2: ['swing_whoosh']}
SWINGS = ('attack', 'attack_walk', 'cleave', 'cleave_walk')


def frame_calls(clips):
    """Every frame's `call` lines, for the game's AnimationCall: footsteps and
    the swing's sounds. Hit or miss plays from the game, which knows which."""
    calls = footsteps(clips)
    for name, _, frames in clips:
        if name not in SWINGS:
            continue
        marks = calls.setdefault(name, {})
        for k, names in SWING_CALLS.items():
            if k < len(frames):
                marks[k] = names + marks.get(k, [])
    return calls


def walking(frames):
    """The same frames with the walk's legs under them, for using an action on
    the move. The upper body keeps the action's pose and timing; the legs and
    the bob come from the walk at the matching moment of its cycle."""
    out, at = [], 0
    for pose, ms in frames:
        upper = {k: v for k, v in pose.items() if k not in LEGS}
        upper.update(walk_legs(2 * math.pi * (at + ms / 2) / WALK_MS))
        out.append((upper, ms))
        at += ms
    return out


def clips():
    hunch = {'chest': (5, 0, 0), 'head': (-4, 0, 0)}

    def with_hunch(pose):
        out = dict(hunch)
        for k, v in pose.items():
            out[k] = tuple(a + b for a, b in zip(out.get(k, (0, 0, 0)), v)) if isinstance(v, tuple) else v
        # The coat tails follow the legs, so a stride never pokes through them.
        for side in ('r', 'l'):
            pitch = out.get(f'{side}_hip', (0, 0, 0))[0]
            out[f'{side}_coat'] = (pitch * COAT_FOLLOW, 0, 0)
        return out
    idle = [
        ({}, 500), ({'chest': (1, 0, 0)}, 500), ({'chest': (2, 0, 0), 'head': (2, 8, 0)}, 500), ({'chest': (1, 0, 0), 'head': (1, 4, 0)}, 500),
        # The Grey Cough: doubled forward, the gloved hand to the scarf.
        ({'chest': (14, 0, 0), 'head': (12, 0, 0), 'l_shoulder': (-55, 0, 14), 'l_elbow': (-80, 0, 0)}, 160),
        ({'chest': (18, 0, 0), 'head': (16, 0, 0), 'l_shoulder': (-60, 0, 16), 'l_elbow': (-85, 0, 0)}, 160),
        ({'chest': (10, 0, 0), 'head': (8, 0, 0), 'l_shoulder': (-40, 0, 10), 'l_elbow': (-60, 0, 0)}, 220),
        ({'chest': (2, 0, 0)}, 500),
    ]
    walk = []
    for k in range(8):
        a = k * math.pi / 4
        s = math.sin(a)
        walk.append((dict(walk_legs(a), **{
            'chest': (8, 0, 3 * s), 'head': (-4, 0, -2 * s),
            'r_shoulder': (16 * s, 0, 0), 'l_shoulder': (-16 * s, 0, 0), 'l_elbow': (-12, 0, 0), 'r_elbow': (-14, 0, 0)}), 76))
    step = {'l_hip': (-22, 0, 0), 'r_hip': (12, 0, 0), 'l_knee': (14, 0, 0), 'r_knee': (8, 0, 0)}
    # The chest twists little against the hips and the shoulder takes the rest,
    # so the coat stays whole around the belt.
    attack = [
        ({'r_shoulder': (-30, -6, -10), 'r_elbow': (-40, 0, 0), 'chest': (4, -6, 0)}, 72),
        (dict(step, r_shoulder=(-125, -8, -14), r_elbow=(-70, 0, 0), chest=(-6, -10, 0), head=(-4, -6, 0), l_shoulder=(-30, 0, 10)), 95),
        (dict(step, r_shoulder=(-165, -8, -10), r_elbow=(-80, 0, 0), chest=(-12, -12, 0), head=(-6, -6, 0), l_shoulder=(-40, 0, 14)), 48),
        # The blow lands here, frame 3.
        (dict(step, r_shoulder=(-75, 8, 0), r_elbow=(-8, 0, 0), chest=(22, 8, 0), head=(6, 4, 0), l_shoulder=(10, 0, 8), offset=(0, -1.0, 0)), 48),
        (dict(step, r_shoulder=(-25, 10, 8), r_elbow=(0, 0, 0), chest=(28, 10, 0), head=(8, 4, 0), l_shoulder=(16, 0, 8), offset=(0, -1.5, 0)), 80),
        ({'r_shoulder': (-20, 0, 0), 'r_elbow': (-20, 0, 0), 'chest': (14, 4, 0), 'l_hip': (-8, 0, 0)}, 85),
        ({'r_shoulder': (-8, 0, 0), 'chest': (6, 2, 0)}, 70),
    ]
    # Cleave: the axe held out level and swept across in front of her, from
    # her right side to her left. The blow lands on frame 3 as it passes the front.
    brace = {'l_hip': (-16, 0, 6), 'r_hip': (8, 0, -6), 'l_knee': (12, 0, 0), 'r_knee': (10, 0, 0), 'offset': (0, -0.8, 0)}
    cleave = [
        ({'r_shoulder': (-50, -40, -20), 'r_elbow': (-30, 0, 0), 'chest': (4, -8, 0), 'l_shoulder': (-20, 0, 10)}, 70),
        (dict(brace, r_shoulder=(-80, -95, 0), r_elbow=(-15, 0, 0), chest=(2, -14, 0), head=(0, -8, 0), l_shoulder=(-35, 20, 20), l_elbow=(-30, 0, 0)), 110),
        (dict(brace, r_shoulder=(-88, -55, 0), r_elbow=(-5, 0, 0), chest=(4, -8, 0), head=(0, -4, 0), l_shoulder=(-30, 10, 18), l_elbow=(-30, 0, 0)), 40),
        # The blow lands here, frame 3: the axe straight out in front.
        (dict(brace, r_shoulder=(-90, 5, 0), r_elbow=(0, 0, 0), chest=(8, 4, 0), head=(2, 2, 0), l_shoulder=(-10, 0, 14), l_elbow=(-20, 0, 0)), 45),
        (dict(brace, r_shoulder=(-85, 60, 0), r_elbow=(-5, 0, 0), chest=(10, 12, 0), head=(4, 6, 0), l_shoulder=(10, 0, 12)), 60),
        (dict(brace, r_shoulder=(-70, 80, 10), r_elbow=(-20, 0, 0), chest=(10, 14, 0), head=(4, 6, 0), l_shoulder=(12, 0, 10)), 90),
        ({'r_shoulder': (-35, 30, 0), 'r_elbow': (-25, 0, 0), 'chest': (8, 6, 0), 'l_hip': (-6, 0, 0)}, 85),
        ({'r_shoulder': (-10, 0, 0), 'chest': (4, 2, 0)}, 70),
    ]
    # War Cry: she gathers herself, then throws her arms wide and her head back
    # and yells, holds it, and settles.
    stance = {'l_hip': (-6, 0, 10), 'r_hip': (4, 0, -10), 'l_knee': (8, 0, 0), 'r_knee': (8, 0, 0), 'offset': (0, -0.6, 0)}
    shout = [
        ({'chest': (16, 0, 0), 'head': (8, 0, 0), 'r_shoulder': (-30, 0, 20), 'l_shoulder': (-30, 0, -20), 'r_elbow': (-70, 0, 0), 'l_elbow': (-70, 0, 0)}, 110),
        (dict(stance, chest=(-14, 0, 0), head=(-18, 0, 0), r_shoulder=(-20, 0, -70), l_shoulder=(-20, 0, 70), r_elbow=(-50, 0, 0), l_elbow=(-50, 0, 0), mouth=2), 90),
        (dict(stance, chest=(-16, 0, 0), head=(-20, 0, 0), r_shoulder=(-25, 0, -75), l_shoulder=(-25, 0, 75), r_elbow=(-60, 0, 0), l_elbow=(-60, 0, 0), mouth=2), 260),
        (dict(stance, chest=(-8, 0, 0), head=(-10, 0, 0), r_shoulder=(-15, 0, -45), l_shoulder=(-15, 0, 45), r_elbow=(-35, 0, 0), l_elbow=(-35, 0, 0), mouth=1), 120),
        ({'chest': (2, 0, 0), 'r_shoulder': (-8, 0, -10), 'l_shoulder': (-8, 0, 10)}, 110),
    ]
    # Pain: the Tithe-mark takes. She snatches the marked arm in against her
    # chest, kept low so the axe in that hand never looks raised to strike,
    # then doubles over it, clutching the forearm with her left hand,
    # shudders, and straightens.
    crouch = {'l_hip': (-14, 0, 0), 'r_hip': (-10, 0, 0), 'l_knee': (18, 0, 0), 'r_knee': (16, 0, 0), 'offset': (0, -1.6, 0)}
    clutch = dict(crouch, chest=(26, 0, 0), head=(16, 0, 0), r_shoulder=(-34, 0, 16), r_elbow=(-78, 0, 0),
                  l_shoulder=(-48, 0, -26), l_elbow=(-58, 0, 0), mouth=1)
    pain = [
        ({'r_shoulder': (-22, 0, 14), 'r_elbow': (-55, 0, 0), 'chest': (-8, 0, 0), 'head': (-12, 0, 0), 'mouth': 2}, 110),
        ({'r_shoulder': (-28, 0, 18), 'r_elbow': (-70, 0, 0), 'chest': (-12, 4, 0), 'head': (-16, 4, 0), 'l_shoulder': (-20, 0, -10), 'mouth': 2}, 160),
        (dict(clutch, chest=(18, 0, 0), head=(10, 0, 0)), 140),
        (clutch, 320),
        (dict(clutch, chest=(28, 0, 3), head=(18, 0, 2)), 120),
        (dict(clutch, chest=(25, 0, -3), head=(15, 0, -2)), 120),
        (dict(clutch, chest=(28, 0, 2), head=(18, 0, 1)), 120),
        (clutch, 420),
        ({'chest': (14, 0, 0), 'head': (6, 0, 0), 'r_shoulder': (-24, 0, 8), 'r_elbow': (-50, 0, 0), 'l_shoulder': (-22, 0, -10), 'l_elbow': (-30, 0, 0),
          'l_knee': (8, 0, 0), 'r_knee': (6, 0, 0), 'offset': (0, -0.6, 0)}, 260),
        ({'chest': (4, 0, 0), 'r_elbow': (-20, 0, 0)}, 240),
    ]
    out = [('idle', True, idle), ('walk', True, walk), ('pain', False, pain)]
    # Each action has a standing clip and a twin with walking legs; the game
    # picks one with HellfeatherWarrior.ActionClip.
    for name, frames in (('attack', attack), ('cleave', cleave), ('shout', shout)):
        out.append((name, False, frames))
        out.append((name + '_walk', False, walking(frames)))
    return [(name, looping, [(with_hunch(p), ms) for p, ms in frames]) for name, looping, frames in out]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    base = wren().rig
    # All scaled alike, by her own height without clothes or helmet.
    fit(base, HEIGHT)
    rigs = {'Warrior': base}
    variants = [('WarriorLeatherArmor', True, True), ('WarriorUnmarked', False, False),
                ('WarriorLeatherArmorUnmarked', True, False)]
    for armor, title in (('ring', 'WarriorRingMail'), ('scale', 'WarriorScaleMail'), ('plate', 'WarriorPlateMail')):
        variants += [(title, armor, True), (title + 'Unmarked', armor, False)]
    for name, armor, marked in variants:
        rigs[name] = wren(armor=armor, marked=marked).rig
        rigs[name].scale = base.scale
    made = clips()
    build_variants(rigs, made, (64, 96, 72), args.preview, frame_calls(made))


if __name__ == '__main__':
    main()
