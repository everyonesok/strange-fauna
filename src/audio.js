// ---------------------------------------------------------------------------
// audio.js — creature sounds, synthesized live with the Web Audio API.
//
// There are no sound files yet. Each footstep is cooked up on the spot from
// two ingredients, a bit like a foley artist layering sounds:
//   1. THUMP  — a low tone that quickly drops in pitch (the weight landing)
//   2. SQUISH — a burst of hiss pushed through a sweeping filter (the wet,
//               blobby squelch)
// Later we can swap these for recorded or AI-generated samples; the timing
// code in main.js won't need to change.
// ---------------------------------------------------------------------------

let ctx = null;         // the AudioContext: the browser's audio engine
let master = null;      // master volume knob everything plugs into
let noiseBuffer = null; // half a second of white noise, reused for every squish
let enabled = false;

function setup() {
  ctx = new AudioContext();

  // A compressor on the master output stops loud overlapping sounds from distorting
  const compressor = ctx.createDynamicsCompressor();
  master = ctx.createGain();
  master.gain.value = 0.8;
  master.connect(compressor).connect(ctx.destination);

  // White noise = random values. Filtering it is how you make hisses, splats and squelches.
  noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.5, ctx.sampleRate);
  const data = noiseBuffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
}

// Browsers only allow sound after the user clicks something, so audio is
// switched on by a button rather than automatically.
export function toggleSound() {
  if (!ctx) setup();
  enabled = !enabled;
  if (enabled) ctx.resume();
  else ctx.suspend();
  return enabled;
}

// Returns a number slightly above or below 1, e.g. vary(0.1) -> 0.9..1.1.
// Tiny random differences stop repeated steps sounding robotic ("machine-gunning").
const vary = (amount) => 1 + (Math.random() * 2 - 1) * amount;

// loudness: 1 = near foot, smaller = quieter (e.g. the far foot)
export function playFootstep(loudness = 1) {
  if (!enabled) return;

  const t = ctx.currentTime;          // "now" on the audio engine's clock
  const vol = 0.6 * loudness * vary(0.15);
  const pitch = vary(0.08);

  // ----- 1. THUMP: a sine tone sliding from 130Hz down to 45Hz -----
  const osc = ctx.createOscillator();
  osc.frequency.setValueAtTime(130 * pitch, t);
  osc.frequency.exponentialRampToValueAtTime(45 * pitch, t + 0.12);

  // Volume "envelope": snap up almost instantly, then fade out
  const thumpGain = ctx.createGain();
  thumpGain.gain.setValueAtTime(0.0001, t);
  thumpGain.gain.exponentialRampToValueAtTime(vol, t + 0.006);
  thumpGain.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);

  osc.connect(thumpGain).connect(master);
  osc.start(t);
  osc.stop(t + 0.3);

  // ----- 2. SQUISH: noise through a filter sweeping from bright to dull -----
  const noise = ctx.createBufferSource();
  noise.buffer = noiseBuffer;

  // A "bandpass" filter only lets a narrow range of frequencies through.
  // Sweeping that range downward fast is what gives the wet "squelch".
  const filter = ctx.createBiquadFilter();
  filter.type = 'bandpass';
  filter.Q.value = 6;                 // higher Q = narrower, more "resonant" and wet
  filter.frequency.setValueAtTime(1400 * pitch, t);
  filter.frequency.exponentialRampToValueAtTime(250 * pitch, t + 0.14);

  const squishGain = ctx.createGain();
  squishGain.gain.setValueAtTime(0.0001, t);
  squishGain.gain.exponentialRampToValueAtTime(vol * 1.5, t + 0.015);
  squishGain.gain.exponentialRampToValueAtTime(0.0001, t + 0.18);

  noise.connect(filter).connect(squishGain).connect(master);
  noise.start(t);
  noise.stop(t + 0.2);
}
