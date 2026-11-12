"""Builds Act I people from figure.py rigs: parts measured off the concept sheets
in Act1-refs, painted from kit.py's materials, posed into the clips the game
plays (idle and talk for NPCs, see Spots.SetTalking).

Everyone is authored at 70 rig voxels tall, feet at the origin, facing +Z, and
scaled to the height in voxels that Cast.dk gives AddPerson (the voxel size
there sets their size in the world). Their left is +X. Body does the parts
most people share; each recipe adds what makes them themselves. act1.MODELS
keeps each one's entry, marked recipe=True, so inspect_models.py scores it
against the sheet and act1.py leaves it alone.

    python Tools/Models/people.py              build everyone
    python Tools/Models/people.py Edda Moth    build some of them
    python Tools/Models/inspect_models.py Edda compare with the sheet
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure import Rig, build, capsule, column, ellipsoid, minus, shell, union, where  # noqa: E402
from kit import (BRASS, BURLAP, CLOTH_BROWN, CLOTH_PALE, CLOTH_RED, COAT_BROWN, FACE_DARK, FLOUR, GLOW, GUANO,  # noqa: E402
                 HABIT, HAIR_DARK, HAIR_GREY, IRON, LEATHER, LIPS_RED, NAVY, PAPER, RAVEN, SCARF, SKIN, SKIN_PALE,
                 SMOCK, STRAW, TAPE, TROUSERS, VELVET, WAISTCOAT, WIMPLE, WOOD, WOOD_DARK, WOOL, DRESS_MILL,
                 hash2, pick)


def speckled(shades, seed, grain=2, drop=5):
    """A material: shades in cells grain wide and drop tall, so cloth reads as
    hanging folds rather than flat or checkered."""
    def material(x, y, z, pose):
        cell = hash2(np.floor(x / grain).astype(int) * 31 + np.floor(z / grain).astype(int), np.floor(y / drop).astype(int), seed)
        return pick(shades, cell ** 1.7)
    return material


def dusted(base, dust, amount, seed):
    """base with a scatter of dust (flour, droppings) over it."""
    def material(x, y, z, pose):
        out = base(x, y, z, pose) if callable(base) else np.full(np.shape(x), base)
        speck = hash2(np.floor(x).astype(int) * 7 + np.floor(z).astype(int), np.floor(y).astype(int), seed) < amount
        return np.where(speck, pick(dust, hash2(np.floor(x).astype(int), np.floor(y).astype(int), seed + 1)), out)
    return material


def flat(value):
    return lambda y: value + 0 * y


def bump(y, at, width):
    return np.exp(-((y - at) / width) ** 2)


class Body:
    """A standing figure. Measurements are in rig voxels of a 70-tall person:
    shoulders at 53, waist at 38, chin at 58, crown at 69."""

    def __init__(self, scale=1.0, shoulder=10.0, waist=9.5, depth=6.8, bust=0.0, belly=0.0):
        self.rig = Rig(scale)
        self.shoulder, self.waist, self.depth, self.bust, self.belly = shoulder, waist, depth, bust, belly
        r = self.rig
        r.bone('root', (0, 0, 0))
        r.bone('chest', (0, 38, 0), 'root')
        r.bone('head', (0, 57, 0.5), 'chest')

    def part(self, bone, shape, material):
        self.rig.part(bone, shape, material)

    # Body measurements as functions of height.
    def torso_x(self, y):
        top = self.shoulder - np.clip(y - 52, 0, None) * 0.75
        return np.where(y < 52, self.waist + (self.shoulder - self.waist) * np.clip((y - 39) / 12, 0, 1) + self.belly * 0.4 * bump(y, 41, 4), top)

    def torso_z(self, y):
        return self.depth + self.bust * bump(y, 47, 4) + self.belly * bump(y, 41, 4.5) - np.clip(y - 53, 0, None) * 0.5

    def torso_c(self, y):
        return 0.4 * self.bust * bump(y, 47, 4) + 0.5 * self.belly * bump(y, 41, 4.5)

    def torso(self, material, grow=0.0, low=36, high=57):
        shape = column(low, high, lambda y: self.torso_x(y) + grow, lambda y: self.torso_z(y) + grow, self.torso_c, power=2.3)
        self.part('chest', shape, material)
        return shape

    def boots(self, top=11, shades=LEATHER[1:3], gap=3.8):
        for side in (-gap, gap):
            self.part('root', union(capsule((side, 2, 0), (side, top, -0.3), 2.5), ellipsoid((side, 1.5, 2.4), (2.5, 1.6, 3.3))),
                       lambda x, y, z, pose: np.where(y < 1, FACE_DARK[0], pick(shades, hash2(np.floor(z).astype(int), np.floor(y / 2).astype(int), 3))))

    def legs(self, material, gap=3.8, top=36, bottom=8, r=3.0):
        for side in (-gap, gap):
            self.part('root', capsule((side * 1.05, top, 0), (side, bottom, 0), r + 0.4, r - 0.3), material)

    def skirt(self, material, hem=8, top=39, flare=3.0, wave=0.5, front_cut=None, grow=0.0):
        """A skirt, coat tail or habit from the waist to the hem, flaring by
        `flare`. front_cut(y) is the half width of an open front, for coats."""
        wx, wz = self.waist + 0.6 + grow, self.depth + 0.4 + grow

        def rx(y):
            return wx + flare * np.clip((top - y) / (top - hem), 0, 1)

        def rz(y):
            return wz + flare * 0.8 * np.clip((top - y) / (top - hem), 0, 1)
        body = column(hem, top, rx, rz, flat(0.3))
        if wave:
            ripple = lambda x, y, z: (y > hem + wave * (1 + np.sin(np.arctan2(z, x) * 7)))  # noqa: E731
            body = where(body, ripple)
        if front_cut:
            body = minus(body, lambda x, y, z: (z > 1.0) & (np.abs(x) < front_cut(y)))
        self.part('root', body, material)
        return body, rx, rz

    def apron(self, material, hem, low_half, bib_half, bib_top=51, skirt_top=39, flare=3.0, straps=None, grow=1.2):
        """A layer over the front of skirt and chest."""
        wx, wz = self.waist + 0.6, self.depth + 0.4
        skirt_out = column(hem, skirt_top, lambda y: wx + grow + flare * np.clip((skirt_top - y) / (skirt_top - hem), 0, 1),
                           lambda y: wz + grow + flare * 0.8 * np.clip((skirt_top - y) / (skirt_top - hem), 0, 1), flat(0.3))
        skirt_in = column(hem - 1, skirt_top + 1, lambda y: wx + 0.2 + flare * np.clip((skirt_top - y) / (skirt_top - hem), 0, 1),
                          lambda y: wz + 0.2 + flare * 0.8 * np.clip((skirt_top - y) / (skirt_top - hem), 0, 1), flat(0.3))
        front = lambda x, y, z: (z > 2.5) & (np.abs(x) < low_half)  # noqa: E731
        self.part('root', where(shell(skirt_in, skirt_out), front), material)
        if bib_half:
            torso_in = column(35, bib_top + 1, lambda y: self.torso_x(y) + 0.1, lambda y: self.torso_z(y) + 0.1, self.torso_c, power=2.3)
            torso_out = column(36, bib_top, lambda y: self.torso_x(y) + 1.1, lambda y: self.torso_z(y) + 1.1, self.torso_c, power=2.3)
            self.part('chest', where(shell(torso_in, torso_out), lambda x, y, z: (z > 2.5) & (np.abs(x) < bib_half)), material)
            if straps is not None:
                for side in (-bib_half + 1, bib_half - 1):
                    zf = self.torso_z(np.array(bib_top - 1.0)) + 1.0
                    self.part('chest', union(capsule((side, bib_top - 1, zf), (side * 1.25, 56, 2.5), 0.9),
                                             capsule((side * 1.25, 56, 2.5), (side * 1.2, 50, -self.depth - 0.6), 0.9)), straps)

    def belt(self, material, y=38, buckle=BRASS[0], height=2.5):
        w, d = self.waist + 0.9, self.depth + 0.9
        self.part('root', shell(column(y - 1, y + height, flat(w - 1.4), flat(d - 1.4)), column(y - 0.5, y + height - 0.5, flat(w), flat(d))), material)
        if buckle is not None:
            self.part('root', ellipsoid((0, y + height / 2 - 0.5, d + 0.4), (1.4, 1.2, 0.8)), buckle)

    def arm(self, side, shoulder, elbow, wrist, sleeve, forearm, hand=None, r=3.0, cuff=None, flare=0.0):
        """One arm: sleeve from shoulder to elbow, forearm (a sleeve material,
        or skin for a rolled sleeve) to the wrist, and the hand beyond it.
        flare widens a sleeve toward the wrist, for habits and coats."""
        name = 'r' if side < 0 else 'l'
        self.rig.bone(f'{name}_shoulder', shoulder, 'chest')
        self.rig.bone(f'{name}_elbow', elbow, f'{name}_shoulder')
        self.part(f'{name}_shoulder', capsule(shoulder, elbow, r + 0.3, r), sleeve)
        bare = forearm in (SKIN, SKIN_PALE)
        if bare:
            self.part(f'{name}_elbow', capsule(elbow, wrist, r - 0.6, r - 0.9), speckled(forearm[:2], 10, 3))
            self.part(f'{name}_elbow', capsule(elbow, np.array(elbow) + (np.array(wrist) - np.array(elbow)) * 0.18, r + 0.4), cuff if cuff is not None else sleeve)
        else:
            self.part(f'{name}_elbow', capsule(elbow, wrist, r - 0.1, r - 0.4 + flare), forearm)
            if cuff is not None:
                tip = np.array(wrist, float)
                self.part(f'{name}_elbow', capsule(tip - (tip - np.array(elbow)) * 0.12, tip, r + 0.1 + flare), cuff)
        if hand is not None:
            e, w = np.array(elbow, float), np.array(wrist, float)
            reach = (w - e) / np.linalg.norm(w - e)
            self.part(f'{name}_elbow', ellipsoid(tuple(w + reach * 2.0), (2.0, 2.4, 2.0)), hand)
        return name

    def head(self, skin=SKIN, lips=None, beard=None, eyes_down=False, earring=None, eyes=None):
        """The head, face to +Z. lips is a color for painted lips, beard a
        list of shades for stubble or a beard."""
        def face(x, y, z, pose):
            out = pick(skin[:2], hash2(np.floor(x).astype(int), np.floor(y).astype(int), 12) * 0.7)
            front = z > 4.2
            eye_y = 63.0 if eyes_down else 63.5
            eye = front & (np.abs(np.abs(x) - 1.8) < 0.8) & (np.abs(y - eye_y) < 0.5)
            opened = pose.get('mouth', 0)
            mouth = front & (np.abs(x) < (1.4 if opened or lips is not None else 1.0)) & (y > 59.6 - opened) & (y < 60.4)
            cheeks = front & (np.abs(np.abs(x) - 2.6) < 0.8) & (np.abs(y - 61.8) < 0.8)
            out = np.where(cheeks, skin[2], out)
            if beard is not None:
                chin = (y < 61.2) & (z > 0.5) & (hash2(np.floor(x).astype(int), np.floor(y).astype(int) * 3 + np.floor(z).astype(int), 15) < 0.8)
                out = np.where(chin & ~mouth, pick(beard, hash2(np.floor(x).astype(int), np.floor(y).astype(int), 16)), out)
            out = np.where(eye, FACE_DARK[0] if eyes is None else eyes, out)
            return np.where(mouth, FACE_DARK[0] if opened else (lips if lips is not None else skin[2]), out)
        self.part('head', ellipsoid((0, 63, 1.2), (4.5, 5.6, 4.8)), face)
        self.part('head', ellipsoid((0, 62.2, 5.9), (0.7, 1.1, 0.8)), skin[0])
        if earring is not None:
            self.part('head', ellipsoid((4.5, 62, 1.2), (0.5, 0.7, 0.5)), earring)
        self.part('chest', capsule((0, 54, 0.2), (0, 58.5, 0.8), 2.4), skin[1])

    def hair(self, shades, style='short'):
        """short: a rough cap. wavy: fuller, over the ears and nape. bun: smooth
        and pinned up at the back. fringe: bald crown, grey ring round the back."""
        cap = ellipsoid((0, 64.6, 0.4), (5.4, 5.6, 5.6))
        face = lambda x, y, z: (z > 1.8) & (y < 66.2)  # noqa: E731
        material = speckled(shades, 14, 1, 1)
        if style == 'short':
            bare = lambda x, y, z: face(x, y, z) | (y < 60.5) | ((np.abs(x) > 4.2) & (y < 63.5) & (z > -1.5))  # noqa: E731
            curls = lambda x, y, z: hash2(np.floor(x * 0.9).astype(int) * 17 + np.floor(z).astype(int), np.floor(y).astype(int), 13) < 0.82  # noqa: E731
            self.part('head', where(minus(cap, bare), curls), material)
        elif style == 'wavy':
            full = union(ellipsoid((0, 64.6, 0.2), (5.7, 5.9, 5.8)), ellipsoid((0, 60, -2.4), (5.0, 3.6, 3.6)))
            bare = lambda x, y, z: (face(x, y, z) & ~((y > 64.8) & (np.abs(x) < 4.2))) | (y < 57.5)  # noqa: E731
            self.part('head', minus(full, bare), speckled(shades, 14, 1, 2))
        elif style == 'bun':
            smooth = ellipsoid((0, 64.8, 0.4), (5.0, 5.2, 5.3))
            bare = lambda x, y, z: face(x, y, z) | (y < 61) | ((np.abs(x) > 4.0) & (y < 63.5) & (z > -1.5))  # noqa: E731
            self.part('head', minus(smooth, bare), speckled(shades, 14, 1, 3))
            self.part('head', ellipsoid((0, 66.2, -4.6), (2.4, 2.2, 2.0)), speckled(shades, 15, 1, 1))
        elif style == 'fringe':
            ring = minus(ellipsoid((0, 63, 0.6), (5.2, 5.0, 5.4)), lambda x, y, z: (y > 65.5) | (y < 59.5) | (z > 2.0))
            wisps = lambda x, y, z: hash2(np.floor(x).astype(int) * 13 + np.floor(z).astype(int), np.floor(y).astype(int), 17) < 0.75  # noqa: E731
            self.part('head', where(ring, wisps), material)

    def talking(self, gesture, idle_extra=None):
        """idle and talk clips. gesture is the pose (without mouth) of the two
        talking frames' raised arm; the third frame uses a smaller version."""
        base = idle_extra or {}

        def mix(*poses):
            out = {}
            for p in poses:
                for k, v in p.items():
                    if isinstance(v, tuple) and k in out and isinstance(out[k], tuple):
                        out[k] = tuple(a + b for a, b in zip(out[k], v))
                    else:
                        out[k] = v
            return out
        half = {k: tuple(a * 0.6 for a in v) for k, v in gesture.items()}
        idle = [
            (mix(base), 900),
            (mix(base, {'head': (2, 7, 0)}), 700),
            (mix(base, {'head': (1, 3, 0)}), 400),
            (mix(base, {'head': (-1, -6, 0)}), 700),
        ]
        talk = [
            (mix(base, {'mouth': 0}), 200),
            (mix(base, gesture, {'mouth': 1, 'head': (6, 0, 0)}), 180),
            (mix(base, gesture, {'mouth': 0, 'head': (-3, -6, 0)}), 180),
            (mix(base, half, {'mouth': 1, 'head': (3, 0, 0)}), 160),
        ]
        return [('idle', True, idle), ('talk', True, talk)]


# The people.

def edda():
    """Edda the Ravenkeeper: old, broad and blunt. Dark dress with sleeves
    rolled to the elbow, a heavy leather apron streaked white, a scarf at the
    throat, grey hair cropped short. A falconer's glove on her left arm with a
    raven on the fist, a sack of black feathers at her right hip. 70 tall."""
    b = Body(shoulder=10.6, waist=10.0, depth=7.4, bust=1.6, belly=0.6)
    r = b.rig
    dress = speckled(CLOTH_BROWN, 1)
    b.boots()
    b.skirt(dress, hem=8, flare=2.6)
    b.torso(dress)

    def apron_material(x, y, z, pose):
        base = pick(LEATHER[:2], hash2(np.floor(x / 2).astype(int), np.floor(y / 6).astype(int), 4))
        lane = np.floor(x / 1.4).astype(int)
        top = 14 + hash2(lane, 0, 5) * 36
        streak = (hash2(lane, 1, 6) < 0.35) & (y < top) & (y > top - 3 - hash2(lane, 2, 7) * 7)
        return np.where(streak, pick(GUANO[:2], hash2(lane, np.floor(y).astype(int), 8)), base)
    b.apron(apron_material, hem=10, low_half=8.8, bib_half=6.4, straps=LEATHER[2], flare=2.6)
    b.belt(LEATHER[2])
    b.part('root', minus(ellipsoid((5, 34.5, 9.4), (1.8, 2.2, 0.9)), ellipsoid((5, 34.5, 9.4), (0.9, 1.2, 2))), IRON[1])
    # The sack of feathers at her right hip.
    b.part('root', capsule((-8.5, 39, 6.5), (-11.5, 32, 6.5), 0.8), LEATHER[2])
    b.part('root', ellipsoid((-12, 27.5, 6.5), (4.2, 5.0, 3.6)), lambda x, y, z, pose: np.where(y > 30.5, LEATHER[2], pick(LEATHER[1:3], hash2(np.floor(x).astype(int), np.floor(y / 2).astype(int), 9))))
    for k, (dx, dz) in enumerate(((-1.5, -1), (0.5, 0.5), (2, -0.5), (-0.5, 1.5))):
        b.part('root', capsule((-12 + dx * 0.6, 31, 6.5 + dz * 0.5), (-12 + dx * 1.6, 38 + k % 2, 6.5 + dz), 0.7), RAVEN[0])
    b.arm(-1, (-10.5, 53, 0), (-12.5, 41, 0.5), (-12.4, 31, 2), dress, SKIN, SKIN[1], r=3.2, cuff=SCARF[2])
    # Left arm: the falconer's gauntlet and fist held forward.
    b.arm(1, (10.5, 53, 0), (12.5, 42, 1), (12.2, 47, 8.5), dress, speckled(LEATHER[:3], 2), r=3.2)
    b.part('l_elbow', ellipsoid((12, 48, 10.4), (3.2, 3.0, 3.3)), LEATHER[3])
    b.part('chest', ellipsoid((0, 56.2, 0.2), (6.4, 2.2, 5.0)), speckled(SCARF, 11))
    b.head(SKIN, earring=BRASS[0])
    b.hair(HAIR_GREY, 'short')

    # The raven on the fist, looking off to her right, with folded wings.
    r.bone('raven', (12, 51, 10.5), 'l_elbow')
    r.bone('raven_head', (12, 59, 10.5), 'raven')
    r.bone('raven_lwing', (14.5, 58, 9.5), 'raven')
    r.bone('raven_rwing', (9.5, 58, 9.5), 'raven')
    b.part('raven', capsule((12, 53.5, 10.4), (12, 57.5, 9.6), 3.8, 3.2), RAVEN[0])
    b.part('raven', capsule((12, 54, 7.2), (12, 46.5, 4.2), 2.2, 1.0), RAVEN[0])
    for bone, side in (('raven_lwing', 1), ('raven_rwing', -1)):
        b.part(bone, ellipsoid((12 + side * 3.2, 54.5, 8.6), (1.1, 4.6, 3.6)), RAVEN[1])
    b.part('raven_head', ellipsoid((12, 61.0, 10.8), (2.6, 2.6, 2.8)), lambda x, y, z, pose: np.where(y > 62.4, RAVEN[1], RAVEN[0]))
    b.part('raven_head', capsule((11.2, 60.8, 12.8), (9.6, 60.0, 15.4), 1.1, 0.5), RAVEN[2])
    b.part('raven_head', ellipsoid((10.0, 61.6, 12.0), (0.6, 0.6, 0.6)), RAVEN[2])
    for dx in (-1, 1):
        b.part('raven', capsule((12 + dx, 51.5, 10.8), (12 + dx, 50.8, 11.5), 0.5), IRON[0])

    idle = [
        ({}, 900),
        ({'raven_head': (0, 40, 0)}, 500),
        ({'raven_head': (0, 40, 0), 'head': (2, 8, 0)}, 700),
        ({'head': (2, 8, 0)}, 400),
        ({'raven_lwing': (0, 0, -18), 'raven_rwing': (0, 0, 18), 'raven': (-6, 0, 0)}, 160),
        ({'raven_lwing': (0, 0, -8), 'raven_rwing': (0, 0, 8)}, 160),
        ({}, 900),
    ]
    talk = [
        ({'mouth': 0}, 200),
        ({'mouth': 1, 'head': (7, 0, 0), 'r_elbow': (-55, 0, 0), 'r_shoulder': (-10, 0, -8)}, 180),
        ({'mouth': 0, 'head': (-3, -6, 0), 'r_elbow': (-70, 15, 0), 'r_shoulder': (-14, 0, -10), 'raven_head': (0, -25, 0)}, 180),
        ({'mouth': 1, 'head': (3, 0, 0), 'r_elbow': (-40, 0, 0), 'r_shoulder': (-6, 0, -5)}, 160),
    ]
    return r, [('idle', True, idle), ('talk', True, talk)]


def coat_front(open_top, open_hem, hem=8, top=56):
    """The half width of a coat's open front at height y: narrow at the chest,
    wider toward the hem."""
    return lambda y: open_top + (open_hem - open_top) * np.clip((top - y) / (top - hem), 0, 1)


def matthew():
    """Matthew the Journeyman: polite, neat, unremarkable. A long brown
    travelling coat open over a dark waistcoat and pale shirt, a tool roll on
    his back, his felt cap held in both hands. Dark wavy hair. 72 tall."""
    b = Body(scale=72 / 70, shoulder=9.6, waist=8.2, depth=6.0)
    coat = speckled(COAT_BROWN, 20)
    b.boots(shades=LEATHER[2:3] + [FACE_DARK[0]])
    b.legs(speckled(TROUSERS, 21))
    opening = coat_front(1.8, 4.5, hem=12)
    b.skirt(coat, hem=12, flare=3.2, wave=0.0, front_cut=opening)

    def chest(x, y, z, pose):
        out = coat(x, y, z, pose)
        front = z > 2.0
        lapel = front & (np.abs(x) < opening(y) + 1.4) & (np.abs(x) >= opening(y)) & (y > 44)
        vest = front & (np.abs(x) < opening(y))
        shirt = vest & (np.abs(x) < 1.3) & (y > 49)
        out = np.where(lapel, COAT_BROWN[2], out)
        out = np.where(vest, WAISTCOAT[1], out)
        return np.where(shirt, CLOTH_PALE[0], out)
    b.torso(chest)
    b.part('chest', ellipsoid((0, 55.6, 0.6), (5.0, 1.6, 4.4)), CLOTH_PALE[1])
    for side, sx in ((-1, -9.6), (1, 9.6)):
        b.arm(side, (sx, 53, 0), (sx * 1.08, 43, 2.5), (sx * 0.38, 38, 7.5), coat, coat, SKIN[1], r=2.9, cuff=COAT_BROWN[2])
    # The felt cap held in front, the tool roll across his back.
    b.part('l_elbow', minus(ellipsoid((0, 37.5, 9.5), (4.4, 3.2, 2.2)), ellipsoid((0, 38.5, 11.5), (3.4, 2.4, 1.6))), LEATHER[2])
    b.part('chest', capsule((-6.5, 50.5, -7.2), (6.5, 50.5, -7.2), 2.5), speckled(BURLAP, 22, 2, 2))
    for sx in (-3.5, 3.5):
        b.part('chest', capsule((sx, 50.5, -9.8), (sx, 50.5, -9.6), 0.8), LEATHER[2])
        b.part('chest', capsule((sx, 51, -6), (sx * 1.6, 55.5, 1), 0.6), LEATHER[2])
    b.head(SKIN)
    b.hair(HAIR_DARK, 'wavy')
    return b.rig, b.talking({'r_elbow': (-20, -45, 0), 'r_shoulder': (-8, 0, -14)})


def reeve_hollan():
    """Reeve Hollan: middle-aged, tired, soft around the middle. A dark blue
    doublet with pale cuffs and a brass chain of office, tall boots, a belt
    pouch, papers under his left arm, stubble. 72 tall."""
    b = Body(scale=72 / 70, shoulder=11.0, waist=10.6, depth=7.6, belly=2.6)
    navy = speckled(NAVY, 30)
    b.boots(top=19, shades=LEATHER[1:3])
    b.legs(speckled(TROUSERS, 31), r=3.4)
    b.skirt(navy, hem=24, flare=2.0, wave=0.4, front_cut=lambda y: 0.8 + 0 * y)
    b.torso(navy)
    b.belt(LEATHER[2], y=36)
    b.part('root', ellipsoid((-5.5, 32, 10.2), (2.4, 2.8, 1.6)), LEATHER[1])
    # The chain of office: links from shoulder to shoulder, the badge low on the chest.
    for k in range(13):
        t = k / 12.0
        a = math.pi * t
        x = -7.2 * math.cos(a)
        y = 55 - 7.0 * math.sin(a)
        z = b.torso_z(np.array(y)) + b.torso_c(np.array(y)) + 0.6 if 0.15 < t < 0.85 else 4.0
        b.part('chest', ellipsoid((x, y, z), (1.0, 1.0, 0.8)), BRASS[k % 2])
    b.part('chest', ellipsoid((0, 46, b.torso_z(np.array(46.0)) + 1.2), (1.8, 2.1, 0.8)), BRASS[0])
    b.arm(-1, (-11, 53, 0), (-12.6, 42, 1), (-12.4, 32, 2.5), navy, navy, SKIN[1], r=3.3, cuff=CLOTH_PALE[1])
    b.arm(1, (11, 53, 0), (12.8, 43, 2.5), (9.5, 44, 9.0), navy, navy, SKIN[1], r=3.3, cuff=CLOTH_PALE[1])
    # The bundle of papers clamped against his side, with a red seal.
    b.part('l_elbow', capsule((11.4, 41, 6.0), (11.4, 50, 6.0), 2.6), lambda x, y, z, pose: pick(PAPER, hash2(np.floor(y).astype(int), 0, 32)))
    b.part('l_elbow', ellipsoid((11.4, 45, 8.4), (0.9, 0.9, 0.6)), CLOTH_RED[0])
    b.part('chest', ellipsoid((0, 55.8, 0.6), (5.4, 1.6, 4.8)), CLOTH_PALE[1])
    b.head(SKIN, beard=HAIR_DARK[:2])
    b.hair(HAIR_DARK, 'wavy')
    return b.rig, b.talking({'r_elbow': (-60, 10, 0), 'r_shoulder': (-12, 0, -10)})


def marra_senn():
    """Marra Senn: a lean, sharp-faced woman of fifty, arms crossed. Dark skirt,
    leather vest over a shirt with rolled sleeves, a leather work apron with
    pockets and a rag at the hip, a measuring tape round her neck, a
    pincushion strapped to her wrist, a bandaged thumb. Hair pinned up. 72 tall."""
    b = Body(scale=72 / 70, shoulder=8.8, waist=7.4, depth=5.6, bust=1.0)
    skirt = speckled(CLOTH_BROWN, 40)
    vest = speckled(LEATHER[1:3], 41)
    b.boots()
    b.skirt(skirt, hem=8, flare=2.4)
    b.torso(lambda x, y, z, pose: np.where((z > 2) & (np.abs(x) < 1.6) & (y > 50), SCARF[2], vest(x, y, z, pose)))
    pockets = lambda x, y, z, pose: np.where((y > 25) & (y < 33) & (np.abs(np.abs(x) - 4.2) < 2.6), LEATHER[2], pick(LEATHER[:2], hash2(np.floor(x / 2).astype(int), np.floor(y / 6).astype(int), 42)))  # noqa: E731
    b.apron(pockets, hem=12, low_half=8.0, bib_half=0, flare=2.4)
    b.belt(LEATHER[2], y=37, buckle=IRON[1], height=2)
    b.part('root', capsule((-8.8, 34, 4.0), (-9.6, 22, 5.0), 1.6, 2.4), CLOTH_PALE[1])
    for k in range(3):
        b.part('root', capsule((3.0 + k, 32, 8.6), (3.4 + k * 1.2, 35, 8.8), 0.4), IRON[1])
    # Measuring tape round the neck, hanging down both sides of the chest.
    for sx in (-3.0, 3.0):
        b.part('chest', capsule((sx * 0.8, 56, 3.0), (sx, 44, b.depth + b.bust + 0.6), 0.7), TAPE[0])
    shirt = speckled(SCARF, 43)
    # Arms crossed: right forearm over the left, hands tucked at the elbows.
    b.arm(-1, (-8.8, 53, 0), (-10.4, 44, 3.5), (3.5, 46.5, 9.0), shirt, SKIN_PALE, SKIN_PALE[1], r=2.8, cuff=SCARF[1])
    b.arm(1, (8.8, 53, 0), (10.4, 44.5, 3.5), (-3.5, 45.0, 7.6), shirt, SKIN_PALE, SKIN_PALE[1], r=2.8, cuff=SCARF[1])
    b.part('r_elbow', ellipsoid((1.5, 47, 10.6), (1.9, 1.6, 1.4)), CLOTH_RED[0])
    b.part('r_elbow', ellipsoid((1.5, 48.5, 10.6), (0.4, 0.6, 0.4)), IRON[1])
    b.part('l_elbow', ellipsoid((-5.6, 46.5, 8.6), (0.7, 0.7, 0.7)), CLOTH_PALE[0])
    b.head(SKIN_PALE, earring=IRON[1])
    b.hair([HAIR_DARK[1], HAIR_GREY[1], HAIR_DARK[0]], 'bun')
    return b.rig, b.talking({'r_elbow': (-25, -70, 0), 'r_shoulder': (-4, 0, -10)})


def moth():
    """Moth: a thin fence in a long moth-grey velvet coat with gold-stitched
    hems, open over a brass-brown waistcoat and a pale cravat, a jeweller's
    loupe on a chain, rings on every finger. A shuttered lantern in his right
    hand. Dark hair tied back. 72 tall."""
    b = Body(scale=72 / 70, shoulder=8.8, waist=6.8, depth=5.0)

    def velvet(x, y, z, pose):
        out = pick(VELVET, hash2(np.floor(x / 2).astype(int) * 31 + np.floor(z / 2).astype(int), np.floor(y / 5).astype(int), 50))
        stitch = (y < 19) & (hash2(np.floor(np.arctan2(z, x) * 9).astype(int), np.floor(y / 2).astype(int), 51) < 0.22)
        return np.where(stitch, BRASS[1], out)
    b.boots(shades=[FACE_DARK[0], LEATHER[2]])
    b.legs(speckled(TROUSERS, 52), r=2.6)
    opening = coat_front(1.6, 4.0, hem=6)
    b.skirt(velvet, hem=6, flare=3.4, wave=0.4, front_cut=opening)

    def chest(x, y, z, pose):
        out = velvet(x, y, z, pose)
        front = z > 1.8
        vest = front & (np.abs(x) < opening(y))
        out = np.where(vest, pick(WAISTCOAT, hash2(np.floor(x).astype(int), np.floor(y / 2).astype(int), 53)), out)
        lapel = front & (np.abs(x) >= opening(y)) & (np.abs(x) < opening(y) + 1.6) & (y > 45)
        return np.where(lapel, VELVET[2], out)
    b.torso(chest)
    b.part('chest', ellipsoid((0, 54.5, 4.4), (1.8, 2.4, 1.4)), CLOTH_PALE[0])
    b.part('chest', capsule((1.2, 55, 4.5), (2.0, 48, b.depth + 0.8), 0.4), BRASS[1])
    b.part('chest', minus(ellipsoid((2.0, 46.6, b.depth + 1.0), (1.2, 1.2, 0.6)), ellipsoid((2.0, 46.6, b.depth + 1.6), (0.6, 0.6, 0.6))), BRASS[0])
    b.arm(-1, (-8.8, 53, 0), (-10.0, 42, 0.5), (-10.4, 31.5, 2.0), velvet, velvet, SKIN_PALE[1], r=2.7, cuff=VELVET[2])
    b.arm(1, (8.8, 53, 0), (10.0, 42, 0.5), (9.4, 32, 2.8), velvet, velvet, SKIN_PALE[1], r=2.7, cuff=VELVET[2])
    for sx, bone in ((-10.4, 'r_elbow'), (9.2, 'l_elbow')):
        for k in range(3):
            b.part(bone, ellipsoid((sx + (k - 1) * 0.9, 28.6, 3.6), (0.4, 0.4, 0.4)), BRASS[0])
    # The shuttered lantern hung from his right hand.
    b.part('r_elbow', capsule((-10.5, 28.5, 2.6), (-10.5, 25.5, 2.6), 0.4), IRON[0])
    b.part('r_elbow', union(capsule((-10.5, 19.5, 2.6), (-10.5, 25, 2.6), 2.3)), lambda x, y, z, pose: np.where(
        (y > 20.5) & (y < 24) & (np.abs(np.arctan2(z - 2.6, x + 10.5)) % 1.0 < 0.55), GLOW[0], IRON[0]))
    b.head(SKIN_PALE, earring=BRASS[0])
    b.hair(HAIR_DARK, 'wavy')
    b.part('head', ellipsoid((0, 60, -5.0), (1.4, 1.8, 1.4)), HAIR_DARK[2])
    return b.rig, b.talking({'l_elbow': (-60, -15, 0), 'l_shoulder': (-10, 0, 10)})


def sister_carmine():
    """Sister Carmine: an upright, smiling hospice nurse. A grey habit to the
    ground under a long red apron with a pale eight-pointed star, a white
    wimple and red veil, very red lips, pouches at the belt, a steel pen
    raised in her right hand. 72 tall."""
    b = Body(scale=72 / 70, shoulder=8.8, waist=7.4, depth=5.8, bust=1.2)
    habit = speckled(HABIT, 60)
    red = speckled(CLOTH_RED, 61)
    b.boots(top=6, shades=[FACE_DARK[0], LEATHER[2]])
    b.skirt(habit, hem=2, flare=3.6, wave=0.6)
    b.torso(habit)

    def apron(x, y, z, pose):
        out = red(x, y, z, pose)
        star = (y > 44) & (y < 50) & ((np.abs(x) < 0.6) | (np.abs(y - 47) < 0.6) | (np.abs(np.abs(x) - np.abs(y - 47)) < 0.6)) & (np.abs(x) < 3)
        return np.where(star, PAPER[0], out)
    b.apron(apron, hem=9, low_half=6.8, bib_half=5.6, straps=CLOTH_RED[1], flare=3.6)
    b.belt(LEATHER[2], y=37, buckle=IRON[1], height=2)
    for sx in (-6.5, 6.0):
        b.part('root', ellipsoid((sx, 32.5, 6.6), (1.8, 2.6, 1.4)), LEATHER[1])
    b.part('root', capsule((4.0, 36, 7.6), (4.5, 28, 8.2), 0.5), IRON[1])
    b.arm(-1, (-8.8, 53, 0), (-10.2, 43.5, 2.0), (-6.2, 50.5, 6.6), habit, habit, SKIN_PALE[1], r=2.8, cuff=WIMPLE[1])
    b.part('r_elbow', capsule((-5.4, 52.5, 8.0), (-4.2, 58, 9.0), 0.5), IRON[1])
    b.arm(1, (8.8, 53, 0), (10.0, 42.5, 0.5), (10.0, 32.5, 2.2), habit, habit, SKIN_PALE[1], r=2.8, cuff=WIMPLE[1])
    b.head(SKIN_PALE, lips=LIPS_RED[0])
    # The wimple framing the face and covering the throat, the red veil over it.
    wimple = minus(ellipsoid((0, 62, 0.8), (5.4, 7.6, 5.6)), lambda x, y, z: ((z > 2.4) & (y > 58.8) & (y < 67.5) & (np.abs(x) < 3.8)))
    b.part('head', wimple, WIMPLE[0])
    veil = union(ellipsoid((0, 65.4, 0.0), (6.2, 5.0, 6.4)), column(50, 64, lambda y: 6.2 + (64 - y) * 0.2, lambda y: 5.6 + (64 - y) * 0.15, flat(-1.6)))
    b.part('head', minus(veil, lambda x, y, z: (z > 1.0 + np.clip(64 - y, 0, None) * 0.9) | ((z > 2.0) & (y < 64.5))), red)
    return b.rig, b.talking({'l_elbow': (-55, -15, 0), 'l_shoulder': (-8, 0, 8)})


def sister_vale():
    """Sister Vale, the Grey Sister: tall, calm, in a long grey coat cut like a
    habit, with a short cape, wide hanging sleeves and a high collar, hands
    folded at the waist. One more sleeve hangs at her left side as if a second
    arm were inside it. Grey hair pinned up. 72 tall."""
    b = Body(scale=72 / 70, shoulder=8.6, waist=7.2, depth=5.6, bust=0.8)
    coat = speckled([WOOL[1], WOOL[0], HABIT[1]], 70)
    b.boots(top=5, shades=[FACE_DARK[0], LEATHER[2]])
    b.skirt(coat, hem=1, flare=4.2, wave=0.6)
    b.torso(lambda x, y, z, pose: np.where((z > 2) & (np.abs(x) < 0.6) & (y < 52), WOOL[1], coat(x, y, z, pose)))
    # The short cape over the shoulders and a high collar.
    cape = shell(column(42, 57, lambda y: b.torso_x(y) + 0.2, lambda y: b.torso_z(y) + 0.2, b.torso_c, power=2.3),
                 column(43, 56.5, lambda y: b.torso_x(y) + 2.6, lambda y: b.torso_z(y) + 2.4, b.torso_c, power=2.3))
    b.part('chest', where(cape, lambda x, y, z: ~((z > 2.5) & (np.abs(x) < 2.0 + (56 - y) * 0.4))), speckled([HABIT[2], HABIT[0]], 71))
    b.part('chest', shell(column(54, 59, flat(2.6), flat(2.8), flat(0.6)), column(54, 59.5, flat(4.0), flat(4.2), flat(0.6))), HABIT[1])
    for sx in (-3.5, 3.5):
        b.part('chest', ellipsoid((sx, 54.0, 5.6), (0.8, 0.8, 0.5)), BRASS[1])
    for side, sx in ((-1, -8.6), (1, 8.6)):
        b.arm(side, (sx, 53, 0), (sx * 1.1, 43, 2.0), (sx * 0.3, 40.0, 7.4), coat, coat, None, r=2.8, flare=1.4, cuff=HABIT[0])
    b.part('l_elbow', ellipsoid((0, 39.4, 10.4), (3.2, 2.0, 1.8)), SKIN_PALE[1])
    b.part('l_elbow', capsule((-2.4, 39.8, 10.8), (2.4, 39.0, 11.0), 0.6), SKIN_PALE[2])
    # The empty sleeve, hanging straight behind her left arm.
    b.part('chest', capsule((9.0, 52, -2.0), (10.6, 33, -1.6), 2.6, 3.8), coat)
    b.head(SKIN_PALE)
    b.hair(HAIR_GREY[:2] + [HABIT[2]], 'bun')
    return b.rig, b.talking({'r_elbow': (-25, 25, 0), 'r_shoulder': (-14, 0, -6)})


def old_hobb():
    """Old Hobb: a stooped miller, eyes down, flour in every crease. A long
    patched smock under a canvas apron, dark trousers, his cap twisted in both
    hands, a grey beard and a bald crown ringed with grey. 66 tall, bent."""
    b = Body(scale=0.99, shoulder=9.8, waist=8.8, depth=6.4)
    smock = dusted(speckled(SMOCK, 80), FLOUR, 0.04, 81)
    b.boots(shades=LEATHER[1:3])
    b.legs(speckled(TROUSERS, 82))
    b.skirt(smock, hem=20, flare=2.6, wave=0.5)
    b.torso(smock)

    def apron(x, y, z, pose):
        out = dusted(speckled([CLOTH_PALE[1], SMOCK[2]], 83), FLOUR, 0.06, 84)(x, y, z, pose)
        patch = ((np.abs(x - 3.5) < 2.4) & (np.abs(y - 26) < 2.6)) | ((np.abs(x + 4) < 1.8) & (np.abs(y - 18) < 2))
        return np.where(patch, LEATHER[1], out)
    b.apron(apron, hem=14, low_half=8.0, bib_half=6.0, straps=LEATHER[2], flare=2.6)
    for side, sx in ((-1, -9.8), (1, 9.8)):
        b.arm(side, (sx, 53, 0), (sx * 1.05, 43.5, 3.5), (sx * 0.25, 44, 8.5), smock, smock, SKIN[1], r=3.0)
    # The cap wrung between his hands.
    b.part('l_elbow', capsule((-3.5, 42.5, 10.5), (3.5, 41.5, 10.2), 2.0, 1.6), speckled(SMOCK[1:], 85, 1, 1))
    b.part('l_elbow', ellipsoid((1.0, 38.5, 10.0), (2.4, 3.0, 1.8)), SMOCK[1])
    b.head(SKIN, beard=HAIR_GREY, eyes_down=True)
    b.hair(HAIR_GREY, 'fringe')
    stoop = {'chest': (16, 0, 0), 'head': (24, 0, 0), 'offset': (0, 0, -2.0)}
    return b.rig, b.talking({'r_elbow': (-10, -40, 0), 'r_shoulder': (-6, 0, -14)}, idle_extra=stoop)


def lise_hobb():
    """Lise Hobb: a young woman leaning on a crutch under her left arm, her
    hip sitting wrong. A plain mill dress with rolled sleeves, a pale
    flour-dusted apron, dark hair pinned up. Still, watching. 72 tall."""
    b = Body(scale=72 / 70, shoulder=8.8, waist=7.2, depth=5.6, bust=1.2)
    dress = speckled(DRESS_MILL, 90)
    b.boots()
    b.skirt(dress, hem=7, flare=3.0)
    b.torso(dress)
    apron = dusted(speckled([CLOTH_PALE[1], CLOTH_PALE[0]], 91), FLOUR, 0.05, 92)
    b.apron(apron, hem=13, low_half=7.6, bib_half=5.0, straps=CLOTH_PALE[1], flare=3.0)
    b.belt(CLOTH_PALE[1], y=37.5, buckle=None, height=1.5)
    b.arm(-1, (-8.8, 53, 0), (-10.2, 42, 0.5), (-10.2, 32, 2.0), dress, SKIN_PALE, SKIN_PALE[1], r=2.8)
    b.arm(1, (8.8, 53, 0), (10.6, 42.5, 1.0), (11.6, 37.5, 4.2), dress, SKIN_PALE, SKIN_PALE[1], r=2.8)
    # The crutch: a pad under the arm, the hand grip, one shaft to the ground.
    b.part('chest', capsule((10.4, 50, 2.6), (13.0, 49.6, 2.6), 1.2), LEATHER[1])
    b.part('root', capsule((11.8, 49, 2.6), (14.4, 0.5, 4.0), 1.1), WOOD[3])
    b.part('root', capsule((12.8, 37.5, 2.0), (12.8, 37.5, 6.0), 0.8), WOOD[2])
    b.head(SKIN_PALE)
    b.hair(HAIR_DARK, 'bun')
    lean = {'chest': (0, 0, -4), 'head': (0, 0, 3)}
    return b.rig, b.talking({'r_elbow': (-60, -10, 0), 'r_shoulder': (-10, 0, -6)}, idle_extra=lean)


def jessa_bed():
    """Jessa Brune, dying in the hospice: a plank bed with a straw pallet, a
    grey blanket over her, her head on the pillow with black-stained lips,
    her right arm reaching up out of the bed. Static, 40 tall, head to -Z."""
    rig = Rig(1.0)
    rig.bone('root', (0, 0, 0))
    wood = speckled(WOOD[:3], 100, 2, 2)
    for sx in (-15.5, 15.5):
        for sz, top in ((-31.5, 38), (31.5, 24)):
            rig.part('root', capsule((sx, 0, sz), (sx, top, sz), 1.6), wood)
        rig.part('root', capsule((sx, 11, -31.5), (sx, 11, 31.5), 1.4), wood)
    for sz, top in ((-31.5, 36), (31.5, 22)):
        rig.part('root', capsule((-15.5, top - 1, sz), (15.5, top - 1, sz), 1.3), wood)
        rig.part('root', capsule((-15.5, 13, sz), (15.5, 13, sz), 1.3), wood)
    rig.part('root', capsule((-15.5, 28, -31.5), (15.5, 28, -31.5), 1.2), wood)
    rig.part('root', capsule((-15.5, 20, -31.5), (15.5, 20, -31.5), 1.2), wood)
    rig.part('root', column(11, 17, flat(14.8), flat(30.5), power=6.0), dusted(speckled(STRAW, 101, 1, 1), [STRAW[1]], 0.3, 102))
    # A big pillow propping her up against the headboard.
    rig.part('root', capsule((0, 20, -27), (0, 25, -29), 5.0), speckled(BURLAP, 103, 2, 2))
    # The blanket over her body, ragged where it hangs over the sides.
    blanket = union(ellipsoid((0, 18, 8), (12.5, 5.5, 23)), column(10, 19, flat(15.6), flat(28), flat(5.0), power=6.0))
    rag = lambda x, y, z: (y > 13 + 3 * hash2(np.floor(z / 2).astype(int), np.floor(x / 3).astype(int), 104)) | (np.abs(x) < 15)  # noqa: E731
    rig.part('root', where(minus(blanket, lambda x, y, z: z < -15), rag), speckled(WOOL, 105, 2, 2))
    # Her chest in a pale shift, raised on the pillow.
    rig.part('root', capsule((0, 20.5, -11), (0, 22.5, -16.5), 5.6, 4.6), speckled(CLOTH_PALE, 106))

    def face(x, y, z, pose):
        # The face looks up and toward the foot of the bed.
        out = pick(SKIN_PALE[1:], hash2(np.floor(x).astype(int), np.floor(y).astype(int), 107) * 0.8)
        front = (z + 22.0) * 0.6 + (y - 28.0) * 0.8 > 2.6
        eyes = front & (np.abs(np.abs(x) - 1.8) < 0.8) & (np.abs(y - 30.6) < 0.6)
        mouth = front & (np.abs(x) < 1.3) & (np.abs(y - 27.4) < 0.8)
        out = np.where(eyes, FACE_DARK[0], out)
        return np.where(mouth, RAVEN[0], out)
    rig.part('root', ellipsoid((0, 28.6, -22.0), (4.4, 5.0, 4.6)), face)
    rig.part('root', ellipsoid((0, 29.6, -18.2), (0.7, 1.0, 0.8)), SKIN_PALE[2])
    hair = minus(ellipsoid((0, 29.6, -24.0), (6.0, 5.6, 4.2)), lambda x, y, z: (z + 22.0) * 0.6 + (y - 28.0) * 0.8 > 1.2)
    rig.part('root', hair, speckled(HAIR_DARK, 108, 1, 1))
    # Her right arm (-X), reaching out toward the foot of the bed.
    rig.part('root', capsule((-6.5, 23, -14), (-8.4, 26.6, -7.5), 2.0, 1.8), CLOTH_PALE[1])
    rig.part('root', capsule((-8.4, 26.6, -7.5), (-9.6, 29.8, -0.5), 1.4, 1.2), speckled(SKIN_PALE[1:], 109, 2, 2))
    rig.part('root', ellipsoid((-9.8, 30.5, 1.5), (1.5, 1.6, 1.8)), SKIN_PALE[1])
    for k in range(4):
        rig.part('root', capsule((-9.8 + (k - 1.5) * 0.8, 30.7, 2.4), (-9.9 + (k - 1.5) * 1.1, 31.2, 4.0), 0.4), SKIN_PALE[2])
    rig.part('root', capsule((6.5, 21, -13), (8.5, 20, -2), 1.6), CLOTH_PALE[1])
    return rig, []


PEOPLE = {
    'Edda': (edda, (64, 76, 64)),
    'Matthew': (matthew, (60, 78, 60)),
    'ReeveHollan': (reeve_hollan, (64, 78, 64)),
    'MarraSenn': (marra_senn, (60, 78, 60)),
    'Moth': (moth, (60, 78, 60)),
    'SisterCarmine': (sister_carmine, (60, 78, 60)),
    'SisterVale': (sister_vale, (60, 78, 60)),
    'OldHobb': (old_hobb, (60, 74, 64)),
    'LiseHobb': (lise_hobb, (64, 78, 60)),
    'JessaBed': (jessa_bed, (40, 44, 72)),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    for name in args.names or PEOPLE:
        make, size = PEOPLE[name]
        rig, clips = make()
        build(name, rig, clips, size, args.preview)


if __name__ == '__main__':
    main()
