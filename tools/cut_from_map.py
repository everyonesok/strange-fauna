"""
cut_from_map.py: cut creature parts straight out of the ORIGINAL drawing,
using an AI-made colour map to say which pixel belongs to which part.

Why: parts that an AI redraws never quite match the original (different
proportions, shifted). Cutting from the original itself guarantees the
assembled rest pose IS the drawing. The AI only has to do the easy job of
colouring each region, not redrawing it.

Steps:
  1. silhouette: every pixel of the original that's part of the creature
  2. label each silhouette pixel with the nearest colour in the map
     (pixels the map left white, like line art at a border, take the label
     of their nearest labelled neighbour)
  3. for each part, keep its pixels, plus a small overlap tucked under the
     parts drawn in front of it, so joints don't open gaps when they rotate
  4. save each part as a transparent PNG, and print where its top-left corner
     sits in the frame (for rig.json)

Hidden areas (the back under the wing) can't be cut, because the drawing
doesn't show them. For those, pass an AI edit of the original with the
covering part removed; only the pixels it covered are taken from the edit:
    --fill=torso:wing:<original-without-wing.png>

Swap-in versions of a part (a blink, a folded wing) are cut from an AI edit of
the original. A blink keeps the head's outline, so it reuses the main map; a
folded wing has a new outline, so it needs a colour map of the edit too:
    --variant=head-blink:head:<blink-edit.png>
    --variant=wing-folded:wing:<folded-edit.png>:<folded-edit-map.png>

Usage (from the project root):
    python3 tools/cut_from_map.py rabbit-bat-snake <map.png> [<preview-dir>] [--fill=...] [--variant=...]
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cut_parts import MAX_LUM, MIN_CHROMA  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FRAME = (2368, 1776)  # 2x the original drawing, same as rig.json
HALF = (FRAME[0] // 2, FRAME[1] // 2)
OVERLAP = 25          # px a part reaches under the parts in front of it

# Map colour for each part, listed back to front (the order they're drawn).
# These are the colours the model actually painted (sampled from the map),
# which drift a little from the ones asked for.
PARTS = {
    "rabbit-bat-snake": [
        ("far-hind-leg",   (118, 0, 118)),   # purple
        ("far-front-leg",  (0, 255, 255)),   # cyan
        ("tail",           (0, 122, 1)),     # green
        ("torso",          (255, 255, 0)),   # yellow
        ("near-hind-leg",  (254, 164, 1)),   # orange
        ("near-front-leg", (255, 0, 255)),   # magenta
        ("wing",           (0, 0, 255)),     # blue
        ("head",           (255, 0, 0)),     # red
    ],
}


def silhouette(original):
    """The creature's pixels: the connected 'drawing' blob, holes filled.
    The pale ground shadow is too light to count as drawing."""
    # Same test as cut_parts.is_drawing, done on whole images at once (fast):
    # darker than MAX_LUM, or more colourful than MIN_CHROMA
    w, h = original.size
    r, g, b = original.split()
    dark = original.convert("L").point(lambda v: 255 if v < MAX_LUM else 0)
    chroma = ImageChops.subtract(ImageChops.lighter(ImageChops.lighter(r, g), b),
                                 ImageChops.darker(ImageChops.darker(r, g), b))
    colourful = chroma.point(lambda v: 255 if v > MIN_CHROMA else 0)
    mask = Image.new("L", (w + 2, h + 2), 0)
    mask.paste(ImageChops.lighter(dark, colourful), (1, 1))
    ImageDraw.floodfill(mask, (0, 0), 64)      # outside = reachable from the corner
    mask = mask.point(lambda v: 0 if v == 64 else 255)
    return mask.crop((1, 1, w + 1, h + 1))


def main_regions(mask, keep=0.1):
    """Drop stray specks: keep only the connected blobs at least `keep` times
    the size of the biggest one. (Soft edges between two map colours can
    blend into a third part's colour, leaving thin slivers of it.)"""
    work = mask.point(lambda v: 255 if v else 0)
    blobs = []
    while True:
        bbox = work.getbbox()
        if not bbox:
            break
        top = work.crop((bbox[0], bbox[1], bbox[2], bbox[1] + 1)).getbbox()
        seed = (bbox[0] + top[0], bbox[1])
        ImageDraw.floodfill(work, seed, 128)           # this blob -> 128
        blob = work.point(lambda v: 255 if v == 128 else 0)
        blobs.append((blob.histogram()[255], blob))
        work = work.point(lambda v: 0 if v == 128 else v)
    if not blobs:
        return mask
    biggest = max(n for n, _ in blobs)
    out = Image.new("L", mask.size, 0)
    for n, blob in blobs:
        if n >= keep * biggest:
            out = ImageChops.lighter(out, blob)
    return out


def label_masks(seg, sil, palette):
    """One 0/255 mask per part. Map pixels are matched to the nearest palette
    colour; near-white or unclear pixels are filled in from their neighbours."""
    # Snap every map pixel to its nearest colour in a palette of the part
    # colours plus "don't know" colours (white, grey, black): those pixels are
    # left for their neighbours to fill.
    unsure = [(255, 255, 255), (128, 128, 128), (0, 0, 0)]
    colours = [c for _, c in palette] + unsure
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in colours for v in c] + [0] * 3 * (256 - len(colours)))
    quantized = seg.quantize(palette=pal, dither=Image.Dither.NONE)
    # read the raw palette numbers (0, 1, 2...) as a plain greyscale image
    index = Image.frombytes("L", quantized.size, quantized.tobytes())
    masks = [main_regions(ImageChops.multiply(index.point(lambda v, i=i: 255 if v == i else 0), sil))
             for i in range(len(palette))]
    # grow labels outwards into unlabelled silhouette pixels, a few px per round
    for _ in range(150):
        taken = masks[0]
        for m in masks[1:]:
            taken = ImageChops.lighter(taken, m)
        free = ImageChops.subtract(sil, taken)
        if not free.getbbox():
            break
        grown = [ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), free) for m in masks]
        for i, g in enumerate(grown):
            # don't let two labels claim the same pixel in one round
            for j in range(i):
                g = ImageChops.subtract(g, grown[j])
            masks[i] = ImageChops.lighter(masks[i], g)
    return masks


def split(source, map_path, palette):
    """The source drawing's silhouette, and one mask per part (at half size)."""
    sil = silhouette(source)
    # Sorting pixels into parts happens at half size (the drawing's own
    # resolution), which is 4x faster; the masks are scaled back up after.
    seg = Image.open(map_path).convert("RGB").resize(HALF, Image.NEAREST)
    # Wherever the map is background (white), it's not creature, even if the
    # drawing is shaded there: this drops the ground shadow and the gaps
    # between the legs that the shadow encloses. Grown a few px so the
    # drawing's outer ink line stays in.
    r, g, b = seg.split()
    fg = ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v < 200 else 0)
    for _ in range(4):
        fg = fg.filter(ImageFilter.MaxFilter(3))
    sil = ImageChops.multiply(sil, fg.resize(FRAME, Image.NEAREST))
    return sil, label_masks(seg, sil.resize(HALF, Image.NEAREST), palette)


def layer(i, source, sil, masks, fill=None):
    """Cut part number i out of the source drawing, as a cropped RGBA image
    plus its bounding box in the frame.
    fill: (covering part's mask, edit image) to paint in what that part hides."""
    # reach under everything drawn in front of this part
    front = Image.new("L", HALF, 0)
    for m in masks[i + 1:]:
        front = ImageChops.lighter(front, m)
    grown = masks[i]
    for _ in range(OVERLAP // 2):   # many small steps are far faster than one big one
        grown = grown.filter(ImageFilter.MaxFilter(3))
    reach = ImageChops.multiply(grown, front)
    mask = ImageChops.lighter(masks[i], reach).resize(FRAME, Image.BILINEAR)
    alpha = mask.point(lambda v: 255 if v > 127 else 0).filter(ImageFilter.GaussianBlur(0.6))
    alpha = ImageChops.multiply(alpha, sil)
    part = source.convert("RGBA")
    if fill:
        cover, edit_path = fill
        edit = Image.open(edit_path).convert("RGB").resize(FRAME, Image.LANCZOS)
        # the covering part's area, grown a little to tuck under its edge
        area = cover
        for _ in range(3):
            area = area.filter(ImageFilter.MaxFilter(3))
        area = area.resize(FRAME, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
        # inside that area: the edit's pixels, wherever the edit shows creature
        alpha.paste(ImageChops.multiply(silhouette(edit), area).filter(ImageFilter.GaussianBlur(0.6)), (0, 0), area)
        part.paste(edit, (0, 0), area.filter(ImageFilter.GaussianBlur(4)))  # soft seam
    part.putalpha(alpha)
    bbox = alpha.getbbox()
    return part.crop(bbox), bbox


def cut(creature, map_path, preview_dir=None, fills=None, variants=None):
    """fills: {part: (covering part, edit image)}. The edit image is the
    original with the covering part removed by AI; inside the area that part
    covered, the hidden part takes the edit's pixels (e.g. the back under the wing).
    variants: {name: (part, edit image, edit's map or None)}. A swap-in version
    of a part (a blink, a folded wing) cut from an AI edit of the original. With
    no map of its own, the part keeps its original outline (fine for a blink)."""
    palette = PARTS[creature]
    names = [n for n, _ in palette]
    original = Image.open(ROOT / "references" / f"{creature}.png").convert("RGB").resize(FRAME, Image.LANCZOS)
    sil, masks = split(original, map_path, palette)

    dest = ROOT / "public" / "creatures" / creature
    origins = {}

    def save(name, img, bbox):
        img.save(dest / f"{name}.png", optimize=True)
        origins[name] = {"origin": bbox[:2], "size": (bbox[2] - bbox[0], bbox[3] - bbox[1])}
        print(f"{name:15} at {bbox[:2]}  size {origins[name]['size']}")

    for i, name in enumerate(names):
        fill = None
        if fills and name in fills:
            cover, edit_path = fills[name]
            fill = (masks[names.index(cover)], edit_path)
        save(name, *layer(i, original, sil, masks, fill))

    for name, (part, edit_path, edit_map) in (variants or {}).items():
        edit = Image.open(edit_path).convert("RGB").resize(FRAME, Image.LANCZOS)
        v_sil, v_masks = split(edit, edit_map, palette) if edit_map else (sil, masks)
        save(name, *layer(names.index(part), edit, v_sil, v_masks))

    if preview_dir:
        # every pixel tinted by its label, to eyeball the split
        tint = Image.new("RGB", HALF, "white")
        for (_, colour), m in zip(palette, masks):
            tint.paste(colour, (0, 0), m)
        Image.blend(original.resize(HALF), tint, 0.45).save(Path(preview_dir) / f"{creature}-labels.png")
    (dest / "cut-origins.json").write_text(json.dumps(origins, indent=2))


if __name__ == "__main__":
    # --fill=part:covering-part:edit.png        (repeatable)
    # --variant=name:part:edit.png[:edit-map.png] (repeatable)
    fills, variants = {}, {}
    for a in sys.argv:
        if a.startswith("--fill="):
            part, cover, path = a[len("--fill="):].split(":", 2)
            fills[part] = (cover, path)
        if a.startswith("--variant="):
            name, part, path, *edit_map = a[len("--variant="):].split(":")
            variants[name] = (part, path, edit_map[0] if edit_map else None)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cut(args[0], args[1], args[2] if len(args) > 2 else None, fills, variants)
