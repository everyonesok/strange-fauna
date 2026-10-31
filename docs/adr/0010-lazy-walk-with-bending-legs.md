# 0010. A lazy walk for every creature, with legs that bend

- **Status:** Accepted
- **Date:** 2026-10-31

## Context

The first creature, the rabbit-bat-snake, is now cut straight from its
drawing ([0009](0009-cut-parts-from-the-original-with-an-ai-colour-map.md)).
It needed to walk. Two questions came up:

1. **Which gait?** Real hares and rabbits don't really walk: they hop and
   bound, and a jaguar or a bear moves very differently again. Matching each
   animal's real gait would mean a different animation system per creature,
   and a bound (both back legs together, the body stretching and folding) is
   much harder to make convincing in 2D cut-outs.
2. **How do legs move?** Each leg is cut from the drawing as one picture.
   Rotating that picture stiffly at the hip looked like a wooden toy, so the
   first walk "didn't feel natural yet".

## Decision

**Every creature does a lazy walk, never a run or bound.** It's a
lateral-sequence walk (near hind, near front, far hind, far front, a quarter
cycle apart), the way most four-legged animals stroll. Creatures differ only
by their gait numbers (`GAIT` in `src/main.js`: cycle length, stride, step
height, how long each foot stays down), not by a different gait.

**Each leg is one picture that bends** (`src/leg.js`):

- The picture is laid on a fine grid. Every grid point is pinned to the
  nearest of three invisible bones (thigh, shin, paw), blending near the
  joints. Moving the bones bends the picture smoothly: this is *skinning*,
  as in tools like Spine.
- The joints (`knee`, `ankle`, `toe`) are marked per leg in `rig.json`.
- **Two-bone IK** places the knee: given the hip and where the ankle must be,
  the law of cosines gives the knee. The knee always bends the same way it
  does in the drawing.

**Feet are placed, not animated.** For each leg, `footTarget` says where the
toe should be at each moment:

- **Planted** (`duty`, 65% of the cycle): the toe slides back at exactly the
  ground's speed. Near the end, the heel peels up while the toes stay down.
- **Swinging:** the paw lifts in an eased arc and lands ahead.
- The body bobs and rocks a little with the steps, around the torso's joint.
  The hips follow the body, so the legs stay attached.

## Consequences

- One walk system covers every creature; a new creature needs gait numbers
  and joint marks, not new animation code.
- The walk is stylised: a rabbit that walks instead of hopping is part of the
  Seussian whimsy, not a mistake.
- Legs keep the drawing's exact look in the rest pose, and bend without
  visible joints or cracks.
- Legs can only bend at the joints marked in the rig. A leg that needs more
  joints (a long tentacle, say) would need more bones.
- **Fallback:** if a lazy walk never feels right for some creature, try a
  bound for that one.
- Pausing eases every lifted paw onto the ground and stops the body rocking,
  tied to the same spring that slows the walk, so the creature never freezes
  with a foot in the air.
- Gait numbers live in each creature's `rig.json` (`gait`); any left out use
  the defaults in `src/main.js`.
- Now and then a part swaps to another picture for a moment (a blink, the
  wing folding to rest), at random gaps on the life clock (`MOMENTS`).

## Learnings

- **The ground speed depends on how long feet stay down:**
  `stride / (cycle × duty)`. The 0.5 in 0005 only holds when a foot is down
  for exactly half the cycle.
- **What made the walk feel natural** (in order of effect): legs that bend
  instead of rotating stiffly; toes that stay put while the heel peels up; a
  small bob and rock of the body. Each alone wasn't enough.
- Let a leg stretch a little (5%) when it can't quite reach; past that, the
  foot hangs short. Without the limit, legs stretch like rubber.
- Moving the bones of a single picture shows everything it carries. Any bit of
  a neighbouring part left on a leg picture swings with it, so the cut-outs
  had to get cleaner (see the learnings in 0009).
