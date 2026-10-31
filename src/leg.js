// ---------------------------------------------------------------------------
// leg.js — a leg drawn as ONE picture that still bends at its joints.
//
// Inside each leg picture we imagine a wire with three bones:
//   thigh (hip -> knee), shin (knee -> ankle), paw (ankle -> toe)
// The picture is cut into a fine grid of little triangles, and every grid
// point is "pinned" to the bones nearest to it. Points near a joint are
// pinned to both bones, so the picture bends smoothly there instead of
// cracking. Moving the bones then moves the picture: this is called skinning,
// and it's how 2D cut-out tools like Spine animate drawings.
//
// Everything here works in frame coordinates (rig pixels) with y flipped to
// point up, the same as the rest of the scene.
// ---------------------------------------------------------------------------
import * as THREE from 'three';

const GRID = 14;      // size of a grid cell in pixels: smaller = smoother bends
const SOFTNESS = 18;  // how wide the blend zone around a joint is
const MAX_STRETCH = 1.05; // a leg may stretch 5% when it can't otherwise reach

const vec = (p) => new THREE.Vector2(p[0], -p[1]);

// Shortest distance from point p to the segment a-b
function distToSegment(p, a, b) {
  const ab = b.clone().sub(a);
  const t = THREE.MathUtils.clamp(p.clone().sub(a).dot(ab) / ab.lengthSq(), 0, 1);
  return p.distanceTo(a.clone().addScaledVector(ab, t));
}

export function makeLeg(part, texture, order) {
  const { width: w, height: h } = texture.image;
  // Where the picture's top-left corner sits in the frame
  const left = part.at[0] - part.pivot[0], top = part.at[1] - part.pivot[1];

  const rest = { hip: vec(part.at), knee: vec(part.knee), ankle: vec(part.ankle), toe: vec(part.toe) };
  const bones = [[rest.hip, rest.knee], [rest.knee, rest.ankle], [rest.ankle, rest.toe]];

  // A grid-shaped plane laid exactly over the picture's spot in the frame
  const geometry = new THREE.PlaneGeometry(w, h, Math.ceil(w / GRID), Math.ceil(h / GRID));
  geometry.translate(left + w / 2, -(top + h / 2), 0);
  const restPositions = geometry.attributes.position.array.slice();

  // Pin each grid point to the bones: the closer a bone, the stronger the pin
  const count = geometry.attributes.position.count;
  const weights = new Float32Array(count * 3);
  const p = new THREE.Vector2();
  for (let i = 0; i < count; i++) {
    p.set(restPositions[i * 3], restPositions[i * 3 + 1]);
    let total = 0;
    for (let b = 0; b < 3; b++) {
      const d = distToSegment(p, bones[b][0], bones[b][1]);
      const pull = 1 / (d * d + SOFTNESS * SOFTNESS) ** 2;
      weights[i * 3 + b] = pull;
      total += pull;
    }
    for (let b = 0; b < 3; b++) weights[i * 3 + b] /= total;
  }

  const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthTest: false });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.renderOrder = order;
  mesh.frustumCulled = false; // its shape changes every frame
  mesh.name = part.name;

  const thigh = rest.knee.distanceTo(rest.hip), shin = rest.ankle.distanceTo(rest.knee);
  // Which side of the hip-ankle line the knee bends toward (kept while walking)
  const toAnkle = rest.ankle.clone().sub(rest.hip), toKnee = rest.knee.clone().sub(rest.hip);
  const bendSide = Math.sign(toAnkle.cross(toKnee)) || 1;
  // The paw's shape: where the ankle sits relative to the toe
  const toeToAnkle = rest.ankle.clone().sub(rest.toe);

  return { mesh, rest, bones, restPositions, weights, thigh, shin, bendSide, toeToAnkle };
}

const angleOf = (from, to) => Math.atan2(to.y - from.y, to.x - from.x);

// Bend the leg: hip and toe are where they should be now (frame coords, y up),
// pawTilt is how far the paw rotates from its drawn angle (radians,
// negative = heel up / toes down).
export function poseLeg(leg, hip, toe, pawTilt = 0) {
  const { rest, thigh, shin } = leg;

  // 1. The paw is rigid: rotate its drawn shape around the toe to find the ankle
  const ankleGoal = leg.toeToAnkle.clone().rotateAround(new THREE.Vector2(), pawTilt).add(toe);

  // 2. Two-bone IK ("inverse kinematics"): given the hip and ankle, the
  //    triangle hip-knee-ankle has known sides, so the law of cosines tells us
  //    the angle at the hip, and so where the knee must be.
  const toGoal = ankleGoal.clone().sub(hip);
  let reach = toGoal.length();
  // If the ankle is out of reach, let the leg stretch a touch, then give up
  // and let the foot hang slightly short
  const stretch = THREE.MathUtils.clamp(reach / (thigh + shin), 1, MAX_STRETCH);
  const a = thigh * stretch, b = shin * stretch;
  reach = THREE.MathUtils.clamp(reach, Math.abs(a - b) + 1, a + b - 0.01);
  const cosHip = (a * a + reach * reach - b * b) / (2 * a * reach);
  const hipAngle = Math.atan2(toGoal.y, toGoal.x) + leg.bendSide * Math.acos(cosHip);
  const knee = new THREE.Vector2(Math.cos(hipAngle), Math.sin(hipAngle)).multiplyScalar(a).add(hip);
  const ankle = toGoal.setLength(reach).add(hip); // where the ankle actually got to

  // 3. Each bone's move, as "rotate by this much around the joint, then shift"
  const moves = [
    { from: rest.hip, to: hip, turn: angleOf(hip, knee) - angleOf(rest.hip, rest.knee), scale: stretch },
    { from: rest.knee, to: knee, turn: angleOf(knee, ankle) - angleOf(rest.knee, rest.ankle), scale: stretch },
    { from: rest.ankle, to: ankle, turn: pawTilt, scale: 1 },
  ].map((m) => ({ ...m, cos: Math.cos(m.turn) * m.scale, sin: Math.sin(m.turn) * m.scale }));

  // 4. Move every grid point by the blend of its bones' moves
  const pos = leg.mesh.geometry.attributes.position;
  const out = pos.array, src = leg.restPositions, wts = leg.weights;
  for (let i = 0; i < pos.count; i++) {
    const x = src[i * 3], y = src[i * 3 + 1];
    let nx = 0, ny = 0;
    for (let k = 0; k < 3; k++) {
      const w = wts[i * 3 + k];
      if (w < 0.001) continue;
      const m = moves[k], dx = x - m.from.x, dy = y - m.from.y;
      nx += w * (m.to.x + m.cos * dx - m.sin * dy);
      ny += w * (m.to.y + m.sin * dx + m.cos * dy);
    }
    out[i * 3] = nx;
    out[i * 3 + 1] = ny;
  }
  pos.needsUpdate = true;
}
