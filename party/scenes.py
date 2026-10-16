"""The stage and the mini-movies.

STAGE: stories, Ledaie words, phrases, pictures, constellations and scenes each keep their own
timer; `at_once` says how many share the screen (1 = each alone, then a breath, then the next).

SCENES are animated, not pictures slid around: a shooting star is a real streak with sparks
drawn by the shader; a spaceship banks along a curve, its thruster flickers, exhaust particles
trail behind it, its light blinks. Pure Python here; the window turns them into quads + shader fx.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

SOURCES = ("story", "constellation", "ledaie", "phrase", "image", "scene")
DEFAULT_EVERY = {"story": 20.0, "constellation": 45.0, "ledaie": 25.0, "phrase": 8.0, "image": 60.0, "scene": 40.0}


class Stage:
    """The only clock. Every source has its own `every` (seconds from the end of one appearance to
    the start of the next, ±30% jitter, live: a slider change applies at once). `at_once` says how
    many things may be on stage together (1 = the spotlight: one alone, then `breath` of empty
    stage). The longest-overdue source goes first, so nothing starves."""

    def __init__(self, breath: float = 5.0, at_once: int = 1, every: dict | None = None, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.breath = breath
        self.at_once = at_once
        self.every = dict(DEFAULT_EVERY, **(every or {}))
        self.active: set[str] = set()
        self.free_at = 4.0
        self.last: dict[str, float] = {}          # when each source last ended (or first became eligible)
        self.jit: dict[str, float] = {}

    @property
    def on(self) -> str | None:
        """Compat: one name on stage (any), or None."""
        return next(iter(sorted(self.active)), None)

    def _due(self, name: str) -> float:
        return self.last[name] + float(self.every.get(name, 20.0)) * self.jit[name]

    def _rest(self, name: str, t: float) -> None:
        self.last[name] = t
        self.jit[name] = self.rng.uniform(0.7, 1.3)

    def tick(self, t: float, enabled: dict[str, bool], sources: dict) -> set[str]:
        """Returns the set of names on stage right now (empty during a breath)."""
        for name in list(self.active):
            if not sources[name].active:
                self.active.discard(name)
                self._rest(name, t)
                if self.at_once <= 1:
                    self.free_at = t + self.breath
        if t < self.free_at:
            return set(self.active)
        for name in SOURCES:
            if name not in self.last:                          # first appearance: staggered, not all at once
                self.last[name] = t - float(self.every.get(name, 20.0)) * 0.7 + self.rng.uniform(0.0, 0.3) * float(self.every.get(name, 20.0))
                self.jit[name] = 1.0
        due = sorted((self._due(n), n) for n in SOURCES
                     if n in sources and enabled.get(n, False) and n not in self.active and t >= self._due(n))
        for _, name in due:
            if len(self.active) >= max(1, int(self.at_once)):
                break
            src = sources[name]
            src.begin(t)
            if src.active or getattr(src, "pending", False):
                self.active.add(name)
            else:
                self._rest(name, t)                            # nothing to show (empty folder): try again later
        return set(self.active)


class BrainwashSource:
    """Adapter: one Brainwash object, two stage sources (phrase, picture)."""

    def __init__(self, bw, kind: str) -> None:
        self.bw, self.kind = bw, kind
        self.pending = False

    @property
    def active(self) -> bool:
        return (self.bw.text if self.kind == "text" else self.bw.image) is not None or self.pending

    def begin(self, t: float) -> None:
        self.bw.begin(self.kind, t)
        self.pending = True          # it materialises on the next frame()

    def settle(self) -> None:
        self.pending = False


@dataclass
class Quad:
    kind: str                  # sprite kind, or "glow" / "spark"
    x: float
    y: float
    scale: float = 1.0
    alpha: float = 1.0
    angle: float = 0.0         # radians, clockwise on screen
    tint: tuple = (1.0, 1.0, 1.0)


@dataclass
class Frame:
    quads: list = field(default_factory=list)
    streak: tuple = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)     # head x, head y (uv), dir x, dir y, length px, amount
    caption: str = ""
    caption_alpha: float = 0.0
    pose: tuple | None = None                            # (joints, woman, facing) for a rig quad this frame
    bodies: list = field(default_factory=list)           # raymarched 3D bodies: dict(mode, x, y, size, joints, woman, yaw, bank, tint, alpha, engine)


class ShootingStar:
    """A real one: a bright head, a long fading tail, sparks shed along the way. Sometimes a shower."""
    name = "shooting star"

    def __init__(self, rng: random.Random, W: int, H: int) -> None:
        self.rng, self.W, self.H = rng, W, H
        n = 1 if rng.random() < 0.6 else rng.randint(2, 4)
        self.stars = []
        for i in range(n):
            ang = rng.uniform(math.radians(20), math.radians(50)) * (1 if rng.random() < 0.5 else -1)
            dx, dy = math.cos(ang) * (1 if ang > 0 else -1), abs(math.sin(ang))
            x0 = rng.uniform(0.05, 0.4) if dx > 0 else rng.uniform(0.6, 0.95)
            self.stars.append({"t0": i * rng.uniform(0.6, 1.4), "dur": rng.uniform(1.4, 2.6),
                               "x0": x0, "y0": rng.uniform(-0.05, 0.3), "dx": dx, "dy": dy,
                               "speed": rng.uniform(0.35, 0.6), "sparks": []})
        self.dur = max(s["t0"] + s["dur"] for s in self.stars) + 1.2
        self.caption = rng.choice(["a shooting star, make a wish", "a real one, gone in a breath",
                                   "a stone from somewhere, burning up for you", "a shower, each one a wish nobody claimed"])

    def frame(self, u: float, t: float, bass: float) -> Frame:
        f = Frame()
        T = u * self.dur
        best = 0.0
        for s in self.stars:
            k = (T - s["t0"]) / s["dur"]
            if not 0.0 <= k <= 1.0:
                continue
            x = s["x0"] + s["dx"] * 0.75 * k                    # crosses about three quarters of the screen
            y = s["y0"] + s["dy"] * 0.5 * k
            amt = math.sin(k * math.pi) ** 0.5
            if amt > best:
                best = amt
                f.streak = (x, y, s["dx"], s["dy"], 180.0 + 220.0 * k, amt * (0.8 + 0.4 * bass))
            if self.rng.random() < 0.35:
                s["sparks"].append([x, y, self.rng.uniform(-0.02, 0.02), self.rng.uniform(0.0, 0.03), 1.0])
            for sp in s["sparks"]:
                sp[0] += sp[2] * 0.016; sp[1] += sp[3] * 0.016; sp[4] -= 0.025
                if sp[4] > 0:
                    f.quads.append(Quad("spark", sp[0], sp[1], 0.08 * sp[4], 0.9 * sp[4], 0.0, (1.0, 0.85, 0.6)))
            s["sparks"] = [sp for sp in s["sparks"] if sp[4] > 0][-40:]
        f.caption, f.caption_alpha = self.caption, 0.3 * min(1.0, u * 4, (1 - u) * 4)
        return f


class SpaceshipFlight:
    """A ship on a curve: it approaches, banks, passes close, and leaves. Thruster, exhaust, nav light."""
    name = "spaceship"

    def __init__(self, rng: random.Random, W: int, H: int) -> None:
        self.rng = rng
        self.dur = rng.uniform(11.0, 15.0)
        self.kind = rng.choice(["rocket", "ufo", "satellite"])
        flip = rng.random() < 0.5
        self.p0 = (-0.15 if not flip else 1.15, rng.uniform(0.15, 0.4))
        self.p1 = (rng.uniform(0.3, 0.7), rng.uniform(0.2, 0.8))
        self.p2 = (1.15 if not flip else -0.15, rng.uniform(0.15, 0.45))
        self.zmax = rng.uniform(1.6, 2.4)
        self.exhaust: list = []
        self.caption = rng.choice(["a ship passes, engines humming, somebody at the window",
                                   "a ship banks hard just to look at you", "running lights on, headed somewhere good",
                                   "a long haul freighter, quiet as a thought", "the pilot waves; the ship keeps its course"])

    def _pos(self, u: float) -> tuple[float, float]:
        a, b, c = self.p0, self.p1, self.p2
        return ((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * b[0] + u * u * c[0],
                (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * b[1] + u * u * c[1])

    def frame(self, u: float, t: float, bass: float) -> Frame:
        f = Frame()
        x, y = self._pos(u)
        x2, y2 = self._pos(min(1.0, u + 0.01))
        heading = math.atan2(y2 - y, x2 - x)
        z = 1.0 + (self.zmax - 1.0) * (1.0 - math.sin(u * math.pi))        # closest at the middle
        scale = 1.6 / z
        bank = 0.35 * math.sin(u * math.pi * 2.0)
        fade = min(1.0, u * 4.0, (1.0 - u) * 4.0)
        facing = heading + (math.pi / 2 if self.kind == "rocket" else 0.0)
        # exhaust particles, shed behind the ship
        bx, by = x - math.cos(heading) * 0.06 * scale, y - math.sin(heading) * 0.06 * scale
        for _ in range(2):
            self.exhaust.append([bx, by, -math.cos(heading) * 0.08 + self.rng.uniform(-0.02, 0.02),
                                 -math.sin(heading) * 0.08 + self.rng.uniform(-0.02, 0.02), 1.0])
        for e in self.exhaust:
            e[0] += e[2] * 0.016; e[1] += e[3] * 0.016; e[4] -= 0.02
            if e[4] > 0:
                f.quads.append(Quad("glow", e[0], e[1], 0.28 * scale * (1.4 - e[4]), 0.55 * e[4] * fade, 0.0, (0.6, 0.85, 1.0)))
        self.exhaust = [e for e in self.exhaust if e[4] > 0][-60:]
        # thruster flame: flickers with the bass
        flick = 0.7 + 0.5 * self.rng.random() + 0.6 * bass
        f.quads.append(Quad("glow", bx, by, 0.42 * scale * flick, 0.9 * fade, 0.0, (1.0, 0.75, 0.35)))
        f.quads.append(Quad("glow", bx, by, 0.2 * scale * flick, 0.95 * fade, 0.0, (1.0, 0.95, 0.8)))
        # the hull: a lit 3D body, yawed along its heading and banked through the curve
        f.bodies.append({"mode": 1, "x": x, "y": y, "size": 0.36 * scale, "joints": None, "woman": 0.0,
                         "yaw": -heading * 0.0 + 0.0, "bank": -heading - bank, "tint": (1.0, 1.0, 1.0), "alpha": 0.95 * fade,
                         "engine": 0.5 + 0.5 * bass})
        # nav light blinks once a second
        if (t % 1.0) < 0.12:
            f.quads.append(Quad("spark", x + math.cos(heading + 1.3) * 0.03 * scale, y + math.sin(heading + 1.3) * 0.03 * scale,
                                0.05 * scale, 0.9 * fade, 0.0, (1.0, 0.3, 0.3)))
        f.caption, f.caption_alpha = self.caption, 0.3 * min(1.0, (u - 0.1) * 5, (0.9 - u) * 5)
        return f


class Walker:
    """A man walks across the void, close to you, bobbing with each step; stars pass behind him."""
    name = "walker"

    def __init__(self, rng: random.Random, W: int, H: int) -> None:
        self.rng = rng
        self.dur = rng.uniform(12.0, 16.0)
        self.flip = rng.random() < 0.5
        self.y = rng.uniform(0.55, 0.75)
        self.caption = rng.choice(["a man walks by on nothing, going somewhere, unhurried",
                                   "someone out for a walk in the dark, hands swinging", "a walker with no road, fine with it",
                                   "he walks past like the void were a street"])

    def frame(self, u: float, t: float, bass: float) -> Frame:
        from .rigs import walker_pose
        f = Frame()
        x = (-0.12 + 1.24 * u) if not self.flip else (1.12 - 1.24 * u)
        from .rigs import walk_phase
        facing = -1.0 if self.flip else 1.0
        travelled = abs(x - (-0.12 if not self.flip else 1.12)) * 1366 / (0.78 * 768)      # ground covered, in rig units
        j = walker_pose(walk_phase(travelled), 1.0, facing)
        joints = [(j[k][0], j[k][1], z) for k, z in (("hip", 0.0), ("neck", 0.0), ("head", 0.0), ("knee_l", 0.07), ("foot_l", 0.07),
                                                    ("knee_r", -0.07), ("foot_r", -0.07), ("elbow_l", 0.1), ("hand_l", 0.1), ("elbow_r", -0.1), ("hand_r", -0.1))]
        yaw = 0.5 * facing                                                      # three-quarter view, facing the way he walks
        f.bodies.append({"mode": 0, "x": x, "y": self.y, "size": 0.78, "joints": joints, "woman": 0.0, "yaw": yaw, "bank": 0.0,
                         "tint": (1.0, 1.0, 1.0), "alpha": 0.95 * min(1.0, u * 4, (1 - u) * 4)})
        f.caption, f.caption_alpha = self.caption, 0.3 * min(1.0, (u - 0.1) * 5, (0.9 - u) * 5)
        return f


class Kiss:
    """A woman steps out of the dark, blows you a kiss; the kiss flies at you and she dissolves."""
    name = "kiss"

    def __init__(self, rng: random.Random, W: int, H: int) -> None:
        self.rng = rng
        self.dur = rng.uniform(9.0, 11.0)
        self.x = rng.uniform(0.3, 0.7)
        self.caption = rng.choice(["she blows you a kiss and dissolves into the void", "a kiss from somewhere far, aimed well",
                                   "she waves the kiss off her hand and it finds you"])

    def frame(self, u: float, t: float, bass: float) -> Frame:
        from .rigs import kiss_pose
        f = Frame()
        j, kiss = kiss_pose(u, t)
        fade = min(1.0, u * 3.0, (1.0 - u) * 2.5) if u < 0.9 else max(0.0, (1 - u) * 10)
        rise = max(0.0, min(1.0, (u - 0.15) / 0.3)); push = max(0.0, min(1.0, (u - 0.47) / 0.13))
        depth = {"hip": 0.0, "neck": 0.0, "head": 0.0, "knee_l": 0.0, "foot_l": 0.0, "knee_r": 0.0, "foot_r": 0.0,
                 "elbow_l": 0.03, "hand_l": 0.03, "elbow_r": 0.08 + 0.1 * rise, "hand_r": 0.12 * rise + 0.35 * push}   # the hand comes toward you
        joints = [(j[k][0], j[k][1], depth[k]) for k in ("hip", "neck", "head", "knee_l", "foot_l", "knee_r", "foot_r", "elbow_l", "hand_l", "elbow_r", "hand_r")]
        f.bodies.append({"mode": 0, "x": self.x, "y": 0.62, "size": 0.9, "joints": joints, "woman": 1.0, "yaw": 0.15 * math.sin(t * 0.4), "bank": 0.0,
                         "tint": (1.0, 0.97, 1.0), "alpha": 0.95 * fade})
        joints_d = j
        if kiss > 0.0 and u >= 0.5:
            k = min(1.0, (u - 0.5) / 0.35)                      # the kiss flies toward you: grows, drifts up, fades
            hx, hy = joints_d["hand_r"]
            kx = self.x + hx * 0.26 + 0.05 * math.sin(k * 6.0)
            ky = 0.62 + (0.95 - hy) * 0.26 * 0 - (hy - 0.5) * 0.26 * 0.5 - 0.12 * k
            f.quads.append(Quad("heart", kx, ky, 0.25 + 1.6 * k * k, 0.9 * (1.0 - k) ** 0.7, -0.15 + 0.3 * math.sin(k * 5.0), (1.0, 0.55, 0.75)))
            f.quads.append(Quad("glow", kx, ky, 0.4 + 1.5 * k, 0.5 * (1.0 - k), 0.0, (1.0, 0.6, 0.8)))
        f.caption, f.caption_alpha = self.caption, 0.3 * min(1.0, (u - 0.1) * 5, (0.9 - u) * 5)
        return f


SCENES = [ShootingStar, SpaceshipFlight, Walker]     # Kiss is out of the rotation (his call)


class Scenes:
    """The scene source for the stage: one mini-movie at a time."""

    def __init__(self, W: int = 1366, H: int = 768, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.W, self.H = W, H
        self.current = None
        self.t0 = 0.0
        self.pending = False
        self.auto = False

    @property
    def active(self) -> bool:
        return self.current is not None or self.pending

    def begin(self, t: float) -> None:
        from .clips import CLIPS, ClipScene
        real = [i for i, c in enumerate(CLIPS) if not any(tr.kind.startswith("sprite:") for tr in c.tracks)]   # no drawn pictures: bodies and light only
        if not getattr(self, "deck", None):                     # every clip once before any repeats
            self.deck = list(real); self.rng.shuffle(self.deck)
        if self.rng.random() < 0.7 and self.deck:               # mostly the little stories; sometimes a pure scene
            self.current = ClipScene(self.rng, self.W, self.H, CLIPS[self.deck.pop()])
        else:
            self.current = self.rng.choice(SCENES)(self.rng, self.W, self.H)
        self.t0 = t
        self.pending = False

    def frame(self, t: float, bass: float = 0.0) -> Frame | None:
        if self.current is None:
            return None
        u = (t - self.t0) / self.current.dur
        if u >= 1.0:
            self.current = None
            return None
        return self.current.frame(u, t, bass)
