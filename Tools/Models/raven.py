"""Builds the ambient raven, Assets/Raven.qvox, which Source/Ravens.dk sets on
roofs, perches and gibbets and flies off when Wren comes close.

It is a figure.py rig on the enemies' Bird, with two sets of wings: folded
against the body while it sits, and jointed spread wings (an arm and a hand
with fingered primaries) for flight. A pose shows one set or the other by its
`spread` key. The clips keep the names and timings Ravens.dk plays: idle, caw,
fly and land, as on the raven's sprite atlas in Act1-refs.

Voxels are 0.025 units, as the people's are. Ravens.dk must use that Voxel and
take Height from the box height the build prints (the middle number), because
it stands the raven by half its Height.

    python Tools/Models/raven.py --preview
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enemies import Bird, feathered  # noqa: E402
from figure import build, ellipsoid, fit, where  # noqa: E402
from kit import RAVEN_LIT, hash2, pick

RAVEN = RAVEN_LIT  # noqa: E402

# Perched, the raven stands this many voxels tall. With its head carried
# forward in line with its back, that makes it 0.85 units long and 1.6 across
# the wings, as the old one was.
HEIGHT = 17
# Glossy black, lit with a blue-grey sheen on the feather edges.
PLUMAGE = [RAVEN[0], RAVEN[1], RAVEN[3], RAVEN[2]]


def folded(pose):
    return not pose.get('spread')


def spread(pose):
    return bool(pose.get('spread'))


def raven():
    # Short legs and a deep body, as a raven sits: most of its height is bird.
    b = Bird(feathered(PLUMAGE, 500), feathered([RAVEN[1], RAVEN[0], RAVEN[2]], 501), leg=12,
             body=(13, 15, 26), neck=((0, 30, 16), (0, 35, 27)), neck_r=(9.2, 8.0), head=(8.6, 8.2, 10.0),
             bill=('crow', 17), bill_color=[RAVEN[1], RAVEN[0]], feet=[RAVEN[0], RAVEN[1]], gap=5, webbed=False,
             eye=RAVEN[2], eye_r=2.2)
    r = b.rig
    # The Bird's own wings are the folded ones: show them only while perched.
    r.parts = [(bone, shape, material, folded if bone in ('l_wing', 'r_wing') else when)
               for bone, shape, material, when in r.parts]
    # A shaggy throat (ravens have a ruff of hackles) and a long wedge tail.
    b.part('neck', ellipsoid((0, 29, 25.5), (7.0, 5.8, 4.4)), feathered([RAVEN[1], RAVEN[0]], 502, 0.7))
    b.part('tail', where(ellipsoid((0, b.cy + 3, -36), (8.0, 2.6, 14.0)), lambda x, y, z: z < -26), feathered([RAVEN[0], RAVEN[1]], 503))

    # The spread wings: an arm from the shoulder and a hand beyond the wrist,
    # flat in the horizontal plane, leading edge forward, the long primaries
    # fingered at the tip. A voxel of the built raven is about four rig units,
    # so the wings are a voxel thick and the gaps between primaries a voxel
    # wide; anything thinner would break up into dots.
    # Authored for the left (+X); the right mirrors it.
    bx, by, bz = b.body
    shoulder_y, shoulder_z = b.cy + by * 0.4, 8.0
    arm_long, hand_long = 34.0, 42.0

    def plumage(x, y, z, pose):
        span = np.abs(x)
        back = shoulder_z - z
        row = np.floor(back / 5.0).astype(int)
        out = pick([RAVEN[0], RAVEN[1], RAVEN[0]], hash2(np.floor(span / 5).astype(int), row, 504))
        coverts = back < 9.0
        out = np.where(coverts, RAVEN[1], out)
        edge = ((span / 5.0) % 1.0) < 0.2
        return np.where(edge & ~coverts, RAVEN[2], out)
    for side, name in ((1, 'l'), (-1, 'r')):
        sx = side * (bx - 2)
        r.bone(f'{name}_arm', (sx, shoulder_y, shoulder_z), 'body')
        wx = sx + side * arm_long
        r.bone(f'{name}_hand', (wx, shoulder_y, shoulder_z), f'{name}_arm')

        def arm(x, y, z, side=side, sx=sx):
            u = (x - sx) * side
            chord = 26 - u * 0.12
            return (u >= -2) & (u <= arm_long + 1) & (np.abs(y - shoulder_y) < 2.4) & (z <= shoulder_z + 2.5) & (z >= shoulder_z - chord)
        lo_x, hi_x = sorted((sx, sx + side * (arm_long + 2)))
        arm.box = (np.array([lo_x - 2, shoulder_y - 3, shoulder_z - 28]), np.array([hi_x + 2, shoulder_y + 3, shoulder_z + 3]))
        r.part(f'{name}_arm', arm, plumage, when=spread)

        def hand(x, y, z, side=side, wx=wx):
            u = (x - wx) * side
            back = shoulder_z - z
            chord = 22 - u * 0.25
            # The tip breaks into five separate primaries, each longer toward
            # the leading edge.
            finger = np.floor(back / 5.0).astype(int)
            gap = (u > hand_long * 0.55) & ((back % 5.0) > 3.6)
            reach = hand_long - np.clip(finger, 0, 6) * 3.0
            return (u >= -2) & (u <= reach) & (np.abs(y - shoulder_y) < 2.0) & (z <= shoulder_z + 2.0) & (back <= chord) & ~gap
        lo_x, hi_x = sorted((wx, wx + side * (hand_long + 2)))
        hand.box = (np.array([lo_x - 2, shoulder_y - 3, shoulder_z - 26]), np.array([hi_x + 2, shoulder_y + 3, shoulder_z + 3]))
        r.part(f'{name}_hand', hand, plumage, when=spread)
    fit(r, HEIGHT)
    return r


def wings(stroke, hand=0.0, sweep=0.0):
    """Both wings' pose: stroke lifts them (degrees, up positive), hand bends
    the hand further the same way, sweep draws them back."""
    return {'spread': 1,
            'l_arm': (0, -sweep, stroke), 'l_hand': (0, -sweep * 0.5, hand),
            'r_arm': (0, sweep, -stroke), 'r_hand': (0, sweep * 0.5, -hand)}


def merged(*poses):
    out = {}
    for p in poses:
        for k, v in p.items():
            if isinstance(v, tuple) and isinstance(out.get(k), tuple):
                out[k] = tuple(a + b for a, b in zip(out[k], v))
            else:
                out[k] = v
    return out


def clips():
    tuck = {'l_leg': (-70, 0, 0), 'r_leg': (-70, 0, 0)}
    idle = [
        ({}, 160), ({'head': (0, 14, 0)}, 160), ({'head': (2, 26, 0), 'tail': (4, 0, 0)}, 160),
        ({'head': (4, 10, 0), 'neck': (4, 0, 0)}, 160), ({'head': (0, -16, 0)}, 160), ({'head': (0, -6, 0), 'tail': (-4, 0, 0)}, 160),
    ]
    caw = [
        ({}, 110), ({'neck': (-6, 0, 0)}, 110), ({'neck': (8, 0, 0), 'body': (4, 0, 0)}, 110),
        ({'neck': (14, 0, 0), 'head': (-10, 0, 0), 'jaw': (32, 0, 0), 'body': (8, 0, 0), 'l_wing': (0, 0, 12), 'r_wing': (0, 0, -12)}, 110),
        ({'neck': (12, 0, 0), 'head': (-8, 0, 0), 'jaw': (26, 0, 0), 'body': (6, 0, 0), 'l_wing': (0, 0, 8), 'r_wing': (0, 0, -8)}, 110),
        ({'neck': (8, 0, 0), 'jaw': (8, 0, 0)}, 110), ({}, 110),
    ]
    # One wingbeat in eight frames: the downstroke from high to low, then the
    # upstroke with the hands folded in to slip through the air.
    beat = [(55, 20), (35, 5), (5, -10), (-30, -15), (-45, -5), (-25, 25), (10, 45), (40, 40)]
    fly = [(merged(tuck, {'body': (10, 0, 0), 'neck': (2, 0, 0), 'tail': (-6, 0, 0)}, wings(s, h),
                   {'offset': (0, 2.5 - s * 0.03, 0)}), 70) for s, h in beat]
    land = [
        (merged(tuck, {'body': (4, 0, 0)}, wings(20, 5)), 90),
        (merged(tuck, {'body': (-8, 0, 0)}, wings(45, 15, 10)), 90),
        (merged({'body': (-20, 0, 0), 'l_leg': (20, 0, 0), 'r_leg': (20, 0, 0), 'tail': (-14, 0, 0)}, wings(60, 25, 20)), 90),
        (merged({'body': (-26, 0, 0), 'l_leg': (30, 0, 0), 'r_leg': (30, 0, 0), 'tail': (-18, 0, 0)}, wings(30, 40, 25), {'offset': (0, 1, 0)}), 90),
        (merged({'body': (-14, 0, 0), 'l_leg': (10, 0, 0), 'r_leg': (10, 0, 0)}, wings(70, 40, 40)), 90),
        ({'body': (-6, 0, 0), 'l_wing': (0, 0, 40), 'r_wing': (0, 0, -40)}, 90),
        ({'l_wing': (0, 0, 14), 'r_wing': (0, 0, -14), 'neck': (6, 0, 0)}, 90),
        ({}, 90),
    ]
    # Perched, a raven sits upright: chest up, tail down toward the perch.
    # The body tips up about a third of the way to upright, the short neck
    # rises from the chest and the head turns back so the bill points level;
    # the long tail carries on the line of the back, down toward the perch.
    sit = {'body': (-34, 0, 0), 'neck': (6, 0, 0), 'head': (28, 0, 0), 'tail': (4, 0, 0)}
    idle = [(merged(sit, p), ms) for p, ms in idle]
    caw = [(merged(sit, p), ms) for p, ms in caw]
    land = [(merged(sit, p) if not p.get('spread') else p, ms) for p, ms in land]
    return [('idle', True, idle), ('caw', False, caw), ('fly', True, fly), ('land', False, land)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    build('Raven', raven(), clips(), (120, 70, 100), args.preview)


if __name__ == '__main__':
    main()
