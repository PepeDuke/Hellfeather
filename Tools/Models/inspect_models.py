"""Checks built voxel models against the concept sheets they were cut from.

For each model it renders the rest pose from the front, back, left, right and
top, and from the game's camera as the game shows it, and lays the reference
crops beside them. Every clip of an animated model gets a strip of game-view
frames. The sheets go to Tools/Models/Inspect.

It also scores each model: how much of the reference's front and side outline
the model fills (intersection over union, after scaling both to the same
height), and how far its front colors are from the reference's. A model made
from two views that do not agree, a crop that caught a label or a neighbor, or
a pedestal left under the feet all show up as a low score.

    python Tools/Models/inspect_models.py                 every model in act1.MODELS
    python Tools/Models/inspect_models.py Matthew Raven   some of them, or any Assets/*.qvox
    python Tools/Models/inspect_models.py --check         also fail if a score is too low
    python Tools/Models/inspect_models.py --no-clips      skip the clip strips

Gear: with --gear, a model is shown holding and wearing other models on its
sockets, placed as the engine places them (World.FollowSocket: the item's grip
lined up with the socket, both in position and turn). Each chosen frame gets
front, back, left, right and top views and the game camera at four facings;
45 degrees is how the game spawns the player, facing the camera.

    python Tools/Models/inspect_models.py Warrior --gear hand_r=BattleAxe head=MinersHelmet
    python Tools/Models/inspect_models.py WarriorLeatherArmor --gear hand_r=BattleAxe --frames idle:0 attack:2 attack:3
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'Assets'
OUT = ROOT / 'Tools/Models/Inspect'
PANEL = 300          # height in pixels of every view
BACKGROUND = (34, 36, 46)
# The lowest outline match a model may have before --check fails, and for
# models marked loose in act1.MODELS: sparse reeds and thin hanging signs.
MIN_MATCH = 0.80
MIN_MATCH_LOOSE = 0.70
# Recipe-built buildings (buildings.py) are drawn from parts, not cut from the
# outlines, and the sheets' outlines carry smoke, signs and clutter, so they
# only need to stay roughly in shape.
MIN_MATCH_RECIPE = 0.65
# The game's camera looks along (-1, -1, -1), up is +Y.
FORWARD = np.array([-1.0, -1.0, -1.0]) / math.sqrt(3.0)
RIGHT = np.array([1.0, 0.0, -1.0]) / math.sqrt(2.0)
UP = np.array([-1.0, 2.0, -1.0]) / math.sqrt(6.0)
LIGHT = np.array([0.45, 1.0, 0.65]) / np.linalg.norm([0.45, 1.0, 0.65])


def read_qvox(path):
    """Returns the palette as sRGB, the base grid and clips of (name, [grids]).
    Grids are int arrays indexed [x, y, z], -1 for empty."""
    lines = path.read_text(encoding='ascii').split('\n')
    width, height, depth = (int(v) for v in lines[1].split()[1:4])
    palette = {}
    symbol_width = 1
    grids = []
    clips = []
    current = None
    y = z = 0

    def new_grid():
        return np.full((width, height, depth), -1, dtype=np.int32)

    for line in lines[2:]:
        line = line.rstrip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('color '):
            _, symbol, value = line.split()
            symbol_width = len(symbol)
            palette[symbol] = len(palette)
            continue
        if line.startswith('clip '):
            clips.append((line.split()[1], []))
            continue
        if line.startswith('frame '):
            current = new_grid()
            clips[-1][1].append(current)
            y = z = 0
            continue
        if line.startswith('socket '):
            continue
        if current is None:
            current = new_grid()
            grids.append(current)
            y = z = 0
        for x in range(width):
            symbol = line[x * symbol_width:(x + 1) * symbol_width]
            if symbol and symbol[0] != '.':
                current[x, y, z] = palette[symbol]
        z += 1
        if z == depth:
            z = 0
            y += 1
    colors = []
    for line in lines[2:]:
        if line.startswith('color '):
            value = line.split()[2]
            colors.append(tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)))
    srgb = np.array([[display(c) for c in color] for color in colors], dtype=np.float64)
    base = grids[0] if grids else clips[0][1][0]
    return srgb, base, clips


def display(channel):
    """The model files hold linear light; screens want sRGB."""
    value = channel / 255.0
    value = value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
    return min(255.0, max(0.0, value * 255.0))


def axis_view(grid, palette, axis, near_high, flip):
    """An orthographic view along one axis: the nearest voxel of each column,
    darkened a little with depth so the relief reads. Returns an RGB array with
    rows running down, and a mask."""
    solid = grid >= 0
    moved = np.moveaxis(solid, axis, -1)
    colors = np.moveaxis(grid, axis, -1)
    depth = moved.shape[-1]
    order = np.arange(depth)
    if near_high:
        index = np.where(moved, order, -1).max(axis=-1)
        nearness = index / max(1, depth - 1)
    else:
        index = np.where(moved, order, depth).min(axis=-1)
        nearness = 1.0 - index / max(1, depth - 1)
    mask = moved.any(axis=-1)
    safe = np.clip(index, 0, depth - 1)
    picked = np.take_along_axis(colors, safe[..., None], axis=-1)[..., 0]
    rgb = palette[np.clip(picked, 0, len(palette) - 1)] * (0.55 + 0.45 * nearness)[..., None]
    rgb[~mask] = BACKGROUND
    return rgb, mask


def views(grid, palette):
    """Front, back, left, right and top, as images with rows running down."""
    out = {}
    # Front: from +Z, X to the right, Y up. Grid axes after moveaxis: (x, y).
    rgb, mask = axis_view(grid, palette, 2, True, False)
    out['front'] = (rgb.transpose(1, 0, 2)[::-1], mask.T[::-1])
    rgb, mask = axis_view(grid, palette, 2, False, False)
    out['back'] = (rgb.transpose(1, 0, 2)[::-1, ::-1], mask.T[::-1, ::-1])
    # Left: from -X, Z to the right, like the sheets' side views. Axes (y, z).
    rgb, mask = axis_view(grid, palette, 0, False, False)
    out['left'] = (rgb[::-1], mask[::-1])
    rgb, mask = axis_view(grid, palette, 0, True, False)
    out['right'] = (rgb[::-1, ::-1], mask[::-1, ::-1])
    # Top: from +Y, X to the right, +Z toward the bottom. Axes (x, z).
    rgb, mask = axis_view(grid, palette, 1, True, False)
    out['top'] = (rgb.transpose(1, 0, 2), mask.T)
    return out


def game_view(grid, palette, yaw_degrees, scale):
    """The model as the game's camera sees it, turned by yaw about +Y. Each
    surface voxel is splatted as a lit square, far ones first."""
    solid = grid >= 0
    padded = np.pad(solid, 1)
    normal = np.zeros(solid.shape + (3,))
    exposed = np.zeros(solid.shape, dtype=bool)
    for axis in range(3):
        for sign in (-1, 1):
            neighbor = np.roll(padded, -sign, axis=axis)[1:-1, 1:-1, 1:-1]
            open_side = solid & ~neighbor
            exposed |= open_side
            normal[..., axis] += open_side * sign
    xs, ys, zs = np.nonzero(exposed)
    if len(xs) == 0:
        return np.full((8, 8, 3), BACKGROUND, dtype=np.uint8)
    w, h, d = solid.shape
    points = np.stack([xs - w / 2 + 0.5, ys + 0.5, zs - d / 2 + 0.5], axis=1)
    normals = normal[xs, ys, zs]
    angle = math.radians(yaw_degrees)
    turn = np.array([[math.cos(angle), 0.0, math.sin(angle)], [0.0, 1.0, 0.0], [-math.sin(angle), 0.0, math.cos(angle)]])
    points = points @ turn.T
    normals = normals @ turn.T
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(length > 0, normals / np.maximum(length, 1e-6), np.array([0.0, 1.0, 0.0]))
    light = 0.42 + 0.58 * np.clip(normals @ LIGHT, 0.0, 1.0)
    colors = palette[grid[xs, ys, zs]] * light[:, None]
    sx = points @ RIGHT
    sy = points @ UP
    near = points @ -FORWARD
    order = np.argsort(near)
    left, top = sx.min(), sy.max()
    size_x = int((sx.max() - left) * scale) + 4
    size_y = int((top - sy.min()) * scale) + 4
    image = Image.new('RGB', (size_x, size_y), BACKGROUND)
    draw = ImageDraw.Draw(image)
    half = max(1.0, scale * 0.62)
    for i in order:
        cx = (sx[i] - left) * scale + 2
        cy = (top - sy[i]) * scale + 2
        draw.rectangle((cx - half, cy - half, cx + half, cy + half), fill=tuple(int(c) for c in colors[i]))
    return np.asarray(image)


def to_image(rgb, height):
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    scale = height / image.height
    return image.resize((max(1, round(image.width * scale)), height), Image.NEAREST)


def reference(model, view, height):
    """The sheet's crop of a view, the background dimmed, at a given height."""
    pixels = np.asarray(Image.open(act1.CROPS / f"{model['name']}.{view}.png").convert('RGB'), dtype=np.int32)
    if view == 'side' and model.get('flip'):
        pixels = pixels[:, ::-1]
    mask = act1.silhouette(pixels, model.get('trim', 0))
    if model.get('pedestal', model['kind'] == 'npc'):
        cut = act1.pedestal_cut(mask)
        if cut is not None:
            mask[cut:] = False
    pixels, mask = act1.tighten(pixels, mask)
    shown = pixels.astype(np.float64)
    shown[~mask] = shown[~mask] * 0.25 + np.array(BACKGROUND) * 0.75
    return to_image(shown, height), mask, pixels


def bounding(mask):
    rows = np.nonzero(mask.any(axis=1))[0]
    columns = np.nonzero(mask.any(axis=0))[0]
    return mask[rows.min():rows.max() + 1, columns.min():columns.max() + 1]


def outline_match(model_mask, reference_mask):
    """Intersection over union of two outlines scaled to the same box."""
    a = bounding(model_mask)
    b = bounding(reference_mask)
    size = (max(a.shape[1], b.shape[1]), max(a.shape[0], b.shape[0]))
    a = np.asarray(Image.fromarray(a.astype(np.uint8) * 255).resize(size, Image.NEAREST)) > 127
    b = np.asarray(Image.fromarray(b.astype(np.uint8) * 255).resize(size, Image.NEAREST)) > 127
    union = (a | b).sum()
    return float((a & b).sum()) / union if union else 0.0


def color_gap(model_rgb, model_mask, reference_image, reference_mask):
    """Mean difference, out of 255, between the model's front and the sheet's,
    where both have something."""
    a = bounding(model_mask)
    rows = np.nonzero(model_mask.any(axis=1))[0]
    columns = np.nonzero(model_mask.any(axis=0))[0]
    rgb = model_rgb[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
    b = bounding(reference_mask)
    ref = np.asarray(reference_image.resize((a.shape[1], a.shape[0]), Image.BILINEAR), dtype=np.float64)
    b = np.asarray(Image.fromarray(b.astype(np.uint8) * 255).resize((a.shape[1], a.shape[0]), Image.NEAREST)) > 127
    both = a & b
    if not both.any():
        return 255.0
    return float(np.abs(rgb[both] - ref[both]).mean())


def label(image, text):
    canvas = Image.new('RGB', (image.width, image.height + 14), BACKGROUND)
    canvas.paste(image, (0, 14))
    ImageDraw.Draw(canvas).text((3, 1), text, fill=(230, 210, 150))
    return canvas


def row(images, gap=8):
    width = sum(i.width for i in images) + gap * (len(images) - 1)
    height = max(i.height for i in images)
    canvas = Image.new('RGB', (width, height), BACKGROUND)
    x = 0
    for image in images:
        canvas.paste(image, (x, 0))
        x += image.width + gap
    return canvas


def engine_rotation(yaw, pitch, roll):
    """The engine's socket turn (QuaxelRotation.FromDegrees): roll about Z,
    then pitch about X, then yaw about Y, by the right-hand rule."""
    a, b, c = (math.radians(v) for v in (pitch, yaw, roll))
    rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return ry @ rx @ rz


def read_sockets(path, size):
    """Sockets per frame: {clip: [{name: (position, rotation)}]}, with the static
    grid's under the key None. Positions are relative to the grid's center, as
    the engine stores them (QuaxelVoxels.AddSocket: a whole number is a cell's
    center)."""
    out = {None: [{}]}
    clip = None
    half = np.array(size, float) * 0.5
    for line in path.read_text(encoding='ascii').splitlines():
        if line.startswith('clip '):
            clip = line.split()[1]
            out[clip] = []
        elif line.startswith('frame ') and clip:
            out[clip].append({})
        elif line.startswith('socket '):
            parts = line.split()
            values = [float(v) for v in parts[2:]] + [0.0] * 3
            position = np.array(values[:3]) + 0.5 - half
            target = out[clip][-1] if clip else out[None][0]
            target[parts[1]] = (position, engine_rotation(*values[3:6]))
    return out


def dress(grid, palette, sockets, gear, twists=None):
    """The grid with each worn item drawn in, placed as World.FollowSocket
    places it: turn = socket * grip^-1, and the grip's point on the socket.
    gear maps socket names to (palette, grid, sockets) of the items. Returns a
    grid padded to hold them, and the joined palette."""
    pad = 48
    shape = np.array(grid.shape)
    out = np.full(tuple(shape + 2 * pad), -1, dtype=np.int32)
    out[pad:pad + shape[0], pad:pad + shape[1], pad:pad + shape[2]] = grid
    colors = palette
    for name, (item_palette, item, item_sockets) in gear.items():
        if name not in sockets:
            continue    # the engine hides an item whose socket a frame leaves out
        position, turn = sockets[name]
        if twists and name in twists:
            # An extra turn in the socket's own frame, to try out another
            # socket rotation without rebuilding the holder.
            turn = turn @ twists[name]
        grip = item_sockets[None][0].get('grip')
        grip_position, grip_turn = grip if grip else (np.zeros(3), np.eye(3))
        rotation = turn @ grip_turn.T
        offset = len(colors)
        colors = np.concatenate([colors, item_palette])
        cells = np.argwhere(item >= 0)
        local = cells + 0.5 - np.array(item.shape) * 0.5
        placed = position + (local - grip_position) @ rotation.T
        # Back to the holder's cell indices, then into the padded grid.
        index = np.floor(placed + shape * 0.5).astype(int) + pad
        keep = np.all((index >= 0) & (index < out.shape), axis=1)
        out[tuple(index[keep].T)] = offset + item[tuple(cells[keep].T)]
    filled = np.argwhere(out >= 0)
    lo, hi = filled.min(axis=0), filled.max(axis=0) + 1
    # Keep the feet's row as the floor so every view stands on the same line.
    lo[1] = min(lo[1], pad)
    return out[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], colors


def inspect_gear(name, gear_names, frames, twists=None, views_wanted=None, out_name=None):
    """A sheet of the model wearing its gear, for each frame: the five axis
    views and the game camera at four facings."""
    path = ASSETS / f'{name}.qvox'
    palette, base, clips = read_qvox(path)
    sockets = read_sockets(path, base.shape)
    gear = {}
    for pair in gear_names:
        socket, item = pair.split('=')
        item_path = ASSETS / f'{item}.qvox'
        item_palette, item_grid, _ = read_qvox(item_path)
        gear[socket] = (item_palette, item_grid, read_sockets(item_path, item_grid.shape))
    by_name = dict(clips)
    picks = frames or ([f'{clips[0][0]}:0'] + [f'{c}:{len(g) // 2}' for c, g in clips[1:]] if clips else [None])
    rows = []
    for pick in picks:
        if pick is None:
            grid, frame_sockets, title = base, sockets[None][0], 'rest'
        else:
            clip, index = pick.split(':')
            grid, frame_sockets, title = by_name[clip][int(index)], sockets[clip][int(index)], pick
        dressed, colors = dress(grid, palette, frame_sockets, gear, twists)
        shown = views(dressed, colors)
        wanted = views_wanted or ['front', 'back', 'left', 'right', 'top', 'game45', 'game135', 'game-135', 'game-45']
        tiles = []
        for v in wanted:
            if v.startswith('game'):
                tiles.append(label(to_image(game_view(dressed, colors, float(v[4:]), 4), PANEL), f'{title} {v}'))
            else:
                tiles.append(label(to_image(shown[v][0], PANEL), f'{title} {v}'))
        rows.append(row(tiles))
    width = max(r.width for r in rows)
    sheet = Image.new('RGB', (width, sum(r.height + 8 for r in rows)), BACKGROUND)
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f'{out_name or name + ".gear"}.png'
    sheet.save(target)
    return target


def inspect(name, model, clips_too):
    path = ASSETS / f'{name}.qvox'
    palette, base, clips = read_qvox(path)
    rest = clips[0][1][0] if clips else base
    shown = views(rest, palette)
    tiles = []
    scores = {}
    if model:
        front_ref, front_ref_mask, front_pixels = reference(model, 'front', PANEL)
        side_ref, side_ref_mask, _ = reference(model, 'side', PANEL)
        tiles.append(label(front_ref, 'sheet front'))
    tiles.append(label(to_image(shown['front'][0], PANEL), 'front'))
    if model:
        tiles.append(label(side_ref, 'sheet side'))
    for view in ('left', 'back', 'right', 'top'):
        tiles.append(label(to_image(shown[view][0], PANEL if view != 'top' else PANEL // 2), view))
    # People and enemies turn toward the camera in the game; buildings do not.
    yaw = 45.0 if clips else 0.0
    scale = PANEL / max(rest.shape[1], 1) * 0.8
    tiles.append(label(Image.fromarray(game_view(rest, palette, yaw, scale)), 'game view'))
    if clips:
        # Walking across the screen, toward its right.
        tiles.append(label(Image.fromarray(game_view(rest, palette, 135.0, scale)), 'game, walking'))
    rows = [row(tiles)]
    if model:
        front_rgb, front_mask = shown['front']
        side_mask = shown['left'][1]
        scores['front'] = outline_match(front_mask, front_ref_mask)
        scores['side'] = outline_match(side_mask, side_ref_mask)
        scores['color'] = color_gap(front_rgb, front_mask, Image.fromarray(front_pixels.astype(np.uint8)), front_ref_mask)
    if clips_too:
        small = PANEL * 0.45 / max(rest.shape[1], 1)
        for clip, frames in clips:
            strip = [Image.fromarray(game_view(frame, palette, yaw, small)) for frame in frames]
            rows.append(label(row(strip, 4), f'{clip} ({len(frames)} frames)'))
    sheet = Image.new('RGB', (max(r.width for r in rows) + 16, sum(r.height for r in rows) + 12 * len(rows) + 8), BACKGROUND)
    y = 8
    for r in rows:
        sheet.paste(r, (8, y))
        y += r.height + 12
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / f'{name}.png')
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--no-clips', action='store_true')
    parser.add_argument('--gear', nargs='+', metavar='SOCKET=ITEM', help='show the model with these Assets items on its sockets')
    parser.add_argument('--frames', nargs='+', metavar='CLIP:FRAME', help='with --gear, the frames to show')
    parser.add_argument('--twist', nargs='+', metavar='SOCKET=YAW,PITCH,ROLL', help='with --gear, turn a worn item further on its socket, in the socket frame')
    parser.add_argument('--views', nargs='+', help='with --gear, the views to show: front back left right top game<yaw>')
    parser.add_argument('--out', help='with --gear, the sheet file name in Tools/Models/Inspect')
    args = parser.parse_args()
    if args.gear:
        twists = {}
        for pair in args.twist or []:
            socket, angles = pair.split('=')
            twists[socket] = engine_rotation(*(float(v) for v in angles.split(',')))
        for name in args.names:
            print(f'Sheet in {inspect_gear(name, args.gear, args.frames, twists, args.views, args.out)}')
        return
    by_name = {m['name']: m for m in act1.MODELS}
    names = args.names or [m['name'] for m in act1.MODELS] + ['Raven', 'SilverSpark']
    failed = []
    print(f"{'model':20} {'front':>6} {'side':>6} {'color':>6}")
    for name in names:
        scores = inspect(name, by_name.get(name), not args.no_clips)
        if not scores:
            print(f'{name:20} {"-":>6} {"-":>6} {"-":>6}')
            continue
        flag = ''
        lowest = MIN_MATCH_RECIPE if by_name[name].get('recipe') else MIN_MATCH_LOOSE if by_name[name].get('loose') else MIN_MATCH
        if min(scores['front'], scores['side']) < lowest:
            flag = '  <- outlines disagree with the sheet'
            failed.append(name)
        print(f"{name:20} {scores['front']:6.2f} {scores['side']:6.2f} {scores['color']:6.1f}{flag}")
    print(f'Sheets in {OUT}')
    if args.check and failed:
        print('Too far from the sheet: ' + ', '.join(failed))
        sys.exit(1)


if __name__ == '__main__':
    main()
