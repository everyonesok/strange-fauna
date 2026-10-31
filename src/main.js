// ---------------------------------------------------------------------------
// main.js — draws a cut-out creature from its rig.json, like a paper puppet.
//
// Each body part is a flat picture (a "sprite") pinned at its joint. A joint
// is a THREE.Group: moving or rotating the group moves the picture with it,
// around the pivot point. Legs are the exception: they bend (see leg.js).
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import { toggleSound, playFootstep } from './audio.js';
import { makeLeg, poseLeg } from './leg.js';

const CREATURE = 'rabbit-bat-snake';
const FOLDER = `/creatures/${CREATURE}/`; // files in public/ are served from the site root

// ----- Renderer ------------------------------------------------------------
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0xefeaf2); // soft paper colour until the landscape arrives
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();

// An orthographic camera has no perspective: perfect for flat 2D art.
// We measure the world in the rig's own pixels, so a part placed "at
// [1850, 830]" in rig.json lands at x 1850 here. One difference: the rig
// counts y downward (like an image), Three.js counts y upward, so we flip y.
const camera = new THREE.OrthographicCamera();
camera.position.z = 10;

let frame = [2368, 1776]; // replaced by the rig's frame once it loads
let groundY = 1590;        // and the rig's ground height
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h);
  // Fit the whole frame on screen, keeping its shape (extra space goes to the sides)
  const scale = Math.max(frame[0] / w, frame[1] / h);
  const halfW = (w * scale) / 2, halfH = (h * scale) / 2;
  const cx = frame[0] / 2, cy = -frame[1] / 2; // centre of the frame (y flipped)
  camera.left = cx - halfW;
  camera.right = cx + halfW;
  camera.top = cy + halfH;
  camera.bottom = cy - halfH;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);

// ----- Build the puppet from rig.json --------------------------------------
const loader = new THREE.TextureLoader();

function loadTexture(file) {
  return new Promise((resolve, reject) => {
    loader.load(FOLDER + file, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace; // the PNGs are ordinary sRGB images
      resolve(tex);
    }, undefined, reject);
  });
}

// A flat picture whose pivot point sits at (0, 0)
function makeSprite(tex, [px, py], order) {
  const { width: w, height: h } = tex.image;
  // A plane the size of the image. By default it's centred on (0, 0); shift
  // it so the pivot point is at (0, 0) instead, so rotating spins around the joint.
  const geometry = new THREE.PlaneGeometry(w, h);
  geometry.translate(w / 2 - px, -(h / 2 - py), 0);

  const material = new THREE.MeshBasicMaterial({
    map: tex,
    transparent: true, // the PNG's see-through background stays see-through
    depthTest: false,  // layering comes from the list order instead (below)
  });
  const sprite = new THREE.Mesh(geometry, material);
  sprite.renderOrder = order; // rig.json lists parts back to front
  return sprite;
}

// One part = a joint (Group) holding a picture whose pivot sits at the joint.
async function makePart(part, order) {
  const tex = await loadTexture(part.image);
  if (part.knee) {
    // Legs are bendable pictures (see leg.js) rather than rigid ones
    const leg = makeLeg(part, tex, order);
    leg.mesh.userData.leg = leg;
    return leg.mesh;
  }
  const joint = new THREE.Group();
  joint.name = part.name;
  joint.add(makeSprite(tex, part.pivot, order));
  joint.position.set(part.at[0], -part.at[1], 0);
  joint.rotation.z = -THREE.MathUtils.degToRad(part.rotate ?? 0); // rig: clockwise; Three: counter-clockwise
  const s = part.scale ?? 1;
  const [sx, sy] = Array.isArray(s) ? s : [s, s];
  joint.scale.set(part.flipX ? -sx : sx, sy, 1);
  // Remember the rest pose: animation adds small offsets to it every frame,
  // so the creature can always settle back exactly here.
  joint.userData.rest = {
    x: joint.position.x, y: joint.position.y, rot: joint.rotation.z,
    sx: joint.scale.x, sy: joint.scale.y,
  };
  return joint;
}

async function loadCreature() {
  const rig = await (await fetch(FOLDER + 'rig.json')).json();
  frame = rig.frame;
  groundY = rig.ground;
  GAIT = { ...DEFAULT_GAIT, ...rig.gait }; // the creature's own walk numbers win
  resize();

  const creature = new THREE.Group();
  // Load all the pictures at once, then add them in back-to-front order
  const joints = await Promise.all(rig.parts.map(makePart));
  joints.forEach((joint) => creature.add(joint));
  scene.add(creature);
  // Look joints up by name, e.g. joint.tail
  const byName = Object.fromEntries(joints.map((j) => [j.name, j]));

  // Swap-in pictures (a blink, a folded wing) go on the same joint as their
  // part, hidden, so they move exactly like it. showSwap() flips between them.
  for (const [name, alt] of Object.entries(rig.alternates ?? {})) {
    const joint = byName[alt.part];
    const order = joint.children[0].renderOrder;
    const sprite = makeSprite(await loadTexture(alt.image), alt.pivot, order);
    sprite.visible = false;
    sprite.name = name;
    joint.add(sprite);
  }
  return byName;
}

// Show a part's swap-in picture by name, or its usual one when name is null
function showSwap(joint, name) {
  joint.children.forEach((sprite, i) => {
    sprite.visible = name ? sprite.name === name : i === 0;
  });
}

// ----- Signs of life (life clock) -------------------------------------------
// Small, slow movements that keep the creature alive even when it stands
// still. Distances are in rig pixels (the frame is drawn at about a third of
// its size on a laptop screen, so 6 here is about 2 on screen).
// Try changing these numbers to see the effect.
const ALIVE = {
  breathSeconds: 3.4, // one breath in and out
  chestSwell: 0.012,  // how much the torso grows on a breath in (1.2%)
  rise: 5,            // how far the head and wing ride up on a breath in
  headTilt: 1.2,      // degrees the head nods, slightly after the breath
  wingLift: 1.0,      // degrees the wing lifts with each breath
  tailSway: 2.5,      // degrees the tail sways
  tailSeconds: 4.7,   // one slow tail sway (not a multiple of the breath, so
                      // the two drift in and out of step and never look looped)
};

// The walk moves the whole body: it bobs down (rig pixels) and rocks nose
// up / nose down (pitch, radians) around the middle of the torso.
// Everything attached to the body (head, wing, tail, hips) rides along.
const body = { bob: 0, pitch: 0, pivot: new THREE.Vector2() };

// Where the moving body has carried a point that sits at (x, y) at rest
function onBody(x, y) {
  const c = Math.cos(body.pitch), s = Math.sin(body.pitch);
  const dx = x - body.pivot.x, dy = y - body.pivot.y;
  return new THREE.Vector2(body.pivot.x + c * dx - s * dy, body.pivot.y + s * dx + c * dy - body.bob);
}

// Set a joint to its rest pose, carried by the body, plus an offset
// (rotation in degrees, clockwise like rig.json).
function pose(joint, { dx = 0, dy = 0, rot = 0, sx = 1, sy = 1 } = {}) {
  const r = joint.userData.rest;
  const at = onBody(r.x, r.y);
  joint.position.set(at.x + dx, at.y - dy, 0); // dy is downward, like the rig
  joint.rotation.z = r.rot + body.pitch - THREE.MathUtils.degToRad(rot);
  joint.scale.set(r.sx * sx, r.sy * sy, 1);
}

function animateAlive(joint, time) {
  const TAU = Math.PI * 2;
  const breath = Math.sin((time / ALIVE.breathSeconds) * TAU);           // -1..1
  const later = Math.sin((time / ALIVE.breathSeconds) * TAU - 0.8);      // same, a beat behind
  // A second, faster wave on the tail keeps its sway from looking mechanical
  const sway = Math.sin((time / ALIVE.tailSeconds) * TAU)
             + 0.3 * Math.sin((time / ALIVE.tailSeconds) * TAU * 2.3);

  pose(joint.torso, { sy: 1 + ALIVE.chestSwell * breath, sx: 1 + ALIVE.chestSwell * 0.4 * breath });
  pose(joint.head, { dy: -ALIVE.rise * breath, rot: ALIVE.headTilt * later });
  pose(joint.wing, { dy: -ALIVE.rise * breath, rot: -ALIVE.wingLift * later });
  pose(joint.tail, { rot: ALIVE.tailSway * sway });
}

// ----- Little moments (life clock) -----------------------------------------
// Now and then a part swaps to another picture for a moment: a blink, or the
// wing folding to rest. The gaps are random, so they never look looped.
// Each: which part, which swap-in picture, seconds between (shortest,
// longest), and seconds it lasts (shortest, longest).
const MOMENTS = [
  { part: 'head', swap: 'head-blink', every: [2.5, 6], lasts: [0.12, 0.16] },
  { part: 'wing', swap: 'wing-folded', every: [10, 18], lasts: [2, 4] },
];
const between = ([lo, hi]) => lo + Math.random() * (hi - lo);

function animateMoments(joint, time) {
  for (const m of MOMENTS) {
    if (!joint[m.part]) continue;
    m.start ??= time + between(m.every); // first time: pick when it happens
    if (time >= m.start && !m.end) {
      m.end = time + between(m.lasts);
      showSwap(joint[m.part], m.swap);
    } else if (m.end && time >= m.end) {
      showSwap(joint[m.part], null);
      // Blinks sometimes come in pairs, like real ones
      const again = m.swap === 'head-blink' && Math.random() < 0.25;
      m.start = time + (again ? 0.18 : between(m.every));
      m.end = null;
    }
  }
}

// ----- Walk (walk clock) ---------------------------------------------------
// A lazy walk: one leg moves at a time, each a quarter of a cycle after the
// last (hind, front on the same side, other hind, other front), the way
// cats, bears and most four-legged animals walk slowly.
// Each foot spends `duty` of the cycle planted (sliding back as the world
// scrolls), and the rest swinging forward through the air.
// These are the defaults: each creature's rig.json has a "gait" with its own
// numbers, which replace these when it loads (see loadCreature).
const DEFAULT_GAIT = {
  cycle: 1.7,  // seconds for all four legs to take one step
  duty: 0.65,  // share of the cycle each foot is on the ground
  stride: 200, // how far a foot travels in one step (rig pixels)
  lift: 45,    // how high a swinging paw lifts
  peel: 22,    // degrees the heel lifts as a foot pushes off (toes stay down)
  bob: 5,      // how far the body dips as feet land
  pitch: 0.6,  // degrees the body rocks nose-up / nose-down
  // When each leg starts its step, as a share of the cycle
  phase: { 'near-hind-leg': 0, 'near-front-leg': 0.25, 'far-hind-leg': 0.5, 'far-front-leg': 0.75 },
  // Where each toe is mid-step, ahead of its hip or shoulder (rig pixels).
  // It depends on how the creature is drawn, so each rig sets its own.
  reach: { 'near-hind-leg': 0, 'far-hind-leg': 0, 'near-front-leg': 0, 'far-front-leg': 0 },
};
let GAIT = DEFAULT_GAIT;
// The ground must slide at exactly the speed a planted foot moves backward,
// otherwise the feet look like they're skating.
const groundSpeed = () => GAIT.stride / (GAIT.cycle * GAIT.duty);

const smooth = (u) => u * u * (3 - 2 * u); // "smoothstep" easing: slow start and finish
const DEG = Math.PI / 180;

// Where a toe should be at point t (0..1) in its own cycle, and how far the
// paw is tilted (negative = heel up)
function footTarget(name, leg, t) {
  const center = leg.rest.hip.x + GAIT.reach[name], groundY = leg.rest.toe.y;
  const peel = GAIT.peel * DEG;
  if (t < GAIT.duty) {
    // Planted: slide from front to back at ground speed. Near the end the
    // heel peels up while the toes stay put, ready to push off.
    const u = t / GAIT.duty;
    return { x: center + GAIT.stride * (0.5 - u), y: groundY, tilt: -peel * smooth(Math.max(0, (u - 0.75) / 0.25)) };
  }
  // Swinging: arc from back to front, paw curled at first, flat for landing
  const u = (t - GAIT.duty) / (1 - GAIT.duty);
  return {
    x: center + GAIT.stride * (smooth(u) - 0.5),
    y: groundY + GAIT.lift * Math.sin(Math.PI * u),
    tilt: -peel * (1 - smooth(u)),
  };
}

const lastLegPhase = {}; // each leg's cycle position last frame, to hear landings

// walking: 1 while walking, easing to 0 as the creature stops. As it eases
// down, lifted paws settle onto the ground and the body stops rocking, so it
// never freezes with a foot in the air.
function animateWalk(joint, walkTime, walking = 1) {
  const phase = (walkTime / GAIT.cycle) % 1;
  // Twice per cycle the body settles onto a newly planted hind paw, and rocks
  body.bob = walking * GAIT.bob * Math.sin(phase * Math.PI * 4);
  body.pitch = walking * GAIT.pitch * DEG * Math.cos(phase * Math.PI * 4);
  for (const [name, offset] of Object.entries(GAIT.phase)) {
    const leg = joint[name].userData.leg;
    const t = (phase + 1 - offset) % 1;
    // A leg's cycle runs 0 -> 1 then wraps back to 0, and that wrap is the
    // moment its paw lands. Far paws are a little quieter.
    if (t < (lastLegPhase[name] ?? t)) playFootstep(name.startsWith('near') ? 1 : 0.6);
    lastLegPhase[name] = t;
    const foot = footTarget(name, leg, t);
    const ground = leg.rest.toe.y;
    const y = ground + (foot.y - ground) * walking; // lifted paws come down
    const hip = onBody(leg.rest.hip.x, leg.rest.hip.y);
    poseLeg(leg, hip, new THREE.Vector2(foot.x, y), foot.tilt * walking); // and lie flat
  }
}

// ----- Ground (placeholder until the landscape arrives) ---------------------
// A line with evenly spaced marks that scroll left, so you can see whether
// the planted feet move with the ground or skate over it.
const MARK_GAP = 200;
function makeGround(y) {
  const ground = new THREE.Group();
  const material = new THREE.MeshBasicMaterial({ color: 0xc9bed2, depthTest: false });
  const line = new THREE.Mesh(new THREE.PlaneGeometry(frame[0] * 3, 3), material);
  line.position.set(frame[0] / 2, y, 0);
  ground.add(line);
  for (let x = -frame[0]; x < frame[0] * 2; x += MARK_GAP) {
    const mark = new THREE.Mesh(new THREE.PlaneGeometry(36, 8), material);
    mark.position.set(x, y - 14, 0);
    ground.add(mark);
  }
  ground.traverse((m) => { m.renderOrder = -1; }); // behind the creature
  scene.add(ground);
  return ground;
}

// ----- Springs: the secret to fluid motion ---------------------------------
// Instead of jumping straight to a new value, a spring pulls toward it,
// overshoots a little, and settles — like a real, physical thing.
// stiffness = how strongly it pulls; damping = how quickly it calms down.
function makeSpring(value = 0) {
  return { value, velocity: 0, target: value };
}
function stepSpring(s, dt, stiffness = 70, damping = 9) {
  const accel = stiffness * (s.target - s.value) - damping * s.velocity;
  s.velocity += accel * dt;
  s.value += s.velocity * dt;
}

// ----- Controls ------------------------------------------------------------
const soundButton = document.getElementById('sound');
soundButton.addEventListener('click', () => {
  soundButton.textContent = toggleSound() ? '🔊 Sound on' : '🔇 Sound off';
});

// Play / pause the walk. Instead of freezing instantly, a spring eases the
// walk speed between 1 (walking) and 0 (standing), so the creature slows to a
// halt and settles onto all four feet.
const walkSpeed = makeSpring(1);
const walkButton = document.getElementById('walk');
function toggleWalk() {
  const walking = walkSpeed.target === 0; // flip the current state
  walkSpeed.target = walking ? 1 : 0;
  walkButton.textContent = walking ? '⏸ Pause' : '▶ Play';
  walkButton.setAttribute('aria-label', walking ? 'Pause walking' : 'Resume walking');
}
walkButton.addEventListener('click', toggleWalk);
window.addEventListener('keydown', (e) => {
  // Skip when a button has focus: space already "clicks" a focused button,
  // so handling it here too would toggle twice.
  if (e.code !== 'Space' || e.target.closest('button, input')) return;
  e.preventDefault(); // stop the page from scrolling
  toggleWalk();
});

// ----- Animation loop ------------------------------------------------------
let last = performance.now();
let time = 0;     // "life clock": always runs (breathing, sway, springs)
let walkTime = 0; // "walk clock": only advances while walking (steps, ground)

resize();
loadCreature().then((joint) => {
  const ground = makeGround(-groundY);
  body.pivot.set(joint.torso.userData.rest.x, joint.torso.userData.rest.y);
  renderer.setAnimationLoop((now) => {
    const dt = Math.min((now - last) / 1000, 1 / 30); // avoid huge jumps after tab switches
    last = now;
    time += dt;

    // stiffness 25 / damping 10 = "critically damped": smooth, no overshoot
    // (an overshoot would make the creature briefly walk backward)
    stepSpring(walkSpeed, dt, 25, 10);
    if (walkSpeed.value > 0.001) walkTime += dt * walkSpeed.value;

    animateWalk(joint, walkTime, THREE.MathUtils.clamp(walkSpeed.value, 0, 1));
    animateAlive(joint, time);
    animateMoments(joint, time);
    // The world moves, not the creature: slide the marks left, wrapping
    // every MARK_GAP so they never run out
    ground.position.x = -((walkTime * groundSpeed()) % MARK_GAP);
    renderer.render(scene, camera);
  });
});
