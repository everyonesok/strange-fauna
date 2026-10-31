# Art pipeline: AI-assisted separations

How concept art becomes animation-ready layers. The look and the reasons for it
are in [ADR 0007](adr/0007-embrace-2d-cel-animation.md).

Concept art and test results live in a local `references/` folder that is
kept out of the repo, so the image paths below exist only on the artist's machine.

## Recommended: cut the parts from the original

Decided in [ADR 0009](adr/0009-cut-parts-from-the-original-with-an-ai-colour-map.md).
The AI never redraws anything visible, so the assembled rest pose matches the
concept art pixel for pixel. Two generations per creature, both with **Nano
Banana 2** (`google/nano-banana-2`, 2K, 4:3), which kept the framing better
than Krea 3 in side-by-side tests.

**1. Colour map** (`references/separations/<creature>-segmap-nb2.png`)

```text
Turn this drawing into a flat-colour segmentation map of the creature's body
parts. Keep the exact same framing, pose, size and position, so every part's
silhouette lines up pixel-for-pixel with the original. Remove all line art,
shading, texture and the ground shadow; the background becomes pure white. Fill
each part with one solid flat colour: the head including ears, down to the jaw
and throat = pure red; the body (back, belly, chest fur, neck) = yellow; the bat
wing, membrane and arm bones = blue; the green snake tail = green; the front leg
reaching forward to the rightmost foot, including its grey shoulder = magenta;
the other front leg behind it, with the foot under the chest = cyan; the hind
leg including its big grey thigh, whose foot is at the far left = orange; the
dark brown hind leg reaching forward under the belly = purple.
```

Describe each leg by something visible (where its foot is, its colour), because
"near" and "far" are ambiguous to the model.

Concept art should have **no ground shadow**: shadows are drawn in code, and a
shadow joining the feet makes the cut harder. (Only the rabbit-bat-snake has
one; the cutter handles it by treating the map's white as background.)

**2. Hidden areas** (`references/separations/<creature>-nowing-nb2.jpg`)

```text
Remove the bat wing completely. Where the wing covered the rabbit, continue the
rabbit's grey back fur with one smooth back outline running from the rump up to
the shoulders and neck, in the same ink line and flat colour style. Where the
wing covered empty space, show the plain white background. Keep everything else
exactly the same: same framing, pose, size and position of every part, so the
result lines up pixel-for-pixel with the original.
```

Do the same for each near leg, one leg per edit. Ask for the leg's whole thigh to
go and for a **slim** body underside in its place. Asking for "a rounded rump and
haunch" left a thigh painted on the body, and it stood still while the real
thigh swung, like an udder. Removing a near leg also uncovers the far leg behind
it, so make a colour map of the edit too (same prompt as step 1, with that leg
left out) and pass it after the edit. Then the body only takes body pixels, and
the far leg takes its own uncovered top from the same edit:

```text
--fill=torso:near-hind-leg:<no-near-hind.jpg>:<no-near-hind-map.jpg>
--fill=far-hind-leg:near-hind-leg:<no-near-hind.jpg>:<no-near-hind-map.jpg>
```

**3. Cut and check**

```bash
python3 tools/cut_from_map.py rabbit-bat-snake references/separations/rabbit-bat-snake-segmap-nb2.png <preview-dir> --fill=torso:wing:references/separations/rabbit-bat-snake-nowing-nb2.jpg
python3 tools/onion_skin.py rabbit-bat-snake <out.png>
```

- Sample the map's actual colours and put them in the palette in
  `tools/cut_from_map.py`; models drift from the colours asked for.
- The preview dir gets `<creature>-labels.png`, the original tinted by part, to
  check the split.
- Set each part's pivot (joint) in `rig.json`; `at` is the same joint in the
  frame, and scale is always 1.
**4. Swap-in images** (a blink, a folded wing): more Nano Banana 2 edits of the
original, in the same framing, cut with `--variant`.

```text
Close the rabbit's eye in a gentle blink: the eyelid fully closed, drawn as a
soft curved ink line with the surrounding fur colours, no eyeball visible. Keep
everything else exactly the same: same framing, pose, size and position of every
part, so the result lines up pixel-for-pixel with the original.
```

```text
Fold the bat wing closed, like a resting bat's wing: the same wing with the same
colours and ink style, still attached at the same shoulder point, with its arm
bones folded and the membrane tucked in so it lies close along the rabbit's
back, pointing back toward the tail. Where the open wing used to be, show the
rabbit's grey back fur and the plain white background. Keep everything else
exactly the same: same framing, pose, size and position of the rabbit, head,
tail and legs, so they line up pixel-for-pixel with the original.
```

The blink keeps the head's outline, so it reuses the main colour map. The
folded wing has a new outline, so it also needs a colour map of the folded
edit (step 1's prompt, run on that edit, with "folded bat wing"). Add to the
cut command:

```bash
--variant=head-blink:head:references/separations/rabbit-bat-snake-blink-nb2.jpg
--variant=wing-folded:wing:references/separations/rabbit-bat-snake-wingfolded-nb2.jpg:references/separations/rabbit-bat-snake-wingfolded-segmap-nb2.jpg
```

Each swap-in goes in the rig's `alternates` with its own pivot (the same joint
as its part). Preview one with
`python3 tools/preview_rig.py <creature> <out-dir> head-blink wing-folded`.

## Earlier experiment: Krea-drawn parts

Superseded by the process above: Krea redrew each part, so the parts never
quite matched the original. Kept for the prompts and learnings.

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

## 2. Cut out and assemble the parts (Krea-drawn parts)

1. **Cut:** `python3 tools/cut_parts.py` cuts each part out of its sheet into a
   transparent PNG in `public/creatures/<creature>/`. Each part is listed in the
   script with its source sheet, a crop box and a seed point inside it. The
   script grabs the connected drawing under the seed (like a magic wand), fills
   holes so eye highlights stay opaque, and softens the edge.
2. **Fit:** edit `public/creatures/<creature>/rig.json` (format in
   [ADR 0008](adr/0008-creatures-are-parts-plus-a-rig-file.md)), then check the fit with
   `python3 tools/preview_rig.py <creature> <out-dir>`. It draws the assembly
   alone and over a faded copy of the original drawing.

**Rabbit-bat-snake assembly learnings:**

- **Tuck leg tops behind the torso.** Krea's torso already has a haunch and a
  shoulder drawn in, so the torso hides the joints. Legs on top of the body
  showed their outlined tops as seams.
- **Fit the head by its eye, not its outline.** Matching the iris and the
  ear-tip height between the original and the cut-out gave the exact scale
  (1.39). The head then needed nudging down because Krea's redrawn torso has a
  shorter neck than the original.
- **Layer order follows the original:** ears in front of the wing, wing in
  front of the body.
- **Far-side legs reuse the near legs, darkened to 62%.** That alone gives
  convincing depth.

## 3. Background: multiplane layers

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
