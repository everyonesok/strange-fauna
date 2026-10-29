// ---------------------------------------------------------------------------
// main.js — the "puppeteer".
// Every frame (~60x per second) we:
//   1. work out where the body, legs and tail should be
//   2. send those numbers ("uniforms") to the shader, which draws them
// ---------------------------------------------------------------------------
import * as THREE from 'three';
import fragmentShader from './creature.glsl?raw'; // ?raw = load the file as plain text
import { toggleSound, playFootstep } from './audio.js';

const { Vector3, Vector4 } = THREE;

// ----- Renderer: one full-screen rectangle the shader paints onto ----------
const renderer = new THREE.WebGLRenderer({ antialias: false });
// Raymarching is heavy on the graphics card, so cap the resolution a bit
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.Camera(); // placeholder — the shader has its own camera

const TAIL_POINTS = 10;
const uniforms = {
  uResolution: { value: new THREE.Vector2() },
  uTime: { value: 0 },
  uScroll: { value: 0 },
  uCamAngle: { value: 0 },
  uBody: { value: new Vector3() },
  uHead: { value: new Vector3() },
  uLegs: { value: Array.from({ length: 6 }, () => new Vector3()) },
  uTail: { value: Array.from({ length: TAIL_POINTS }, () => new Vector4()) },
  uTailAmount: { value: 0 },
};

const screenQuad = new THREE.Mesh(
  new THREE.PlaneGeometry(2, 2),
  new THREE.ShaderMaterial({
    uniforms,
    vertexShader: 'void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader,
  }),
);
screenQuad.frustumCulled = false;
scene.add(screenQuad);

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.getDrawingBufferSize(uniforms.uResolution.value);
}
window.addEventListener('resize', resize);
resize();

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

// ----- Walk cycle ----------------------------------------------------------
// One cycle = left step + right step. Each foot spends half the cycle on the
// ground (sliding backward as the world scrolls) and half swinging forward.
const WALK = { cycle: 1.1, stride: 0.9, lift: 0.28 };
// The ground must slide at exactly the speed a planted foot moves backward,
// otherwise the feet look like they're skating.
const GROUND_SPEED = WALK.stride / (WALK.cycle * 0.5);

// Where a foot is (relative to its hip) at point t (0..1) in its cycle
function footOffset(t) {
  if (t < 0.5) {
    // Planted: slide from front to back
    const u = t / 0.5;
    return { x: WALK.stride * (0.5 - u), y: 0 };
  }
  // Swinging: arc from back to front, lifted off the ground
  const u = (t - 0.5) / 0.5;
  const eased = u * u * (3 - 2 * u); // "smoothstep" easing
  return { x: WALK.stride * (-0.5 + eased), y: WALK.lift * Math.sin(Math.PI * u) };
}

// Two-bone IK ("inverse kinematics"): given the hip and where the foot must
// be, work out where the knee goes. Uses the triangle rule (law of cosines).
const THIGH = 0.62, SHIN = 0.62;
function solveKnee(hip, foot, kneeOut) {
  const dx = foot.x - hip.x, dy = foot.y - hip.y;
  const dist = Math.hypot(dx, dy);
  const d = Math.min(dist, THIGH + SHIN - 0.001); // can't reach further than the leg is long
  const dirX = dx / dist, dirY = dy / dist;
  const cosA = (THIGH * THIGH + d * d - SHIN * SHIN) / (2 * THIGH * d);
  const sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
  // Bend direction: perpendicular to hip->foot, pointing forward
  const perpX = -dirY, perpY = dirX;
  kneeOut.set(
    hip.x + THIGH * (dirX * cosA + perpX * sinA),
    hip.y + THIGH * (dirY * cosA + perpY * sinA),
    hip.z,
  );
}

// ----- Tail ----------------------------------------------------------------
function updateTail(amount, time) {
  const a = Math.max(0, amount);           // the spring can briefly dip below 0
  const body = uniforms.uBody.value;
  const length = 2.4 * a;
  const segment = length / (TAIL_POINTS - 1);
  const thickness = Math.min(1, a * 2.5);  // fattens quickly, then lengthens

  let x = body.x - 0.62, y = body.y + 0.05;
  let angle = Math.PI + 0.4;               // start pointing back and a little down
  for (let i = 0; i < TAIL_POINTS; i++) {
    const along = i / (TAIL_POINTS - 1);   // 0 at the base, 1 at the tip
    // Each point swings a little later than the one before -> a wave travels down the tail
    const z = 0.25 * along * Math.sin(time * 2.2 - i * 0.5) * a;
    const radius = (0.26 + (0.04 - 0.26) * along) * thickness;
    uniforms.uTail.value[i].set(x, y, z, radius);

    angle -= 0.12;                                          // curl upward toward the tip
    angle += 0.18 * along * Math.sin(time * 3.0 - i * 0.6); // sway
    x += Math.cos(angle) * segment;
    y += Math.sin(angle) * segment;
  }
}

// ----- Controls ------------------------------------------------------------
const tail = makeSpring(0);
document.getElementById('tail').addEventListener('input', (e) => {
  tail.target = parseFloat(e.target.value);
});

const soundButton = document.getElementById('sound');
soundButton.addEventListener('click', () => {
  soundButton.textContent = toggleSound() ? '🔊 Sound on' : '🔇 Sound off';
});

// Play / pause the walk. Instead of freezing instantly, a spring eases the
// walk speed between 1 (walking) and 0 (standing), so the creature slows to a halt.
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
  // Skip when a button or slider has focus: space already "clicks" a focused
  // button, so handling it here too would toggle twice.
  if (e.code !== 'Space' || e.target.closest('button, input')) return;
  e.preventDefault(); // stop the page from scrolling
  toggleWalk();
});

// Drag to orbit the camera; let go and it springs back to profile
const cam = makeSpring(0);
let dragging = false;
renderer.domElement.addEventListener('pointerdown', (e) => {
  dragging = true;
  renderer.domElement.setPointerCapture(e.pointerId);
});
renderer.domElement.addEventListener('pointermove', (e) => {
  if (dragging) cam.target += e.movementX * 0.01;
});
renderer.domElement.addEventListener('pointerup', () => {
  dragging = false;
  cam.target = 0;
});

// ----- Animation loop ------------------------------------------------------
let last = performance.now();
let time = 0;     // "life clock": always runs (tail sway, springs, camera)
let walkTime = 0; // "walk clock": only advances while walking (steps, bob, ground)
const hip = new Vector3();
// Each leg's cycle position from the previous frame, used to detect landings
const lastLegPhase = [0, 0.5];

renderer.setAnimationLoop((now) => {
  const dt = Math.min((now - last) / 1000, 1 / 30); // avoid huge jumps after tab switches
  last = now;
  time += dt;

  stepSpring(tail, dt);
  stepSpring(cam, dt, dragging ? 400 : 20, dragging ? 40 : 7);
  // stiffness 25 / damping 10 = "critically damped": smooth, no overshoot
  // (an overshoot would make the creature briefly walk backward)
  stepSpring(walkSpeed, dt, 25, 10);
  // A spring only *approaches* 0 and never quite gets there, so treat
  // anything below 0.1% speed as fully stopped.
  if (walkSpeed.value > 0.001) walkTime += dt * walkSpeed.value;

  const phase = (walkTime / WALK.cycle) % 1;

  // Body bobs down each time a foot lands (twice per cycle)
  const bob = -0.06 * Math.cos(phase * Math.PI * 4);
  uniforms.uBody.value.set(0, 1.5 + bob, 0);
  uniforms.uHead.value.set(0.62, 1.92 + bob * 0.5 + 0.03 * Math.sin(phase * Math.PI * 4 - 1), 0);

  // Legs: near leg (z = +0.28) and far leg (z = -0.28), half a cycle apart
  for (let leg = 0; leg < 2; leg++) {
    const side = leg === 0 ? 0.28 : -0.28;
    hip.set(0.05, uniforms.uBody.value.y - 0.38, side);
    const legPhase = (phase + leg * 0.5) % 1;

    // A leg's cycle runs 0 -> 1 then wraps back to 0, and that wrap is the
    // moment the foot touches down. If the number went backward since last frame,
    // the foot just landed. The far foot (leg 1) is a bit quieter.
    if (legPhase < lastLegPhase[leg]) playFootstep(leg === 0 ? 1 : 0.7);
    lastLegPhase[leg] = legPhase;

    const f = footOffset(legPhase);
    const foot = uniforms.uLegs.value[leg * 3 + 2].set(hip.x + f.x, 0.1 + f.y, side);
    uniforms.uLegs.value[leg * 3].copy(hip);
    solveKnee(hip, foot, uniforms.uLegs.value[leg * 3 + 1]);
  }

  updateTail(tail.value, time);
  uniforms.uTailAmount.value = tail.value;
  uniforms.uTime.value = time;
  uniforms.uScroll.value = walkTime * GROUND_SPEED;
  uniforms.uCamAngle.value = cam.value;

  renderer.render(scene, camera);
});
