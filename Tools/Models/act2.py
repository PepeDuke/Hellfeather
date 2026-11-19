"""The Act II reference sheets: cropping their views, and the registry of Act II models.

The Act II sheets differ from Act I's. Each shows one model three times side by side
on near-black: the front (facing +Z, toward the camera), the side, and a third view
(the back, or a three-quarter view). There is no dimension panel, so sizes come from
Act2Models.md. The `_Animation` sheets are frame grids for the rigs and are not
cropped here.

The import finds the views by itself: it marks what stands out from the background,
splits the sheet at the empty column gaps between the views, and saves each view as
<Name>.front.png, <Name>.side.png and <Name>.third.png in Assets/Reference/Act2. A
sheet whose views come in another order says so in ORDER. It also saves
Tools/Models/Inspect/Act2Crops.png, every sheet with its found boxes drawn on, to
check the cuts at a glance.

    python Tools/Models/act2.py --import C:/Users/PC/Downloads/act2refs
    python Tools/Models/act2.py --import C:/Users/PC/Downloads/act2refs FeatherFire   one sheet again
    python Tools/Models/act2.py                    build every hull model into Assets
    python Tools/Models/act2.py TitheHanged --preview

MODELS lists every Act II model in act1.MODELS's format, with `crops` pointing at
this act's folder. Buildings that matter are recipes (camp.py, thornwick.py); the
rest, and the people and creatures, are built here by act1.py's visual hull, posed
into clips by bending it, as Act I's first models were. inspect_models.py scores
them all against their sheets.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import act1  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CROPS = ROOT / 'Assets/Reference/Act2'
CONTACT = ROOT / 'Tools/Models/Inspect/Act2Crops.png'
VIEWS = ('front', 'side', 'third')
# Sheets whose views are not front, side, third from left to right: the order of
# the views as they stand on the sheet.
ORDER = {
    'PilgrimsEncampment': ('third', 'front', 'side'),
}
# Sheets painting something the game draws as an effect above the model, such
# as the Feather Fire's flame: the share of each view's height cut off its top,
# so the crop shows only what the model has to match.
CUT_TOP = {
    'FeatherFire': 0.34,
}
# Sheets whose views stand too close for the gap search: the x positions, in
# sheet pixels, that split them into views.
SPLITS = {
    'InscriptionLoom': (555, 896),
}
# Columns of background at least this wide (in pixels) separate two views.
GAP = 24
# Pieces narrower than this are labels, sparks or smoke, not a view.
NARROWEST = 30
PAD = 4

# Sheets saved under another model's name: the Act II Carmine sheet is the Red
# Warden boss, a model of its own, while Act I's SisterCarmine.qvox stays the
# hospice gate's nurse.
ALIAS = {
    'SisterCarmine': 'RedWarden',
}


def hull(name, height, kind='static', flip=True, **extra):
    """A model act1.py builds from the two views (a visual hull). Props and
    buildings face +Z with their front on the left of the side view, so they
    flip; most figures face right in theirs, so creatures and people do not."""
    roundness = extra.pop('round', 6.0 if kind == 'static' else 2.6)
    return dict(name=name, height=height, kind=kind, flip=flip, crops=CROPS, round=roundness, **extra)


def creature(name, height, legs=0.45, flip=False, **extra):
    return hull(name, height, 'creature', flip, legs=legs, **extra)


def npc(name, height, flip=False, **extra):
    return hull(name, height, 'npc', flip, **extra)


def recipe(name, height):
    """A model a recipe file (camp.py, thornwick.py) builds; listed so
    inspect_models.py scores it against its sheet."""
    return dict(name=name, height=height, kind='static', recipe=True, flip=True, crops=CROPS)


# Every Act II model. Heights are in voxels: 0.0625 units for props and
# buildings (16 to a unit), 0.025 for people and creatures, whose models taller
# than act1.TALLEST get coarser voxels (the build prints the size).
MODELS = [
    # The Pilgrims' Encampment (camp.py recipes).
    recipe('PilgrimShrine', 112),
    recipe('FeatherFire', 32),
    recipe('WrensTent', 48),
    recipe('PilgrimTent', 40),
    recipe('PilgrimTentB', 40),
    # Camp props.
    hull('Brazier', 20),
    hull('CampWagon', 40),
    hull('CampWagonB', 40),
    hull('CookPot', 24),
    hull('CorvinsBench', 40),
    hull('CorvinsBenchPacked', 36),
    hull('DryingRack', 40, loose=True),
    hull('FeatherSack', 16),
    hull('HesksWagon', 56),
    hull('Jetty', 20),
    hull('LatrineScreen', 28),
    hull('LongTable', 16, loose=True),
    hull('OfferingPile', 10),
    hull('PilgrimTentStruck', 14),
    hull('RavenCage', 44),
    hull('StakePalisade', 32),
    hull('SwanScare', 48, loose=True),
    hull('TinkersCart', 40),
    hull('TorchPole', 52, loose=True),
    hull('TorchPoleCold', 48, loose=True),
    hull('WaterBarrels', 20),
    # The Hospice Road and Thornmere.
    hull('RoadGibbet', 64),
    hull('RoadGibbetEmpty', 64, loose=True),
    hull('RoadsideShrine', 48),
    hull('SwanNest', 14),
    hull('SwanMatriarchNest', 20),
    hull('DrownedCart', 24, loose=True),
    hull('PilgrimCampRoadside', 48),
    # Thornwick (thornwick.py recipes), the Cloister and the hospice's south wing.
    recipe('ThornwickGate', 128),
    recipe('TitheHouse', 128),
    recipe('ClothiersGuildhall', 144),
    recipe('ClothiersGuildhallBurnt', 144),
    recipe('ClothiersRow', 112),
    dict(recipe('ClothiersRowB', 112), flip=False),
    hull('DyeVats', 24),
    recipe('InscriptionLoom', 64),
    recipe('CloisterOfLooms', 192),
    hull('HospiceSouthWing', 112, round=8.0),
    # Interiors: the Cloister, the Records Cellar and the South Wing.
    hull('PracticeLoom', 40),
    hull('Lectern', 24),
    hull('Bookshelf', 48, round=8.0),
    hull('BookshelfEast', 48, round=8.0),
    hull('ExpulsionCabinet', 40, round=8.0),
    recipe('ChalkCircle', 2),
    hull('ThreadSpools', 28),
    hull('RecordShelf', 52, round=8.0),
    hull('RecordShelfEast', 52, round=8.0),
    hull('TransferredCabinet', 40, round=8.0),
    hull('ClerksDesk', 28),
    hull('BoilerHatch', 32, round=8.0),
    hull('WardBed', 18),
    hull('WardBedEast', 18),
    hull('WardBedOccupied', 22),
    hull('StitchFrame', 48, loose=True),
    hull('CellDoor', 40, round=8.0),
    hull('CellDoorOpen', 40, round=8.0),
    hull('RestraintChair', 28),
    hull('MedicineCart', 22, loose=True),
    hull('WardCurtain', 40, loose=True),
    hull('RelaySocket', 24),
    hull('PatientFrame', 52),
    hull('PatientFrameEmpty', 48, loose=True),
    # People.
    npc('PilgrimMotherHesk', 72),
    npc('TollyTinker', 72),
    npc('CorvinHale', 66),
    npc('CorvinHaleChained', 60),
    npc('MistressAgnet', 74),
    npc('CloisterNovice', 66),
    npc('CloisterNoviceWriting', 66),
    npc('Pilgrim01', 70),
    npc('Pilgrim02', 70),
    npc('Pilgrim03', 70, flip=True),
    npc('PilgrimSitting', 60, flip=True),
    npc('ThornwickDyerMadder', 72),
    npc('ThornwickDyerWoad', 72),
    npc('ThornwickGateCuff', 76),
    npc('TitheClerk', 72),
    # Enemies of the Hospice Road and Thornmere.
    creature('TitheHanged', 76),
    creature('MoultingHound', 44, legs=0.4),
    creature('HighwayCuff', 76),
    creature('FeatherblightSwan', 96, legs=0.25, flip=True),
    creature('SwanMatriarch', 130, legs=0.25),
    creature('CygnetBrood', 30, legs=0.3),
    creature('ReedDrowner', 74, flip=True),
    # The Cloister of Looms.
    creature('LoomWight', 78, legs=0.35),
    creature('NoviceWeaver', 70),
    hull('AnimatedShuttle', 14, 'crawler', False, loose=True),
    hull('InkBlot', 24, 'crawler', False, loose=True),
    creature('FailedLoom', 110, legs=0.35, round=4.0),
    # The Records Cellar.
    hull('ArchiveRat', 14, 'crawler', False),
    creature('CellarWatchman', 76),
    creature('ClerkShade', 72, legs=0.0),
    # The South Wing, and Carmine as its boss.
    creature('StitchedPatient', 60, legs=0.3),
    creature('WardScreamer', 72),
    creature('HospiceOrderly', 92),
    creature('OrderlyBrann', 104),
    creature('LatticeHost', 74),
    creature('RedWarden', 74),
]


def build(names, preview):
    """Builds every hull model (or those named) into Assets with act1.py's builder."""
    for model in MODELS:
        if model.get('recipe') or (names and model['name'] not in names):
            continue
        act1.build_model(model, preview)


def stands_out(pixels):
    """What stands out from the sheet's near-black background."""
    bright = ndimage.uniform_filter(pixels.max(axis=2).astype(float), 5)
    return bright > 22.0


def view_boxes(pixels, splits=None):
    """The (left, top, right, bottom) box of each view, from left to right."""
    mask = stands_out(pixels)
    if splits:
        edges = [0] + list(splits) + [mask.shape[1]]
        boxes = []
        for left, right in zip(edges[:-1], edges[1:]):
            part = mask[:, left:right]
            cols = np.nonzero(part.sum(axis=0) > 2)[0]
            rows = np.nonzero(part.any(axis=1))[0]
            boxes.append((left + int(cols.min()), int(rows.min()), left + int(cols.max()) + 1, int(rows.max()) + 1))
        return boxes
    used = mask.sum(axis=0) > 2
    runs = []
    x = 0
    width = len(used)
    while x < width:
        if not used[x]:
            x += 1
            continue
        start = x
        while x < width:
            if used[x]:
                x += 1
                continue
            gap_end = x
            while gap_end < width and not used[gap_end]:
                gap_end += 1
            if gap_end - x >= GAP or gap_end == width:
                break
            x = gap_end
        runs.append((start, x))
    boxes = []
    for left, right in runs:
        if right - left < NARROWEST:
            continue
        rows = np.nonzero(mask[:, left:right].any(axis=1))[0]
        top, bottom = int(rows.min()), int(rows.max()) + 1
        boxes.append((max(0, left - PAD), max(0, top - PAD), min(width, right + PAD), min(mask.shape[0], bottom + PAD)))
    return boxes


def import_sheets(directory, names=None):
    CROPS.mkdir(parents=True, exist_ok=True)
    sheets = sorted(p for p in Path(directory).iterdir() if p.suffix.lower() == '.png' and '_Animation' not in p.stem
                    and (not names or p.stem in names))
    thumbs = []
    odd = []
    for path in sheets:
        image = Image.open(path).convert('RGB')
        boxes = view_boxes(np.asarray(image, dtype=np.int32), SPLITS.get(path.stem))
        order = ORDER.get(path.stem, VIEWS)
        if len(boxes) != 3:
            odd.append(f'{path.stem} ({len(boxes)} views)')
        cut = CUT_TOP.get(path.stem, 0.0)
        boxes = [(l, t + round((b - t) * cut), r, b) for l, t, r, b in boxes]
        stem = ALIAS.get(path.stem, path.stem)
        for view, box in zip(order, boxes):
            image.crop(box).save(CROPS / f'{stem}.{view}.png')
        thumb = image.copy()
        draw = ImageDraw.Draw(thumb)
        for k, box in enumerate(boxes):
            draw.rectangle(box, outline=(255, 64, 64), width=4)
            draw.text((box[0] + 8, box[1] + 8), order[k] if k < len(order) else '?', fill=(255, 255, 0))
        draw.text((10, 10), path.stem, fill=(255, 255, 255))
        thumb.thumbnail((720, 260))
        thumbs.append(thumb)
    if names:
        print(f'{len(sheets)} sheets cropped into {CROPS}')
        return
    columns = 3
    rows = (len(thumbs) + columns - 1) // columns
    contact = Image.new('RGB', (columns * 720, rows * 260), (20, 20, 24))
    for i, thumb in enumerate(thumbs):
        contact.paste(thumb, ((i % columns) * 720, (i // columns) * 260))
    CONTACT.parent.mkdir(parents=True, exist_ok=True)
    contact.save(CONTACT)
    print(f'{len(sheets)} sheets cropped into {CROPS}; boxes drawn in {CONTACT}')
    if odd:
        print('Not three views, check these: ' + ', '.join(odd))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--import', dest='source')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('names', nargs='*', help='only these sheets or models')
    args = parser.parse_args()
    if args.source:
        import_sheets(args.source, args.names)
    else:
        build(args.names, args.preview)


if __name__ == '__main__':
    main()
