"""AURA — a click-through light layer over the whole screen.

Every frame: grab the root window (party/capture.py), hand it to the GPU, find every
edge (window borders, lines, glyph strokes) with a Sobel pass, blur that edge map
into a halo, tint it with the scene hue and the beat, and draw it as a premultiplied
ARGB layer that KWin composites over everything. No app is touched.

The grab sees our own layer too, so the edge pass first un-blends last frame's glow
(we know exactly what we drew). Ping-pong FBOs keep the previous glow around.
`AuraPipeline` is window-agnostic so the same code renders an offline PNG for proof.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from OpenGL import GL as gl
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication, QSurfaceFormat
from PyQt6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLShader, QOpenGLShaderProgram, QOpenGLWindow

VERT = """#version 330 core
const vec2 verts[3] = vec2[3](vec2(-1.0,-1.0), vec2(3.0,-1.0), vec2(-1.0,3.0));
out vec2 uv;
void main(){ vec2 p = verts[gl_VertexID]; uv = (p + 1.0) * 0.5; gl_Position = vec4(p, 0.0, 1.0); }
"""
EDGES = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D screen; uniform sampler2D prevGlow; uniform vec2 texel;
uniform float t0; uniform float t1;
float luma(vec2 p){
  vec4 c = texture(screen, p); vec4 g = texture(prevGlow, p);
  float a = min(g.a, 0.95);
  vec3 s = clamp((c.rgb - g.rgb) / (1.0 - a), 0.0, 1.0);
  return dot(s, vec3(0.299, 0.587, 0.114));
}
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
  for (int i = 1; i < 5; i++) {
    s += texture(src, uv + dir * float(i)).r * w[i];
    s += texture(src, uv - dir * float(i)).r * w[i];
  }
  frag = vec4(s, s, s, 1.0);
}
"""
COMPOSE = """#version 330 core
in vec2 uv; out vec4 frag;
uniform sampler2D edges; uniform sampler2D halo;
uniform float time; uniform float hue; uniform float loud; uniform float bass; uniform float flash;
uniform float coreAmt; uniform float haloAmt; uniform float astralAmt; uniform float ghostAmt;
uniform int colorMode; uniform int border; uniform vec2 res;
float hash21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  float a = hash21(i), b = hash21(i + vec2(1, 0)), c = hash21(i + vec2(0, 1)), d = hash21(i + vec2(1, 1));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { v += a * vnoise(p); p = p * 2.03 + 11.7; a *= 0.5; } return v; }
vec3 hsv2rgb(vec3 c){ vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0); return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y); }
// mother-of-pearl: a pastel cosine palette pulled toward white
vec3 pearl(float t){ vec3 c = 0.72 + 0.28 * cos(6.28318 * (t + vec3(0.0, 0.33, 0.67))); return mix(c, vec3(1.0), 0.22); }
// the colour worlds — t: a 0..1 field over the screen, k: local strength 0..1
vec3 palette(int mode, float t, float k){
  if (mode == 1) return hsv2rgb(vec3(hue / 360.0, 0.85, 1.0));                                   // MONO
  if (mode == 2) return hsv2rgb(vec3(fract(t * 1.5), 0.9, 1.0));                                 // RAINBOW
  if (mode == 3) return mix(vec3(0.9, 0.15, 0.0), vec3(1.0, 0.95, 0.6), k) * (0.6 + 0.4 * k);    // FIRE
  if (mode == 4) return mix(vec3(0.2, 0.5, 1.0), vec3(0.85, 1.0, 1.0), k);                       // ICE
  if (mode == 5) return mix(vec3(1.0, 0.72, 0.25), vec3(1.0, 0.98, 0.85), k);                    // HOLY
  if (mode == 6) { float b = 0.5 + 0.5 * sin(t * 12.0 + time * 0.5); return mix(vec3(0.2, 1.0, 0.5), vec3(0.6, 0.3, 1.0), b); } // AURORA
  return pearl(t);                                                                               // PEARL
}
// the border styles — h: blurred edge map (a soft distance to the nearest stroke), hs: the same, offset
float ring(int style, float h, float hs, vec2 px){
  if (style == 1) return pow(h, 0.5) * 0.5 + smoothstep(0.12, 0.35, h) * 0.9;                             // NEON
  if (style == 2) return smoothstep(0.05, 0.09, h) * (1.0 - smoothstep(0.10, 0.15, h)) * 1.6 + smoothstep(0.28, 0.45, h); // DOUBLE
  if (style == 3) return smoothstep(0.08, 0.11, h) * (1.0 - smoothstep(0.12, 0.17, h)) * 1.8;            // OUTLINE
  if (style == 4) return h * (0.5 + step(0.45, vnoise(px * 0.12 + vec2(time * 7.0, -time * 5.0))));       // ELECTRIC
  if (style == 5) return hs;                                                                              // SHADOW
  return h;                                                                                               // SOFT
}
void main(){
  float e = texture(edges, uv).r;
  float h = texture(halo, uv).r;
  float hs = texture(halo, uv - vec2(5.0, -5.0) / res).r;
  vec2 px = uv * res;
  float t = hue / 360.0 + 0.12 * sin(uv.x * 4.1 + time * 0.21) + 0.12 * sin(uv.y * 3.3 - time * 0.17)
          + 0.10 * (vnoise(uv * 3.0 + time * 0.05) - 0.5);
  float k = clamp(h * 3.0, 0.0, 1.0);
  vec3 ringC = palette(colorMode, t, k);
  vec3 coreC = mix(palette(colorMode, t + 0.08, 1.0), vec3(1.0), 0.6);
  float ringA = ring(border, h, hs, px) * (1.0 - e) * haloAmt;   // beside the strokes, never on them
  float coreA = e * coreAmt;                                       // only when he wants bold
  float content = smoothstep(0.02, 0.25, h);
  // stars: look at the 3x3 neighbouring cells so no star is cut at a cell edge
  float star = 0.0; vec2 cell = floor(px / 28.0);
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 c = cell + vec2(i, j);
    if (hash21(c + 11.0) < 0.55) continue;
    vec2 cp = (c + vec2(hash21(c), hash21(c + 7.0))) * 28.0;
    float tw = pow(0.5 + 0.5 * sin(time * (1.0 + hash21(c + 3.0) * 2.0) + hash21(c) * 6.28), 6.0);
    star += smoothstep(2.2, 0.0, length(px - cp)) * tw;
  }
  star *= 0.35 + 0.65 * flash;
  // orbs born on the beat: same 3x3 search, so they drift across cell borders whole
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
  // the background: a domain-warped nebula and a ghost party, where there is no content
  vec2 q = vec2(fbm(uv * 2.0 + time * 0.02), fbm(uv * 2.0 - time * 0.015));
  float n = fbm(uv * 3.0 + q * 1.5 + time * 0.01);
  float neb = smoothstep(0.35, 0.8, n) * (0.10 + 0.14 * loud) * ghostAmt;
  float ghost = 0.0;
  for (int i = 0; i < 6; i++) {
    float fi = float(i); float ph = hash21(vec2(fi, 3.0)) * 6.28;
    vec2 c = vec2(0.08 + 0.84 * fract(hash21(vec2(fi, 1.0)) + time * 0.012 * (0.5 + hash21(vec2(fi, 2.0)))),
                  0.58 + 0.10 * sin(time * 0.7 + ph));
    c.x += 0.015 * sin(time * 2.0 * (1.0 + bass) + ph);                       // sway on the beat
    vec2 d = (uv - c) * vec2(res.x / res.y, 1.0);
    float body = exp(-dot(d * vec2(9.0, 4.0), d * vec2(9.0, 4.0)));
    vec2 dh = d - vec2(0.0, -0.17);
    float head = exp(-dot(dh * 14.0, dh * 14.0));
    ghost += (body * 0.8 + head) * (0.6 + 0.4 * sin(time * 1.3 + ph));
  }
  ghost *= ghostAmt * (0.05 + 0.08 * loud + 0.10 * flash);
  float sky = (star * 0.9 + orb) * astralAmt + neb + ghost;
  sky *= 1.0 - content * 0.85;
  vec3 skyC = palette(colorMode, t + 0.3 + 0.25 * n, n);
  float total = coreA + ringA + sky;
  float a = clamp(total, 0.0, 0.9);
  vec3 rgb = (coreC * coreA + ringC * ringA + skyC * sky) / max(total, 1e-4);
  frag = vec4(rgb * a, a);                       // premultiplied, as X ARGB visuals expect
}
"""
BLIT = """#version 330 core
in vec2 uv; out vec4 frag; uniform sampler2D src;
void main(){ frag = texture(src, vec2(uv.x, 1.0 - uv.y)); }
"""


COLOR_MODES = ["PEARL", "MONO", "RAINBOW", "FIRE", "ICE", "HOLY", "AURORA"]
BORDER_STYLES = ["SOFT", "NEON", "DOUBLE", "OUTLINE", "ELECTRIC", "SHADOW"]


@dataclass
class AuraParams:
    hue: float = 200.0        # degrees
    loud: float = 0.0
    bass: float = 0.0
    flash: float = 0.0
    sensitivity: float = 1.0
    width: float = 2.0        # halo width, 0.5..6
    bold: bool = False        # paint the stroke pixels themselves (makes things bolder)
    astral: bool = True
    time: float = 0.0
    color_mode: int = 0       # index into COLOR_MODES
    border: int = 0           # index into BORDER_STYLES
    ghost: bool = True        # nebula + ghost party in the background

    def intensity(self) -> float:
        base = 0.12 + 0.5 * self.loud + 0.7 * self.flash
        return max(0.0, min(1.6, base * self.sensitivity))


def _rgb(hue: float, sat: float, val: float) -> tuple[float, float, float]:
    c = QColor.fromHsvF((hue % 360.0) / 360.0, sat, val)
    return c.redF(), c.greenF(), c.blueF()


class AuraPipeline:
    """GL-context-bound. Call `init()` with a current context, then `render()` per frame."""

    def __init__(self, width: int, height: int) -> None:
        self.w, self.h = width, height
        self.cur = 0

    def init(self) -> None:
        self.vao = gl.glGenVertexArrays(1)
        self.programs = {}
        for name, src in (("edges", EDGES), ("blur", BLUR), ("compose", COMPOSE), ("blit", BLIT)):
            prog = QOpenGLShaderProgram()
            if not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERT) or \
               not prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, src) or \
               not prog.link():
                raise RuntimeError(f"shader {name}: {prog.log()}")
            self.programs[name] = prog
        self.screen_tex = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.screen_tex)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, self.w, self.h, 0,
                        gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, None)
        full = QSize(self.w, self.h)
        half = QSize(max(1, self.w // 2), max(1, self.h // 2))
        mk = lambda size: QOpenGLFramebufferObject(size, QOpenGLFramebufferObject.Attachment.NoAttachment,
                                                   gl.GL_TEXTURE_2D, gl.GL_RGBA8)
        self.edges_fbo = mk(full)
        self.blur_fbo = [mk(half), mk(half)]
        self.glow_fbo = [mk(full), mk(full)]
        for f in (self.edges_fbo, *self.blur_fbo, *self.glow_fbo):
            gl.glBindTexture(gl.GL_TEXTURE_2D, f.texture())
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
            f.bind()
            gl.glClearColor(0, 0, 0, 0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            f.release()
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def upload(self, frame_bgra: np.ndarray) -> None:
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.screen_tex)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        gl.glTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, self.w, self.h,
                           gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, np.ascontiguousarray(frame_bgra))

    def _draw(self, name: str, textures: list[int], size: tuple[int, int], uniforms: dict) -> None:
        prog = self.programs[name]
        prog.bind()
        for unit, tex in enumerate(textures):
            gl.glActiveTexture(gl.GL_TEXTURE0 + unit)
            gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        for k, v in uniforms.items():
            loc = prog.uniformLocation(k)
            if isinstance(v, int):
                gl.glUniform1i(loc, v)
            elif isinstance(v, float):
                gl.glUniform1f(loc, v)
            elif len(v) == 2:
                gl.glUniform2f(loc, *v)
            else:
                gl.glUniform3f(loc, *v)
        gl.glViewport(0, 0, *size)
        gl.glBindVertexArray(self.vao)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        prog.release()

    def render(self, params: AuraParams, target_fbo: int, target_size: tuple[int, int]) -> int:
        """Run all passes; the glow ends up in glow_fbo[cur] and on `target_fbo`. Returns glow tex."""
        gl.glDisable(gl.GL_BLEND)
        prev = self.glow_fbo[1 - self.cur].texture()
        W, H = self.w, self.h
        hw, hh = self.blur_fbo[0].width(), self.blur_fbo[0].height()
        self.edges_fbo.bind()
        self._draw("edges", [self.screen_tex, prev], (W, H),
                   {"screen": 0, "prevGlow": 1, "texel": (1.0 / W, 1.0 / H), "t0": 0.07, "t1": 0.32})
        radius = max(0.3, params.width) * (0.6 + 0.9 * params.bass)
        passes = 2 if params.width > 2.2 else 1          # wide halos: blur twice, still cheap at half res
        src = self.edges_fbo.texture()
        for _ in range(passes):
            self.blur_fbo[0].bind()
            self._draw("blur", [src], (hw, hh), {"src": 0, "dir": (radius / hw, 0.0)})
            self.blur_fbo[1].bind()
            self._draw("blur", [self.blur_fbo[0].texture()], (hw, hh), {"src": 0, "dir": (0.0, radius / hh)})
            src = self.blur_fbo[1].texture()
        amt = params.intensity()
        self.glow_fbo[self.cur].bind()
        self._draw("compose", [self.edges_fbo.texture(), self.blur_fbo[1].texture()], (W, H),
                   {"edges": 0, "halo": 1, "time": float(params.time), "hue": float(params.hue),
                    "loud": float(params.loud), "bass": float(params.bass), "flash": float(params.flash),
                    "coreAmt": amt * 0.8 if params.bold else 0.0, "haloAmt": amt * 2.6,
                    "astralAmt": 1.0 if params.astral else 0.0, "ghostAmt": 1.0 if params.ghost else 0.0,
                    "colorMode": int(params.color_mode), "border": int(params.border),
                    "res": (float(W), float(H))})
        glow = self.glow_fbo[self.cur].texture()
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, target_fbo)
        gl.glClearColor(0, 0, 0, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        self._draw("blit", [glow], target_size, {"src": 0})
        self.cur = 1 - self.cur
        return glow


class AuraWindow(QOpenGLWindow):
    """Fullscreen, frameless, always on top, transparent for input. He never notices it is a window."""

    def __init__(self, params_fn, fps: int = 30) -> None:
        super().__init__()
        self.params_fn = params_fn
        self.fps = fps
        self.frame_ms = 0.0
        self.error = ""
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setAlphaBufferSize(8)
        fmt.setSwapInterval(0)
        self.setFormat(fmt)
        self.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
                      | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput
                      | Qt.WindowType.BypassWindowManagerHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setTitle("Party Aura")
        geo = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        self.grab = None
        self.pipe = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self._slow = 0

    def start(self) -> None:
        self.show()
        self.timer.start(max(8, 1000 // self.fps))

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def initializeGL(self) -> None:  # noqa: N802
        from ..capture import ScreenGrab
        try:
            self.grab = ScreenGrab()
            self.pipe = AuraPipeline(self.grab.width, self.grab.height)
            self.pipe.init()
        except Exception as exc:                 # noqa: BLE001 — say it in the UI, never hang
            self.error = f"aura: {exc}"
            self.timer.stop()

    def paintGL(self) -> None:  # noqa: N802
        if self.pipe is None or self.grab is None:
            return
        t = time.perf_counter()
        try:
            self.pipe.upload(self.grab.grab())
            self.pipe.render(self.params_fn(), self.defaultFramebufferObject(),
                             (self.width(), self.height()))
        except Exception as exc:                 # noqa: BLE001
            self.error = f"aura: {exc}"
            self.timer.stop()
            return
        ms = (time.perf_counter() - t) * 1000.0
        self.frame_ms += (ms - self.frame_ms) * 0.1
        # usable-PC guard: if a frame costs more than its slot, step the rate down
        if self.frame_ms > 1000.0 / self.fps * 0.8:
            self._slow += 1
            if self._slow > 60 and self.fps > 15:
                self.fps -= 5
                self.timer.setInterval(1000 // self.fps)
                self._slow = 0
        else:
            self._slow = 0


def render_png(src_png: str, out_png: str, params: AuraParams | None = None, frames: int = 3) -> None:
    """Offline proof: run the exact pipeline on a screenshot and write the glow layer."""
    from PyQt6.QtGui import QImage, QOffscreenSurface, QOpenGLContext
    img = QImage(src_png).convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    frame = np.frombuffer(img.constBits().asarray(h * img.bytesPerLine()), dtype=np.uint8)
    frame = frame.reshape(h, img.bytesPerLine() // 4, 4)[:, :w, :]
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    surf = QOffscreenSurface()
    surf.setFormat(fmt)
    surf.create()
    ctx = QOpenGLContext()
    ctx.setFormat(fmt)
    if not ctx.create() or not ctx.makeCurrent(surf):
        raise RuntimeError("no OpenGL 3.3 context")
    pipe = AuraPipeline(w, h)
    pipe.init()
    out = QOpenGLFramebufferObject(QSize(w, h), QOpenGLFramebufferObject.Attachment.NoAttachment,
                                   gl.GL_TEXTURE_2D, gl.GL_RGBA8)
    p = params or AuraParams(hue=190.0, loud=0.7, bass=0.6, flash=0.8)
    for i in range(frames):                     # a few frames so the un-blend path runs too
        p.time = 1.7 + 0.033 * i
        pipe.upload(frame)
        pipe.render(p, out.handle(), (w, h))
    glow = out.toImage(False)
    glow.save(out_png)
    # also a composite preview: the screenshot with the glow over it (premultiplied source-over)
    from PyQt6.QtGui import QPainter
    comp = img.copy()
    painter = QPainter(comp)
    painter.drawImage(0, 0, glow.mirrored(False, True))
    painter.end()
    comp.save(out_png.replace(".png", "-over.png"))
    ctx.doneCurrent()
