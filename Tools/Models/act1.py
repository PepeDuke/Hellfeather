"""Builds the Act I voxel models from the concept sheets.

Each model is cut from a front view and a side view, scaled to its height in
voxels, and made solid where both silhouettes agree (a visual hull). Faces that
look forward take their color from the front view, the rest from the side view.

Characters and creatures are then posed into clips by bending the hull: the
upper body pitches about the hips, legs swing, rows rise and fall. The raven is
the exception: every frame of its atlas has a side and a back view, so each of
its frames is a hull of its own.

    python Tools/Models/act1.py --import DIR       crop the views out of the sheets in DIR
    python Tools/Models/act1.py                    build every model
    python Tools/Models/act1.py RoadDrake Moth     build some of them
    python Tools/Models/act1.py --preview          also save renders to Tools/Models/Preview

The crops live in Assets/Reference/Act1 so the sheets themselves stay out of the
repository.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
CROPS = ROOT / 'Assets/Reference/Act1'
ASSETS = ROOT / 'Assets'
PREVIEW = ROOT / 'Tools/Models/Preview'
# One-character palette symbols keep the files half the size.
SYMBOLS = [chr(c) for c in range(33, 127) if chr(c) not in '.#']
# Animated models taller than this many voxels get coarser voxels instead, so
# their files stay a few megabytes. Heights in MODELS are in voxels of CELL.
TALLEST = 72
CELL = 0.025

# Kinds:
#   creature  idle, walk, attack, hit and death clips
#   npc       idle and talk clips
#   static    no clips
# Boxes are left, top, right, bottom on the sheet. Sheet names are matched by a
# piece of the file name. Height is in voxels. Round is the hull's squareness:
# 2 is an ellipse, higher is boxier. FlipSide mirrors the side view, for the
# building elevations that look at the right-hand wall. Recipe marks a model
# that buildings.py builds instead; this tool skips it.
MODELS = [
    # The road.
    dict(name='RoadDrake', sheet='Road Drake', front=(810, 30, 1015, 352), side=(1350, 40, 1760, 352), height=92, kind='creature', legs=0.3),
    dict(name='CarrionRook', sheet='havraního tvora', front=(840, 40, 1050, 332), side=(1400, 60, 1745, 332), height=40, kind='creature', legs=0.25),
    dict(name='TitheStray', sheet='Tithestray', front=(930, 5, 1100, 365), side=(1510, 5, 1710, 365), height=72, kind='creature', legs=0.45),
    # Fennick Water.
    dict(name='ReedDuck', sheet='Reedduck', front=(870, 30, 1060, 335), side=(1400, 40, 1745, 335), height=62, kind='creature', legs=0.25),
    dict(name='Duckling', sheet='Kachňátko', front=(880, 60, 1060, 350), side=(1450, 60, 1745, 350), height=26, kind='creature', legs=0.3),
    dict(name='MoultedGander', sheet='husího tvora', front=(820, 10, 1020, 355), side=(1360, 10, 1760, 355), height=88, kind='creature', legs=0.3),
    dict(name='BlackHoneyLeech', sheet='BlackHoneyLeech', front=(890, 60, 1020, 325), side=(1350, 165, 1758, 300), height=14, kind='crawler'),
    dict(name='OldGreyneck', sheet='Oldgreyneck', front=(880, 5, 1060, 358), side=(1420, 5, 1760, 358), height=100, kind='creature', legs=0.3),
    # Orra's Hill.
    dict(name='PilgrimPenitent', sheet='Poutník', front=(880, 5, 1075, 345), side=(1490, 5, 1690, 345), height=88, kind='creature', legs=0.4),
    dict(name='BlackHoneyFiend', sheet='Blackhoneyfienda', front=(880, 5, 1065, 352), side=(1490, 5, 1720, 352), height=70, kind='creature', legs=0.45),
    dict(name='GallowsRook', sheet='GallowsRook', front=(870, 20, 1060, 252), side=(1410, 30, 1750, 252), height=44, kind='creature', legs=0.2),
    # Hobb's Mill.
    dict(name='PondDrake', sheet='Ponddrake', front=(880, 15, 1065, 350), side=(1420, 15, 1760, 350), height=70, kind='creature', legs=0.3),
    dict(name='MillhandThrall', sheet='přisluhovače', front=(900, 15, 1090, 365), side=(1500, 15, 1710, 365), height=74, kind='creature', legs=0.4),
    dict(name='Cuffman', sheet='Cuffman', front=(910, 20, 1090, 342), side=(1546, 20, 1730, 342), height=76, kind='creature', legs=0.45),
    dict(name='BladelockArbalist', sheet='Arbaletník', front=(900, 20, 1090, 342), side=(1520, 20, 1720, 342), height=76, kind='creature', legs=0.45),
    dict(name='SergeantOttar', sheet='Ottar', front=(940, 15, 1140, 362), side=(1560, 15, 1720, 362), height=80, kind='creature', legs=0.45, pedestal=True),
    # The Millrace Undercroft.
    dict(name='HollowedBearer', sheet='Hollowedbearer', front=(900, 10, 1110, 368), side=(1510, 10, 1710, 368), height=96, kind='creature', legs=0.0),
    dict(name='BroodDrake', sheet='BroodDrake', front=(870, 20, 1060, 345), side=(1420, 30, 1750, 345), height=80, kind='creature', legs=0.3),
    dict(name='RingKeeperWarden', sheet='Strážce prstenu', front=(860, 10, 1060, 368), side=(1550, 10, 1710, 368), height=84, kind='creature', legs=0.45, pedestal=True),
    dict(name='Mardra', sheet='Mardra', front=(980, 5, 1220, 305), side=(1500, 5, 1730, 305), height=112, kind='creature', legs=0.35),
    # Ravenford's people.
    dict(name='Matthew', sheet='Matthew', front=(970, 15, 1120, 350), side=(1500, 15, 1690, 350), height=76, kind='npc'),
    dict(name='Edda', sheet='Edd', front=(920, 20, 1150, 362), side=(1500, 20, 1700, 362), height=70, kind='npc'),
    dict(name='ReeveHollan', sheet='Hollana', front=(915, 15, 1110, 356), side=(1530, 15, 1690, 356), height=74, kind='npc'),
    dict(name='MarraSenn', sheet='Marra Senn', front=(960, 15, 1110, 316), side=(1540, 15, 1670, 316), height=72, kind='npc'),
    dict(name='Moth', sheet='Můří kupec', front=(930, 15, 1145, 360), side=(1540, 15, 1680, 360), height=76, kind='npc'),
    dict(name='SisterCarmine', sheet='Carmine', front=(960, 15, 1115, 362), side=(1530, 15, 1665, 362), height=72, kind='npc'),
    dict(name='SisterVale', sheet='Valeové', front=(960, 20, 1115, 360), side=(1540, 20, 1680, 360), height=78, kind='npc'),
    dict(name='OldHobb', sheet='mlynáře', front=(936, 24, 1134, 366), side=(1500, 24, 1700, 366), height=66, kind='npc'),
    dict(name='LiseHobb', sheet='Lise', front=(930, 20, 1140, 366), side=(1500, 20, 1700, 366), height=72, kind='npc'),
    dict(name='JessaBed', sheet='Jessa', front=(840, 90, 1090, 375), side=(1410, 100, 1745, 335), height=40, kind='static', round=6.0),
    # Buildings, at a sixteenth of a unit. The side is the right-hand elevation.
    dict(name='CrookedRaven', sheet='CrookedRaven', front=(815, 10, 1130, 390), side=(380, 610, 550, 825), height=120, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='SennsNeedlehouse', sheet='krejčovského', front=(810, 10, 1050, 392), side=(360, 620, 520, 830), height=96, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='PellsChandlery', sheet='PellsChandlery', front=(850, 10, 1060, 388), side=(350, 620, 510, 825), height=104, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='LanternAndMoth', sheet='LanternAndMoth', front=(850, 10, 1070, 388), side=(330, 620, 500, 825), height=88, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='ReevesHall', sheet='ReevesHall', front=(810, 60, 1135, 385), side=(360, 620, 570, 825), height=88, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='RookeryTower', sheet='Rookery', front=(880, 10, 1150, 395), side=(340, 600, 470, 825), height=176, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='OrrasHospice', sheet='hospic', front=(800, 40, 1150, 400), side=(350, 600, 590, 796), height=100, kind='static', round=8.0, flip=True, recipe=True),
    dict(name='HobbsMill', sheet='Hobbsův mlýn', front=(780, 30, 1060, 385), side=(360, 620, 530, 830), height=96, kind='static', round=8.0, flip=True, recipe=True),
    # Props, at a sixteenth of a unit.
    dict(name='FeatherShrine', sheet='Ptačí svatyni', front=(100, 0, 620, 870), side=(1360, 0, 1650, 870), height=64, kind='static', round=6.0),
    dict(name='Gibbet', sheet='šibenicová', front=(40, 0, 540, 870), side=(1290, 0, 1600, 870), height=64, kind='static', round=6.0),
    dict(name='IronFrame', sheet='železný rám', front=(40, 20, 650, 870), side=(1370, 20, 1640, 870), height=48, kind='static', round=8.0),
    dict(name='RingPedestal', sheet='kamenný podstavec', front=(40, 20, 620, 740), side=(40, 20, 620, 740), height=28, kind='static', round=3.0),
    # Loose is for shapes two outlines cannot hold, such as sparse blades or a
    # thin hanging sign. tools/inspect_models.py expects less of them.
    dict(name='WetlandReeds', sheet='rákosový mokřad', front=(30, 20, 640, 830), side=(1370, 20, 1720, 830), height=40, kind='static', round=2.0, loose=True),
    dict(name='CattailReeds', sheet='rákosí a orobinec', front=(30, 20, 650, 820), side=(1370, 20, 1710, 820), height=40, kind='static', round=2.0, loose=True),
    dict(name='RavenBanner', sheet='havraní prapor', front=(30, 10, 690, 840), side=(1480, 10, 1620, 840), height=40, kind='static', round=8.0),
    dict(name='MothSign', sheet='ceduli s můry', front=(60, 0, 740, 800), side=(1580, 0, 1700, 800), height=24, kind='static', round=8.0, loose=True),
    dict(name='NeedleSign', sheet='jehlou a nití', front=(30, 10, 720, 800), side=(1540, 10, 1680, 800), height=24, kind='static', round=8.0, loose=True),
    dict(name='RavenPerch', sheet='Вороньи', front=(100, 190, 680, 720), side=(1650, 200, 2010, 720), height=24, kind='static', round=8.0),
]

# The standalone raven's atlas: every frame has a side and a back view.
RAVEN = dict(
    name='Raven', sheet='atlas', scale=0.26,
    clips=[
        # Name, loop, frame milliseconds, side row top and bottom, back row top and bottom, half width, frame centers.
        ('idle', True, 160, (785, 885), (885, 985), 48, [200, 290, 382, 475, 568, 660]),
        ('caw', False, 110, (785, 885), (885, 985), 48, [895, 985, 1075, 1165, 1256, 1347, 1438]),
        ('fly', True, 70, (118, 238), (222, 322), 86, [233, 404, 577, 753, 925, 1098, 1270, 1442]),
        ('land', False, 90, (440, 552), (540, 638), 86, [235, 410, 585, 757, 927, 1098, 1272, 1442]),
    ],
)


def sheet_for(directory, key):
    found = [p for p in Path(directory).iterdir() if p.suffix == '.png' and key in p.name]
    if len(found) != 1:
        raise SystemExit(f'{len(found)} sheets match {key!r}')
    return found[0]


def import_sheets(directory):
    CROPS.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        sheet = Image.open(sheet_for(directory, model['sheet'])).convert('RGB')
        sheet.crop(model['front']).save(CROPS / f"{model['name']}.front.png")
        sheet.crop(model['side']).save(CROPS / f"{model['name']}.side.png")
    atlas = Image.open(sheet_for(directory, RAVEN['sheet'])).convert('RGB')
    atlas.save(CROPS / 'Raven.atlas.png')
    print(f'{len(MODELS)} models and the raven atlas cropped into {CROPS}')


def silhouette(pixels, trim=0):
    """A mask of what stands out from the dark background of a crop."""
    bright = ndimage.uniform_filter(pixels.max(axis=2).astype(float), 5)
    border = np.concatenate([bright[0], bright[-1], bright[:, 0], bright[:, -1]])
    level = max(18.0, np.percentile(border, 60) + 9.0)
    mask = bright > level
    # A panel border can run across the top of a crop and touch a roof.
    for y in range(min(16, mask.shape[0])):
        if mask[y].mean() > 0.6:
            mask[:y + 3] = False
    mask = ndimage.binary_closing(mask, iterations=2)
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    # Panel borders are long thin lines; drop pieces only a few pixels tall or wide.
    boxes = ndimage.find_objects(labels)
    thick = [min(b[0].stop - b[0].start, b[1].stop - b[1].start) > 8 for b in boxes]
    keep = np.isin(labels, [i + 1 for i, s in enumerate(sizes) if thick[i] and s >= max(300, sizes.max() * 0.04)])
    # Fill small enclosed holes, leave large gaps such as between legs open.
    holes = ndimage.binary_fill_holes(keep) & ~keep
    hole_labels, hole_count = ndimage.label(holes)
    if hole_count:
        hole_sizes = ndimage.sum(holes, hole_labels, range(1, hole_count + 1))
        small = np.isin(hole_labels, [i + 1 for i, s in enumerate(hole_sizes) if s < 500])
        keep |= small
    if trim:
        ys = np.nonzero(keep.any(axis=1))[0]
        keep[ys.max() - trim + 1:] = False
    return keep


def pedestal_cut(mask):
    """The first row of a display pedestal under the feet, or None. The people
    sheets stand each figure on a round base: below the feet the silhouette
    either breaks off and starts again, or suddenly doubles in width."""
    rows = np.nonzero(mask.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    start = bottom - int((bottom - top) * 0.15)
    narrowest = None
    for y in range(start, bottom + 1):
        width = int(mask[y].sum())
        if width == 0:
            return y
        if narrowest is not None and width > narrowest * 2.0 and width > narrowest + 20:
            return y
        narrowest = width if narrowest is None else min(narrowest, width)
    return None


def tighten(pixels, mask):
    ys, xs = np.nonzero(mask)
    return pixels[ys.min():ys.max() + 1, xs.min():xs.max() + 1], mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def shrink(pixels, mask, scale):
    """Averages each cell of the view into one voxel. Returns colors and coverage,
    with rows running up."""
    height = max(1, round(mask.shape[0] * scale))
    width = max(1, round(mask.shape[1] * scale))
    colors = np.zeros((height, width, 3))
    cover = np.zeros((height, width), dtype=bool)
    for y in range(height):
        y0, y1 = int(y / scale), max(int(y / scale) + 1, int((y + 1) / scale))
        for x in range(width):
            x0, x1 = int(x / scale), max(int(x / scale) + 1, int((x + 1) / scale))
            cell = mask[y0:y1, x0:x1]
            if cell.size == 0 or cell.mean() < 0.4:
                continue
            cover[y, x] = True
            colors[y, x] = pixels[y0:y1, x0:x1][cell].mean(axis=0)
    return colors[::-1], cover[::-1]


def runs(row):
    found = []
    start = None
    for i, value in enumerate(list(row) + [False]):
        if value and start is None:
            start = i
        elif not value and start is not None:
            found.append((start, i - 1))
            start = None
    return found


def hull(front, front_cover, side, side_cover, roundness):
    """Solid where both views agree. Returns a color grid indexed [x, y, z]."""
    height = min(front_cover.shape[0], side_cover.shape[0])
    width = front_cover.shape[1]
    depth = side_cover.shape[1]
    solid = np.zeros((width, height, depth), dtype=bool)
    color = np.zeros((width, height, depth, 3))
    for y in range(height):
        for x0, x1 in runs(front_cover[y]):
            cx, rx = (x0 + x1) / 2, (x1 - x0) / 2 + 0.5
            for z0, z1 in runs(side_cover[y]):
                cz, rz = (z0 + z1) / 2, (z1 - z0) / 2 + 0.5
                for x in range(x0, x1 + 1):
                    for z in range(z0, z1 + 1):
                        u, w = (x - cx) / rx, (z - cz) / rz
                        if abs(u) ** roundness + abs(w) ** roundness > 1.0:
                            continue
                        solid[x, y, z] = True
                        # Faces turned toward the front take the front view's color.
                        # No sheet shows a back, so a back takes the color of the
                        # profile's back edge, shaded by the front's light and dark
                        # so it is not one flat stripe per row.
                        if w > abs(u) * 0.8:
                            color[x, y, z] = front[y, x]
                        elif w < -abs(u) * 0.8:
                            edge = side[y, z0:min(z1 + 1, z0 + 3)].mean(axis=0)
                            light = front[y, x].mean() / max(1.0, front[y, x0:x1 + 1].mean())
                            color[x, y, z] = edge * min(1.25, max(0.75, light))
                        else:
                            color[x, y, z] = side[y, z]
    return solid, color


def voxel_height(model):
    if model['kind'] in ('creature', 'crawler', 'npc'):
        return min(model['height'], TALLEST)
    return model['height']


def voxel_size(model):
    """World size of one voxel of the built model, for the creature kinds."""
    return CELL * model['height'] / voxel_height(model)


def load_views(model):
    front_image = np.asarray(Image.open(CROPS / f"{model['name']}.front.png").convert('RGB'), dtype=np.int32)
    side_image = np.asarray(Image.open(CROPS / f"{model['name']}.side.png").convert('RGB'), dtype=np.int32)
    if model.get('flip'):
        side_image = side_image[:, ::-1]
    front_mask = silhouette(front_image, model.get('trim', 0))
    side_mask = silhouette(side_image, model.get('trim', 0))
    if model.get('pedestal', model['kind'] == 'npc'):
        for mask in (front_mask, side_mask):
            cut = pedestal_cut(mask)
            if cut is not None:
                mask[cut:] = False
    front_pixels, front_mask = tighten(front_image, front_mask)
    side_pixels, side_mask = tighten(side_image, side_mask)
    height = voxel_height(model)
    front, front_cover = shrink(front_pixels, front_mask, height / front_mask.shape[0])
    side, side_cover = shrink(side_pixels, side_mask, height / side_mask.shape[0])
    return front, front_cover, side, side_cover


def pad(grid, width, depth):
    """Centers the model in a grid of the given width and depth."""
    w, h, d = grid.shape
    out = np.full((width, h, depth), -1, dtype=np.int32)
    x0, z0 = (width - w) // 2, (depth - d) // 2
    out[x0:x0 + w, :, z0:z0 + d] = grid
    return out


# Posing. Each pose takes the rest grid and returns a new one of the same size.

def pitch(grid, angle, pivot_y, pivot_z, above=0, squash=1.0, drop=0):
    """Tips everything at or above row `above` forward (+Z) by angle degrees about
    the pivot, and can squash and lower it."""
    w, h, d = grid.shape
    out = grid.copy()
    out[:, above:, :] = -1
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    ys, zs = np.meshgrid(np.arange(h), np.arange(d), indexing='ij')
    # Inverse map: where in the rest grid each target cell came from.
    ty = (ys + drop - pivot_y) / squash
    tz = zs - pivot_z
    sy = np.rint(pivot_y + ty * ca - tz * sa).astype(int)
    sz = np.rint(pivot_z + ty * sa + tz * ca).astype(int)
    valid = (sy >= above) & (sy < h) & (sz >= 0) & (sz < d)
    for x in range(w):
        layer = np.full((h, d), -1, dtype=np.int32)
        layer[valid] = grid[x][sy[valid], sz[valid]]
        keep = layer >= 0
        out[x][keep & (ys >= 0)] = layer[keep]
    return out


def stride(grid, legs_top, swing, lift):
    """Moves the left legs forward and the right ones back by `swing` cells,
    lifting the forward one."""
    out = grid.copy()
    w, h, d = grid.shape
    solid = np.nonzero((grid >= 0).any(axis=(1, 2)))[0]
    middle = (solid.min() + solid.max()) / 2 if len(solid) else w / 2
    out[:, :legs_top, :] = -1
    for x in range(w):
        side = 1 if x < middle else -1
        dz = int(round(swing * side))
        dy = lift if dz > 0 else 0
        part = grid[x, :legs_top, :]
        for y in range(legs_top):
            ty = min(legs_top - 1, y + dy)
            row = np.roll(part[y], dz)
            if dz > 0:
                row[:dz] = -1
            elif dz < 0:
                row[dz:] = -1
            keep = row >= 0
            out[x, ty][keep] = row[keep]
    return out


def rise(grid, above, dy):
    """Lifts every row at or above `above` by dy, stretching the row below."""
    if dy == 0:
        return grid.copy()
    out = grid.copy()
    h = grid.shape[1]
    out[:, above + dy:, :] = grid[:, above:h - dy, :]
    for y in range(above, above + dy):
        out[:, y, :] = grid[:, above, :]
    return out


def shift(grid, dz, dy=0):
    out = np.full_like(grid, -1)
    w, h, d = grid.shape
    zs = slice(max(0, dz), d + min(0, dz))
    zf = slice(max(0, -dz), d - max(0, dz))
    ys = slice(max(0, dy), h + min(0, dy))
    yf = slice(max(0, -dy), h - max(0, dy))
    out[:, ys, zs] = grid[:, yf, zf]
    return out


def body_box(grid):
    solid = grid >= 0
    zs = np.nonzero(solid.any(axis=(0, 1)))[0]
    ys = np.nonzero(solid.any(axis=(0, 2)))[0]
    return ys.min(), ys.max(), zs.min(), zs.max()


def creature_clips(rest, legs):
    y0, y1, z0, z1 = body_box(rest)
    height = y1 - y0 + 1
    hips = y0 + max(1, int(height * legs)) if legs > 0 else y0 + int(height * 0.45)
    middle_z = (z0 + z1) // 2
    step = max(1, round(height * 0.05))
    clips = []
    clips.append(('idle', True, [(rest, 520), (rise(rest, hips, 1), 520)]))
    walk = []
    for i in range(4):
        phase = (0, 1, 0, -1)[i]
        frame = stride(rest, hips, step * phase, 1) if legs > 0 else rest
        frame = rise(frame, hips, 1 if phase == 0 else 0)
        walk.append((frame, 130))
    clips.append(('walk', True, walk))
    attack = []
    for angle, ms in ((-12, 130), (-18, 140), (28, 80), (12, 120), (0, 90)):
        attack.append((pitch(rest, angle, hips, middle_z, above=hips), ms))
    clips.append(('attack', False, attack))
    clips.append(('hit', False, [(shift(pitch(rest, -14, hips, middle_z, above=hips), -1), 110), (pitch(rest, -6, hips, middle_z, above=hips), 110)]))
    death = []
    for k, (angle, squash) in enumerate(((18, 0.9), (32, 0.72), (40, 0.55), (42, 0.45))):
        death.append((pitch(rest, angle, y0, middle_z, above=y0, squash=squash), 130 if k < 3 else 400))
    clips.append(('death', False, death))
    return clips


def crawler_clips(rest):
    y0, y1, z0, z1 = body_box(rest)
    middle_z = (z0 + z1) // 2
    clips = [('idle', True, [(rest, 300), (rise(rest, y0 + 1, 1), 300)])]
    walk = []
    for i in range(4):
        walk.append((shift(rest, (0, 1, 2, 1)[i]), 140))
    clips.append(('walk', True, walk))
    front = z0 + (z1 - z0) * 2 // 3
    clips.append(('attack', False, [(pitch(rest, -20, y0, front, above=y0), 160), (shift(rest, 3), 80), (shift(rest, 2), 100), (rest, 100)]))
    clips.append(('hit', False, [(shift(rest, -1), 90), (rest, 90)]))
    flat = rest.copy()
    clips.append(('death', False, [(pitch(rest, 0, y0, middle_z, above=y0, squash=0.6), 120), (pitch(rest, 0, y0, middle_z, above=y0, squash=0.3), 400)]))
    return clips


def npc_clips(rest):
    y0, y1, z0, z1 = body_box(rest)
    height = y1 - y0 + 1
    chest = y0 + int(height * 0.55)
    neck = y0 + int(height * 0.82)
    middle_z = (z0 + z1) // 2
    idle = [(rest, 950), (rise(rest, chest, 1), 900)]
    talk = [(rest, 200), (pitch(rest, 6, neck, middle_z, above=neck), 180), (rest, 160), (pitch(rest, -4, neck, middle_z, above=neck), 180)]
    return [('idle', True, idle), ('talk', True, talk)]


def margin_for(kind, rest):
    w, h, d = rest.shape
    if kind == 'creature':
        # Room for the lunge and the fall.
        reach = int(h * 0.55) + 4
        return w + 6, max(d + 2 * reach, d + 8)
    if kind == 'crawler':
        return w + 4, d + 10
    if kind == 'npc':
        return w + 4, d + int(h * 0.2) + 4
    return w, d


def trim(rest, clips):
    """Cuts the canvas down to what any frame uses, keeping the model centered
    so it does not slide between clips."""
    used = rest >= 0
    for _, _, frames in clips:
        for grid, _ in frames:
            used = used | (grid >= 0)
    w, h, d = rest.shape
    xs = np.nonzero(used.any(axis=(1, 2)))[0]
    zs = np.nonzero(used.any(axis=(0, 1)))[0]
    half_x = int(max(w / 2 - xs.min(), xs.max() + 1 - w / 2)) + 1
    half_z = int(max(d / 2 - zs.min(), zs.max() + 1 - d / 2)) + 1
    x0, x1 = max(0, w // 2 - half_x), min(w, w // 2 + half_x)
    z0, z1 = max(0, d // 2 - half_z), min(d, d // 2 + half_z)
    cut = lambda g: g[x0:x1, :, z0:z1]
    return cut(rest), [(name, looping, [(cut(g), ms) for g, ms in frames]) for name, looping, frames in clips]


def quantize(frames):
    """One palette for every frame of the model, at most one symbol per color."""
    cells = np.concatenate([color[solid] for solid, color in frames]).astype(np.uint8)
    count = min(len(SYMBOLS), max(1, len(cells)))
    strip = Image.fromarray(cells.reshape(1, -1, 3), 'RGB').quantize(count, method=Image.Quantize.MEDIANCUT)
    palette = np.array(strip.getpalette()[:count * 3]).reshape(-1, 3)
    indexes = np.asarray(strip).reshape(-1)
    grids = []
    at = 0
    for solid, color in frames:
        grid = np.full(solid.shape, -1, dtype=np.int32)
        n = int(solid.sum())
        grid[solid] = indexes[at:at + n]
        at += n
        grids.append(grid)
    return grids, palette


def linear(channel):
    """The engine reads model colors as linear light, as the terrain's are, while
    the sheets are sRGB. Without this the models come out pale and flat."""
    value = channel / 255.0
    value = value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    return int(round(value * 255.0))


def write(path, palette, base, clips):
    w, h, d = base.shape
    lines = ['qvox 1', f'size {w} {h} {d}', '']
    for i, color in enumerate(palette):
        r, g, b = (linear(int(c)) for c in color)
        lines.append(f'color {SYMBOLS[i]} {r:02X}{g:02X}{b:02X}')

    def grid_lines(grid):
        for y in range(h):
            lines.append(f'# y = {y}')
            for z in range(d):
                lines.append(''.join('.' if grid[x, y, z] < 0 else SYMBOLS[grid[x, y, z]] for x in range(w)))

    if not clips:
        lines.append('')
        grid_lines(base)
    for name, looping, frames in clips:
        lines.append('')
        lines.append(f"clip {name} {'loop' if looping else 'once'}")
        for grid, ms in frames:
            lines.append(f'frame {ms}')
            grid_lines(grid)
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def render(grid, palette, yaw):
    w, h, d = grid.shape
    angle = math.radians(yaw)
    size = int(w + d) + 2
    image = np.zeros((h, size, 3), dtype=np.uint8)
    best = np.full((h, size), -1e9)
    for x, y, z in zip(*np.nonzero(grid >= 0)):
        px, pz = x - w / 2, z - d / 2
        u = int(px * math.cos(angle) + pz * math.sin(angle) + size / 2)
        near = pz * math.cos(angle) - px * math.sin(angle)
        if 0 <= u < size and near > best[h - 1 - y, u]:
            best[h - 1 - y, u] = near
            image[h - 1 - y, u] = palette[grid[x, y, z]]
    return image


def save_preview(name, palette, base, clips):
    PREVIEW.mkdir(parents=True, exist_ok=True)
    rows = [np.concatenate([render(base, palette, yaw) for yaw in (0.0, 45.0, 90.0)], axis=1)]
    for clip, _, frames in clips:
        rows.append(np.concatenate([render(grid, palette, 90.0) for grid, _ in frames], axis=1))
    width = max(r.shape[1] for r in rows)
    sheet = np.concatenate([np.pad(r, ((0, 2), (0, width - r.shape[1]), (0, 0))) for r in rows], axis=0)
    scale = max(1, min(4, 900 // max(sheet.shape)))
    Image.fromarray(sheet).resize((sheet.shape[1] * scale, sheet.shape[0] * scale), Image.NEAREST).save(PREVIEW / f'{name}.png')


def build_model(model, preview):
    front, front_cover, side, side_cover = load_views(model)
    solid, color = hull(front, front_cover, side, side_cover, model.get('round', 2.6))
    kind = model['kind']
    # Pose with color indexes standing in for colors: index into a flat list.
    flat = color[solid]
    rest = np.full(solid.shape, -1, dtype=np.int32)
    rest[solid] = np.arange(len(flat))
    width, depth = margin_for(kind, rest)
    rest = pad(rest, width, depth)
    if kind == 'creature':
        clips = creature_clips(rest, model.get('legs', 0.3))
    elif kind == 'crawler':
        clips = crawler_clips(rest)
    elif kind == 'npc':
        clips = npc_clips(rest)
    else:
        clips = []
    rest, clips = trim(rest, clips)
    frames = [(rest >= 0, flat[np.maximum(rest, 0)])]
    for _, _, clip_frames in clips:
        for grid, _ in clip_frames:
            frames.append((grid >= 0, flat[np.maximum(grid, 0)]))
    grids, palette = quantize(frames)
    base = grids[0]
    at = 1
    posed = []
    for name, looping, clip_frames in clips:
        out = []
        for _, ms in clip_frames:
            out.append((grids[at], ms))
            at += 1
        posed.append((name, looping, out))
    write(ASSETS / f"{model['name']}.qvox", palette, base, posed)
    if preview:
        save_preview(model['name'], palette, base, posed)
    w, h, d = base.shape
    size = f', voxel {voxel_size(model):.4f}' if kind in ('creature', 'crawler', 'npc') else ''
    print(f"{model['name']}: {w} x {h} x {d}, {int(solid.sum())} voxels, {len(frames) - 1} frames{size}")


def raven_view(atlas, box, scale):
    pixels = np.asarray(atlas.crop(box), dtype=np.int32)
    mask = silhouette(pixels)
    if not mask.any():
        return None
    pixels, mask = tighten(pixels, mask)
    return shrink(pixels, mask, scale)


def build_raven(preview):
    atlas = Image.open(CROPS / 'Raven.atlas.png').convert('RGB')
    scale = RAVEN['scale']
    built = []
    for name, looping, ms, side_rows, back_rows, half, centers in RAVEN['clips']:
        frames = []
        for cx in centers:
            side = raven_view(atlas, (cx - half, side_rows[0], cx + half, side_rows[1]), scale)
            back = raven_view(atlas, (cx - half, back_rows[0], cx + half, back_rows[1]), scale)
            if side is None or back is None:
                continue
            # Both views show the same pose, so give them the same height.
            height = min(side[1].shape[0], back[1].shape[0])
            s_color, s_cover = side[0][:height], side[1][:height]
            b_color, b_cover = back[0][:height], back[1][:height]
            frames.append(hull(b_color, b_cover, s_color, s_cover, 2.4))
        built.append((name, looping, ms, frames))
    width = max(s.shape[0] for _, _, _, fs in built for s, _ in fs) + 2
    height = max(s.shape[1] for _, _, _, fs in built for s, _ in fs) + 1
    depth = max(s.shape[2] for _, _, _, fs in built for s, _ in fs) + 2
    flat_frames = []
    for _, _, _, fs in built:
        for solid, color in fs:
            w, h, d = solid.shape
            big_solid = np.zeros((width, height, depth), dtype=bool)
            big_color = np.zeros((width, height, depth, 3))
            x0, z0 = (width - w) // 2, (depth - d) // 2
            big_solid[x0:x0 + w, :h, z0:z0 + d] = solid
            big_color[x0:x0 + w, :h, z0:z0 + d] = color
            flat_frames.append((big_solid, big_color))
    grids, palette = quantize(flat_frames)
    posed = []
    at = 0
    for name, looping, ms, fs in built:
        posed.append((name, looping, [(grids[at + i], ms) for i in range(len(fs))]))
        at += len(fs)
    # Perched birds land on their feet, so the idle frames sit on the floor;
    # flying frames float in the middle of the grid.
    write(ASSETS / 'Raven.qvox', palette, grids[0], posed)
    if preview:
        save_preview('Raven', palette, grids[0], posed)
    print(f'Raven: {width} x {height} x {depth}, {len(flat_frames)} frames')


def build_spark(preview):
    """The Silver Spark has no shape to cut out: a crackling mote of light,
    a bright core with arcs that change every frame."""
    size = 16
    palette = np.array([(250, 252, 255), (196, 222, 255), (120, 170, 240), (70, 110, 200)])
    rng = np.random.default_rng(5)

    def mote(core, arcs, reach):
        grid = np.full((size, size, size), -1, dtype=np.int32)
        c = (size - 1) / 2
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    d = math.dist((x, y, z), (c, c, c))
                    if d <= core:
                        grid[x, y, z] = 0
                    elif d <= core + 1.2:
                        grid[x, y, z] = 1
        for _ in range(arcs):
            direction = rng.normal(size=3)
            direction /= np.linalg.norm(direction)
            point = np.array([c, c, c])
            for step in range(int(reach)):
                point = point + direction + rng.normal(scale=0.45, size=3)
                ix, iy, iz = np.rint(point).astype(int)
                if 0 <= ix < size and 0 <= iy < size and 0 <= iz < size:
                    grid[ix, iy, iz] = 2 if step < reach / 2 else 3
        return grid

    clips = [
        ('idle', True, [(mote(1.6, 4, 5), 90), (mote(1.8, 5, 6), 90), (mote(1.5, 3, 5), 90)]),
        ('walk', True, [(mote(1.6, 4, 6), 80), (mote(1.7, 6, 6), 80)]),
        ('attack', False, [(mote(2.2, 8, 7), 80), (mote(3.0, 12, 8), 120), (mote(1.6, 4, 5), 120)]),
        ('hit', False, [(mote(1.2, 2, 3), 120)]),
        ('death', False, [(mote(1.0, 6, 7), 100), (mote(0.6, 3, 4), 120), (mote(0.0, 1, 2), 300)]),
    ]
    write(ASSETS / 'SilverSpark.qvox', palette, clips[0][2][0][0], clips)
    if preview:
        save_preview('SilverSpark', palette, clips[0][2][0][0], clips)
    print('SilverSpark: 16 x 16 x 16')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*')
    parser.add_argument('--import', dest='source')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if args.source:
        import_sheets(args.source)
        return
    for model in MODELS:
        # Recipe models are built by buildings.py; their entry here only keeps
        # the sheet crops for inspect_models.py.
        if model.get('recipe'):
            continue
        if not args.names or model['name'] in args.names:
            build_model(model, args.preview)
    if not args.names or 'Raven' in args.names:
        build_raven(args.preview)
    if not args.names or 'SilverSpark' in args.names:
        build_spark(args.preview)


if __name__ == '__main__':
    main()
