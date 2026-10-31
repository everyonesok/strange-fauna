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
Several fills can go into one part, and one edit can remove several parts:
    --fill=torso:near-front-leg+near-hind-leg:<original-without-near-legs.png>
Removing a near leg uncovers the far leg behind it, which the fill would wrongly
glue onto the body. Add a colour map of the edit, and only the part's own
pixels in it are taken:
    --fill=torso:near-hind-leg:<edit.png>:<edit-map.png>

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
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
FRAME = (2368, 1776)  # 2x the original drawing, same as rig.json
HALF = (FRAME[0] // 2, FRAME[1] // 2)
OVERLAP = 25          # px a part reaches under the parts in front of it
# Far-side legs swing their whole thigh behind the body, so they reach deeper
DEEP_OVERLAP = 60
SEAM = 6              # px of a part's own edge, along the parts in front, repainted too
# A pixel counts as drawing if it's darker than MAX_LUM or more colourful
# than MIN_CHROMA. A ground shadow is light and nearly grey (brightness
# 200-230, colourfulness under 9), so these leave it out; everything inside
# the ink outline is kept anyway (holes get filled).
MAX_LUM = 195
MIN_CHROMA = 12

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
    # Darker than MAX_LUM, or more colourful than MIN_CHROMA, tested on whole
    # images at once (fast)
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


def layer(i, source, sil, masks, fills=(), deep=False, skip=None):
    """Cut part number i out of the source drawing, as a cropped RGBA image
    plus its bounding box in the frame.
    fills: (covering parts' mask, edit image) pairs, to paint in what they hide.
    skip: parts in front it shouldn't reach under (a far leg under a near leg:
    the near leg steps away, and the reach would show as a stray wedge)."""
    # reach under everything drawn in front of this part
    front = Image.new("L", HALF, 0)
    for m in masks[i + 1:]:
        front = ImageChops.lighter(front, m)
    grown = masks[i]
    overlap = DEEP_OVERLAP if deep else OVERLAP
    for _ in range(overlap // 2):   # many small steps are far faster than one big one
        grown = grown.filter(ImageFilter.MaxFilter(3))
    reach = ImageChops.multiply(grown, front if skip is None else ImageChops.subtract(front, skip))
    # round off the reach's blocky edge (growing in square steps leaves corners)
    reach = reach.filter(ImageFilter.GaussianBlur(3)).point(lambda v: 255 if v > 127 else 0)
    # keep only what's still attached to the part: reaching across a gap can
    # grab loose bits of a neighbour (e.g. a sliver of the other leg's outline)
    whole = main_regions(ImageChops.multiply(ImageChops.lighter(masks[i], reach), sil.resize(HALF)))
    reach = ImageChops.multiply(reach, whole)
    mask = ImageChops.lighter(masks[i], reach)
    if skip is not None and skip.getbbox():
        # where the part was cut off by a skipped neighbour, round the cut edge
        # (it shows once the neighbour steps away); the rest stays crisp
        zone = skip
        for _ in range(4):
            zone = zone.filter(ImageFilter.MaxFilter(3))
        smooth = mask.filter(ImageFilter.GaussianBlur(12)).point(lambda v: 255 if v > 127 else 0)
        mask.paste(smooth, (0, 0), zone)
    mask = mask.resize(FRAME, Image.BILINEAR)
    alpha = mask.point(lambda v: 255 if v > 127 else 0).filter(ImageFilter.GaussianBlur(0.6))
    alpha = ImageChops.multiply(alpha, sil)
    part = source.convert("RGBA")

    # The drawing has nothing of this part under the parts in front, only
    # THEIR pixels (and the ink outline between them). If those stayed on
    # this part, they'd swing with it as a visible seam when it moves. So the
    # tucked-under area, and this part's last few pixels along the seam, are
    # painted in this part's own average colour near the seam instead.
    near_front = front
    for _ in range(SEAM // 2):
        near_front = near_front.filter(ImageFilter.MaxFilter(3))
    hidden = ImageChops.lighter(reach, ImageChops.multiply(masks[i], near_front))
    sample = ImageChops.subtract(masks[i], near_front)        # own pixels just inside the seam
    for _ in range(4):
        near_front = near_front.filter(ImageFilter.MaxFilter(3))
    sample = ImageChops.multiply(sample, near_front)
    if not sample.getbbox():
        sample = masks[i]
    colour = tuple(round(v) for v in ImageStat.Stat(source.resize(HALF), sample).mean)
    part.paste(colour + (255,), (0, 0), hidden.resize(FRAME, Image.BILINEAR))
    for cover, edit_path, own, front_e in fills:
        edit = Image.open(edit_path).convert("RGB").resize(FRAME, Image.LANCZOS)
        # the covering part's area, grown a little to tuck under its edge
        area = cover
        for _ in range(3):
            area = area.filter(ImageFilter.MaxFilter(3))
        area = area.resize(FRAME, Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
        # inside that area: the edit's pixels, wherever the edit shows creature.
        # With a map of the edit (own = this part's pixels in it), only this
        # part's: removing a near leg uncovers the far one, which isn't body.
        if own is None:
            alpha.paste(ImageChops.multiply(silhouette(edit), area).filter(ImageFilter.GaussianBlur(0.6)), (0, 0), area)
            part.paste(edit, (0, 0), area.filter(ImageFilter.GaussianBlur(4)))  # soft seam
            continue
        # ...and the part still tucks under whatever the edit draws in front of
        # it (front_e), but no longer under the removed part, which isn't there
        tucked = ImageChops.multiply(alpha, front_e)
        alpha.paste(ImageChops.lighter(own, tucked).filter(ImageFilter.GaussianBlur(0.6)), (0, 0), area)
        part.paste(edit, (0, 0), ImageChops.multiply(own, area).filter(ImageFilter.GaussianBlur(4)))
    part.putalpha(alpha)
    bbox = alpha.getbbox()
    return part.crop(bbox), bbox


def cut(creature, map_path, preview_dir=None, fills=None, variants=None):
    """fills: {part: [(covering parts, edit image), ...]}. The edit image is
    the original with the covering parts removed by AI; inside the area they
    covered, the hidden part takes the edit's pixels (e.g. the back under the
    wing). Covering parts are joined with "+", e.g. "near-front-leg+near-hind-leg".
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
        part_fills = []
        for covers, edit_path, edit_map in (fills or {}).get(name, []):
            area = Image.new("L", HALF, 0)
            for cover in covers.split("+"):
                area = ImageChops.lighter(area, masks[names.index(cover)])
            own = front_e = None
            if edit_map:
                edit = Image.open(edit_path).convert("RGB").resize(FRAME, Image.LANCZOS)
                e_sil, e_masks = split(edit, edit_map, palette)
                own = ImageChops.multiply(e_masks[i].resize(FRAME, Image.BILINEAR), e_sil)
                front_e = Image.new("L", HALF, 0)
                for m in e_masks[i + 1:]:
                    front_e = ImageChops.lighter(front_e, m)
                front_e = front_e.resize(FRAME, Image.BILINEAR)
            part_fills.append((area, edit_path, own, front_e))
        # far legs tuck deep under the body, but not under the legs in front
        far = name.startswith("far-")
        skip = Image.new("L", HALF, 0)
        for j in range(i + 1, len(names)):
            if far and names[j].endswith("-leg"):
                skip = ImageChops.lighter(skip, masks[j])
        save(name, *layer(i, original, sil, masks, part_fills, deep=far, skip=skip))

    for name, (part, edit_path, edit_map) in (variants or {}).items():
        edit = Image.open(edit_path).convert("RGB").resize(FRAME, Image.LANCZOS)
        v_sil, v_masks = split(edit, edit_map, palette) if edit_map else (sil, masks)
        save(name, *layer(names.index(part), edit, v_sil, v_masks, deep=part.startswith("far-")))

    if preview_dir:
        # every pixel tinted by its label, to eyeball the split
        tint = Image.new("RGB", HALF, "white")
        for (_, colour), m in zip(palette, masks):
            tint.paste(colour, (0, 0), m)
        Image.blend(original.resize(HALF), tint, 0.45).save(Path(preview_dir) / f"{creature}-labels.png")
    (dest / "cut-origins.json").write_text(json.dumps(origins, indent=2))


if __name__ == "__main__":
    # --fill=part:covering-part:edit.png[:edit-map.png] (repeatable)
    # --variant=name:part:edit.png[:edit-map.png]       (repeatable)
    fills, variants = {}, {}
    for a in sys.argv:
        if a.startswith("--fill="):
            part, cover, path, *edit_map = a[len("--fill="):].split(":")
            fills.setdefault(part, []).append((cover, path, edit_map[0] if edit_map else None))
        if a.startswith("--variant="):
            name, part, path, *edit_map = a[len("--variant="):].split(":")
            variants[name] = (part, path, edit_map[0] if edit_map else None)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cut(args[0], args[1], args[2] if len(args) > 2 else None, fills, variants)
