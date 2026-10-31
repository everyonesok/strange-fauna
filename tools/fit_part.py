"""
fit_part.py: line a rig part up with the original drawing by measurement.

Uses "chamfer matching":
  1. find the edges (outlines, bones, fur lines) in the original drawing
  2. build a distance map: each pixel stores how far it is from the nearest edge
  3. take the part's own edges, place them with the rig's position, scale and
     rotation, and look up how far each one lands from an original edge
  4. nudge position / scale / rotation (and optionally stretch) to make that
     distance as small as possible, from big steps down to fine ones

Distances are capped, so part edges with no partner in the original (like a
cut neck that's hidden under the head) can't drag the fit around.

Usage (from the project root):
    python3 tools/fit_part.py rabbit-bat-snake torso [--stretch] [--below=0.45] [--write]
Without --write it only reports the fit; with --write it updates rig.json.
--below=F fits using only the lowest (1 - F) of the part, for parts whose top
is hidden in the original (the rabbit's back is under its wing).
"""
import json
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_rig import ROOT, scale_xy  # noqa: E402

DOWN = 4        # work at 1/4 resolution for speed
CAP = 12.0      # max distance (in 1/4-res px) any single edge point can cost
POINTS = 1500   # how many part edge points to sample


def edges(gray, threshold=40):
    """Edge pixels of a greyscale image, as a 0/255 mask."""
    e = gray.filter(ImageFilter.FIND_EDGES)
    return e.point(lambda v: 255 if v > threshold else 0)


def distance_map(mask):
    """Two-pass chamfer distance transform: distance to the nearest edge pixel."""
    w, h = mask.size
    m = mask.load()
    big = 1e9
    d = [[0.0 if m[x, y] else big for x in range(w)] for y in range(h)]
    r2 = math.sqrt(2)
    for y in range(h):
        row, up = d[y], d[y - 1] if y else None
        for x in range(w):
            v = row[x]
            if x: v = min(v, row[x - 1] + 1)
            if up:
                v = min(v, up[x] + 1)
                if x: v = min(v, up[x - 1] + r2)
                if x < w - 1: v = min(v, up[x + 1] + r2)
            row[x] = v
    for y in range(h - 1, -1, -1):
        row, dn = d[y], d[y + 1] if y < h - 1 else None
        for x in range(w - 1, -1, -1):
            v = row[x]
            if x < w - 1: v = min(v, row[x + 1] + 1)
            if dn:
                v = min(v, dn[x] + 1)
                if x < w - 1: v = min(v, dn[x + 1] + r2)
                if x: v = min(v, dn[x - 1] + r2)
            row[x] = v
    return d


def part_edge_points(folder, part, below=0.0):
    """Edge points of a part. below = only use the part's lower portion (0..1),
    for parts whose upper edges are hidden in the original (a back under a wing)."""
    img = Image.open(folder / part["image"]).convert("RGBA")
    if part.get("flipX"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    flat = Image.new("RGB", img.size, "white")
    flat.paste(img, (0, 0), img)
    mask = edges(ImageOps.autocontrast(flat.convert("L")))
    m = mask.load()
    top = int(img.height * below)
    pts = [(x, y) for y in range(top, img.height) for x in range(img.width) if m[x, y]]
    random.seed(1)
    return random.sample(pts, min(POINTS, len(pts)))


def cost(params, pts, pivot, dist):
    ax, ay, sx, sy, rot = params
    c, n = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    h, w = len(dist), len(dist[0])
    total = 0.0
    for x, y in pts:
        dx, dy = (x - pivot[0]) * sx, (y - pivot[1]) * sy
        fx = (ax + c * dx - n * dy) / DOWN
        fy = (ay + n * dx + c * dy) / DOWN
        ix, iy = int(fx + 0.5), int(fy + 0.5)
        total += min(dist[iy][ix], CAP) if 0 <= ix < w and 0 <= iy < h else CAP
    return total / len(pts)


def fit(params, pts, pivot, dist, stretch):
    steps = [24.0, 24.0, 0.04, 0.04, 2.0]  # at x/y, scale x/y, rotation
    best = cost(params, pts, pivot, dist)
    while steps[0] > 0.5:
        improved = True
        while improved:
            improved = False
            for i in range(5):
                for sign in (1, -1):
                    trial = list(params)
                    trial[i] += sign * steps[i]
                    if not stretch and i in (2, 3):
                        trial[2] = trial[3] = params[i] + sign * steps[i]
                    c = cost(trial, pts, pivot, dist)
                    if c < best - 1e-6:
                        best, params, improved = c, trial, True
        steps = [s / 2 for s in steps]
    return params, best


if __name__ == "__main__":
    creature, name = sys.argv[1], sys.argv[2]
    stretch, write = "--stretch" in sys.argv, "--write" in sys.argv
    folder = ROOT / "public" / "creatures" / creature
    rig = json.loads((folder / "rig.json").read_text())
    part = next(p for p in rig["parts"] if p["name"] == name)

    original = Image.open(ROOT / "references" / f"{creature}.png").convert("L").resize(tuple(rig["frame"]))
    small = ImageOps.autocontrast(original).resize((rig["frame"][0] // DOWN, rig["frame"][1] // DOWN))
    dist = distance_map(edges(small))
    below = next((float(a.split("=")[1]) for a in sys.argv if a.startswith("--below=")), 0.0)
    pts = part_edge_points(folder, part, below)

    sx, sy = scale_xy(part)
    start = [part["at"][0], part["at"][1], sx, sy, part.get("rotate", 0)]
    before = cost(start, pts, part["pivot"], dist)
    params, after = fit(start, pts, part["pivot"], dist, stretch)
    ax, ay, sx, sy, rot = params
    print(f"{name}: average edge distance {before * DOWN:.1f}px -> {after * DOWN:.1f}px")
    print(f"  at [{ax:.0f}, {ay:.0f}]  scale [{sx:.3f}, {sy:.3f}]  rotate {rot:.1f}")
    if write:
        part["at"] = [round(ax), round(ay)]
        part["scale"] = [round(sx, 3), round(sy, 3)] if stretch else round(sx, 3)
        part["rotate"] = round(rot, 1)
        text = json.dumps(rig, indent=2)
        (folder / "rig.json").write_text(text + "\n")
        print("  written to rig.json")
