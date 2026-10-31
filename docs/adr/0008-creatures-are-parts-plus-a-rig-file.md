# 0008. Creatures are cut-out parts plus a rig file

- **Status:** Accepted
- **Date:** 2026-10-30

## Context

With 2D cel animation chosen ([0007](0007-embrace-2d-cel-animation.md)), each
creature arrives as separately generated parts (head, torso, legs, tail,
wings), each at its own scale. Something has to say how they fit together,
and the same description must drive both quick still previews and the live
animation. Creatures will also swap parts with each other when morphing.

## Decision

Each creature is a folder in `public/creatures/<name>/` holding:

- **Transparent part PNGs**, cut from Krea sheets by `tools/cut_parts.py`.
- **`rig.json`**: the rest pose, as a list of parts in back-to-front order.
  Each part names its `image`, and a `pivot` (the joint on the image, e.g. the
  hip at the top of a leg), `at` (where that joint sits on the creature),
  `scale`, `rotate` and optional `flipX` and `shade`. Coordinates are pixels in
  a frame twice the size of the original concept drawing, with the ground at a
  fixed height. `alternates` lists swap-in images (blinking head, folded wing),
  each naming the part it replaces and its own pivot.

Far-side limbs are listed as their own parts that reuse the near-side images
with a `shade` below 1.

## Consequences

- The same file drives the Python preview and (next) the Three.js animation, so
  what we check is what animates.
- Pivots are the joints the walk will rotate around, so the rest pose doubles
  as the skeleton.
- Placement is hand-tuned per creature (about 3 preview rounds for the first one).
- Krea draws some parts far larger than they're used (the legs ended up at 30%
  size), so the cutter can shrink a part as it saves it (`resize` in
  `tools/cut_parts.py`), and the rig's pivot and scale are adjusted to match.
  Halving the legs took the creature from 7.7 MB to 4.3 MB with no visible change.

## Learnings

- Two-point fitting (eye + ear tip) found the head's scale exactly. Matching
  landmarks beats eyeballing outlines.
- Parts generated separately don't always agree on anatomy (Krea's torso had a
  shorter neck), so the rig absorbs small mismatches by nudging and slight rotation.
- Eyeballed placement looked right in a quick preview but wasn't. An onion skin
  (`tools/onion_skin.py`: original in red, rig in cyan, matches in grey) showed
  it immediately. Measured fitting (`tools/fit_part.py`) fixed the head and
  wing, but not parts whose shapes differ. That led to cutting parts from the
  original instead ([0009](0009-cut-parts-from-the-original-with-an-ai-colour-map.md)),
  which makes the rest pose exact (every part at scale 1).
