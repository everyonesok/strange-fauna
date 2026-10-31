"""
cut_parts.py: cut creature parts out of Krea sheets into transparent PNGs.

Each part on a sheet is an inked drawing on a near-white background. For each
part we:
  1. mark every pixel that isn't near-white as "drawing"
  2. flood out from a seed point inside the part to grab only that connected
     piece (like a magic wand), leaving neighbouring parts behind
  3. fill holes inside it, so white details (eye highlights) stay opaque
  4. soften the cut edge slightly so it isn't jagged

Usage (from the project root):
    python3 tools/cut_parts.py
Reads from references/separations/ (local only) and writes to public/creatures/.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "references" / "separations"

# A pixel counts as "drawing" if it's darker than this, or noticeably coloured
MAX_LUM = 225
MIN_CHROMA = 15

# name: (source image, crop box (left, top, right, bottom), seed point inside the part[, resize])
# Coordinates are in the source image's own pixels. The optional resize shrinks
# parts Krea drew far larger than they're used (the legs end up at ~30% size).
CREATURES = {
    "rabbit-bat-snake": {
        "torso":       ("rabbit-bat-snake-torso-subtractive.png", (560, 650, 1900, 1400), (1184, 888)),
        "head":        ("rabbit-bat-snake-parts-v2.png",          (1190, 59, 1616, 645),  (1362, 497)),
        "head-blink":  ("rabbit-bat-snake-parts-v2.png",          (1800, 59, 2238, 645),  (1965, 497)),
        "wing-open":   ("rabbit-bat-snake-parts-v2.png",          (112, 89, 1066, 657),   (592, 296)),
        "wing-folded": ("rabbit-bat-snake-parts-v2.png",          (1498, 663, 1782, 1302), (1658, 1006)),
        "tail":        ("rabbit-bat-snake-parts-v1.png",          (95, 1373, 1438, 1598), (710, 1480)),
        "front-leg":   ("rabbit-bat-snake-frontleg.png",          None,                   (888, 710), 0.5),
        "hind-leg":    ("rabbit-bat-snake-hindleg.png",           None,                   (829, 829), 0.5),
    },
}


def is_drawing(rgb):
    r, g, b = rgb
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return lum < MAX_LUM or max(r, g, b) - min(r, g, b) > MIN_CHROMA


def cut(src_path, box, seed):
    im = Image.open(src_path).convert("RGB")
    if box is None:
        box = (0, 0, im.width, im.height)
    pad = 4  # empty margin so the outside is always connected around the part
    crop = im.crop(box)
    sx, sy = seed[0] - box[0] + pad, seed[1] - box[1] + pad

    # 1. drawing mask: 255 = drawing, 0 = background
    mask = Image.new("L", (crop.width + 2 * pad, crop.height + 2 * pad), 0)
    px, cp = mask.load(), crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            if is_drawing(cp[x, y]):
                px[x + pad, y + pad] = 255
    if px[sx, sy] != 255:
        raise SystemExit(f"seed {seed} in {src_path.name} is not on the drawing")

    # 2. grab the connected piece under the seed (marked 128)
    ImageDraw.floodfill(mask, (sx, sy), 128)
    part = mask.point(lambda v: 255 if v == 128 else 0)

    # 3. outside = everything reachable from the corner without crossing the part;
    #    whatever is left (the part plus enclosed holes) becomes opaque
    ImageDraw.floodfill(part, (0, 0), 64)
    alpha = part.point(lambda v: 0 if v == 64 else 255)

    # 4. soften the edge a touch
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))

    out = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
    out.paste(crop, (pad, pad))
    out.putalpha(alpha)
    bbox = alpha.getbbox()
    # Where the part's top-left corner sat in its source image (used to place
    # parts that were cut from the original drawing's frame, like the torso)
    origin = (box[0] - pad + bbox[0], box[1] - pad + bbox[1])
    return out.crop(bbox), origin


if __name__ == "__main__":
    for creature, parts in CREATURES.items():
        dest = ROOT / "public" / "creatures" / creature
        dest.mkdir(parents=True, exist_ok=True)
        origins = {}
        for name, (src, box, seed, *rest) in parts.items():
            img, origin = cut(SRC / src, box, seed)
            resize = rest[0] if rest else 1
            if resize != 1:
                img = img.resize((round(img.width * resize), round(img.height * resize)), Image.LANCZOS)
            img.save(dest / f"{name}.png", optimize=True)
            origins[name] = {"source": src, "origin": origin, "resize": resize}
            print(f"{creature}/{name}.png  {img.width}x{img.height}  from {origin}")
        (dest / "cut-origins.json").write_text(json.dumps(origins, indent=2))
