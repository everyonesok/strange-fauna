# 0007. Embrace 2D cel animation, including its limitations

- **Status:** Accepted
- **Date:** 2026-10-30
- **Supersedes:** [0003](0003-procedural-sdf-creature-in-threejs.md)

## Context

The first concept art (`references/`) set the visual target: hand-drawn,
feature-animation-style creatures with clean ink lines, flat color and one soft
shading tone, walking through a hand-painted alien landscape. The whimsy comes
from the creature combinations (rabbit + bat wings + snake tail), in the spirit
of Dr. Seuss. To keep v1 simple, every creature has four legs.

The SDF blob creature from ADR 0003 can't reach this look: faces, fur tufts,
spots and feathers are illustration detail, not soft math shapes. We compared:

| Option | Matches the art | Smooth morphing | 3D rotation | Effort |
| --- | --- | --- | --- | --- |
| **2D cel rig in code** | Closest (uses the actual drawings) | Strong for tails, growing parts; dissolves for the rest | No | ~1–1.5 weeks |
| 3D toon-shaded models | Close in spirit | True morphing | Yes | ~3–4+ weeks, heavy modelling |
| Stylized SDF blobs | No | Yes | Yes | Low |

## Decision

Build the creature as a **2D cel animation rig, driven by code** (still rendered
with Three.js). Embrace both what's beautiful about cel animation *and* its
limitations, so it feels authentic rather than "3D pretending to be 2D":

- **Cel construction:** creatures are cut into painted parts (head, torso, four
  legs, tail, extras like wings and antlers), each a flat cel with ink line and
  one shading tone, stacked in layers.
- **Multiplane depth:** the world is painted background layers that scroll at
  different speeds (parallax), like Disney's multiplane camera. A dark foreground
  layer passes *in front of* the creature from time to time. Distant layers are
  hazier and less saturated, so the busy background sits back.
- **Authentic limitations, used on purpose:**
  - Side view only. No 3D rotation.
  - Optional animation "on twos" (12 drawings per second) and gently "boiling"
    ink lines, like hand-redrawn frames.
  - Transformations use the era's tricks rather than computer morphing:
    sprouting and growing with squash and stretch, smear frames, dissolves
    with sparkle or smoke, and curves that uncurl (tails, tentacles).

The engineering from the spike carries over unchanged: IK walk (now four
legs), springs, the two clocks, play/pause and synced sound.

## Consequences

- The look comes straight from the concept art, which is the main win.
- 3D rotation is dropped. The "drag to rotate" control goes away (or becomes
  a small cel-style head turn later).
- New art pipeline: creatures must be separated into parts in a consistent
  rest pose, all facing right; backgrounds must be split into depth layers that
  tile horizontally. We're testing whether an AI edit model (Krea) can produce
  these separations as a starting point.
- Heads and patterns can't truly morph between unrelated drawings; they
  dissolve or wipe instead. That's accepted as part of the authentic style.
