# 0002. The character creator is the main event

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The project is a recent, web-based, AI-assisted portfolio piece for a creative
technologist role. A full game is out of scope. We needed a slice that's small
enough to finish but still feels like play.

## Decision

Build only the character creator, and make it fun on its own. A creature walks
across an alien landscape in side view while a handful of sliders (two
"crossfade" axes plus size) transform it live: tail, wings, horns, tentacles,
scales and pet companions.

Quality bars, in priority order:

1. **Fluid transformation.** Changes blend while the creature keeps moving; nothing pops.
2. **Few, expressive controls.** About three sliders, each with a big effect.
3. **Reactive sound.** Foley-style sounds tied to the creature's traits, with no speech.
4. **A painterly look.** It should feel hand-painted, not plastic 3D.

## Consequences

- Scope stays small: we polish a few traits instead of building many rough ones.
- Every technical choice is judged first by how fluid the morphing feels.
- No game loop, goals or levels; "start game" is deliberately absent.
