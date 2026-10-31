"""
preview_rig.py: draw a creature's rig.json as a still image, to check the fit.

Saves <out>/<creature>-rig.png with two panels:
  left:  the assembled creature on its own
  right: the assembly over a faded copy of the original drawing (to compare)

Usage (from the project root):
    python3 tools/preview_rig.py rabbit-bat-snake <out-dir>
"""
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent


def scale_xy(part):
    """A part's scale: one number (same both ways) or [across, down] for a stretch."""
    s = part["scale"]
    return (s, s) if isinstance(s, (int, float)) else (s[0], s[1])


def place(part, folder, frame):
    """Scale and rotate one part around its pivot, onto a frame-sized canvas."""
    img = Image.open(folder / part["image"]).convert("RGBA")
    if part.get("flipX"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if part.get("shade", 1) != 1:
        rgb = ImageEnhance.Brightness(img.convert("RGB")).enhance(part["shade"])
        rgb.putalpha(img.getchannel("A"))
        img = rgb
    sx, sy = scale_xy(part)
    th = math.radians(part.get("rotate", 0))
    (px, py), (ax, ay) = part["pivot"], part["at"]
    c, n = math.cos(th), math.sin(th)
    # Inverse mapping (frame -> part image): p = pivot + S^-1 * R(-rotate) * (P - at)
    a, b = c / sx, n / sx
    d, e = -n / sy, c / sy
    data = (a, b, px - (a * ax + b * ay), d, e, py - (d * ax + e * ay))
    return img.transform(frame, Image.AFFINE, data, resample=Image.BICUBIC)


def render(creature):
    folder = ROOT / "public" / "creatures" / creature
    rig = json.loads((folder / "rig.json").read_text())
    frame = tuple(rig["frame"])
    out = Image.new("RGBA", frame, (0, 0, 0, 0))
    for part in rig["parts"]:
        out = Image.alpha_composite(out, place(part, folder, frame))
    return out, frame


if __name__ == "__main__":
    creature, out_dir = sys.argv[1], Path(sys.argv[2])
    assembled, frame = render(creature)
    original = Image.open(ROOT / "references" / f"{creature}.png").convert("RGBA").resize(frame)
    faded = Image.blend(Image.new("RGBA", frame, "white"), original, 0.35)
    panel = Image.new("RGBA", (frame[0] * 2, frame[1]), "white")
    panel.alpha_composite(Image.alpha_composite(Image.new("RGBA", frame, (238, 236, 242, 255)), assembled), (0, 0))
    panel.alpha_composite(Image.alpha_composite(faded, assembled), (frame[0], 0))
    panel.convert("RGB").resize((frame[0], frame[1] // 2)).save(out_dir / f"{creature}-rig.png")
    print("saved", out_dir / f"{creature}-rig.png")
