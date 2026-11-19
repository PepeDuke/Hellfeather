"""Builds the models of the gear Wren wears and holds, which ride the sockets on
her body model (player.py): helmets on `head`, shields on `hand_l`, weapons on
`hand_r`. Each is a static .qvox with a `grip` socket, the point and turn the
engine lines up with her socket (Quaxel-Engine Docs/VoxelModels.md).

They are drawn in Wren's rig units and scaled like her, so a helmet built
around player.HEAD sits on her head. Weapons follow Assets/BattleAxe.qvox,
which was made by hand: the haft runs along +Y, the blade lies in the XY plane,
and the grip turns by yaw -90.

    python Tools/Models/gear.py                 build every piece
    python Tools/Models/gear.py MinersHelmet    build some of them
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402
import player  # noqa: E402
from figure import Rig, capsule, ellipsoid, fit, minus, where  # noqa: E402
from kit import BRASS, CLOTH_PALE, CLOTH_RED, FEATHER_PALE, GLOW, IRON, LEATHER, RAVEN, SILVER, STONE, WOOD, WOOD_DARK, compact, hash2, pick  # noqa: E402
from people import speckled  # noqa: E402


def wren_scale():
    rig = player.wren().rig
    fit(rig, player.HEIGHT)
    return rig.scale


def new_rig(grip, yaw=0.0, pitch=0.0, roll=0.0):
    r = Rig(wren_scale())
    r.bone('root', (0, 0, 0))
    r.socket('grip', 'root', grip, yaw=yaw, pitch=pitch, roll=roll)
    return r


def write(name, rig, size=(80, 120, 80)):
    """Renders the rig, cuts it to its voxels on every side and writes it with
    its grip socket."""
    # Lifted so parts below the grip, such as a pommel, are not cut off at
    # the canvas floor; the cut below drops the empty space again.
    pose = {'offset': (0, 30, 0)}
    grid = rig.render(pose, size)
    xs, ys, zs = (np.nonzero((grid >= 0).any(axis=axes))[0] for axes in ((1, 2), (0, 2), (0, 1)))
    lo = np.array([xs.min(), ys.min(), zs.min()])
    grid = grid[xs.min():xs.max() + 1, ys.min():ys.max() + 1, zs.min():zs.max() + 1]
    # The grip's canvas position, as figure.Rig.socket_lines works it out,
    # moved by the cut.
    line = rig.socket_lines(pose, size)[0].split()
    point = np.array([float(v) for v in line[2:5]]) - lo
    angles = ' '.join(line[5:8])
    (grid,), palette = compact([grid])
    path = act1.ASSETS / f'{name}.qvox'
    act1.write(path, palette, grid, [])
    text = path.read_text(encoding='ascii').split('\n')
    at = text.index('# y = 0')
    text.insert(at, f'socket grip {point[0]:.2f} {point[1]:.2f} {point[2]:.2f} {angles}')
    path.write_text('\n'.join(text), encoding='ascii')
    print(f'{name}: {grid.shape[0]} x {grid.shape[1]} x {grid.shape[2]}, grip {point[0]:.1f} {point[1]:.1f} {point[2]:.1f}')


def miners_helmet():
    """A worn leather miner's cap, pushed back, a darker band, a brass oil lamp
    on the front with its flame lit."""
    hx, hy, hz = player.HEAD
    r = new_rig(player.HEAD)
    cap = where(ellipsoid((0, hy + 2.4, hz - 2.4), (5.0, 3.8, 5.2)), lambda x, y, z: y > hy + 2.6)
    r.part('root', cap, speckled(LEATHER[1:3], 405, 1, 2))
    r.part('root', where(ellipsoid((0, hy + 2.4, hz - 2.4), (5.3, 3.9, 5.5)), lambda x, y, z: (y > hy + 2.4) & (y < hy + 3.8)), LEATHER[2])
    r.part('root', capsule((0, hy + 4.4, hz + 2.4), (0, hy + 4.6, hz + 4.2), 1.4), BRASS[1])
    r.part('root', ellipsoid((0, hy + 4.6, hz + 4.4), (1.0, 1.0, 0.6)), GLOW[0])
    return r


def iron_helm():
    """An iron helm: a round skull with a riveted gold band and a nose guard."""
    hx, hy, hz = player.HEAD
    r = new_rig(player.HEAD)
    dome = where(ellipsoid((0, hy + 0.8, hz - 0.4), (5.4, 6.4, 5.6)), lambda x, y, z: y > hy - 0.6)
    face = lambda x, y, z: (z > hz + 1.0) & (y < hy + 2.6) & (np.abs(x) > 0.9)  # noqa: E731
    r.part('root', minus(dome, face), speckled(IRON, 410, 1, 2))
    r.part('root', where(ellipsoid((0, hy + 0.8, hz - 0.4), (5.7, 6.5, 5.9)), lambda x, y, z: (y > hy + 2.8) & (y < hy + 3.9)),
           lambda x, y, z, pose: np.where(hash2(np.floor(np.arctan2(z, x) * 6).astype(int), 0, 411) < 0.2, SILVER[1], BRASS[0]))
    r.part('root', capsule((0, hy + 2.0, hz + 5.2), (0, hy - 2.6, hz + 5.6), 0.8), IRON[1])
    return r


def round_shield():
    """A round wooden shield: planks with a steel rim and a steel boss. Its face
    looks along +Z; the grip is behind its middle, where the forearm goes."""
    r = new_rig((0, 0, -1.6))
    radius = 8.5

    def planks(x, y, z, pose):
        out = pick(WOOD[:3], hash2(np.floor(x / 2.4).astype(int), 0, 412))
        out = np.where(np.abs(((x / 2.4) % 1.0) - 0.5) > 0.42, WOOD_DARK[0], out)
        rim = np.hypot(x, y) > radius - 1.1
        return np.where(rim, IRON[1], out)
    disc = where(ellipsoid((0, 0, 0), (radius, radius, 0.8)), lambda x, y, z: True)
    r.part('root', disc, planks)
    r.part('root', where(ellipsoid((0, 0, 0.4), (2.4, 2.4, 1.8)), lambda x, y, z: z > 0.3), SILVER[1])
    r.part('root', capsule((-2.5, 0, -1.4), (2.5, 0, -1.4), 0.6), LEATHER[2])
    return r


def short_sword():
    """A short steel sword with a gold crossguard and a leather-wrapped grip."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -3.5, 0), (0, 3.5, 0), 0.8), LEATHER[2])
    r.part('root', ellipsoid((0, -4.6, 0), (1.2, 1.1, 1.1)), BRASS[0])
    r.part('root', capsule((-4.0, 4.4, 0), (4.0, 4.4, 0), 0.8), BRASS[0])

    def blade(x, y, z):
        half = np.where(y < 26, 1.4, 1.4 * np.clip((31 - y) / 5, 0, 1))
        return (np.abs(x) <= half) & (np.abs(z) < 0.5) & (y > 5) & (y < 31)
    blade.box = (np.array([-1.5, 5, -0.6]), np.array([1.5, 31, 0.6]))
    r.part('root', blade, lambda x, y, z, pose: np.where(np.abs(x) < 0.4, SILVER[0], SILVER[1]))
    return r


def millstone_maul():
    """A maul with a quarter of a millstone for a head, on a long iron-banded haft."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -8, 0), (0, 34, 0), 1.0), lambda x, y, z, pose: np.where(np.floor(y) % 9 == 0, IRON[0], WOOD[1]))
    r.part('root', capsule((0, -2.5, 0), (0, 3.5, 0), 1.2), LEATHER[2])
    stone = where(ellipsoid((0, 37, 0), (8.0, 4.6, 4.6)), lambda x, y, z: np.hypot(x, z) > 1.2)
    r.part('root', stone, lambda x, y, z, pose: pick(STONE, hash2(np.floor(x / 2).astype(int), np.floor(y / 2).astype(int), 413)))
    r.part('root', where(ellipsoid((0, 37, 0), (8.3, 1.0, 4.9)), lambda x, y, z: True), IRON[0])
    return r


def chain_coif():
    """A hood of iron rings over the skull and down to the shoulders, open at the
    face, rows of rings catching the light in turn."""
    hx, hy, hz = player.HEAD
    r = new_rig(player.HEAD)
    hood = where(ellipsoid((0, hy + 0.6, hz - 0.6), (5.6, 6.8, 5.8)), lambda x, y, z: y > hy - 5.4)
    face = lambda x, y, z: (z > hz + 0.6) & (y < hy + 2.4) & (y > hy - 4.6) & (np.abs(x) < 3.4)  # noqa: E731

    def rings(x, y, z, pose):
        row = np.floor((y - hy) / 1.0).astype(int)
        lit = (row + np.floor(np.arctan2(z - hz, x) * 4).astype(int)) % 2 == 0
        return np.where(lit, IRON[1], IRON[0])
    r.part('root', minus(hood, face), rings)
    # A leather band where the hood meets the brow.
    r.part('root', where(ellipsoid((0, hy + 0.6, hz - 0.6), (5.9, 6.9, 6.1)), lambda x, y, z: (y > hy + 2.4) & (y < hy + 3.2)), LEATHER[2])
    return r


def great_helm():
    """A flat-topped steel great helm that closes over the whole head, with a
    dark eye slit, a row of breathing holes and a gold cross down the front."""
    hx, hy, hz = player.HEAD
    r = new_rig(player.HEAD)

    def pot(x, y, z):
        return (np.hypot(x / 5.6, (z - hz + 0.4) / 5.8) <= 1.0) & (y > hy - 5.6) & (y < hy + 6.0)
    pot.box = (np.array([-5.7, hy - 5.7, hz - 6.3]), np.array([5.7, hy + 6.1, hz + 5.5]))

    def plates(x, y, z, pose):
        out = np.where(hash2(np.floor(x).astype(int), np.floor(y).astype(int), 414) < 0.5, SILVER[1], IRON[1])
        front = z > hz + 3.0
        slit = front & (np.abs(y - (hy + 1.2)) < 0.6) & (np.abs(x) > 0.7)
        holes = front & (np.abs(y - (hy - 2.2)) < 0.5) & (np.floor(x + 0.5).astype(int) % 2 == 0) & (np.abs(x) > 1.2)
        cross = front & ((np.abs(x) < 0.7) | (np.abs(y - (hy + 1.2)) < 0.4) & ~slit)
        out = np.where(cross, BRASS[0], out)
        return np.where(slit | holes, IRON[0], out)
    r.part('root', pot, plates)
    r.part('root', where(ellipsoid((0, hy + 6.0, hz - 0.4), (5.6, 0.8, 5.8)), lambda x, y, z: True), IRON[1])
    return r


def kite_shield():
    """A tall kite shield painted dark red, rounded at the top and coming to a
    point below, a steel rim and a black raven across its face. Built and gripped
    like the round shield."""
    r = new_rig((0, 0, -1.6))

    def outline(x, y):
        top = np.hypot(x / 7.0, np.maximum(y - 4.0, 0) / 5.0) <= 1.0
        below = (y <= 4.0) & (np.abs(x) <= 7.0 * np.clip((y + 14.0) / 18.0, 0, 1))
        return top & (y <= 9.0) | below & (y >= -14.0)

    def board(x, y, z):
        return outline(x, y) & (np.abs(z) < 0.8)
    board.box = (np.array([-7.2, -14.2, -0.9]), np.array([7.2, 9.2, 0.9]))

    def paint(x, y, z, pose):
        rim = ~outline(x * 1.16, (y - 1.0) * 1.12 + 1.0)
        bird = (np.hypot(x / 3.6, (y - 1.0) / 1.2) <= 1.0) | (np.hypot(x / 1.2, (y - 1.5) / 3.6) <= 1.0)
        out = np.where(bird & (z > 0), RAVEN[0], CLOTH_RED[1])
        return np.where(rim, IRON[1], out)
    r.part('root', board, paint)
    r.part('root', capsule((-2.5, 0, -1.4), (2.5, 0, -1.4), 0.6), LEATHER[2])
    return r


def hand_axe():
    """Wren's woodsman's hand axe: a short ash handle wrapped at the grip and one
    bearded steel blade. Built like the Battle Axe: the haft along +Y, the blade
    in the XY plane toward -X, which hangs back when she carries it."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -4.0, 0), (0, 17.0, 0), 0.9), lambda x, y, z, pose: np.where(np.floor(y * 0.7) % 7 == 0, WOOD[2], WOOD[0]))
    r.part('root', capsule((0, -3.0, 0), (0, 2.5, 0), 1.1), LEATHER[2])

    def blade(x, y, z):
        # Narrow at the eye, widening to a curved bit that hangs down in a beard.
        reach = (-x - 0.6) / 7.0
        low = 11.0 - 4.5 * np.clip(reach, 0, None) ** 1.5
        high = 16.5 + 1.5 * reach
        return (x < -0.6) & (x > -7.6) & (y > low) & (y < high) & (np.abs(z) < 0.6 - 0.3 * reach)
    blade.box = (np.array([-7.7, 5.5, -0.7]), np.array([-0.5, 18.2, 0.7]))
    r.part('root', blade, lambda x, y, z, pose: np.where(x < -6.2, SILVER[0], SILVER[1]))
    # The eye of the head around the haft, and a short poll behind it.
    r.part('root', capsule((1.6, 14.2, 0), (-1.0, 14.2, 0), 1.5), IRON[1])
    return r


def falchion():
    """A falchion: a broad single-edged blade that swells toward its clipped
    point, an iron crossguard and a leather grip. Built like the short sword,
    its edge toward -X like the axes' blades."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -3.5, 0), (0, 3.5, 0), 0.8), LEATHER[2])
    r.part('root', ellipsoid((0, -4.6, 0), (1.1, 1.0, 1.0)), IRON[1])
    r.part('root', capsule((-3.6, 4.4, 0), (3.6, 4.4, 0), 0.8), IRON[1])

    def blade(x, y, z):
        # The back stays straight; the edge bellies out and sweeps up to the point.
        edge = 1.3 + 1.4 * np.clip((y - 5) / 20, 0, 1)
        edge = np.where(y > 25, edge * np.clip((30 - y) / 5, 0, 1), edge)
        return (x <= 1.1) & (x >= -edge) & (np.abs(z) < 0.5) & (y > 5) & (y < 30)
    blade.box = (np.array([-2.8, 5, -0.6]), np.array([1.2, 30, 0.6]))
    r.part('root', blade, lambda x, y, z, pose: np.where(x < -1.6, SILVER[0], SILVER[1]))
    return r


def flanged_mace():
    """A flanged mace: a steel head of six upright flanges on an iron-banded
    wooden haft."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -4.0, 0), (0, 22.0, 0), 0.9), lambda x, y, z, pose: np.where(np.floor(y) % 8 == 0, IRON[0], WOOD[1]))
    r.part('root', capsule((0, -3.0, 0), (0, 2.5, 0), 1.1), LEATHER[2])
    r.part('root', capsule((0, 18.0, 0), (0, 26.0, 0), 1.8), IRON[1])

    def flanges(x, y, z):
        angle = np.arctan2(z, x)
        sector = np.abs(((angle / (np.pi / 3)) % 1.0) - 0.5) > 0.38
        radius = np.hypot(x, z)
        swell = 1.8 + 2.4 * np.sin(np.clip((y - 18.0) / 8.0, 0, 1) * np.pi)
        return sector & (radius < swell) & (y > 18.0) & (y < 26.0)
    flanges.box = (np.array([-4.3, 17.9, -4.3]), np.array([4.3, 26.1, 4.3]))
    r.part('root', flanges, lambda x, y, z, pose: np.where(np.hypot(x, z) > 3.2, SILVER[0], SILVER[1]))
    r.part('root', ellipsoid((0, 27.0, 0), (1.2, 1.4, 1.2)), SILVER[1])
    return r


def war_hammer():
    """A war hammer from the Undercroft: a blocky steel head with a square face
    on each side and a short spike on top, on an iron-banded haft."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -4.0, 0), (0, 24.0, 0), 0.9), lambda x, y, z, pose: np.where(np.floor(y) % 7 == 0, IRON[0], WOOD_DARK[0]))
    r.part('root', capsule((0, -3.0, 0), (0, 2.5, 0), 1.1), LEATHER[2])

    def head(x, y, z):
        return (np.abs(x) <= 4.6) & (np.abs(z) <= 2.2) & (y > 20.0) & (y < 26.0)
    head.box = (np.array([-4.7, 19.9, -2.3]), np.array([4.7, 26.1, 2.3]))

    def steel(x, y, z, pose):
        face = np.abs(x) > 3.8
        band = np.abs(y - 23.0) < 0.6
        out = np.where(face, SILVER[0], SILVER[1])
        return np.where(band & ~face, IRON[0], out)
    r.part('root', head, steel)
    r.part('root', capsule((0, 26.0, 0), (0, 29.5, 0), 0.7), SILVER[0])
    return r


def tower_shield():
    """A tall oblong tower shield of iron-bound planks with a steel rim and a
    dark boss. Built and gripped like the round shield."""
    r = new_rig((0, 0, -1.6))
    half_w, low, high = 6.5, -15.0, 10.0

    def board(x, y, z):
        return (np.abs(x) <= half_w) & (y >= low) & (y <= high) & (np.abs(z) < 0.8)
    board.box = (np.array([-half_w - 0.1, low - 0.1, -0.9]), np.array([half_w + 0.1, high + 0.1, 0.9]))

    def planks(x, y, z, pose):
        out = pick(WOOD[:3], hash2(np.floor(x / 2.6).astype(int), 0, 415))
        out = np.where(np.abs(((x / 2.6) % 1.0) - 0.5) > 0.42, WOOD_DARK[0], out)
        bands = (np.abs(y - 6.0) < 0.7) | (np.abs(y + 10.0) < 0.7)
        out = np.where(bands, IRON[0], out)
        rim = (np.abs(x) > half_w - 1.0) | (y < low + 1.0) | (y > high - 1.0)
        return np.where(rim, IRON[1], out)
    r.part('root', board, planks)
    r.part('root', where(ellipsoid((0, -2.0, 0.4), (2.2, 2.2, 1.6)), lambda x, y, z: z > 0.3), IRON[0])
    r.part('root', capsule((-2.5, 0, -1.4), (2.5, 0, -1.4), 0.6), LEATHER[2])
    return r


def visored_helm():
    """A steel helm with a pointed visor drawn forward like a snout, rows of
    breathing slits on it, and a gold rim around the face opening."""
    hx, hy, hz = player.HEAD
    r = new_rig(player.HEAD)
    skull = where(ellipsoid((0, hy + 0.8, hz - 0.6), (5.5, 6.6, 5.7)), lambda x, y, z: y > hy - 5.2)
    r.part('root', skull, lambda x, y, z, pose: np.where(hash2(np.floor(x).astype(int), np.floor(y).astype(int), 416) < 0.5, SILVER[1], IRON[1]))

    def visor(x, y, z):
        # A wedge that narrows to a ridge as it reaches forward.
        reach = np.clip((z - hz) / 4.0, 0, 1)
        return (z > hz) & (z < hz + 4.0 + 1.6) & (np.abs(x) <= 4.6 * (1.0 - reach) + 0.6) & (y > hy - 4.0) & (y < hy + 2.6)
    visor.box = (np.array([-5.3, hy - 4.1, hz]), np.array([5.3, hy + 2.7, hz + 5.7]))

    def slits(x, y, z, pose):
        out = np.where(np.abs(x) < 0.7, SILVER[0], SILVER[1])
        eye = np.abs(y - (hy + 1.2)) < 0.5
        vents = (y < hy - 0.6) & (np.floor(y + 0.5).astype(int) % 2 == 0) & (np.abs(x) > 0.8)
        return np.where(eye | vents, IRON[0], out)
    r.part('root', visor, slits)
    r.part('root', where(ellipsoid((0, hy + 0.8, hz - 0.6), (5.8, 6.8, 6.0)), lambda x, y, z: (y > hy + 2.6) & (y < hy + 3.4)), BRASS[0])
    return r


def swanbone_buckler():
    """Act II's Swanbone Buckler (II-1): a small round buckler of pale boiled
    leather over a frame of swan bones whose wingbone ends show at the rim, a
    black feather tied to the iron boss. Faces +Z like the round shield."""
    r = new_rig((0, 0, -1.4))
    radius = 6.5
    pale = [CLOTH_PALE[0], CLOTH_PALE[1], LEATHER[3]]

    def face(x, y, z, pose):
        out = pick(pale, hash2(np.floor(x).astype(int), np.floor(y).astype(int), 430) * 0.8)
        # Bones run across the face as spokes, pale and knuckled at the rim.
        angle = np.arctan2(y, x)
        spoke = np.abs(np.sin(angle * 3.0)) < 0.16
        return np.where(spoke | (np.hypot(x, y) > radius - 0.9), FEATHER_PALE[2], out)
    disc = where(ellipsoid((0, 0, 0), (radius, radius, 0.7)), lambda x, y, z: True)
    r.part('root', disc, face)
    for k in range(6):
        a = k * np.pi / 3.0
        r.part('root', ellipsoid((np.cos(a) * (radius + 0.6), np.sin(a) * (radius + 0.6), 0), (0.9, 0.9, 0.9)), FEATHER_PALE[0])
    r.part('root', where(ellipsoid((0, 0, 0.3), (1.8, 1.8, 1.4)), lambda x, y, z: z > 0.2), IRON[1])
    r.part('root', capsule((0.6, -0.5, 1.4), (1.6, -5.5, 1.0), 0.45), RAVEN[0])
    r.part('root', capsule((-2.0, 0, -1.2), (2.0, 0, -1.2), 0.55), LEATHER[2])
    return r


def carmines_quill():
    """Carmine's Quill (II-6): the Red Warden's steel pen grown into a dagger, a
    long split nib for a blade, a red-lacquered grip and a capped end. Held
    like the short sword: along +Y, turned by yaw -90."""
    r = new_rig((0, 0, 0), yaw=-90)
    r.part('root', capsule((0, -3.0, 0), (0, 3.0, 0), 0.75), CLOTH_RED[0])
    r.part('root', ellipsoid((0, -3.8, 0), (1.0, 1.0, 1.0)), SILVER[1])
    r.part('root', capsule((-1.6, 3.6, 0), (1.6, 3.6, 0), 0.6), SILVER[1])

    def nib(x, y, z):
        half = 1.3 * np.clip((22 - y) / 18, 0, 1)
        return (np.abs(x) <= half) & (np.abs(z) < 0.45) & (y > 4) & (y < 22)
    nib.box = (np.array([-1.4, 4, -0.5]), np.array([1.4, 22, 0.5]))
    # The slit down the middle of the nib, and the breather hole.
    r.part('root', nib, lambda x, y, z, pose: np.where((np.abs(x) < 0.3) & (y > 9), RAVEN[0], np.where(np.hypot(x, y - 8) < 0.6, RAVEN[0], SILVER[0])))
    return r


GEAR = {
    'MinersHelmet': miners_helmet,
    'IronHelm': iron_helm,
    'RoundShield': round_shield,
    'ShortSword': short_sword,
    'MillstoneMaul': millstone_maul,
    'HandAxe': hand_axe,
    'Falchion': falchion,
    'FlangedMace': flanged_mace,
    'KiteShield': kite_shield,
    'ChainCoif': chain_coif,
    'GreatHelm': great_helm,
    'WarHammer': war_hammer,
    'TowerShield': tower_shield,
    'VisoredHelm': visored_helm,
    'SwanboneBuckler': swanbone_buckler,
    'CarminesQuill': carmines_quill,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    for name in args.names or GEAR:
        write(name, GEAR[name]())


if __name__ == '__main__':
    main()
