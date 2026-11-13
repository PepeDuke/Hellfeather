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
from kit import BRASS, GLOW, IRON, LEATHER, SILVER, STONE, WOOD, WOOD_DARK, compact, hash2, pick  # noqa: E402
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


GEAR = {
    'MinersHelmet': miners_helmet,
    'IronHelm': iron_helm,
    'RoundShield': round_shield,
    'ShortSword': short_sword,
    'MillstoneMaul': millstone_maul,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    for name in args.names or GEAR:
        write(name, GEAR[name]())


if __name__ == '__main__':
    main()
