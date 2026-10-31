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
- Swap-in images (the blinking head and folded wing) are cut the same way,
  from AI edits of the original (`--variant`), so they swap in without a jump.
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

Once the parts moved ([0010](0010-lazy-walk-with-bending-legs.md)), the seams
between them showed:

- **The tucked-under part of a piece has to be its own colour.** Copied from
  the drawing, it carries the neighbour's pixels and outline, which swing out
  as a pale band. The cutter now paints it in the part's own average colour.
- **Far legs tuck deep under the body, but not under the near legs.** The body
  never moves away, so the deep tuck stays hidden. A near leg steps away, and
  the tuck under it showed up as a stray wedge.
- **Reaching across a gap grabs loose bits**, like a sliver of the other leg's
  outline. Only pieces still attached to the part are kept.
- **Ask for a slim body where a near leg is removed.** Asking for "a rounded
  rump and haunch" painted a second thigh on the body, which stood still while
  the real one swung.
- **Removing a near leg uncovers the far one.** Without a colour map of the
  edit, the far leg's top got copied onto the body. With one (passed after
  the edit in `--fill`), the body takes only body pixels and the far leg takes
  its own top.
- Edits that remove two legs at once are unreliable (wrong legs removed,
  other legs moved). One leg per edit works.
