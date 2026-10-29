// ---------------------------------------------------------------------------
// creature.glsl — the fragment shader that draws the whole scene.
//
// How it works (in plain words):
// For every pixel, we shoot an imaginary ray from the camera into the world.
// The creature isn't made of triangles — it's described by a "distance
// function" (SDF): give it any point in space and it tells you how far that
// point is from the creature's surface. We step along the ray by that distance
// until we touch the surface. This is called "raymarching".
//
// The magic for Strange Fauna: SDF shapes can be blended with "smooth min" (smin),
// so a growing tail melts out of the body like clay instead of popping on.
// ---------------------------------------------------------------------------

uniform vec2  uResolution;   // canvas size in pixels
uniform float uTime;         // seconds since start
uniform float uScroll;       // how far the ground has scrolled (fakes walking forward)
uniform float uCamAngle;     // 0 = profile view; changes when you drag
uniform vec3  uBody;         // centre of the body blob
uniform vec3  uHead;         // centre of the head
uniform vec3  uLegs[6];      // near leg: hip, knee, foot — then far leg: hip, knee, foot
uniform vec4  uTail[10];     // tail points: xyz = position, w = thickness
uniform float uTailAmount;   // 0..1 how grown the tail is

// ----- Small helper functions ----------------------------------------------

// Pseudo-random number from a 2D position (same input -> same output)
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

// "Smooth minimum": joins two shapes with a soft, fleshy blend.
// k = how wide the blend is. Bigger k = gooier joins.
float smin(float a, float b, float k) {
  float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
  return mix(b, a, h) - k * h * (1.0 - h);
}

float sdSphere(vec3 p, float r) { return length(p) - r; }

// A squashed sphere (r = radius on each axis)
float sdEllipsoid(vec3 p, vec3 r) {
  float k0 = length(p / r);
  float k1 = length(p / (r * r));
  return k0 * (k0 - 1.0) / k1;
}

// A tapered tube from point a (radius ra) to point b (radius rb).
// Used for leg segments and tail segments.
float sdTaper(vec3 p, vec3 a, vec3 b, float ra, float rb) {
  vec3 pa = p - a, ba = b - a;
  float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-5), 0.0, 1.0);
  return length(pa - ba * h) - mix(ra, rb, h);
}

// ----- The creature --------------------------------------------------------
// Returns vec2(distance, material). material: 0 = skin, 1 = eye.
vec2 map(vec3 p) {
  // Body + head, smoothly merged into one blob
  float d = sdEllipsoid(p - uBody, vec3(0.75, 0.6, 0.55));
  d = smin(d, sdSphere(p - uHead, 0.38), 0.25);

  // Two legs, each made of a thigh and a shin
  for (int i = 0; i < 2; i++) {
    vec3 hip = uLegs[i * 3], knee = uLegs[i * 3 + 1], foot = uLegs[i * 3 + 2];
    float leg = min(sdTaper(p, hip, knee, 0.16, 0.11),
                    sdTaper(p, knee, foot, 0.11, 0.09));
    d = smin(d, leg, 0.12);
  }

  // Tail: a chain of tapered segments, blended in with a big gooey smin
  if (uTailAmount > 0.001) {
    float t = 1e5;
    for (int i = 0; i < 9; i++) {
      t = min(t, sdTaper(p, uTail[i].xyz, uTail[i + 1].xyz, uTail[i].w, uTail[i + 1].w));
    }
    d = smin(d, t, 0.3);
  }

  // Eyes: a hard union (plain min) so they stay crisp, not melted.
  // abs(q.z) mirrors one eye to make two.
  vec3 q = p - (uHead + vec3(0.27, 0.1, 0.0));
  q.z = abs(q.z) - 0.17;
  float eye = sdSphere(q, 0.09);
  if (eye < d) return vec2(eye, 1.0);

  return vec2(d, 0.0);
}

// Walk along a ray until we hit the creature (or give up)
vec2 march(vec3 ro, vec3 rd, float tMax) {
  float t = 0.0;
  for (int i = 0; i < 120; i++) {
    vec2 h = map(ro + rd * t);
    if (h.x < 0.001) return vec2(t, h.y);
    t += h.x * 0.9;              // 0.9 = small safety margin for the blends
    if (t > tMax) break;
  }
  return vec2(-1.0, 0.0);        // missed
}

// Which way the surface faces at point p (needed for lighting)
vec3 calcNormal(vec3 p) {
  const vec2 e = vec2(1.0, -1.0) * 0.001;
  return normalize(e.xyy * map(p + e.xyy).x + e.yyx * map(p + e.yyx).x +
                   e.yxy * map(p + e.yxy).x + e.xxx * map(p + e.xxx).x);
}

// Soft shadows: march toward the light; near-misses give a soft penumbra
float softShadow(vec3 ro, vec3 rd) {
  float res = 1.0, t = 0.02;
  for (int i = 0; i < 40; i++) {
    float h = map(ro + rd * t).x;
    res = min(res, 8.0 * h / t);
    t += clamp(h, 0.02, 0.3);
    if (res < 0.001 || t > 6.0) break;
  }
  return clamp(res, 0.0, 1.0);
}

// ----- The world -----------------------------------------------------------

vec3 sky(vec3 rd) {
  // Warm peach horizon fading up into deep violet
  vec3 col = mix(vec3(0.98, 0.62, 0.45), vec3(0.28, 0.16, 0.42), smoothstep(-0.05, 0.5, rd.y));
  // A big pale alien moon behind the creature
  vec3 moonDir = normalize(vec3(-0.4, 0.35, -1.0));
  col += vec3(1.0, 0.85, 0.7) * smoothstep(0.995, 0.997, dot(rd, moonDir)) * 0.6;
  return col;
}

vec3 groundColor(vec3 p) {
  vec2 g = vec2(p.x + uScroll, p.z);           // uScroll makes the ground slide by
  vec3 col = vec3(0.22, 0.12, 0.30);

  // Scattered glowing spots, like alien moss
  vec2 cell = floor(g * 1.2);
  vec2 f = fract(g * 1.2) - 0.5;
  vec2 off = vec2(hash(cell + 7.1), hash(cell + 3.3)) - 0.5;
  float spot = smoothstep(0.18, 0.12, length(f - off * 0.5)) * step(0.55, hash(cell));
  col = mix(col, vec3(0.35, 0.85, 0.75), spot);

  // Faint bands so you can feel the motion
  col *= 0.85 + 0.15 * sin(g.x * 3.0);
  return col;
}

// ----- Main: runs once per pixel -------------------------------------------
void main() {
  // Pixel position, centred, so the middle of the screen is (0,0)
  vec2 uv = (gl_FragCoord.xy - 0.5 * uResolution) / uResolution.y;

  // Camera orbiting around the creature
  vec3 target = vec3(0.0, 1.2, 0.0);
  vec3 ro = target + vec3(sin(uCamAngle) * 6.5, 0.6, cos(uCamAngle) * 6.5);
  vec3 fw = normalize(target - ro);
  vec3 rt = normalize(cross(fw, vec3(0.0, 1.0, 0.0)));
  vec3 up = cross(rt, fw);
  vec3 rd = normalize(uv.x * rt + uv.y * up + 1.8 * fw);   // 1.8 = lens zoom

  vec3 L = normalize(vec3(-0.5, 0.8, 0.6));   // light direction
  vec3 col = sky(rd);

  // Where does this ray hit the flat ground (y = 0), if at all?
  float tGround = rd.y < 0.0 ? -ro.y / rd.y : 1e5;
  vec2 hit = march(ro, rd, min(tGround, 30.0));

  if (hit.x > 0.0) {
    // We hit the creature
    vec3 p = ro + rd * hit.x;
    vec3 n = calcNormal(p);
    vec3 base = hit.y > 0.5 ? vec3(0.05, 0.04, 0.08) : vec3(0.95, 0.45, 0.42);
    float dif = clamp(dot(n, L) * 0.5 + 0.5, 0.0, 1.0);     // soft "wrapped" light
    float sh  = softShadow(p + n * 0.01, L);
    float rim = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0); // glowy edge light
    col = base * (0.35 + 0.75 * dif * mix(0.5, 1.0, sh));
    col += rim * vec3(0.4, 0.8, 1.0) * 0.5;
    if (hit.y > 0.5) col += pow(max(dot(reflect(rd, n), L), 0.0), 30.0); // eye glint
  } else if (tGround < 1e4) {
    // We hit the ground
    vec3 p = ro + rd * tGround;
    col = groundColor(p);
    col *= mix(0.45, 1.0, softShadow(p + vec3(0.0, 0.01, 0.0), L));
    // Fade into the sky with distance (atmospheric haze)
    col = mix(col, sky(normalize(vec3(rd.x, 0.02, rd.z))), 1.0 - exp(-0.04 * tGround));
  }

  gl_FragColor = vec4(col, 1.0);
}
