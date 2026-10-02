"""AURA — a click-through light layer over the whole screen.

Every frame: grab the root window (party/capture.py), hand it to the GPU, recover
the clean screen (un-blend our own last frame; keep what we last saw beneath the
lens), find every edge (window borders, lines, glyph strokes), blur it into a halo,
tint it, add the sky (stars, nebula, ghosts), the edge waves and the black-hole
lens, stamp sprites (stories, brainwash), and hand KWin a premultiplied ARGB layer.
No app is touched. `AuraPipeline` is window-agnostic: `render_png` proves it offline.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from OpenGL import GL as gl
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QSurfaceFormat
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLShader, QOpenGLShaderProgram, QOpenGLWindow

from ..analysis import N_BINS

COLOR_MODES = ["PEARL", "MONO", "RAINBOW", "FIRE", "ICE", "HOLY", "AURORA", "LALA"]
PHRASE_ANIMS = ["FADE", "PULSE", "RISE", "TYPE", "FLASH"]
PHRASE_FONT_NAMES = ["MONO", "SERIF", "SANS", "HANDSCRIPT"]


def phrase_tint(mode: int, hue: float, t: float, custom: tuple[float, float] = (200.0, 0.8)) -> tuple[float, float, float]:
    """The colour worlds, as one tint for a text quad (the shader palettes, in Python). -2 = his own hue/light."""
    import math
    if mode == -2:
        c = QColor.fromHslF((custom[0] % 360) / 360, 0.9, max(0.05, min(0.98, custom[1])))
    elif mode == 1:
        c = QColor.fromHsvF((hue % 360) / 360, 0.75, 1.0)
    elif mode == 2:
        c = QColor.fromHsvF((t * 0.08) % 1.0, 0.85, 1.0)
    elif mode == 3:
        c = QColor.fromRgbF(1.0, 0.55 + 0.25 * math.sin(t * 3), 0.2)
    elif mode == 4:
        c = QColor.fromRgbF(0.6, 0.85, 1.0)
    elif mode == 5:
        c = QColor.fromRgbF(1.0, 0.85, 0.5)
    elif mode == 6:
        b = 0.5 + 0.5 * math.sin(t * 0.7)
        c = QColor.fromRgbF(0.2 + 0.4 * b, 0.9 - 0.5 * b, 0.5 + 0.5 * b)
    elif mode == 7:
        k = t * 0.4
        c = QColor.fromRgbF(1.0, 0.80 + 0.1 * math.sin(k), 0.88 + 0.08 * math.sin(k + 2.0))
    else:
        k = t * 0.3
        c = QColor.fromRgbF(0.85 + 0.15 * math.sin(k), 0.85 + 0.15 * math.sin(k + 2.1), 0.9 + 0.1 * math.sin(k + 4.2))
    return c.redF(), c.greenF(), c.blueF()
BORDER_STYLES = ["SOFT", "NEON", "DOUBLE", "OUTLINE", "ELECTRIC", "SHADOW", "WATER", "GHOST", "FIRE", "PASTEL"]
WAVE_STYLES = ["OFF", "ELECTRIC", "AQUA", "FIRE", "GHOST", "MAGIC"]
EDGE_PRESETS = [(1, "BOTTOM"), (15, "ALL"), (2, "TOP"), (12, "SIDES"), (3, "TOP+BOTTOM")]

VERT = """#version 330 core
const vec2 verts[3] = vec2[3](vec2(-1.0,-1.0), vec2(3.0,-1.0), vec2(-1.0,3.0));
out vec2 uv;
void main(){ vec2 p = verts[gl_VertexID]; uv = (p + 1.0) * 0.5; gl_Position = vec4(p, 0.0, 1.0); }
"""
NOISE = """
float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  float a = hash21(i), b = hash21(i + vec2(1, 0)), c = hash21(i + vec2(0, 1)), d = hash21(i + vec2(1, 1));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { v += a * vnoise(p); p = p * 2.03 + 11.7; a *= 0.5; } return v; }
"""
CLEAN = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D screen; uniform sampler2D prevGlow; uniform sampler2D prevClean;
void main(){
  vec4 c = texture(screen, uv); vec4 g = texture(prevGlow, uv);
  if (g.a > 0.97) { frag = vec4(texture(prevClean, uv).rgb, 1.0); return; }   // only what we drew SOLID (lens, a body at 0.985): keep what we last saw beneath
  float a = min(g.a, 0.95);
  frag = vec4(clamp((c.rgb - g.rgb) / (1.0 - a), 0.0, 1.0), 1.0);
}
"""
EDGES = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D clean; uniform vec2 texel; uniform float t0; uniform float t1;
float luma(vec2 p){ return dot(texture(clean, p).rgb, vec3(0.299, 0.587, 0.114)); }
void main(){
  float tl=luma(uv+texel*vec2(-1,-1)), t=luma(uv+texel*vec2(0,-1)), tr=luma(uv+texel*vec2(1,-1));
  float l=luma(uv+texel*vec2(-1,0)),                                 r=luma(uv+texel*vec2(1,0));
  float bl=luma(uv+texel*vec2(-1,1)), b=luma(uv+texel*vec2(0,1)),  br=luma(uv+texel*vec2(1,1));
  float gx = -tl - 2.0*l - bl + tr + 2.0*r + br;
  float gy = -tl - 2.0*t - tr + bl + 2.0*b + br;
  float e = smoothstep(t0, t1, length(vec2(gx, gy)) / 4.0);
  frag = vec4(e, e, e, 1.0);
}
"""
BLUR = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D src; uniform vec2 dir;
const float w[5] = float[5](0.227, 0.195, 0.122, 0.054, 0.016);
void main(){
  float s = texture(src, uv).r * w[0];
  for (int i = 1; i < 5; i++) { s += texture(src, uv + dir * float(i)).r * w[i]; s += texture(src, uv - dir * float(i)).r * w[i]; }
  frag = vec4(s, s, s, 1.0);
}
"""
COMPOSE = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D edges; uniform sampler2D halo; uniform sampler2D clean; uniform sampler2D spectrum;
uniform float time; uniform float hue; uniform float loud; uniform float bass; uniform float flash;
uniform float coreAmt; uniform float haloAmt; uniform float astralAmt; uniform float ghostAmt;
uniform int colorMode; uniform int border; uniform int waveStyle; uniform int waveShape; uniform int edgeMask; uniform int barColor; uniform float barHeight; uniform float barFill; uniform vec2 lens; uniform float lensOn;
uniform float bright;
uniform vec4 streak; uniform vec2 streakLenAmt;      // a shooting star: head uv, direction, (length px, amount)
uniform vec2 res;
""" + NOISE + """
vec3 hsv2rgb(vec3 c){ vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0); return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y); }
vec3 pearl(float t){ vec3 c = 0.72 + 0.28 * cos(6.28318 * (t + vec3(0.0, 0.33, 0.67))); return mix(c, vec3(1.0), 0.22); }
vec3 palette(int mode, float t, float k){
  if (mode == 1) return hsv2rgb(vec3(hue / 360.0, 0.85, 1.0));
  if (mode == 2) return hsv2rgb(vec3(fract(t * 1.5), 0.9, 1.0));
  if (mode == 3) return mix(vec3(0.9, 0.15, 0.0), vec3(1.0, 0.95, 0.6), k) * (0.6 + 0.4 * k);
  if (mode == 4) return mix(vec3(0.2, 0.5, 1.0), vec3(0.85, 1.0, 1.0), k);
  if (mode == 5) return mix(vec3(1.0, 0.72, 0.25), vec3(1.0, 0.98, 0.85), k);
  if (mode == 6) { float b = 0.5 + 0.5 * sin(t * 12.0 + time * 0.5); return mix(vec3(0.2, 1.0, 0.5), vec3(0.6, 0.3, 1.0), b); }
  if (mode == 7) { vec3 c = 0.84 + 0.16 * cos(6.28318 * (t + vec3(0.0, 0.18, 0.36))); return mix(c, vec3(1.0, 0.86, 0.93), 0.35); }   // LALA: creamy pinks
  return pearl(t);
}
// border styles: h = blurred edge map (soft distance to the nearest stroke); hs = shifted copy; hu = copy from below
float ring(int style, float h, float hs, float hu, vec2 px, out vec3 tint, out float tintAmt){
  tint = vec3(1.0); tintAmt = 0.0;
  if (style == 1) return pow(h, 0.5) * 0.5 + smoothstep(0.12, 0.35, h) * 0.9;
  if (style == 2) return smoothstep(0.05, 0.09, h) * (1.0 - smoothstep(0.10, 0.15, h)) * 1.6 + smoothstep(0.28, 0.45, h);
  if (style == 3) return smoothstep(0.08, 0.11, h) * (1.0 - smoothstep(0.12, 0.17, h)) * 1.8;
  if (style == 4) return h * (0.5 + step(0.45, vnoise(px * 0.12 + vec2(time * 7.0, -time * 5.0))));
  if (style == 5) return hs;
  if (style == 6) {                                                                   // WATER: ripple + caustics
    tint = vec3(0.35, 0.85, 1.0); tintAmt = 0.6;
    float ripple = 0.7 + 0.5 * sin(px.x * 0.08 + time * 2.5) * sin(px.y * 0.07 - time * 1.9);
    float caustic = pow(vnoise(px * 0.05 + vec2(time * 0.8, -time * 0.5)), 3.0) * smoothstep(0.02, 0.2, h) * 1.4;
    return h * ripple + caustic;
  }
  if (style == 7) {                                                                   // GHOST: wisps drifting up
    tint = vec3(0.85, 0.85, 1.0); tintAmt = 0.6;
    float wisp = 0.5 + 0.5 * fbm(px * 0.02 + vec2(time * 0.3, -time * 0.6));
    return (h * wisp + hu * 0.6 * wisp) * (0.75 + 0.25 * sin(time * 1.1 + px.x * 0.01));
  }
  if (style == 9) {                                                                   // PASTEL: a thin soft band, no glow at all
    tint = vec3(1.0, 0.86, 0.92); tintAmt = 0.5;
    return smoothstep(0.10, 0.16, h) * (1.0 - smoothstep(0.16, 0.26, h)) * 1.1;
  }
  if (style == 8) {                                                                   // FIRE: flames rising off every stroke
    float flame = fbm(px * vec2(0.06, 0.035) + vec2(0.0, time * 3.0));
    float f = hu * (0.4 + 1.4 * flame) + h * 0.5;
    tint = mix(vec3(1.0, 0.15, 0.0), vec3(1.0, 0.95, 0.5), clamp(f * 1.5, 0.0, 1.0)); tintAmt = 0.85;
    return f;
  }
  return h;
}
void main(){
  vec2 px = uv * res;
  vec2 asp = vec2(res.x / res.y, 1.0);
  float e = texture(edges, uv).r;
  float h = texture(halo, uv).r;
  // ---- the black hole at the pointer: replaces pixels, so it comes first ----
  if (lensOn > 0.5) {
    vec2 d = (uv - lens) * asp; float r = length(d);
    float R = 0.08, r0 = 0.009;
    if (r < R) {
      float k = 0.0028;
      float swirl = 0.9 * clamp(R / max(r, 1e-3) - 1.0, 0.0, 6.0) * 0.12;
      float cs = cos(swirl), sn = sin(swirl);
      vec2 dr = vec2(d.x * cs - d.y * sn, d.x * sn + d.y * cs);
      vec2 src = lens + (dr * (1.0 + k / max(r * r, 1e-4))) / asp;
      vec3 col = texture(clean, clamp(src, 0.0, 1.0)).rgb;
      float horizon = smoothstep(r0, r0 * 1.35, r);
      float photon = exp(-pow((r - r0 * 1.7) / (r0 * 0.55), 2.0)) * (0.7 + 0.3 * flash);
      col = col * horizon + vec3(1.0, 0.75, 0.4) * photon;
      float rim = smoothstep(R, R * 0.78, r);
      frag = vec4(col * rim, rim);
      if (rim > 0.999) return;
      // inside the soft rim, fall through and let the glow add on top at (1-rim)
      e *= (1.0 - rim); h *= (1.0 - rim);
    }
  }
  float hs = texture(halo, uv - vec2(5.0, -5.0) / res).r;
  float hu = texture(halo, uv + vec2(0.0, (6.0 + 18.0 * fbm(px * 0.05 + time)) / res.y)).r;
  float t = hue / 360.0 + 0.12 * sin(uv.x * 4.1 + time * 0.21) + 0.12 * sin(uv.y * 3.3 - time * 0.17)
          + 0.10 * (vnoise(uv * 3.0 + time * 0.05) - 0.5);
  float k = clamp(h * 3.0, 0.0, 1.0);
  vec3 btint; float btintAmt;
  float ringA = ring(border, h, hs, hu, px, btint, btintAmt) * (1.0 - e) * haloAmt;
  vec3 ringC = mix(palette(colorMode, t, k), btint, btintAmt);
  vec3 coreC = mix(palette(colorMode, t + 0.08, 1.0), vec3(1.0), 0.6);
  float coreA = e * coreAmt;
  float content = smoothstep(0.02, 0.25, h);
  // ---- stars and orbs (3x3 cell lookup so nothing is cut at a cell edge) ----
  float star = 0.0; vec2 cell = floor(px / 28.0);
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 c = cell + vec2(i, j);
    if (hash21(c + 11.0) < 0.55) continue;
    vec2 cp = (c + vec2(hash21(c), hash21(c + 7.0))) * 28.0;
    float tw = pow(0.5 + 0.5 * sin(time * (1.0 + hash21(c + 3.0) * 2.0) + hash21(c) * 6.28), 6.0);
    star += smoothstep(2.2, 0.0, length(px - cp)) * tw;
  }
  star *= 0.35 + 0.65 * flash;
  float orb = 0.0; vec2 oc = floor(px / 180.0);
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 c = oc + vec2(i, j);
    if (hash21(c + 13.0) < 0.5) continue;
    vec2 op = (c + vec2(hash21(c + 5.0), hash21(c + 9.0))) * 180.0
            + vec2(sin(time * 0.3 + hash21(c) * 6.0), cos(time * 0.27 + hash21(c + 1.0) * 6.0)) * 40.0;
    float orad = 14.0 + 40.0 * hash21(c + 2.0) * (0.5 + bass);
    orb += smoothstep(orad, orad * 0.2, length(px - op));
  }
  orb *= flash * 0.35;
  // ---- nebula and the ghost party ----
  vec2 q = vec2(fbm(uv * 2.0 + time * 0.02), fbm(uv * 2.0 - time * 0.015));
  float n = fbm(uv * 3.0 + q * 1.5 + time * 0.01);
  float neb = smoothstep(0.35, 0.8, n) * (0.10 + 0.14 * loud) * ghostAmt;
  float ghost = 0.0, eyes = 0.0;
  for (int i = 0; i < 6; i++) {
    float fi = float(i); float ph = hash21(vec2(fi, 3.0)) * 6.28;
    vec2 c = vec2(0.08 + 0.84 * fract(hash21(vec2(fi, 1.0)) + time * 0.012 * (0.5 + hash21(vec2(fi, 2.0)))), 0.58 + 0.10 * sin(time * 0.7 + ph));
    c.x += 0.015 * sin(time * 2.0 * (1.0 + bass) + ph);
    vec2 d = (uv - c) * asp;
    float body = exp(-dot(d * vec2(9.0, 4.0), d * vec2(9.0, 4.0)));
    vec2 dh = d - vec2(0.0, -0.17);
    float head = exp(-dot(dh * 14.0, dh * 14.0));
    float vis = 0.6 + 0.4 * sin(time * 1.3 + ph);
    ghost += (body * 0.8 + head) * vis;
    vec2 e1 = dh - vec2(-0.022, -0.01), e2 = dh - vec2(0.022, -0.01);        // two dark eyes
    eyes += (exp(-dot(e1 * 90.0, e1 * 90.0)) + exp(-dot(e2 * 90.0, e2 * 90.0))) * vis;
  }
  ghost *= ghostAmt * (0.16 + 0.22 * loud + 0.28 * flash);
  eyes *= ghostAmt * (0.5 + 0.4 * loud) * (1.0 - content);
  float sky = ((star * 0.9 + orb) * astralAmt + neb + ghost) * (1.0 - content * 0.85);
  vec3 skyC = palette(colorMode, t + 0.3 + 0.25 * n, n);
  // ---- the sound climbing in from the four borders ----
  float wave = 0.0; vec3 waveC = vec3(1.0);
  if (waveStyle > 0 && edgeMask > 0) {
    float dl = px.x, dr = res.x - px.x, dt = px.y, db = res.y - px.y;
    float dist = 1e9; float along = uv.x;                                     // only the edges he chose
    if ((edgeMask & 1) != 0 && db < dist) { dist = db; along = uv.x; }       // bottom
    if ((edgeMask & 2) != 0 && dt < dist) { dist = dt; along = uv.x; }       // top
    if ((edgeMask & 4) != 0 && dl < dist) { dist = dl; along = uv.y; }       // left
    if ((edgeMask & 8) != 0 && dr < dist) { dist = dr; along = uv.y; }       // right
    float sp = texture(spectrum, vec2(along, 0.5)).r;
    float gapMask = 1.0;
    if (waveShape == 1) {                                                      // BARS: 64 slim bars per edge
      float slot = along * 64.0;
      sp = texture(spectrum, vec2((floor(slot) + 0.5) / 64.0, 0.5)).r;       // linear filter interpolates the 32 bins
      float f = fract(slot);
      gapMask = step(0.5 - barFill * 0.5, f) * step(f, 0.5 + barFill * 0.5);   // his slimness
    }
    float hmax = res.y * barHeight * (0.5 + 0.5 * loud);
    float height = sp * hmax;
    float inside = 1.0 - clamp(dist / max(height, 1.0), 0.0, 1.0);           // 1 at the border, 0 at the crest
    if (waveStyle == 1) {                                                      // ELECTRIC
      height *= 0.6 + 0.8 * vnoise(vec2(along * 60.0, time * 11.0));
      wave = smoothstep(height, height - 3.0, dist) * (0.35 + 0.5 * step(0.5, vnoise(vec2(along * 90.0, time * 23.0))));
      waveC = mix(vec3(0.2, 0.8, 1.0), vec3(1.0), inside);
    } else if (waveStyle == 2) {                                               // AQUA
      height += 6.0 * sin(along * 40.0 + time * 2.2) + 4.0 * sin(along * 17.0 - time * 1.3);
      wave = smoothstep(height, height - 10.0, dist) * (0.25 + 0.45 * inside);
      wave += smoothstep(height, height - 3.0, dist) * (1.0 - smoothstep(height - 3.0, height - 6.0, dist)) * 0.7;
      waveC = mix(vec3(0.1, 0.55, 0.9), vec3(0.85, 1.0, 1.0), smoothstep(height - 8.0, height, dist));
    } else if (waveStyle == 3) {                                               // FIRE
      float fl = fbm(vec2(along * 14.0, dist * 0.03 - time * 1.8));
      height *= 0.5 + 1.1 * fl;
      wave = smoothstep(height, height * 0.2, dist) * 0.8;
      waveC = mix(vec3(0.8, 0.1, 0.0), vec3(1.0, 0.95, 0.5), pow(inside, 1.5));
    } else if (waveStyle == 4) {                                               // GHOST
      wave = exp(-dist / max(height * 0.6, 1.0)) * (0.3 + 0.2 * fbm(vec2(along * 8.0, time * 0.5))) * step(0.02, sp);
      waveC = vec3(0.8, 0.8, 1.0);
    } else {                                                                   // MAGIC
      float sparkle = step(0.985, hash21(floor(px / 3.0) + floor(time * 8.0)));
      wave = smoothstep(height, height - 14.0, dist) * (0.3 + 0.3 * inside) + sparkle * smoothstep(height + 10.0, height - 4.0, dist) * 0.9;
      waveC = mix(vec3(0.55, 0.25, 1.0), vec3(1.0, 0.85, 0.4), fract(along * 3.0 + time * 0.2));
    }
    if (waveShape == 1) {                                                      // bars: hard top + bright cap
      float barA = step(dist, height) * (0.45 + 0.4 * inside);
      float cap = step(height - 3.0, dist) * step(dist, height) * 0.9;
      wave = (barA + cap) * gapMask;                                           // bars only, no wave behind them
    }
    if (barColor >= 0) waveC = palette(barColor, along * 0.8 + time * 0.03, 0.35 + 0.65 * inside);   // his colour world
    wave *= 0.75 * (1.0 - content * 0.6);
  }
  // ---- a shooting star, when one is crossing ----
  float meteor = 0.0; vec3 meteorC = vec3(1.0);
  if (streakLenAmt.y > 0.001) {
    vec2 head = streak.xy * res; vec2 dir = normalize(streak.zw * vec2(1.0, 1.0));
    vec2 d = px - head;
    float along = dot(d, -dir);                       // distance back along the tail
    float perp = abs(d.x * dir.y - d.y * dir.x);
    float L = streakLenAmt.x;
    if (along > 0.0 && along < L) {
      float k = along / L;
      float w = 1.2 + 5.0 * k;
      meteor = exp(-perp * perp / (2.0 * w * w)) * pow(1.0 - k, 1.6) * (0.7 + 0.3 * vnoise(vec2(along * 0.15, time * 30.0)));
      meteorC = mix(vec3(1.0, 1.0, 1.0), vec3(1.0, 0.6, 0.25), k);
    }
    float headGlow = exp(-dot(d, d) / 60.0) * 1.4 + exp(-dot(d, d) / 600.0) * 0.5;
    meteor = (meteor + headGlow) * streakLenAmt.y;
    meteorC = mix(meteorC, vec3(0.8, 0.9, 1.0), clamp(headGlow, 0.0, 1.0));
  }
  float total = (coreA + ringA + sky + wave + meteor) * bright;
  float a = clamp(total, 0.0, 0.92);
  vec3 rgb = (coreC * coreA + ringC * ringA + skyC * sky + waveC * wave + meteorC * meteor) / max(total, 1e-4);
  float aDark = clamp(a + eyes * 0.85, 0.0, 0.95);                         // eyes add cover, not light
  if (lensOn > 0.5) { vec4 under = frag; float add = min(aDark, 1.0 - under.a); frag = vec4(under.rgb + rgb * a * (add / max(aDark, 1e-4)), under.a + add); return; }
  frag = vec4(rgb * a, aDark);
}
"""
SPRITE_VERT = """#version 330 core
uniform vec4 rect;             // x, y, w, h in texture-space uv (y down)
uniform float angle;           // radians, rotation about the quad centre, in pixel space
uniform vec2 res;
out vec2 tuv;
void main(){
  vec2 q = vec2(float(gl_VertexID & 1), float((gl_VertexID >> 1) & 1));
  tuv = vec2(q.x, 1.0 - q.y);
  vec2 cpx = (rect.xy + rect.zw * 0.5) * res;
  vec2 off = (q - 0.5) * rect.zw * res;
  float c = cos(angle), s = sin(angle);
  vec2 rpx = cpx + vec2(off.x * c - off.y * s, off.x * s + off.y * c);
  vec2 p = rpx / res;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""
SPRITE_FRAG = """#version 330 core
in vec2 tuv; out vec4 frag;
uniform sampler2D tex; uniform sampler2D halo; uniform vec3 tint; uniform float alpha; uniform float behind; uniform vec2 res;
void main(){
  vec4 c = texture(tex, vec2(tuv.x, 1.0 - tuv.y));
  float content = smoothstep(0.02, 0.18, texture(halo, gl_FragCoord.xy / res).r);
  frag = vec4(c.rgb * tint, c.a) * alpha * (1.0 - behind * content * 0.92);
}
"""
SDF_FRAG = """#version 330 core
// A real body, raymarched: capsules and ellipsoids smoothly joined, lit, with skin, hair, cloth.
// mode 0 = figure (joints in rig space, unit height), mode 1 = ship (yaw, bank).
in vec2 tuv; out vec4 frag;
uniform int mode; uniform vec3 joints[12]; uniform float woman; uniform float yaw; uniform float bank;
uniform vec3 tint; uniform float alpha; uniform float time; uniform float engine;
uniform sampler2D halo; uniform sampler2D clean; uniform vec2 res; uniform float behind;
uniform int look;              // 0 chrome · 1 holo · 2 toon · 3 pearl · 4 neon · 5 ghost
float hash21s(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
vec3 pearlc(float t){ vec3 c = 0.72 + 0.28 * cos(6.28318 * (t + vec3(0.0, 0.33, 0.67))); return mix(c, vec3(1.0), 0.22); }
float smin(float a, float b, float k){ float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0); return mix(b, a, h) - k * h * (1.0 - h); }
float sdCapsule(vec3 p, vec3 a, vec3 b, float r){ vec3 pa = p - a, ba = b - a; float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0); return length(pa - ba * h) - r; }
float sdEllipsoid(vec3 p, vec3 r){ return (length(p / r) - 1.0) * min(min(r.x, r.y), r.z); }   // conservative: never overshoots
float sdBox(vec3 p, vec3 b){ vec3 q = abs(p) - b; return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0); }
float sdCone(vec3 p, float h, float r1, float r2){ vec2 q = vec2(length(p.xz), p.y); vec2 k1 = vec2(r2, h); vec2 k2 = vec2(r2 - r1, 2.0 * h);
  vec2 ca = vec2(q.x - min(q.x, (q.y < 0.0) ? r1 : r2), abs(q.y) - h); vec2 cb = q - k1 + k2 * clamp(dot(k1 - q, k2) / dot(k2, k2), 0.0, 1.0);
  float s = (cb.x < 0.0 && ca.y < 0.0) ? -1.0 : 1.0; return s * sqrt(min(dot(ca, ca), dot(cb, cb))); }
mat3 rotY(float a){ float c = cos(a), s = sin(a); return mat3(c, 0, s, 0, 1, 0, -s, 0, c); }
mat3 rotZ(float a){ float c = cos(a), s = sin(a); return mat3(c, -s, 0, s, c, 0, 0, 0, 1); }
mat3 rotX(float a){ float c = cos(a), s = sin(a); return mat3(1, 0, 0, 0, c, -s, 0, s, c); }
// material id in .y: 0 skin, 1 hair, 2 cloth, 3 hull, 4 glass, 5 engine
vec2 figure(vec3 p){
  p = rotY(yaw) * p;
  vec3 hip = joints[0], neck = joints[1], head = joints[2];
  float torso = sdCapsule(p, hip, neck, 0.075);
  float chest = sdEllipsoid(p - mix(hip, neck, 0.72), vec3(0.11, 0.09, 0.075));
  float pelvis = sdEllipsoid(p - hip, vec3(0.095, 0.07, 0.07));
  float d = smin(torso, chest, 0.05); d = smin(d, pelvis, 0.05);
  d = smin(d, sdCapsule(p, hip, joints[3], 0.055), 0.03); d = smin(d, sdCapsule(p, joints[3], joints[4], 0.045), 0.02);
  d = smin(d, sdCapsule(p, hip, joints[5], 0.055), 0.03); d = smin(d, sdCapsule(p, joints[5], joints[6], 0.045), 0.02);
  d = smin(d, sdCapsule(p, neck, joints[7], 0.04), 0.03); d = smin(d, sdCapsule(p, joints[7], joints[8], 0.034), 0.02);
  d = smin(d, sdCapsule(p, neck, joints[9], 0.04), 0.03); d = smin(d, sdCapsule(p, joints[9], joints[10], 0.034), 0.02);
  float hd = sdEllipsoid(p - head, vec3(0.072, 0.085, 0.078));
  d = smin(d, hd, 0.02);
  float mat = 0.0;
  if (woman > 0.5) {
    float hair = sdEllipsoid(p - head - vec3(0.0, 0.02, -0.02), vec3(0.085, 0.1, 0.09));
    hair = smin(hair, sdCapsule(p, head + vec3(0.0, 0.0, -0.05), hip + vec3(0.0, 0.18, -0.06), 0.06), 0.06);
    float skinOnly = d;
    d = smin(d, hair, 0.01);
    if (hair < skinOnly + 0.004 && p.z < head.z - 0.0) mat = 1.0;
    float dress = sdCone(p - hip - vec3(0.0, -0.22, 0.0), 0.22, 0.2, 0.1);
    if (dress < d) { d = dress; mat = 2.0; }
  }
  return vec2(d, mat);
}
vec2 ship(vec3 p){
  p = rotZ(bank) * rotY(yaw) * p;
  float hull = sdEllipsoid(p, vec3(0.42, 0.09, 0.11));
  float nose = sdEllipsoid(p - vec3(0.3, 0.02, 0.0), vec3(0.2, 0.06, 0.07));
  float d = smin(hull, nose, 0.08);
  d = smin(d, sdBox(p - vec3(-0.08, -0.01, 0.0), vec3(0.12 - abs(p.z) * 0.18, 0.012, 0.4)), 0.03);     // swept wings
  d = smin(d, sdBox(p - vec3(-0.3, 0.1, 0.0), vec3(0.08 - (p.y - 0.1) * 0.3, 0.1, 0.012)), 0.03);
  float mat = 3.0;
  float glass = sdEllipsoid(p - vec3(0.14, 0.07, 0.0), vec3(0.13, 0.05, 0.075));
  if (glass < d) { d = glass; mat = 4.0; }
  float eng = sdEllipsoid(p - vec3(-0.42, 0.0, 0.0), vec3(0.06, 0.05, 0.07));
  if (eng < d) { d = eng; mat = 5.0; }
  return vec2(d, mat);
}
vec2 saucer(vec3 p){
  p = rotZ(bank) * rotY(yaw) * p;
  float r = length(p.xz);
  float upper = max(sdEllipsoid(p, vec3(0.5, 0.1, 0.5)), -p.y);                      // lens: domed top
  float lower = max(sdEllipsoid(p - vec3(0.0, 0.01, 0.0), vec3(0.48, 0.17, 0.48)), p.y);  // deeper belly
  float d = smin(upper, lower, 0.03);
  float seam = length(vec2(r - 0.5, p.y)) - 0.025;                                    // equator band
  d = smin(d, seam, 0.01);
  float mat = 3.0;
  float dome = max(length(p - vec3(0.0, 0.05, 0.0)) - 0.2, 0.07 - p.y);              // glass cap rising from the hull
  if (dome < d) { d = dome; mat = 4.0; }
  float lamps = 1e9;
  for (int i = 0; i < 12; i++) { float a = float(i) * 0.5235988; vec3 c = vec3(cos(a) * 0.36, 0.062, sin(a) * 0.36); lamps = min(lamps, length(p - c) - 0.03); }
  float ring = length(vec2(r - 0.22, p.y + 0.165)) - 0.02;                            // engine ring under the belly
  lamps = min(lamps, ring);
  if (lamps < d) { d = lamps; mat = 5.0; }
  return vec2(d, mat);
}

float sdOcta(vec3 p, float s){ p = abs(p); return (p.x + p.y + p.z - s) * 0.57735027; }
// material ids: 6 goldfish body · 7 fin · 8 gem · 9 solar panel
vec2 fish(vec3 p){
  p = rotZ(bank) * rotY(yaw) * p;
  p.z += sin(time * 7.0 + p.x * 5.0) * 0.07 * clamp(-p.x * 2.0, 0.0, 1.0);                 // the tail swings
  float body = sdEllipsoid(p, vec3(0.3, 0.17, 0.12));
  float head = sdEllipsoid(p - vec3(0.2, 0.0, 0.0), vec3(0.14, 0.13, 0.1));
  float d = smin(body, head, 0.06); float mat = 6.0;
  float tail = min(sdEllipsoid(p - vec3(-0.4, 0.09, 0.0), vec3(0.17, 0.08, 0.015)), sdEllipsoid(p - vec3(-0.4, -0.09, 0.0), vec3(0.17, 0.08, 0.015)));
  float dorsal = sdEllipsoid(p - vec3(-0.02, 0.2, 0.0), vec3(0.13, 0.06, 0.012));
  float pect = min(sdEllipsoid(p - vec3(0.08, -0.08, 0.12), vec3(0.07, 0.03, 0.012)), sdEllipsoid(p - vec3(0.08, -0.08, -0.12), vec3(0.07, 0.03, 0.012)));
  float fins = min(min(tail, dorsal), pect);
  if (fins < d) { d = fins; mat = 7.0; }
  float eye = min(length(p - vec3(0.27, 0.04, 0.088)) - 0.025, length(p - vec3(0.27, 0.04, -0.088)) - 0.025);
  if (eye < d) { d = eye; mat = 1.0; }
  return vec2(d, mat);
}
vec2 gem(vec3 p){
  p = rotZ(bank) * rotY(yaw + time * 0.9) * p;
  vec3 q = p; q.y *= 0.72;
  float d = sdOcta(q, 0.36) * 0.72;
  d = max(d, sdBox(p, vec3(0.3, 0.5, 0.3)));
  return vec2(d, 8.0);
}
vec2 satellite(vec3 p){
  p = rotZ(bank) * rotY(yaw) * p;
  float d = sdBox(p, vec3(0.12, 0.1, 0.1)); float mat = 3.0;
  float boom = sdCapsule(p, vec3(-0.6, 0.0, 0.0), vec3(0.6, 0.0, 0.0), 0.012); d = min(d, boom);
  float panels = max(sdBox(p, vec3(0.6, 0.006, 0.12)), -sdBox(p, vec3(0.17, 1.0, 1.0)));
  if (panels < d) { d = panels; mat = 9.0; }
  float mast = sdCapsule(p, vec3(0.0, 0.1, 0.0), vec3(0.0, 0.26, 0.0), 0.012); d = min(d, mast);
  float dish = max(abs(length(p - vec3(0.0, 0.36, 0.0)) - 0.17) - 0.01, p.y - 0.26);
  d = min(d, dish);
  float feed = sdCapsule(p, vec3(0.0, 0.2, 0.0), vec3(0.0, 0.34, 0.0), 0.008); d = min(d, feed);
  float beacon = length(p - vec3(0.0, -0.1, 0.1)) - 0.02; if (beacon < d) { d = beacon; mat = 5.0; }
  return vec2(d, mat);
}
vec2 pump(vec3 p){
  p = rotY(yaw) * p;
  float d = sdBox(p, vec3(0.14, 0.42, 0.09)); float mat = 3.0;
  d = min(d, sdBox(p - vec3(0.0, -0.45, 0.0), vec3(0.2, 0.03, 0.14)));
  float screen = sdBox(p - vec3(0.0, 0.22, 0.09), vec3(0.09, 0.07, 0.01)); if (screen < d) { d = screen; mat = 4.0; }
  float hose = sdCapsule(p, vec3(0.14, 0.1, 0.0), vec3(0.25, -0.25, 0.0), 0.014); d = min(d, hose);
  float nozzle = sdCapsule(p, vec3(0.25, -0.25, 0.0), vec3(0.2, -0.38, 0.0), 0.022); d = min(d, nozzle);
  float lamp = length(p - vec3(0.0, 0.5, 0.0)) - 0.05; if (lamp < d) { d = lamp; mat = 5.0; }
  return vec2(d, mat);
}
vec2 map(vec3 p){ if (mode == 0) return figure(p); if (mode == 1) return ship(p); if (mode == 2) return saucer(p); if (mode == 3) return fish(p); if (mode == 4) return gem(p); if (mode == 5) return satellite(p); return pump(p); }
vec3 normalAt(vec3 p){ vec2 e = vec2(0.002, 0.0); vec3 g = vec3(map(p + e.xyy).x - map(p - e.xyy).x, map(p + e.yxy).x - map(p - e.yxy).x, map(p + e.yyx).x - map(p - e.yyx).x); return normalize(g + vec3(0.0, 0.0, 1e-5)); }
void main(){
  vec2 q = tuv * 2.0 - 1.0;                       // -1..1 over the quad
  vec3 ro, rd;
  if (mode == 0) { ro = vec3(q.x * 0.62, q.y * 0.62 + 0.5, 2.0); rd = vec3(0.0, 0.0, -1.0); }
  else { ro = vec3(q.x * 0.7, q.y * 0.7, 2.0); rd = vec3(0.0, 0.0, -1.0); }
  if (mode == 2) { ro = rotX(0.8) * vec3(q.x * 0.7, q.y * 0.7 + 0.05, 2.0); rd = rotX(0.8) * vec3(0.0, 0.0, -1.0); }   // saucer: hero shot from above
  float t = 0.0, tPrev = 0.0, dmin = 1e9, mat = 0.0; bool hit = false;
  for (int i = 0; i < 160; i++) {
    vec3 p = ro + rd * t; vec2 r = map(p);
    dmin = min(dmin, r.x);
    if (r.x < 0.003) { hit = true; mat = r.y; break; }
    tPrev = t; t += max(r.x * 0.7, 0.001); if (t > 4.0) break;
  }
  if (hit) {                                              // land exactly on the surface, never inside it
    float lo = tPrev, hi = t;
    for (int k = 0; k < 8; k++) { float mid = 0.5 * (lo + hi); if (map(ro + rd * mid).x < 0.0) hi = mid; else lo = mid; }
    t = hi; mat = map(ro + rd * t).y;
  }
  vec3 col = vec3(0.0); float a = 0.0;
  if (hit) {
    vec3 p = ro + rd * t; vec3 n = normalAt(p); vec3 v = -rd;
    vec3 key = normalize(vec3(-0.5, 0.8, 0.9)); vec3 fill = normalize(vec3(0.7, 0.2, 0.6));
    float diff = max(dot(n, key), 0.0); float fl = max(dot(n, fill), 0.0) * 0.35;
    float rim = pow(clamp(1.0 - dot(n, v), 0.0, 1.0), 3.0);       // never pow() a negative: NaN paints black
    float spec = pow(clamp(dot(reflect(-key, n), v), 0.0, 1.0), 24.0);
    vec3 base;
    if (mat < 0.5) base = vec3(0.93, 0.80, 0.70);                 // skin, warm
    else if (mat < 1.5) base = vec3(0.22, 0.14, 0.12);            // hair
    else if (mat < 2.5) base = vec3(0.55, 0.45, 0.75);            // cloth
    else if (mat < 3.5) base = vec3(0.62, 0.66, 0.72);            // hull
    else if (mat < 4.5) base = vec3(0.35, 0.7, 0.95);             // glass
    else if (mat < 5.5) base = vec3(1.0, 0.75, 0.4);              // engine / lamp
    else if (mat < 6.5) base = vec3(1.0, 0.5, 0.14);              // goldfish
    else if (mat < 7.5) base = vec3(1.0, 0.72, 0.38);             // fin
    else if (mat < 8.5) base = vec3(0.95, 0.45, 0.95);            // gem
    else base = vec3(0.12, 0.22, 0.58);                           // solar panel
    bool glassy = (mat > 3.5 && mat < 4.5) || (mat > 7.5 && mat < 8.5); bool isLamp = mat > 4.5 && mat < 5.5; bool subject = mat > 5.5;
    float sss = (mat < 0.5) ? 0.25 * pow(clamp(dot(n, -key), 0.0, 1.0), 1.5) : 0.0;
    col = base * (0.18 + 0.85 * diff + fl) + vec3(1.0, 0.95, 0.9) * spec * ((glassy || mat > 8.5) ? 1.4 : 0.4)
        + vec3(0.85, 0.9, 1.0) * rim * 0.9 + base * sss * vec3(1.0, 0.5, 0.4);
    if (isLamp) col += vec3(1.0, 0.7, 0.3) * (1.5 + 1.5 * engine);
    // ---- the looks (eye exam): same body, different aesthetics ----
    float fres = pow(1.0 - max(dot(n, v), 0.0), 2.0);
    vec3 rv = reflect(rd, n);
    if (look == 0) {                                           // CHROME: brushed metal, sky reflection, hard spec
      vec3 sky = mix(vec3(0.08, 0.09, 0.12), vec3(0.75, 0.82, 0.95), clamp(rv.y * 0.5 + 0.5, 0.0, 1.0));
      vec3 metal = glassy ? vec3(0.4, 0.7, 0.95) : (subject ? base : vec3(0.78, 0.8, 0.84));
      col = metal * (0.15 + 0.6 * diff) + sky * (0.35 + 0.5 * fres) + vec3(1.0) * pow(spec, 2.0) * 1.2;
      if (isLamp) col = vec3(1.0, 0.75, 0.35) * 3.0;
    } else if (look == 1) {                                    // HOLO: light only — contour lines, no solid
      float iso = abs(fract(p.y * 46.0) - 0.5); float lines = smoothstep(0.08, 0.0, iso);
      float ring = smoothstep(0.03, 0.0, abs(length(p.xz) - 0.5)) + smoothstep(0.03, 0.0, abs(length(p.xz) - 0.36)) + smoothstep(0.02, 0.0, abs(length(p.xz) - 0.19));
      vec3 teal = vec3(0.37, 0.89, 0.89);
      col = teal * (lines * 0.8 + ring * 0.9 + fres * 0.9) + (isLamp ? teal * 2.5 : vec3(0.0));
      a = (isLamp) ? 1.0 : clamp(0.1 + lines * 0.6 + ring * 0.7 + fres * 0.7, 0.0, 0.95);
    } else if (look == 2) {                                    // TOON: three bands and ink
      float band = diff < 0.3 ? 0.35 : (diff < 0.65 ? 0.7 : 1.0);
      vec3 flat_ = glassy ? vec3(0.55, 0.85, 1.0) : (isLamp ? vec3(1.0, 0.85, 0.45) : (subject ? base : vec3(0.72, 0.76, 0.84)));
      col = flat_ * band; if (fres > 0.72) col = vec3(0.03, 0.03, 0.05);          // ink outline
    } else if (look == 3) {                                    // PEARL: mother-of-pearl, colour shifts with angle
      vec3 pc = mix(pearlc(fres * 0.8 + p.x * 0.3 + time * 0.05), base, subject ? 0.45 : 0.0);
      col = pc * (0.35 + 0.65 * diff) + vec3(1.0) * spec * 0.6 + pc * fres * 0.6;
      if (isLamp) col = vec3(1.0, 0.9, 0.7) * 2.5;
    } else if (look == 4) {                                    // NEON: dark body, cyan rim, magenta inner rim
      col = vec3(0.02, 0.03, 0.05) + vec3(0.37, 0.89, 1.0) * pow(fres, 1.5) * 1.4 + vec3(1.0, 0.37, 0.78) * pow(clamp(fres - 0.15, 0.0, 1.0), 3.0) * 1.2;
      if (isLamp) col = vec3(0.37, 0.89, 1.0) * 3.0;
    } else if (look == 5) {                                    // GHOST: translucent, lit from inside
      vec3 g = vec3(0.85, 0.88, 1.0);
      col = g * (0.25 + 0.5 * fres) + g * 0.25 * diff; a = 0.35 + 0.5 * fres;
      if (isLamp) { col = vec3(1.0, 0.95, 0.8) * 2.0; a = 1.0; }
    }
    col = min(col * tint, vec3(1.0));                        // valid premultiplied output: never brighter than alpha allows
    if (look != 1 && look != 5) a = 1.0;
  }
  float haloA = exp(-max(dmin, 0.0) * 22.0) * 0.35;             // a soft light around the body
  haloA *= smoothstep(1.0, 0.55, max(abs(q.x), abs(q.y)));    // and nothing at the edge of the quad: no lit square
  col += tint * vec3(0.8, 0.85, 1.0) * haloA * (1.0 - a);
  a = max(a, haloA);
  // Behind the words: the body stays opaque to the capture pass (so it is never un-blended into
  // black), and the screen's own pixels are painted over it where there is text or a line.
  vec2 suv = gl_FragCoord.xy / res;
  float content = smoothstep(0.02, 0.18, texture(halo, suv).r) * behind;
  if (a > 0.5 && look != 1 && look != 5) {
    col = mix(col, texture(clean, suv).rgb, content * 0.95);
    frag = vec4(col * 0.985 * alpha, 0.985 * alpha);
  } else {
    frag = vec4(col * alpha * (1.0 - content * 0.9), a * alpha * (1.0 - content * 0.9));
  }
}
"""
BLIT = """#version 330 core
in vec2 uv; out vec4 frag; uniform sampler2D src;
void main(){ frag = texture(src, vec2(uv.x, 1.0 - uv.y)); }
"""


@dataclass
class AuraParams:
    hue: float = 200.0
    loud: float = 0.0
    bass: float = 0.0
    flash: float = 0.0
    sensitivity: float = 1.0
    width: float = 2.0
    bold: bool = False
    astral: bool = True
    time: float = 0.0
    color_mode: int = 0
    border: int = 0
    ghost: bool = True
    waves: int = 1                      # index into WAVE_STYLES (ELECTRIC by default: bars show)
    edges: int = 1                      # bit mask: 1 bottom, 2 top, 4 left, 8 right
    bar_color: int = 2                  # index into COLOR_MODES, or -1 = the style's own colour
    bar_height: float = 0.10            # fraction of screen height
    bar_fill: float = 0.4               # fraction of each slot that is bar
    wave_shape: int = 1                 # 0 wave, 1 bars
    bright: float = 1.0                 # 0.2..2.5
    lens: bool = False                  # black-hole cursor
    cursor: tuple[float, float] = (0.5, 0.5)   # uv, y down
    spectrum: np.ndarray = field(default_factory=lambda: np.zeros(N_BINS, dtype=np.float32))
    spotlight: float = 0.0              # 1 while something is on stage: the ambient sky steps back
    sprites: list = field(default_factory=list)   # (tex, x, y, w, h in uv, alpha, (r,g,b)[, angle])
    bodies: list = field(default_factory=list)    # dicts: mode, rect(x,y,w,h), joints, woman, yaw, bank, tint, alpha, engine
    streak: tuple = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)   # head x, y, dir x, dir y, length px, amount

    def intensity(self) -> float:
        base = 0.12 + 0.5 * self.loud + 0.7 * self.flash
        return max(0.0, min(1.6, base * self.sensitivity))


class AuraPipeline:
    def __init__(self, width: int, height: int) -> None:
        self.w, self.h = width, height
        self.cur = 0

    def init(self) -> None:
        self.vao = gl.glGenVertexArrays(1)
        self.programs = {}
        for name, vs, fs in (("clean", VERT, CLEAN), ("edges", VERT, EDGES), ("blur", VERT, BLUR),
                             ("compose", VERT, COMPOSE), ("sprite", SPRITE_VERT, SPRITE_FRAG), ("sdf", SPRITE_VERT, SDF_FRAG),
                             ("blit", VERT, BLIT)):
            prog = QOpenGLShaderProgram()
            if not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vs) or \
               not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fs) or not prog.link():
                raise RuntimeError(f"shader {name}: {prog.log()}")
            self.programs[name] = prog
        self.screen_tex = self._tex2d(gl.GL_RGBA8, self.w, self.h, gl.GL_BGRA)
        self.spec_tex = self._tex2d(gl.GL_R8, N_BINS, 1, gl.GL_RED)
        full, half = QSize(self.w, self.h), QSize(max(1, self.w // 2), max(1, self.h // 2))
        mk = lambda size: QOpenGLFramebufferObject(size, QOpenGLFramebufferObject.Attachment.NoAttachment, gl.GL_TEXTURE_2D, gl.GL_RGBA8)
        self.clean_fbo = [mk(full), mk(full)]
        self.edges_fbo = mk(full)
        self.blur_fbo = [mk(half), mk(half)]
        self.glow_fbo = [mk(full), mk(full)]
        for f in (*self.clean_fbo, self.edges_fbo, *self.blur_fbo, *self.glow_fbo):
            gl.glBindTexture(gl.GL_TEXTURE_2D, f.texture())
            self._params()
            f.bind(); gl.glClearColor(0, 0, 0, 0); gl.glClear(gl.GL_COLOR_BUFFER_BIT); f.release()
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    @staticmethod
    def _params() -> None:
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

    def _tex2d(self, internal, w, h, fmt) -> int:
        tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        self._params()
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, internal, w, h, 0, fmt, gl.GL_UNSIGNED_BYTE, None)
        return tex

    def upload(self, frame_bgra: np.ndarray) -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.screen_tex)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, self.w, self.h, gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, np.ascontiguousarray(frame_bgra))

    def _draw(self, name: str, textures: list[int], size: tuple[int, int], uniforms: dict, strip: bool = False) -> None:
        prog = self.programs[name]
        prog.bind()
        for unit, tex in enumerate(textures):
            gl.glActiveTexture(gl.GL_TEXTURE0 + unit)
            gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        for key, v in uniforms.items():
            loc = prog.uniformLocation(key)
            if isinstance(v, bool) or isinstance(v, int):
                gl.glUniform1i(loc, int(v))
            elif isinstance(v, float):
                gl.glUniform1f(loc, v)
            elif len(v) == 2:
                gl.glUniform2f(loc, *v)
            elif len(v) == 3:
                gl.glUniform3f(loc, *v)
            else:
                gl.glUniform4f(loc, *v)
        gl.glViewport(0, 0, *size)
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP if strip else gl.GL_TRIANGLES, 0, 4 if strip else 3)
        prog.release()

    def render(self, p: AuraParams, target_fbo: int, target_size: tuple[int, int]) -> int:
        gl.glDisable(gl.GL_BLEND)
        W, H = self.w, self.h
        hw, hh = self.blur_fbo[0].width(), self.blur_fbo[0].height()
        prev_glow = self.glow_fbo[1 - self.cur].texture()
        prev_clean = self.clean_fbo[1 - self.cur].texture()
        self.clean_fbo[self.cur].bind()
        self._draw("clean", [self.screen_tex, prev_glow, prev_clean], (W, H), {"screen": 0, "prevGlow": 1, "prevClean": 2})
        clean = self.clean_fbo[self.cur].texture()
        self.edges_fbo.bind()
        self._draw("edges", [clean], (W, H), {"clean": 0, "texel": (1.0 / W, 1.0 / H), "t0": 0.07, "t1": 0.32})
        radius = max(0.3, p.width) * (0.6 + 0.9 * p.bass)
        src = self.edges_fbo.texture()
        for _ in range(2 if p.width > 2.2 else 1):
            self.blur_fbo[0].bind(); self._draw("blur", [src], (hw, hh), {"src": 0, "dir": (radius / hw, 0.0)})
            self.blur_fbo[1].bind(); self._draw("blur", [self.blur_fbo[0].texture()], (hw, hh), {"src": 0, "dir": (0.0, radius / hh)})
            src = self.blur_fbo[1].texture()
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.spec_tex)
        spec = np.ascontiguousarray((np.clip(p.spectrum, 0, 1) * 255).astype(np.uint8))
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, N_BINS, 1, gl.GL_RED, gl.GL_UNSIGNED_BYTE, spec)
        amt = p.intensity()
        self.glow_fbo[self.cur].bind()
        self._draw("compose", [self.edges_fbo.texture(), self.blur_fbo[1].texture(), clean, self.spec_tex], (W, H),
                   {"edges": 0, "halo": 1, "clean": 2, "spectrum": 3, "time": float(p.time), "hue": float(p.hue),
                    "loud": float(p.loud), "bass": float(p.bass), "flash": float(p.flash),
                    "coreAmt": amt * 0.8 if p.bold else 0.0, "haloAmt": amt * 2.6,
                    "astralAmt": (1.0 if p.astral else 0.0) * (1.0 - 0.6 * p.spotlight), "ghostAmt": (1.0 if p.ghost else 0.0) * (1.0 - 0.6 * p.spotlight),
                    "colorMode": int(p.color_mode), "border": int(p.border), "waveStyle": int(p.waves),
                    "waveShape": int(p.wave_shape), "bright": float(p.bright), "edgeMask": int(p.edges), "barColor": int(p.bar_color),
                    "barHeight": float(p.bar_height), "barFill": float(p.bar_fill),
                    "lens": (float(p.cursor[0]), float(p.cursor[1])), "lensOn": 1.0 if p.lens else 0.0,
                    "streak": tuple(float(v) for v in p.streak[:4]), "streakLenAmt": (float(p.streak[4]), float(p.streak[5])),
                    "res": (float(W), float(H))})
        if p.bodies:
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA)
            prog = self.programs["sdf"]
            for b in p.bodies:
                prog.bind()
                js = b.get("joints") or [(0.0, 0.0, 0.0)] * 12
                flat = [float(v) for j in js[:12] for v in j] + [0.0] * (36 - 3 * min(12, len(js)))
                gl.glUniform3fv(prog.uniformLocation("joints"), 12, flat)
                prog.release()
                self._draw("sdf", [self.blur_fbo[1].texture(), clean], (W, H), {"halo": 0, "clean": 1, "behind": float(b.get("behind", 1.0)), "mode": int(b["mode"]), "rect": tuple(b["rect"]), "woman": float(b.get("woman", 0.0)),
                                               "yaw": float(b.get("yaw", 0.0)), "bank": float(b.get("bank", 0.0)), "tint": tuple(b.get("tint", (1.0, 1.0, 1.0))),
                                               "alpha": float(b.get("alpha", 1.0)), "time": float(p.time), "engine": float(b.get("engine", 0.0)),
                                               "look": int(b.get("look", 0)),
                                               "angle": 0.0, "res": (float(W), float(H))}, strip=True)
            gl.glDisable(gl.GL_BLEND)
        if p.sprites:
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA)
            for q in p.sprites:
                tex, x, y, w, h, alpha, tint = q[:7]
                angle = float(q[7]) if len(q) > 7 else 0.0
                behind = float(q[8]) if len(q) > 8 else 0.0
                self._draw("sprite", [tex, self.blur_fbo[1].texture()], (W, H), {"tex": 0, "halo": 1, "behind": behind, "rect": (x, y, w, h),
                                                      "alpha": float(alpha), "tint": tint, "angle": angle, "res": (float(W), float(H))}, strip=True)
            gl.glDisable(gl.GL_BLEND)
        glow = self.glow_fbo[self.cur].texture()
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, target_fbo)
        gl.glClearColor(0, 0, 0, 0); gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self._draw("blit", [glow], target_size, {"src": 0})
        self.cur = 1 - self.cur
        return glow


class AuraWindow(QOpenGLWindow):
    """Fullscreen, frameless, always on top, transparent for input. He never notices it is a window."""

    def __init__(self, params_fn, root: Path, fps: int = 30) -> None:
        super().__init__()
        self.params_fn = params_fn
        self.root = root
        self.fps = fps
        self.frame_ms = 0.0
        self.error = ""
        fmt = QSurfaceFormat(); fmt.setVersion(3, 3); fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setAlphaBufferSize(8); fmt.setSwapInterval(0)
        self.setFormat(fmt)
        self.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                      | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.BypassWindowManagerHint
                      | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setTitle("Party Aura")
        self.setGeometry(QGuiApplication.primaryScreen().geometry())
        self.grab = None
        self.pipe = None
        self.textures = None
        self.stories = None
        self.brainwash = None
        self.art = None
        self.ledaie = None
        self.stage = None
        self.scenes = None
        self.flags = {"stories": True, "brainwash": True, "scenes": True, "story_gap": 20.0, "phrase_gap": 5.0,
                      "phrase_font": "MONO", "phrase_color": 0, "phrase_size": 1, "phrase_anim": 0,
                      "phrase_custom": (200.0, 0.8), "ledaie": True, "ledaie_font": "MONO", "ledaie_color": 5,
                      "ledaie_custom": (45.0, 0.8), "caption_font": "MONO", "caption_color": 0,
                      "caption_custom": (200.0, 0.85), "constellations": True,
                      "sources": {}, "sprite_style": "ASTRAL"}
        self.timer = QTimer(self); self.timer.timeout.connect(self.update)
        self._slow = 0
        self._t0 = time.monotonic()

    def start(self) -> None:
        self.show(); self.timer.start(max(8, 1000 // self.fps))

    def stop(self) -> None:
        self.timer.stop(); self.hide()

    def initializeGL(self) -> None:  # noqa: N802
        from ..brainwash import Brainwash
        from ..capture import ScreenGrab
        from ..stories import Stories
        from .sprites import TextureCache
        try:
            self.grab = ScreenGrab()
            self.pipe = AuraPipeline(self.grab.width, self.grab.height)
            self.pipe.init()
            self.textures = TextureCache()
            self.stories = Stories()
            self.brainwash = Brainwash(self.root / "brainwash")
            from ..art import Art
            self.art = Art(self.root / "art", fetch=False)
            from .ghibli import ensure_files
            ensure_files()
            from ..ledaie import LedaieWords
            self.ledaie = LedaieWords()
            from ..stories import Constellations
            self.constellations = Constellations()
            from ..scenes import Stage, Scenes, BrainwashSource
            self.scenes = Scenes(self.grab.width, self.grab.height)
            self.stage = Stage()
            for src in (self.stories, self.constellations, self.ledaie, self.brainwash):
                src.auto = False                                  # the stage decides; nothing self-starts
            self.sources = {"story": self.stories, "constellation": self.constellations, "ledaie": self.ledaie,
                            "phrase": BrainwashSource(self.brainwash, "text"), "image": BrainwashSource(self.brainwash, "image"),
                            "scene": self.scenes}
        except Exception as exc:                 # noqa: BLE001 — say it in the UI, never hang
            self.error = f"aura: {exc}"
            self.timer.stop()

    def _quads(self, p: AuraParams, t: float) -> list:
        W, H = self.pipe.w, self.pipe.h
        out = []
        cap_tint = phrase_tint(int(self.flags["caption_color"]), p.hue, t, tuple(self.flags["caption_custom"]))
        cap_font = str(self.flags["caption_font"])
        self.stories.gap = float(self.flags["story_gap"])
        self.brainwash.gap = float(self.flags["phrase_gap"])
        if self.ledaie is not None:
            self.ledaie.gap = float(self.flags["story_gap"]) * 0.8
        # ---- the stage: one thing at a time ----
        sources = self.flags["sources"]
        self.stories.hidden = {k for k, v in sources.items() if v == "hidden"}
        self.stage.breath = float(self.flags["phrase_gap"])
        enabled = {"story": self.flags["stories"], "constellation": self.flags["stories"] and self.flags["constellations"],
                   "ledaie": self.flags["stories"] and self.flags["ledaie"] and bool(self.ledaie and self.ledaie.entries),
                   "phrase": self.flags["brainwash"] and bool(self.brainwash.phrases),
                   "image": self.flags["brainwash"] and bool(self.brainwash.images), "scene": self.flags["scenes"]}
        on = self.stage.tick(t, enabled, self.sources)
        self._spot = getattr(self, "_spot", 0.0) + ((1.0 if on else 0.0) - getattr(self, "_spot", 0.0)) * 0.08
        p.spotlight = self._spot
        if on == "scene":
            fr = self.scenes.frame(t, p.bass)
            if fr is not None:
                p.streak = fr.streak
                for b in fr.bodies:
                    bw = b["size"] * H / W; bh = b["size"]
                    fixed = int(self.flags.get("look", -1))
                    p.bodies.append({**b, "rect": (b["x"] - bw / 2, b["y"] - bh / 2, bw, bh),
                                     "alpha": 0.985 if b.get("alpha", 1.0) > 0.9 else b.get("alpha", 1.0),
                                     "look": fixed if fixed >= 0 else int(b.get("look", 0)),
                                     "behind": 1.0})                                   # everything passes behind the words
                for q in fr.quads:
                    if q.kind in ("glow", "spark"):
                        tex, w, h = self.textures.glow()
                        k = (0.12 * H) / h
                    elif q.kind.startswith("rig:") and fr.pose is not None:
                        from .rigs_draw import draw_pose
                        joints, woman, facing = fr.pose
                        tex, w, h = self.textures.dynamic(q.kind, draw_pose(joints, woman, 320, facing))
                        k = (0.62 * H) / h                            # a person: close, about two thirds of the screen
                    else:
                        tex, w, h = self.textures.sprite(q.kind, str(self.flags["sprite_style"]))
                        k = (0.22 * H) / h
                    sw, sh = w * k * q.scale / W, h * k * q.scale / H
                    out.append((tex, q.x - sw / 2, q.y - sh / 2, sw, sh, q.alpha, q.tint, q.angle, 1.0))
                if fr.caption_alpha > 0.01:
                    ctex, cw, ch = self.textures.text(fr.caption, 20, cap_font)
                    out.append((ctex, 0.5 - cw / W / 2, 0.86, cw / W, ch / H, fr.caption_alpha, cap_tint))
            return out
        if on not in ("phrase", "image"):
            for name in ("phrase", "image"):
                self.sources[name].settle()
        led_tint = phrase_tint(int(self.flags["ledaie_color"]), p.hue, t, tuple(self.flags["ledaie_custom"]))
        led_font = str(self.flags["ledaie_font"])
        if on == "constellation":
            self.constellations.gap = float(self.flags["story_gap"]) * 1.5
            sky = self.constellations.frame(t)
            if sky is not None:
                ctex, cw, ch = self.textures.constellation(sky.index)
                k = (0.42 * H) / ch; cw, ch = cw * k * sky.scale, ch * k * sky.scale
                out.append((ctex, sky.x - cw / W / 2, sky.y - ch / H / 2, cw / W, ch / H, sky.alpha, (0.9, 0.93, 1.0)))
                lt, lw, lh = self.textures.text(sky.caption, 20, cap_font)
                out.append((lt, sky.x - lw / W / 2, sky.y + ch / H / 2 + 0.01, lw / W, lh / H, sky.caption_alpha, cap_tint))
        if on == "ledaie":
            show = self.ledaie.frame(t)
            if show is not None:
                hx, hw_, hh_ = self.textures.handscript(show.word, 96 if show.kind == "symbol" else 64)
                sw, sh = hw_ * show.scale / W, hh_ * show.scale / H
                out.append((hx, show.x - sw / 2, show.y - sh / 2, sw, sh, show.alpha, led_tint))
                # the Latin spelling always rides under the runes, so a word can always be checked against the dictionary
                line = f"{show.word}  ·  {show.meaning}" if show.kind == "word" else show.word
                lt, lw, lh = self.textures.text(line, 22 if show.kind == "word" else 18, led_font)
                out.append((lt, show.x - lw / W / 2, show.y + sh / 2 + 0.01, lw / W, lh / H, show.alpha * (0.8 if show.kind == "word" else 0.55), led_tint))
        if on == "story":
            shot = self.stories.frame(t)
            if shot is not None:
                wants_art = sources.get(shot.kind) == "painting"
                painting = self.art.pick(shot.kind) if (self.art is not None and wants_art) else None
                got = self.textures.art(str(painting)) if painting else None
                if got is not None:
                    tex, w, h = got
                    k = (0.3 * H) / max(h, 1); w, h = w * k, h * k     # paintings: ~30% of screen height
                else:
                    tex, w, h = self.textures.sprite(shot.kind, str(self.flags["sprite_style"]))
                sw, sh = w * shot.scale / W, h * shot.scale / H
                out.append((tex, shot.x - sw / 2, shot.y - sh / 2, sw, sh, shot.alpha, (0.95, 0.95, 1.0)))
                if shot.caption_alpha > 0.01:
                    ctex, cw, ch = self.textures.text(shot.caption, 20, cap_font)
                    out.append((ctex, 0.5 - cw / W / 2, 0.86, cw / W, ch / H, shot.caption_alpha, cap_tint))
        if on in ("phrase", "image"):
            self.sources[on].settle()
            for item in self.brainwash.frame(t, p.flash):
                if item.kind == "text":
                    px = (22, 30, 44, 64)[int(self.flags["phrase_size"]) % 4]
                    anim = PHRASE_ANIMS[int(self.flags["phrase_anim"]) % len(PHRASE_ANIMS)]
                    text = item.payload
                    if anim == "TYPE":                                   # letters arrive one by one
                        n = max(1, min(len(text), int((t - self.brainwash.text[1]) * 12)))
                        text = text[:n]
                    tex, w, h = self.textures.text(text, px, str(self.flags["phrase_font"]))
                    if anim == "PULSE":
                        item.scale *= 1.0 + 0.18 * p.flash + 0.05 * p.bass
                    elif anim == "RISE":
                        item.y = 1.05 - (1.05 - item.y) * 1.0 - 0.35 * ((t - self.brainwash.text[1]) / self.brainwash.text[2])
                    elif anim == "FLASH":
                        item.alpha = item.alpha * 0.5 + 0.45 * p.flash
                    tint = phrase_tint(int(self.flags["phrase_color"]), p.hue, t, tuple(self.flags["phrase_custom"]))
                    sw, sh = w * item.scale / W, h * item.scale / H
                    out.append((tex, item.x - sw / 2, item.y - sh / 2, sw, sh, item.alpha, tint))
                    continue
                else:
                    got = self.textures.image(item.payload)
                    if got is None:
                        continue
                    tex, w, h = got
                    k = (0.38 * H) / max(h, 1); w, h = w * k, h * k
                sw, sh = w * item.scale / W, h * item.scale / H
                out.append((tex, item.x - sw / 2, item.y - sh / 2, sw, sh, item.alpha, (1.0, 0.96, 0.9)))
        return out

    def paintGL(self) -> None:  # noqa: N802
        if self.pipe is None or self.grab is None:
            return
        t0 = time.perf_counter()
        try:
            p = self.params_fn()
            geo = self.geometry()
            cp = QCursor.pos()
            p.cursor = ((cp.x() - geo.x()) / max(1, geo.width()), (cp.y() - geo.y()) / max(1, geo.height()))
            p.sprites = self._quads(p, time.monotonic() - self._t0)
            self.pipe.upload(self.grab.grab())
            self.pipe.render(p, self.defaultFramebufferObject(), (self.width(), self.height()))
        except Exception as exc:                 # noqa: BLE001
            self.error = f"aura: {exc}"
            self.timer.stop()
            return
        ms = (time.perf_counter() - t0) * 1000.0
        self.frame_ms += (ms - self.frame_ms) * 0.1
        if self.frame_ms > 1000.0 / self.fps * 0.8:
            self._slow += 1
            if self._slow > 60 and self.fps > 15:
                self.fps -= 5; self.timer.setInterval(1000 // self.fps); self._slow = 0
        else:
            self._slow = 0


def render_png(src_png: str, out_png: str, params: AuraParams | None = None, frames: int = 3,
               sprites: bool = False) -> None:
    """Offline proof: run the exact pipeline on a screenshot and write the glow layer."""
    from PyQt6.QtGui import QImage, QOffscreenSurface, QOpenGLContext, QPainter
    img = QImage(src_png).convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    frame = np.frombuffer(img.constBits().asarray(h * img.bytesPerLine()), dtype=np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w, :]
    fmt = QSurfaceFormat(); fmt.setVersion(3, 3); fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    surf = QOffscreenSurface(); surf.setFormat(fmt); surf.create()
    ctx = QOpenGLContext(); ctx.setFormat(fmt)
    if not ctx.create() or not ctx.makeCurrent(surf):
        raise RuntimeError("no OpenGL 3.3 context")
    pipe = AuraPipeline(w, h); pipe.init()
    out = QOpenGLFramebufferObject(QSize(w, h), QOpenGLFramebufferObject.Attachment.NoAttachment, gl.GL_TEXTURE_2D, gl.GL_RGBA8)
    p = params or AuraParams(hue=190.0, loud=0.7, bass=0.6, flash=0.8)
    if sprites:
        from .sprites import TextureCache
        tc = TextureCache()
        art = Path(src_png).parent / "ufo.jpg"
        got = tc.art(str(art)) if art.exists() else None
        tex, sw, sh = got if got else tc.sprite("ufo")
        if got:
            k = (0.3 * h) / sh; sw, sh = sw * k, sh * k
        p.sprites.append((tex, 0.62, 0.18, sw / w, sh / h, 0.6, (0.95, 0.95, 1.0)))
        ttex, tw, th = tc.text("a saucer cruises past, running lights dimmed, late for something", 20)
        p.sprites.append((ttex, 0.5 - tw / w / 2, 0.86, tw / w, th / h, 0.35, (0.94, 0.91, 0.85)))
        btex, bw, bh = tc.text("you go king", 30)
        p.sprites.append((btex, 0.15, 0.3, bw / w, bh / h, 0.25, (1.0, 0.96, 0.9)))
        from ..ledaie import load
        e = load()[3] if load() else None
        if e:
            hx, hw_, hh_ = tc.handscript(e.word, 64)
            p.sprites.append((hx, 0.55 - hw_ / w / 2, 0.42, hw_ / w, hh_ / h, 0.5, (0.98, 0.93, 0.8)))
            lt, lw, lh = tc.text(f"{e.word}  ·  {e.meaning}", 22)
            p.sprites.append((lt, 0.55 - lw / w / 2, 0.42 + hh_ / h + 0.01, lw / w, lh / h, 0.4, (0.94, 0.91, 0.85)))
    for i in range(frames):
        p.time = 1.7 + 0.033 * i
        pipe.upload(frame)
        pipe.render(p, out.handle(), (w, h))
    glow = out.toImage(False)
    glow.save(out_png)
    comp = img.copy(); painter = QPainter(comp); painter.drawImage(0, 0, glow.mirrored(False, True)); painter.end()
    comp.save(out_png.replace(".png", "-over.png"))
    ctx.doneCurrent()
