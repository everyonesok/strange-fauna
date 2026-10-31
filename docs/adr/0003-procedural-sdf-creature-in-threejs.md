# 0003. Draw the creature procedurally with SDFs in a Three.js shader

- **Status:** Superseded by [0007](0007-embrace-2d-cel-animation.md)
- **Date:** 2026-10-28

## Context

The creature has to morph fluidly between very different shapes, and rotating it
in 3D was a wished-for bonus. We considered three approaches:

| Option | Morphing | Can rotate in 3D | Art effort |
| --- | --- | --- | --- |
| 2D in Rive (bones, blend states) | Excellent | No | Designer-friendly |
| 3D models with Blender shape keys | Good | Yes | Heavy modelling per trait |
| **Procedural 3D: SDF raymarching** | **Most fluid** | **Yes, nearly free** | Code, written with AI |

## Decision

The creature is made of math, not meshes. A fragment shader
(`src/creature.glsl`) describes it as signed distance fields (SDFs): spheres,
ellipsoids and tapered tubes, blended with a "smooth minimum" so parts melt
into each other like clay. Three.js provides the canvas and passes in
per-frame positions (`src/main.js`). The camera sits in profile, and dragging
orbits it.

## Consequences

- A growing trait pushes out of the body instead of fading in, which serves quality bar 1 directly.
- 3D rotation comes almost for free, unlike adding it to a 2D build later.
- The natural look is soft and sculpted. The painterly style will come from
  shading and post-processing (e.g. a Kuwahara filter), which is the main style risk.
- Raymarching is heavy on the graphics card. Pixel ratio is capped at 1.5, and
  phones may need a lower-quality mode.
- AI-generated or hand-made 3D models don't fit this pipeline, because they're
  fixed meshes that won't morph.

## Learnings

- The spike (a walking blob plus a growable tail) proved the approach in one
  session, and Opus-class models handled the shader and IK math correctly the first time.
