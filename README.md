# Strange Fauna

A character generator that feels like a fun game in its own right.

In most games, the character creator is a menu you click through before the real fun starts. Strange Fauna treats it as the main event. A creature strolls across an alien landscape, and as you play with a few simple controls it changes shape in real time. It grows a tail, sprouts horns or wings, gets bigger or smaller, and keeps walking the whole time. The goal is for shaping a creature to be fun on its own, even if you never press "start."

## What makes it feel like a game

- **Live transformation.** The creature never stops to rebuild. Every change blends smoothly while it moves, and fluid, springy motion is the top quality bar.
- **A few expressive controls.** A handful of sliders, each with a big effect, instead of a wall of options.
- **Sound that reacts.** Footsteps and other effects are synthesized live and timed to the animation, so the creature sounds as alive as it looks.
- **A painterly world.** The creature is meant to look hand-painted, not like a plastic 3D model.

## Try it

You'll need [Node.js](https://nodejs.org) installed.

```bash
npm install
npm run dev
```

Then open the local address it prints (usually http://localhost:5173).

**Controls**

| Action | How |
| --- | --- |
| Grow the tail | Tail slider |
| Look around the creature | Drag the scene (it springs back to the side view) |
| Pause or resume walking | Pause button or spacebar |
| Footstep sounds | Sound button (browsers keep sound off until you click something) |

## Where it's at

This is an early prototype. Working now: a walking blob creature, a growable tail, play/pause, a draggable camera and synthesized footsteps.

Planned next:

1. Size slider and a better body and walk
2. More traits: wings, horns, tentacles, scales
3. Pet companions that follow the creature around
4. The alien world around it
5. Painterly style and polish

## How it's built

- **[Three.js](https://threejs.org)** renders the scene in the browser.
- The creature is drawn by a shader using signed distance fields (SDFs): math shapes that melt into each other smoothly, which is what makes the shape changes feel fluid.
- Legs are placed with two-bone inverse kinematics (IK), so feet land on the ground correctly at any body size.
- Sound is generated with the Web Audio API. There are no audio files.
- **[Vite](https://vite.dev)** runs the local dev server.

The reasoning behind these choices, and what we learned building them, is recorded in [Architecture Decision Records](docs/adr/README.md).
