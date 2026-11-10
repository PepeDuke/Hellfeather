"""Turns the item reference images in Assets/ItemArt into Source/ItemPictures.dk.

Each image is cut out from its background, scaled down to fit the item's sprite
(its bag footprint, 16 pixels per cell) less a one-pixel margin, and every cell
takes the nearest color the item may use. The dark outline of the source art is
dropped at the edges: the game draws a one-pixel border around icons in the UI
shader, so pictures carry only their colors.

The palette is read from ColorOf in Source/ItemArt.dk and the footprints from
HellfeatherItems.Get in Source/Inventory.dk, so neither is repeated here.

    python Tools/ItemArt/convert.py              write Source/ItemPictures.dk
    python Tools/ItemArt/convert.py --preview p  also save a preview PNG
"""
import argparse
import json
import re
from collections import Counter, deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CELL = 16          # pixels per bag cell
MARGIN = 1         # clear pixels kept around a picture for the outline
LINE = 60          # source pixels darker than this are the art's own outline
BACKGROUND = 24    # how far a pixel may stray from the corner color and still be background
SHADOW = 0.55      # greys at least this share of the background's brightness may be shadow
COVERAGE = 0.5     # share of a cell the item must cover to fill it


def palette():
    text = (ROOT / 'Source/ItemArt.dk').read_text(encoding='utf-8')
    found = re.findall(r'if code == (\d+) \{ return 0x([0-9a-fA-F]{6}) \}', text)
    return {chr(int(code)): tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) for code, value in found}


def footprints():
    text = (ROOT / 'Source/Inventory.dk').read_text(encoding='utf-8')
    found = re.findall(r'item == HellfeatherItems\.(\w+) \{ return Make\("[^"]*", "[^"]*", (\d+), (\d+),', text)
    return {name: (int(w), int(h)) for name, w, h in found}


def distance(a, b):
    # "Redmean" weighted RGB distance, close enough to perceived difference here.
    mean = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (2 + mean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - mean) / 256) * db * db


def cut_out(image, shadows=True):
    """True for each item pixel.

    Anything close to the corner color is background, holes included. A drop
    shadow is a grey a little darker than the background: it is flooded away from
    the background, and the art's dark outline stops the flood at the item.
    """
    width, height = image.size
    pixels = image.load()
    corner = pixels[0, 0]
    floor = sum(corner) / 3 * SHADOW

    def plain(rgb):
        return max(abs(rgb[i] - corner[i]) for i in range(3)) < BACKGROUND

    def shade(rgb):
        return max(rgb) - min(rgb) < 14 and sum(rgb) / 3 >= floor

    background = [[plain(pixels[x, y]) for x in range(width)] for y in range(height)]
    queue = deque((x, y) for y in range(height) for x in range(width) if background[y][x])
    seen = [row[:] for row in background]
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if shadows and 0 <= nx < width and 0 <= ny < height and not seen[ny][nx] and shade(pixels[nx, ny]):
                seen[ny][nx] = True
                background[ny][nx] = True
                queue.append((nx, ny))
    return [[not cell for cell in row] for row in background]


def prepare(image, item):
    """Applies an item's crop and rotation from items.json."""
    corner = image.getpixel((0, 0))
    if 'crop_top' in item:
        # Drops the top share of the image, such as an amulet's long chain.
        cut = int(image.size[1] * item['crop_top'])
        image = image.crop((0, cut, image.size[0], image.size[1]))
    if 'rotate' in item:
        image = image.rotate(item['rotate'], resample=Image.NEAREST, expand=True, fillcolor=corner)
    return image


def convert(image, width, height, colors, codes, shadows=True):
    """Rows of codes, width x height, for the picture inside the margin."""
    mask = cut_out(image, shadows)
    pixels = image.load()
    points = [(x, y) for y, row in enumerate(mask) for x, on in enumerate(row) if on]
    x0 = min(p[0] for p in points)
    y0 = min(p[1] for p in points)
    x1 = max(p[0] for p in points) + 1
    y1 = max(p[1] for p in points) + 1
    scale = max((x1 - x0) / width, (y1 - y0) / height)
    left = (width - (x1 - x0) / scale) / 2
    top = (height - (y1 - y0) / scale) / 2
    nearest = {}

    def code_of(rgb):
        if rgb not in nearest:
            nearest[rgb] = min(codes, key=lambda c: distance(rgb, colors[c]))
        return nearest[rgb]

    grid = [['.'] * width for _ in range(height)]
    for row in range(height):
        for column in range(width):
            sx0 = x0 + (column - left) * scale
            sy0 = y0 + (row - top) * scale
            light = []
            dark = 0
            total = 0
            for y in range(int(sy0), int(sy0 + scale + 0.999)):
                for x in range(int(sx0), int(sx0 + scale + 0.999)):
                    total += 1
                    if not (x0 <= x < x1 and y0 <= y < y1) or not mask[y][x]:
                        continue
                    rgb = pixels[x, y]
                    if max(rgb) < LINE:
                        dark += 1
                    else:
                        light.append(rgb)
            filled = len(light) + dark
            if total == 0 or filled / total < COVERAGE:
                continue
            if light and dark <= filled * 0.6:
                # The cell's average color, so a shade spreads evenly instead of speckling.
                mean = tuple(round(sum(p[i] for p in light) / len(light)) for i in range(3))
                grid[row][column] = code_of(mean)
            else:
                grid[row][column] = 'k'
    return smooth(strip_edge_lines(grid))


def smooth(rows, passes=2):
    """A lone cell whose neighbours mostly agree on another color takes theirs."""
    grid = [list(r) for r in rows]
    height, width = len(grid), len(grid[0])
    for _ in range(passes):
        out = [r[:] for r in grid]
        for y in range(height):
            for x in range(width):
                here = grid[y][x]
                if here in '.k':
                    continue
                around = [grid[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                          if 0 <= x + dx < width and 0 <= y + dy < height]
                if here in around:
                    continue
                common = Counter(c for c in around if c not in '.k').most_common(1)
                if common and common[0][1] >= 3:
                    out[y][x] = common[0][0]
        grid = out
    return [''.join(r) for r in grid]


def strip_edge_lines(grid):
    """Outline cells on the silhouette go: the shader draws that border."""
    height, width = len(grid), len(grid[0])

    def empty(x, y):
        return not (0 <= x < width and 0 <= y < height) or grid[y][x] == '.'

    for _ in range(2):
        edge = [(x, y) for y in range(height) for x in range(width)
                if grid[y][x] == 'k' and any(empty(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in edge:
            grid[y][x] = '.'
    return [''.join(row) for row in grid]


def write_duck(pictures, path):
    out = [
        '// Generated by Tools/ItemArt/convert.py from Assets/ItemArt. Do not edit by hand:',
        '// change the images or Tools/ItemArt/items.json and run the converter again.',
        'HellfeatherItemArt',
        '#{',
        '    Draw(HellfeatherItems item, HellfeatherItemPicture& p)',
        '    {',
    ]
    names = list(pictures)
    for i, name in enumerate(names):
        keyword = 'if' if i == 0 else 'else if'
        out.append(f'        {keyword} item == HellfeatherItems.{name} {{ Picture{name}(p) }}')
    out.append('    }')
    for name, rows in pictures.items():
        out.append('')
        out.append(f'    -Picture{name}(HellfeatherItemPicture& p)')
        out.append('    {')
        for i, row in enumerate(rows):
            if row.strip('.'):
                out.append(f'        p.Row({i}, "{row}")')
        out.append('    }')
    out.append('}')
    path.write_text('\n'.join(out) + '\n', encoding='utf-8', newline='\r\n')


def save_preview(pictures, colors, path, zoom=4, outline=(16, 13, 11)):
    widths = [len(rows[0]) for rows in pictures.values()]
    tile = max(widths)
    tall = max(len(rows) for rows in pictures.values())
    columns = 8
    count = len(pictures)
    sheet = Image.new('RGB', (columns * (tile + 4) * zoom, ((count + columns - 1) // columns) * (tall + 4) * zoom), (52, 48, 43))
    for index, rows in enumerate(pictures.values()):
        bx = (index % columns) * (tile + 4) + 2
        by = (index // columns) * (tall + 4) + 2
        h, w = len(rows), len(rows[0])

        def solid(x, y):
            return 0 <= x < w and 0 <= y < h and rows[y][x] != '.'

        for y in range(h):
            for x in range(w):
                if solid(x, y):
                    color = colors[rows[y][x]]
                elif any(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    color = outline  # what the shader adds
                else:
                    continue
                for yy in range(zoom):
                    for xx in range(zoom):
                        sheet.putpixel(((bx + x) * zoom + xx, (by + y) * zoom + yy), color)
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--preview', help='also save a preview PNG here')
    args = parser.parse_args()
    config = json.loads((Path(__file__).parent / 'items.json').read_text(encoding='utf-8'))
    colors = palette()
    sizes = footprints()
    pictures = {}
    for name, item in config['items'].items():
        image = prepare(Image.open(ROOT / 'Assets/ItemArt' / f'{name}.png').convert('RGB'), item)
        cells_wide, cells_tall = sizes[name]
        width, height = cells_wide * CELL - 2 * MARGIN, cells_tall * CELL - 2 * MARGIN
        codes = [c for c in item.get('colors', ''.join(colors)) if c in colors]
        # Pale steel touching the background can pass for shadow; such items set "shadow": false.
        rows = convert(image, width, height, colors, codes, item.get('shadow', True))
        pad = '.' * MARGIN
        pictures[name] = [pad * (width + 2)] * MARGIN + [pad + r + pad for r in rows] + [pad * (width + 2)] * MARGIN
    write_duck(pictures, ROOT / 'Source/ItemPictures.dk')
    if args.preview:
        save_preview(pictures, colors, args.preview)


if __name__ == '__main__':
    main()
