# 0009. Cut parts from the original drawing, using an AI colour map

- **Status:** Accepted
- **Date:** 2026-10-30

## Context

The first rabbit-bat-snake rig used parts that Krea redrew one at a time
(see [art-pipeline.md](../art-pipeline.md)). An onion-skin check against the
original drawing showed that the assembled rest pose never matched it:

- the torso was a different, shorter drawing, shifted toward the rear
- the tail was straight where the original's is an S-curve
- the legs were short and upright where the original's are long and mid-stride

Measured fitting (`tools/fit_part.py`) placed the head and wing well, but it
can't fix parts whose shapes are different. Since this first creature sets the
process for all the others, we looked for a repeatable way to get an exact match.

## Decision

Cut every part **straight out of the original drawing**. AI is only used for
two jobs it does reliably, and neither of them redraws anything visible:

1. **A colour map:** the original repainted with one flat colour per body part,
   in the same framing. `tools/cut_from_map.py` uses it to sort each pixel of the
   original into a part.
2. **Hidden areas:** an edit of the original with the covering part removed
   (e.g. no wing, so the back is painted in). Only the pixels the covering part
   hid are taken from it (`--fill=torso:wing:<edit>`).

Every part then sits in the rig at scale 1, with no rotation, exactly where it
was cut. The rest pose *is* the drawing.

## Consequences

- The onion-skin check is pixel-perfect: only the ground shadow (left out on
  purpose, drawn in code later) and the whisker tips differ.
- The process is the same for every creature: two AI generations (map and
  hidden-area fill), then one script run.
- The original's pose is now the rest pose, so legs start mid-stride and the
  tail starts curled. The walk animates from there.
- Parts are only as sharp as the original drawing (1184 px wide, used at 2x).
  Upscaling the original first with an enhancer is an option if they look soft.
- Swap-in images (the blinking head and folded wing) must now be made from the
  new cut-out parts. The old Krea-drawn ones no longer match.
- The colour map's palette is listed per creature in `tools/cut_from_map.py`,
  using the colours the model actually painted.

## Learnings

- **Never assume an AI edit keeps the original's framing. Measure it.** Krea's
  "subtractive" torso looked aligned but was redrawn shorter and shifted. The
  onion skin (`tools/onion_skin.py`) shows a mismatch in seconds.
- **Nano Banana 2 beat Krea 3 on both framing-preserving jobs.** Its colour map
  coloured all eight parts (Krea left the thighs and the far leg grey), and it
  removed the whole wing (Krea's regional edit removed only the lower half and
  left the rest floating). Both kept the framing to within about 3 px.
- Models don't paint the exact colours you ask for (the "green" came back
  `#007A01`), so sample the map before cutting.
- Soft edges between two map colours can blend into a third part's colour.
  Keeping only each part's main connected region removes the stray slivers.
- The pale ground shadow connects the feet, which made the gaps between the
  legs look "inside" the creature. Treating the map's white as background fixes it.
