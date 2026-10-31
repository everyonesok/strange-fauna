"""
onion_skin.py: light-table check of a creature's rig against its original drawing.

The original is printed in red and the assembled rig in cyan. Where they line
up, the lines merge into dark grey; where they don't, you see doubled red and
cyan lines. Optionally show only some parts, to check them one at a time.

Usage (from the project root):
    python3 tools/onion_skin.py rabbit-bat-snake <out.png> [part names...]
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_rig import ROOT, place  # noqa: E402


def onion(creature, only=None):
    folder = ROOT / "public" / "creatures" / creature
    rig = json.loads((folder / "rig.json").read_text())
    frame = tuple(rig["frame"])
    rigged = Image.new("RGBA", frame, (255, 255, 255, 255))
    for part in rig["parts"]:
        if not only or part["name"] in only:
            rigged = Image.alpha_composite(rigged, place(part, folder, frame))
    original = Image.open(ROOT / "references" / f"{creature}.png").convert("RGB").resize(frame)
    o = ImageOps.autocontrast(original.convert("L"))
    r = ImageOps.autocontrast(rigged.convert("L"))
    # Red channel from the rig, green and blue from the original:
    #   dark only in the original -> red;  dark only in the rig -> cyan;
    #   dark in both -> dark grey (they line up)
    return Image.merge("RGB", (r, o, o))


if __name__ == "__main__":
    creature, out = sys.argv[1], sys.argv[2]
    onion(creature, set(sys.argv[3:]) or None).save(out)
    print("saved", out)
