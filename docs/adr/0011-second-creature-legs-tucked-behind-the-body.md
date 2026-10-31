# 0011. Second creature: one shared frame, legs tucked behind the body

- **Status:** Accepted
- **Date:** 2026-10-31

## Context

The jaguar-elk-chameleon is the second creature. It went through the same
process as the rabbit-bat-snake ([0009](0009-cut-parts-from-the-original-with-an-ai-colour-map.md),
[0010](0010-lazy-walk-with-bending-legs.md)), and three things were different:

1. Its drawing is smaller (1024 px wide, the hare's is 1184).
2. Nano Banana 2 would not remove its near hind leg. It redrew the green
   scaled leg in brown instead, four times. It did the same when the leg was
   erased first and it was only asked to repair the hole.
3. Its haunch and shoulder have no outline where the legs start: the scales
   and spots just carry on down the leg. Wherever the body and a leg are cut
   apart, the cut edge has no ink line.

The creatures are meant to transform into each other later, so whatever we
chose had to keep them compatible.

## Decision

- **Every creature shares the same frame** (2368 × 1776 rig pixels, with the
  camera fitted to it). A drawing of another size is scaled to fill it.
- **A creature's near legs may be tucked behind its body** instead of drawn
  in front. The cutter's palette lists them before the torso. The body's edge
  stays still on top, and each leg's top slides around unseen underneath. No
  leg-removal edit is needed.
- **Leg tops can be anchored to the body** (`"anchor"` on a leg in the rig).
  Above the hip, the picture only moves with the body; below it, it blends
  into the turning thigh, like skin stretching over a joint.
- The page has a creature picker, so we can compare walks (`?creature=` in the
  address).

A third creature, the **bear-rhino-beetle**, followed the same day. Its concept
was made by Nano Banana 2 from the hare's drawing ("redesign this creature as
..., no ground shadow"). It didn't keep the hare's pose, but it came out as a
clean drawing with outlines around the near thigh and shoulder. So its near
legs stay **in front** of the body, like the hare's, with anchored tops. Its
beetle shell is a part of its own on top of the body, the way the hare's wing
is (the model painted it a different green from the tail). Only two AI images
were needed after the concept: the colour map and a blink.

## Consequences

- One camera and one ground fit every creature, and the parts of two
  creatures already sit in the same space, which morphing will need.
- The creatures are not the same size on screen: each fills its own drawing.
  Morphing will have to scale between them.
- Tucked legs hide their own top. A leg whose top is drawn with a clear
  outline in front of the body (like the hare's grey thigh, or the bear's
  haunch) should stay in front.
- Anchored legs need no leg-removal edits when their top is drawn with an
  outline: the anchored top barely moves, so the body under it never shows.
- Any part that isn't a leg, the head, the wing or the tail (like the shell)
  simply rides along with the body.
- The hare's rig was left as it was: it has no anchors, and its parts weren't
  re-cut with the newer cutter. It walks exactly as before.

## Learnings

- **A hip on the belly line swings the leg's top out below the belly.** Put
  the hip a little inside the body, where a real hip joint is, and anchor the
  top.
- **A leg's hidden top should grow upward into the body, not sideways.** A
  sideways piece beside the leg's top swung out as a small nub.
- **Colour maps follow texture.** The map's border between the scaled leg and
  the scaled rump wobbled along the scales, and the model painted some scale
  lines in the wrong colour. Smoothing the labels (each pixel takes the most
  common label around it) fixed both.
- **A model's map can leave a thin white seam between two colours.** The
  cutter took it for background and punched a hairline hole in the neck.
  White inside the creature is now filled in.
- **The colour under a seam should come from nearby, not from the whole
  part.** One average colour for the whole torso (tan with dark spots) showed
  as a dark line under the cream throat. Nearby colours, leaving out ink lines
  and spots, made it disappear.
- **A big shoulder in front of the body leaves a hole when it swings.** The
  bear's near front leg covered a deep notch of its chest, and the body had
  nothing there. The cutter now fills the body in under near legs in front of
  it, out to where its outline would run without the leg (a "closing": grow
  the shape, then shrink it back by the same amount).
- **A leg that should look straight needs its foot planted far ahead.** The
  jaguar's near front leg folded into a sharp arc because its foot landed
  close under the hip. Moving its `reach` forward (and a shorter stride) keeps
  it extended, as in the drawing.
- AI edits come back slightly larger than the drawing (2400 × 1792 for a
  1024 × 768 drawing, a 0.5% different shape). Scaled into the frame, they
  still lined up.
