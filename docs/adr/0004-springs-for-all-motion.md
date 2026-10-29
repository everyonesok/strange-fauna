# 0004. Drive every change through springs

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Sliders and buttons change values instantly. Applied directly, the creature
would snap from one shape to another, which breaks quality bar 1 (fluid
transformation).

## Decision

No control sets a visual value directly. Each control sets a **target**, and a
spring (`makeSpring` / `stepSpring` in `src/main.js`) pulls the real value
toward it every frame. The springy feel is tuned per use:

| Spring | Stiffness / damping | Feel |
| --- | --- | --- |
| Tail growth | 70 / 9 | Slight overshoot, so it feels alive and fleshy |
| Camera (released) | 20 / 7 | Gentle swing back to profile |
| Camera (dragging) | 400 / 40 | Tight, follows the pointer |
| Walk speed | 25 / 10 | Critically damped: smooth, no overshoot |

## Consequences

- Every morph has weight and follow-through for free.
- New traits plug into the same pattern: add a spring, read its value.
- Values can briefly go outside their range (e.g. a tail amount below 0), so
  code that uses them must clamp.

## Learnings

- **Overshoot isn't always welcome.** A bouncy walk-speed spring would make the
  creature briefly walk *backward* as it stops. Anything that represents speed
  or direction should be critically damped (damping ≈ 2 × √stiffness).
- **Springs never actually reach zero.** They only get closer and closer, so a
  "paused" creature kept creeping at an invisible speed. Pixel-exact frame
  comparison caught it. Treat values below a small threshold (0.001) as stopped.
