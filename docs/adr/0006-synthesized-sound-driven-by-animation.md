# 0006. Synthesize sound live, driven by the animation

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

Sound strongly shapes how a creature reads: squishy, heavy, slithery. Sounds
must change as the creature morphs and stay perfectly in time with its motion.

## Decision

Generate sound in code with the Web Audio API (`src/audio.js`), with no audio
files for now. A footstep layers a **thump** (a sine tone dropping from 130 Hz to
45 Hz) and a **squish** (white noise through a sweeping bandpass filter), with
small random pitch and volume variation. Sounds are triggered by the same
values that drive the visuals (e.g. a foot's cycle wrapping), so they can't
drift out of sync.

## Consequences

- No asset hunting yet, and the sound can respond to any parameter (size → deeper steps).
- Synthesized sound has a ceiling. Recorded or AI-generated samples can replace
  the recipes later by changing only `audio.js`.
- Planned layers: event sounds (footsteps, wing flaps), continuous loops
  crossfaded by sliders (slither, wet textures) and transformation sounds.

## Learnings

- **Browsers block sound until the user clicks something**, so audio starts
  off behind a Sound button. This can become a designed "enter" moment later.
- Identical repeated sounds feel robotic ("machine-gunning"). Even ±8% pitch
  variation fixes it.
