# Art pipeline: AI-assisted separations

How concept art becomes animation-ready layers. The look and the reasons for it
are in [ADR 0007](adr/0007-embrace-2d-cel-animation.md).

Concept art and test results live in a local `references/` folder that is
kept out of the repo, so the image paths below exist only on the artist's machine.

**Model:** Krea 3 (`krea/krea-3`), an instruction-following image editor, with
`thinking_mode: "high"` so it plans the multi-step edit first.

## 1. Creature: cutout puppet parts sheet

One generation per creature. Input: a creature sheet facing right.

```text
Turn this creature into a cutout-animation puppet parts sheet. Separate it into
individual body parts, each drawn complete and laid out apart from the others on
a plain flat white background, in a tidy grid with generous space so no parts
touch or overlap:
- the head with ears, eye open
- the same head with the eye closed, for blinking
- the torso including the neck, with any area hidden behind wings filled in
- one front leg in two pieces: upper leg, and lower leg with paw
- one hind leg in three pieces: thigh, lower leg, and foot
- the tail, straightened out horizontally, base on the left and tip on the right
- [extras, e.g. "the bat wing fully open" and "the same bat wing folded"]
Where parts join, extend each piece slightly past the joint with a rounded end,
so the pieces can overlap and rotate without gaps. Keep the exact same character
design, proportions, colors, clean ink linework, flat cel paint and single soft
shading tone, all in side view facing right. No text, labels, shadows or new details.
```

Why each instruction is there:

| Instruction | Why the animation needs it |
| --- | --- |
| Parts apart, on flat white | Every part has an ink outline, so code can cut it out cleanly from white |
| Drawn complete, hidden areas filled in | When a leg swings or a wing lifts, whatever was behind it becomes visible |
| Overlapping rounded joints | The classic cutout-animation trick that hides seams when a piece rotates |
| Only *one* front and *one* hind leg | The far-side legs reuse them, painted darker, as cel animators often did |
| Tail straightened | Code bends a straight strip along a curve, so the tail can curl, uncurl and morph |
| Closed-eye head | A blink is cheap and adds a lot of life |
| Same scale, side view, facing right | Parts from different creatures must swap onto the same skeleton |

### Test log

**v1, rabbit-bat-snake** (`references/separations/rabbit-bat-snake-parts-v1.png`), took about 30 s.

| Part | Result |
| --- | --- |
| Style (ink line, flat cel paint, colors) | ✅ Faithful to the original |
| Head, eye open and closed | ✅ Excellent; same scale, so a blink is a simple swap |
| Tail straightened | ✅ Exactly what the curve-bending tail needs |
| Parts separated on white | ✅ Clean; easy to cut out |
| Torso | ⚠️ Too short: ends mid-body, and the haunches moved onto the hind legs. Shows "mannequin" cut ends (dark ovals) at the neck and rear |
| Legs | ⚠️ Not split at the joints. Each leg is one piece with a large rounded thigh blob |
| Folded wing | ❌ Not folded, just a second open wing with more fingers |

**v2, rabbit-bat-snake** (`references/separations/rabbit-bat-snake-parts-v2.png`):
the prompt asked for the full-length torso, one-piece straight legs, a truly
folded wing and no cut ends.

| Part | Result |
| --- | --- |
| Folded wing | ✅ Fixed: a narrow, resting bat wing |
| Heads, open wing | ✅ Still excellent |
| No cut ends | ✅ Mostly; the neck ends in rounded fur now (the tail base still shows a cut) |
| Torso | ❌ Full length now, but drawn *with all four legs attached*, which a walking rig can't use |
| Legs | ⚠️ Only two (both front-like), bent rather than straight |
| Tail | ⚠️ Wavy instead of straight (v1's was better) |

**Best of both so far:** heads (either), open wing (either), folded wing (v2),
straight tail (v1). Still missing: a torso *without* legs, and straight front and
hind legs.

**Subtractive, rabbit-bat-snake** (`references/separations/rabbit-bat-snake-*-subtractive.png`):
starting from the original with `regional_edit: true`, one generation asked to
remove everything except the torso, another everything except the legs.

| Part | Result |
| --- | --- |
| Torso | ✅ Accidental win. Nothing was fully removed, but the body was redrawn as a complete, full-length piece (haunches included) with a clean outline, and every other part now floats apart from it with a white gap. It can be cut out as-is. |
| Legs | ❌ Chunky, redrawn legs with smudged white patches and floating paws. Not usable. |

**Single leg per generation, rabbit-bat-snake** (`references/separations/rabbit-bat-snake-{hind,front}leg.png`):

```text
Draw only this creature's near hind leg, from the hip down to the foot, as a
single isolated piece centered on a plain flat white background. Show it
straight, in a relaxed standing pose, side view facing right, with a rounded,
fully painted top where it would join the body. Keep the exact same colors, fur
markings, clean ink linework, flat cel paint and single soft shading tone as the
original. Nothing else in the image: no body, no other legs, no text, no shadow.
```
(The front leg prompt is the same with "near front leg, from the shoulder down to the paw".)

| Part | Result |
| --- | --- |
| Hind leg | ✅ Clean, isolated, straight, with a proper backward-bending hock and the original two-tone coloring |
| Front leg | ✅ Clean and straight, with a fur tuft at the elbow |
| Both | ⚠️ Drawn much larger than the creature (they fill the frame), so code must scale them to match the torso. The big rounded tops are plain and will tuck under the torso. |

**Result: every part of rabbit-bat-snake now exists** (heads v1/v2, wings v1/v2,
straight tail v1, torso subtractive, legs single).

Learnings:

- **One part per generation is the reliable recipe.** Every single-part request
  worked; every multi-part request got some parts wrong.
- Each part comes back at its own scale, so a "rest pose" assembly step is needed
  to size and place the pieces relative to each other.
- Regional edit is built for small local fixes. Large removals leave soft
  white smudges rather than clean erasures.
- Krea 3 keeps style and character identity very well. Anatomy and
  "construction" instructions are followed loosely, and differently every run.
  Fixing one part can break another.
- Long multi-part prompts are a lottery. Expect to pick the best parts across
  several runs, or ask for **one part per generation**.
- One-piece legs are usable, maybe even better: code can bend a single leg
  image at the knee (mesh deformation), which hides joints better than
  separate pieces.

## 2. Background: multiplane layers

One generation per layer, each starting from `references/background.png`.
These are untested so far.

**Far layer** (sky and distant rock spires; scrolls slowest)
```text
Remove every plant, mushroom tree, flower and rock in the foreground and middle
ground, leaving only the sky, the distant rock spires and the far hills, and
repaint the revealed areas in the same hand-painted style. Make it hazier and
less saturated, as if seen through soft morning fog.
```

**Middle layer** (meadow and mushroom trees; the creature walks here)
```text
Remove the sky, the distant rock spires and the dark foreground plants in the
corners, replacing them with flat pure green (#00FF00). Keep the meadow ground
and the mid-distance mushroom trees and flowers in the same hand-painted style,
slightly softened and desaturated.
```

**Foreground layer** (dark plants that pass in front of the creature)
```text
Keep only the darkest, closest foreground plants and leaves along the bottom and
side edges, and turn everything else into flat pure green (#00FF00). Make the
kept plants nearly silhouettes: deep, dark and low in detail.
```

Notes:

- Flat pure green is used (not white) because the painted layers have no ink
  outline to cut along, and none of the background colors are close to pure green.
- A walking creature needs the world to scroll forever, so layers must repeat
  side to side. AI models are unreliable at seamless tiling, so the code will
  blend the edges if needed.
