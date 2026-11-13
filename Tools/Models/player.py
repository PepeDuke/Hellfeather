"""Builds the player, Wren Carrow, from a figure.py rig into Assets/Warrior.qvox.

Wren is a thief-taker and ex-miner: a lean woman in her thirties in a worn
oilcloth coat over a leather jerkin, a miner's leather cap with its lamp pushed
back, a grey scarf over her mouth for the Grey Cough, her right sleeve rolled to
show the Tithe-mark, a silver lattice from wrist to elbow (Story.md).

The game (Warrior.dk, HellfeatherGame.dk) plays three clips: idle, walk and
attack, and her axe, Assets/BattleAxe.qvox, rides the `hand_r` socket that every
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
from kit import (BRASS, CLOTH_RED, FACE_DARK, HAIR_DARK, LEATHER, MUD, SCARF, SILVER, SKIN, SMOCK,  # noqa: E402
                 TROUSERS, hash2, pick)
from people import Body, coat_front, flat, speckled  # noqa: E402

HEIGHT = 78
# Oilcloth: a greasy olive-brown, darker in the creases.
OILCLOTH = [MUD[0], MUD[1], SCARF[1]]
VEST = [SMOCK[1], SMOCK[0], SCARF[0]]
SHORTS = [SCARF[1], MUD[0]]


# The head socket sits at the middle of her skull; helmets are built around it
# (Tools/Models/gear.py), in rest rig coordinates before scaling.
HEAD = (0.0, 63.0, 1.2)


def wren(armor=False):
    """Wren in her basic attire: a worn sleeveless vest and shorts, barefoot,
    the Tithe-mark on her right forearm, dark hair in a loose bun. With armor,
    the Leather Armor on top: the oilcloth coat over a leather jerkin, a coat
    sleeve rolled above the Tithe-mark, a glove, trousers and boots, and the
    scarf over her mouth for the Grey Cough. Both share bones and sockets."""
    b = Body(shoulder=9.0, waist=7.0, depth=5.0, bust=1.0)
    r = b.rig
    skin = speckled(SKIN[:2], 406, 2, 3)
    vest = speckled(VEST, 407, 2, 3)

    # The body as she is: bare legs and feet, shorts, the vest.
    legs(b, skin, SKIN[1], gap=3.4, thigh=(2.9, 2.2), shin=(2.1, 1.5))
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
    b.part('r_elbow', where(capsule((-10.65, 40.0, 1.3), (-10.8, 33.5, 2.8), 2.15, 1.85), woven), lattice)
    b.head(SKIN)
    b.hair(HAIR_DARK, 'bun')
    b.part('head', ellipsoid((-4.2, 61.5, 1.0), (1.0, 2.6, 1.4)), HAIR_DARK[1])

    if armor:
        coat = speckled(OILCLOTH, 400, 2, 4)
        jerkin = speckled(LEATHER[1:3], 401, 2, 3)
        # Trousers over her legs and tall laced boots to the knee.
        for side, hip, knee in ((-3.6, 'r_hip', 'r_knee'), (3.6, 'l_hip', 'l_knee')):
            b.part(hip, capsule((side, 34, 0), (side, 18, 0.4), 3.6, 3.1), speckled(TROUSERS, 402))
            b.part(knee, capsule((side, 17, 0.4), (side, 3, 0), 2.9, 2.4),
                   lambda x, y, z, pose: np.where(np.floor(y) % 4 == 0, LEATHER[2], LEATHER[1]))
            b.part(knee, capsule((side, 17.5, 0.4), (side, 16.0, 0.4), 3.3), LEATHER[3])
            b.part(knee, union(ellipsoid((side, 1.6, 1.9), (2.5, 1.7, 3.6)), capsule((side, 3, 0), (side, 1.2, 0.5), 2.1)), FACE_DARK[0])
        # The long coat, open in front to show the jerkin, to just below the knee.
        opening = coat_front(1.8, 5.0, hem=14)
        b.skirt(coat, hem=14, flare=3.6, wave=0.4, front_cut=opening, grow=0.6)

        def chest(x, y, z, pose):
            out = coat(x, y, z, pose)
            front = z > 1.8
            inside = front & (np.abs(x) < opening(y))
            lapel = front & (np.abs(x) >= opening(y)) & (np.abs(x) < opening(y) + 1.8) & (y > 44)
            out = np.where(lapel, MUD[1], out)
            out = np.where(inside, jerkin(x, y, z, pose), out)
            strap = inside & ((np.abs(y - 47) < 0.7) | (np.abs(y - 42.5) < 0.7))
            return np.where(strap, LEATHER[2], out)
        b.torso(chest, grow=0.7)
        b.belt(LEATHER[2], y=37, buckle=BRASS[0], height=2.2)
        b.part('chest', capsule((-6.5, 54.5, 4.8), (6.5, 38.5, 7.2), 0.9), LEATHER[2])
        b.part('root', ellipsoid((6.8, 34.0, 6.8), (2.6, 3.0, 1.8)), LEATHER[1])
        b.part('root', ellipsoid((-6.0, 33.6, 7.2), (2.0, 2.4, 1.6)), LEATHER[1])
        # Sleeves: the right rolled above the Tithe-mark, the left full, gloved.
        b.part('r_shoulder', capsule((-9.0, 53, 0), (-10.6, 42, 1.0), 3.3, 3.0), coat)
        b.part('r_elbow', capsule((-10.6, 42.5, 1.0), (-10.65, 40.6, 1.2), 3.4), MUD[1])
        b.part('l_shoulder', capsule((9.0, 53, 0), (10.6, 42, 1.0), 3.3, 3.0), coat)
        b.part('l_elbow', capsule((10.6, 42, 1.0), (10.6, 32.5, 2.6), 2.9, 2.6), coat)
        b.part('l_elbow', capsule((10.6, 34.5, 2.3), (10.6, 32.5, 2.6), 3.1), MUD[1])
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
    return b

def clips():
    hunch = {'chest': (5, 0, 0), 'head': (-4, 0, 0)}

    def with_hunch(pose):
        out = dict(hunch)
        for k, v in pose.items():
            out[k] = tuple(a + b for a, b in zip(out.get(k, (0, 0, 0)), v)) if isinstance(v, tuple) else v
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
        walk.append(({'r_hip': (-26 * s, 0, 0), 'l_hip': (26 * s, 0, 0),
                      # Each knee bends as its leg swings through.
                      'r_knee': (6 + 26 * max(0.0, -math.sin(a - 0.6)), 0, 0),
                      'l_knee': (6 + 26 * max(0.0, math.sin(a - 0.6)), 0, 0),
                      'chest': (8, 0, 3 * s), 'head': (-4, 0, -2 * s),
                      'r_shoulder': (16 * s, 0, 0), 'l_shoulder': (-16 * s, 0, 0), 'l_elbow': (-12, 0, 0), 'r_elbow': (-14, 0, 0),
                      'offset': (0, -0.8 * (1 - abs(math.cos(a))), 0)}, 76))
    step = {'l_hip': (-22, 0, 0), 'r_hip': (12, 0, 0), 'l_knee': (14, 0, 0), 'r_knee': (8, 0, 0)}
    attack = [
        ({'r_shoulder': (-30, 0, -10), 'r_elbow': (-40, 0, 0), 'chest': (4, -10, 0)}, 72),
        (dict(step, r_shoulder=(-125, 0, -14), r_elbow=(-70, 0, 0), chest=(-6, -20, 0), head=(-4, 0, 0), l_shoulder=(-30, 0, 10)), 95),
        (dict(step, r_shoulder=(-165, 0, -10), r_elbow=(-80, 0, 0), chest=(-12, -24, 0), head=(-6, 0, 0), l_shoulder=(-40, 0, 14)), 48),
        # The blow lands here, frame 3.
        (dict(step, r_shoulder=(-75, 0, 0), r_elbow=(-8, 0, 0), chest=(22, 16, 0), head=(6, 0, 0), l_shoulder=(10, 0, 8), offset=(0, -1.0, 0)), 48),
        (dict(step, r_shoulder=(-25, 0, 8), r_elbow=(0, 0, 0), chest=(28, 22, 0), head=(8, 0, 0), l_shoulder=(16, 0, 8), offset=(0, -1.5, 0)), 80),
        ({'r_shoulder': (-20, 0, 0), 'r_elbow': (-20, 0, 0), 'chest': (14, 8, 0), 'l_hip': (-8, 0, 0)}, 85),
        ({'r_shoulder': (-8, 0, 0), 'chest': (6, 2, 0)}, 70),
    ]
    return [('idle', True, [(with_hunch(p), ms) for p, ms in idle]),
             ('walk', True, [(with_hunch(p), ms) for p, ms in walk]),
             ('attack', False, [(with_hunch(p), ms) for p, ms in attack])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    base = wren().rig
    armored = wren(armor=True).rig
    # Both scaled alike, by her own height without clothes or helmet.
    fit(base, HEIGHT)
    armored.scale = base.scale
    build_variants({'Warrior': base, 'WarriorLeatherArmor': armored}, clips(), (64, 96, 72), args.preview)


if __name__ == '__main__':
    main()
