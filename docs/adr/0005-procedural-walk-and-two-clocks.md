# 0005. Procedural walk with IK, driven by a separate walk clock

- **Status:** Accepted (the gait, the bending legs and the foot path are
  detailed in [0010](0010-lazy-walk-with-bending-legs.md))
- **Date:** 2026-10-28

## Context

The body will change drastically (size, leg length, weight), so a keyframed
walk cycle would break with every change. The player also needs to pause the
walk while still rotating and watching the creature.

## Decision

- **The walk is computed, not animated.** Each foot follows a cycle: half
  planted (sliding back), half swinging forward in an arc. Two-bone inverse
  kinematics (`solveKnee`) works out where the knee must be.
- **The world moves, not the creature.** The creature stays centred and the
  ground scrolls underneath.
- **Two clocks.** The *life clock* (`time`) always runs: tail sway, springs and
  camera. The *walk clock* (`walkTime`) advances by `dt × walkSpeed`: steps,
  body bob, ground scroll and footsteps. Pausing eases `walkSpeed` to 0.

## Consequences

- The walk adapts automatically to future body changes.
- Pausing stops the walk but leaves the creature alive and rotatable.
- Anything new must choose its clock: *is this part of walking, or part of being alive?*
- Known gap: pausing mid-stride freezes a foot in the air. The planned fix is
  to settle onto both feet when stopping.

## Learnings

- **Feet only look planted if the ground scrolls at exactly the speed a planted
  foot slides back:** `stride / (cycle × 0.5)`. Any mismatch reads as skating.
- Footstep timing comes for free: a foot lands at the moment its cycle wraps from 1 back to 0.
