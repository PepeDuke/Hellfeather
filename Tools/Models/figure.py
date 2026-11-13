"""A small voxel rig for people and creatures.

A figure is a tree of bones and a list of parts. Parts are authored in the rest
pose, in voxel coordinates with the feet at the origin, +Y up and the face
toward +Z, and each belongs to one bone. A pose turns bones about their joints;
rendering maps every voxel of the canvas back into each part's rest space, so a
part keeps its shape and its painted pattern as it moves. Clips are lists of
poses, which is how idle and talk get real motion instead of a bent hull.

Shapes are functions of rest coordinates (X, Y, Z arrays) returning a mask, and
materials are functions of the same coordinates returning palette indexes.
Later parts paint over earlier ones, so add outer layers (aprons, gloves, held
things) after what they cover.
"""
import math

import numpy as np

import act1
from kit import compact


def engine_rotation(yaw, pitch, roll):
    """The engine's socket rotation: roll about Z, then pitch about X, then yaw about Y."""
    a, b, c = (math.radians(v) for v in (pitch, yaw, roll))
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return ry @ rx @ rz


def engine_angles(m):
    """yaw, pitch, roll in degrees with engine_rotation(yaw, pitch, roll) == m."""
    pitch = math.asin(max(-1.0, min(1.0, -m[1][2])))
    yaw = math.atan2(m[0][2], m[2][2])
    roll = math.atan2(m[1][0], m[1][1])
    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)


def rotation(pitch=0.0, yaw=0.0, roll=0.0):
    """Turns about x (pitch, positive tips +Y toward +Z), then z, then y, in degrees."""
    a, b, c = (math.radians(v) for v in (pitch, yaw, roll))
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return ry @ rz @ rx


# Shapes, in rest coordinates.

def ellipsoid(center, radii):
    cx, cy, cz = center
    rx, ry, rz = radii

    def shape(x, y, z):
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1.0
    shape.box = (np.array(center) - np.array(radii), np.array(center) + np.array(radii))
    return shape


def capsule(a, b, r0, r1=None):
    """A rounded limb from a to b, its radius going from r0 to r1."""
    r1 = r0 if r1 is None else r1
    a, b = np.array(a, float), np.array(b, float)
    ab = b - a
    length2 = float(ab @ ab)

    def shape(x, y, z):
        px, py, pz = x - a[0], y - a[1], z - a[2]
        t = np.clip((px * ab[0] + py * ab[1] + pz * ab[2]) / length2, 0.0, 1.0)
        dx, dy, dz = px - t * ab[0], py - t * ab[1], pz - t * ab[2]
        return dx * dx + dy * dy + dz * dz <= (r0 + (r1 - r0) * t) ** 2
    r = max(r0, r1)
    shape.box = (np.minimum(a, b) - r, np.maximum(a, b) + r)
    return shape


def column(y0, y1, radius_x, radius_z, center_z=None, power=2.0):
    """A body of stacked ellipses from y0 to y1. radius_x, radius_z and
    center_z are functions of y; power above 2 squares the sections off."""
    center_z = center_z or (lambda y: 0.0)
    probe = np.linspace(y0, y1, 32)
    reach_x = max(radius_x(v) for v in probe)
    reach_z = max(radius_z(v) + abs(center_z(v)) for v in probe)

    def shape(x, y, z):
        inside = (y >= y0) & (y < y1)
        rx = np.maximum(radius_x(y), 0.01)
        rz = np.maximum(radius_z(y), 0.01)
        return inside & (np.abs(x / rx) ** power + np.abs((z - center_z(y)) / rz) ** power <= 1.0)
    shape.box = (np.array([-reach_x, y0, -reach_z]), np.array([reach_x, y1, reach_z]))
    return shape


def union(*shapes):
    def shape(x, y, z):
        out = shapes[0](x, y, z)
        for s in shapes[1:]:
            out = out | s(x, y, z)
        return out
    shape.box = (np.min([s.box[0] for s in shapes], axis=0), np.max([s.box[1] for s in shapes], axis=0))
    return shape


def minus(keep, cut):
    def shape(x, y, z):
        return keep(x, y, z) & ~cut(x, y, z)
    shape.box = keep.box
    return shape


def where(base, test):
    """base, kept only where test(x, y, z) holds."""
    def shape(x, y, z):
        return base(x, y, z) & test(x, y, z)
    shape.box = base.box
    return shape


def shell(inner, outer):
    """The layer of outer that lies outside inner: an apron over a skirt."""
    return minus(outer, inner)


class Rig:
    def __init__(self, scale=1.0):
        # Canvas voxels per rig voxel: author everyone at 70 tall, scale to fit.
        self.scale = scale
        self.bones = {}
        self.order = []
        self.parts = []
        self.sockets = []

    def bone(self, name, joint, parent=None):
        self.bones[name] = (np.array(joint, float), parent)
        self.order.append(name)

    def part(self, bone, shape, material, when=None):
        """material is a palette index or a function (x, y, z, pose) -> indexes.
        when(pose), if given, says in which poses the part is there at all, for
        things that come and go: a spat bolt, a splash."""
        self.parts.append((bone, shape, material, when))

    def socket(self, name, bone, point, yaw=0.0, pitch=0.0, roll=0.0):
        """A named socket on a bone, such as the hand that holds a weapon.
        point is in rest rig coordinates; the angles are its rotation in the
        rest pose, in the engine's order (roll about Z, then pitch about X,
        then yaw about Y; see Quaxel-Engine Docs/VoxelModels.md)."""
        self.sockets.append((name, bone, np.array(point, float), engine_rotation(yaw, pitch, roll)))

    def socket_lines(self, pose, size, shift=(0, 0)):
        """The pose's socket lines for a canvas of `size`, after the canvas
        has been cut `shift` voxels in x and z."""
        w, h, d = size
        origin = np.array([w // 2, 0, d // 2], float)
        posed = self.transforms(pose)
        out = []
        for name, bone, point, rest in self.sockets:
            pj, pr = posed[bone]
            joint = self.bones[bone][0]
            p = ((point - joint) @ pr.T + pj) * self.scale + origin - 0.5 - np.array([shift[0], 0, shift[1]])
            yaw, pitch, roll = engine_angles(pr @ rest)
            out.append(f'socket {name} {p[0]:.2f} {p[1]:.2f} {p[2]:.2f} {yaw:.0f} {pitch:.0f} {roll:.0f}')
        return out

    def transforms(self, pose):
        """Each bone's posed joint and rotation."""
        out = {}
        for name in self.order:
            joint, parent = self.bones[name]
            turn = rotation(*pose.get(name, (0.0, 0.0, 0.0)))
            if parent is None:
                out[name] = (joint + np.array(pose.get('offset', (0.0, 0.0, 0.0))), turn)
            else:
                pj, pr = out[parent]
                pjoint = self.bones[parent][0]
                out[name] = (pj + pr @ (joint - pjoint), pr @ turn)
        return out

    def render(self, pose, size):
        """The figure in a canvas of `size` voxels, feet centered at the bottom."""
        w, h, d = size
        grid = np.full(size, -1, dtype=np.int32)
        origin = np.array([w // 2, 0, d // 2], float)
        posed = self.transforms(pose)
        for bone, shape, material, when in self.parts:
            if when is not None and not when(pose):
                continue
            pj, pr = posed[bone]
            joint = self.bones[bone][0]
            lo, hi = shape.box
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
            moved = ((corners - joint) @ pr.T + pj) * self.scale + origin
            a = np.maximum(np.floor(moved.min(axis=0)).astype(int) - 1, 0)
            b = np.minimum(np.ceil(moved.max(axis=0)).astype(int) + 2, size)
            if np.any(b <= a):
                continue
            gx, gy, gz = np.meshgrid(*(np.arange(a[i], b[i]) + 0.5 for i in range(3)), indexing='ij')
            p = (np.stack([gx, gy, gz], axis=-1) - origin) / self.scale - pj
            rest = p @ pr + joint
            x, y, z = rest[..., 0], rest[..., 1], rest[..., 2]
            mask = shape(x, y, z)
            if not mask.any():
                continue
            view = grid[a[0]:b[0], a[1]:b[1], a[2]:b[2]]
            if callable(material):
                colors = np.broadcast_to(material(x, y, z, pose), mask.shape)
                view[mask] = colors[mask]
            else:
                view[mask] = material
        return grid


def fit(rig, height, probe=(200, 260, 200)):
    """Sets the rig's scale so its rest pose stands `height` voxels tall."""
    rig.scale = 1.0
    grid = rig.render({}, probe)
    top = int(np.nonzero((grid >= 0).any(axis=(0, 2)))[0].max()) + 1
    rig.scale = height / top


def trim_shift(rest, rendered):
    """Where act1.trim cuts the canvas in x and z, so sockets can follow."""
    used = rest >= 0
    for _, _, frames in rendered:
        for grid, _ in frames:
            used = used | (grid >= 0)
    w, h, d = rest.shape
    xs = np.nonzero(used.any(axis=(1, 2)))[0]
    zs = np.nonzero(used.any(axis=(0, 1)))[0]
    half_x = int(max(w / 2 - xs.min(), xs.max() + 1 - w / 2)) + 1
    half_z = int(max(d / 2 - zs.min(), zs.max() + 1 - d / 2)) + 1
    return max(0, w // 2 - half_x), max(0, d // 2 - half_z)


def build(name, rig, clips, size, preview=False):
    """Renders every clip, trims them to one canvas and writes Assets/<name>.qvox.
    clips are (name, looping, [(pose, milliseconds)])."""
    build_variants({name: rig}, clips, size, preview)


def build_variants(rigs, clips, size, preview=False):
    """Builds several rigs that share bones and clips, such as a body in each
    outfit, into files with the same box and sockets, so the game can swap one
    for another without the model shifting. rigs maps file names to rigs."""
    first = next(iter(rigs.values()))
    renders = {}
    for name, rig in rigs.items():
        rest = rig.render({}, size)
        renders[name] = (rest, [(clip, looping, [(rig.render(pose, size), ms) for pose, ms in frames]) for clip, looping, frames in clips])
    # One trim for all of them: the union of what any frame of any variant uses.
    union = None
    for rest, rendered in renders.values():
        union = rest.copy() if union is None else np.maximum(union, rest)
        for _, _, frames in rendered:
            for grid, _ in frames:
                union = np.maximum(union, grid)
    shift = trim_shift(union, [])
    sockets = [[first.socket_lines(pose, size, shift) for pose, _ in frames] for _, _, frames in clips]
    box = act1.trim(union, [])[0].shape
    x0, z0 = shift

    def cut(grid):
        return grid[x0:x0 + box[0], :, z0:z0 + box[2]]
    trimmed = {name: (cut(rest), [(clip, looping, [(cut(g), ms) for g, ms in frames]) for clip, looping, frames in rendered])
               for name, (rest, rendered) in renders.items()}
    every = [g for rest, rendered in trimmed.values() for g in [rest] + [x for _, _, fr in rendered for x, _ in fr]]
    # Rows above the tallest frame are empty in all of them; every frame is
    # stored whole, so they would only make the file bigger.
    top = max((int(np.nonzero((g >= 0).any(axis=(0, 2)))[0].max()) + 1 for g in every if (g >= 0).any()), default=1)
    if top >= size[1]:
        print(f'a frame reaches the top of the {size[1]}-voxel canvas and is cut off; make the canvas taller')
    for name, (rest, rendered) in trimmed.items():
        flat = [rest] + [g for _, _, frames in rendered for g, _ in frames]
        flat = [g[:, :top, :] for g in flat]
        flat, palette = compact(flat)
        rest, at = flat[0], 1
        out = []
        for i, (clip, looping, frames) in enumerate(rendered):
            out.append((clip, looping, [(flat[at + k], ms, sockets[i][k]) for k, (_, ms) in enumerate(frames)]))
            at += len(frames)
        act1.write(act1.ASSETS / f'{name}.qvox', palette, rest, out)
        if preview:
            act1.save_preview(name, palette, rest, out)
        bw, bh, bd = rest.shape
        stand = int(np.nonzero((rest >= 0).any(axis=(0, 2)))[0].max()) + 1
        print(f'{name}: {bw} x {bh} x {bd}, {stand} tall, {int((rest >= 0).sum())} voxels, {sum(len(f) for _, _, f in out)} frames')
