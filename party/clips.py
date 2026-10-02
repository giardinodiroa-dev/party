"""Little stories that make sense, as data. A clip is a cast of tracks (figure, ship, sprite,
glow, streak) with keyframes, plus captions in time. ClipScene interprets it every frame:
figures walk with planted feet, ships face where they go and trail exhaust, lights blink.

Keyframes: (time_s, x, y, scale, alpha). Positions in screen uv (y down). Add clips here —
the stage draws one at a time and never repeats until the library is used up.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .rigs import STRIDE, walk_phase, walker_pose


@dataclass
class Track:
    kind: str                      # figure | ship | sprite:<actor> | glow | streak
    keys: list                     # (t, x, y, scale, alpha)
    woman: bool = False
    tint: tuple = (1.0, 1.0, 1.0)
    blink: bool = False


@dataclass
class Clip:
    name: str
    dur: float
    tracks: list
    captions: list                 # (t0, t1, text)


def K(*keys) -> list:
    return list(keys)


def _lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def sample(keys: list, t: float) -> tuple[float, float, float, float, float]:
    """x, y, scale, alpha, speed (uv/s) at time t; eased between keys, held outside."""
    if t <= keys[0][0]:
        k0 = keys[0]; return k0[1], k0[2], k0[3], k0[4] * (1.0 if t >= keys[0][0] - 0.01 else 0.0), 0.0
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            span = max(1e-4, b[0] - a[0]); k = (t - a[0]) / span; e = k * k * (3 - 2 * k)
            de = 6 * k * (1 - k) / span
            return (_lerp(a[1], b[1], e), _lerp(a[2], b[2], e), _lerp(a[3], b[3], e), _lerp(a[4], b[4], e),
                    math.hypot((b[1] - a[1]) * de, (b[2] - a[2]) * de))
    kn = keys[-1]; return kn[1], kn[2], kn[3], kn[4], 0.0


# ---------------------------------------------------------------------------------------------
# The library. x,y in uv; a figure's scale is its height as a fraction of the screen; ship scale likewise.
def _walk(x0: float, x1: float, y: float, t0: float, t1: float, h: float = 0.5, woman: bool = False, pauses: list | None = None) -> Track:
    keys = [(t0 - 0.4, x0, y, h, 0.0), (t0, x0, y, h, 1.0)]
    for (ta, tb) in (pauses or []):
        xa = x0 + (x1 - x0) * (ta - t0) / (t1 - t0)
        keys += [(ta, xa, y, h, 1.0), (tb, xa, y, h, 1.0)]
    keys += [(t1, x1, y, h, 1.0), (t1 + 0.4, x1, y, h, 0.0)]
    return Track("figure", keys, woman=woman)


def _ship(path: list, t0: float, t1: float, s: float = 0.3) -> Track:
    n = len(path) - 1
    keys = [(t0 - 0.3, path[0][0], path[0][1], s * 0.6, 0.0)]
    for i, (x, y) in enumerate(path):
        keys.append((t0 + (t1 - t0) * i / n, x, y, s, 1.0))
    keys.append((t1 + 0.3, path[-1][0], path[-1][1], s * 0.6, 0.0))
    return Track("ship", keys, blink=True)


def _sprite(actor: str, path: list, t0: float, t1: float, s: float = 1.0, tint=(0.95, 0.95, 1.0)) -> Track:
    n = max(1, len(path) - 1)
    keys = [(t0 - 0.4, path[0][0], path[0][1], s, 0.0)]
    for i, (x, y) in enumerate(path):
        keys.append((t0 + (t1 - t0) * i / n, x, y, s, 1.0))
    keys.append((t1 + 0.4, path[-1][0], path[-1][1], s, 0.0))
    return Track(f"sprite:{actor}", keys, tint=tint)


def _glow(path: list, t0: float, t1: float, s: float = 0.3, tint=(1.0, 0.85, 0.5)) -> Track:
    return Track("glow", [(t0 - 0.3, path[0][0], path[0][1], s, 0.0)] + [(t0 + (t1 - t0) * i / max(1, len(path) - 1), x, y, s, 0.9) for i, (x, y) in enumerate(path)] + [(t1 + 0.3, path[-1][0], path[-1][1], s, 0.0)], tint=tint)


def _star(x0: float, y0: float, x1: float, y1: float, t0: float, t1: float) -> Track:
    return Track("streak", [(t0, x0, y0, 1.0, 0.0), (t0 + 0.2, x0, y0, 1.0, 1.0), (t1 - 0.2, x1, y1, 1.0, 1.0), (t1, x1, y1, 1.0, 0.0)])


CLIPS: list[Clip] = [
    Clip("the pickup", 18.0,
         [_walk(0.1, 0.45, 0.68, 0.5, 8.0, pauses=[(8.0, 13.0)]) if False else _walk(0.1, 0.45, 0.68, 0.5, 7.0),
          Track("figure", [(7.0, 0.45, 0.68, 0.5, 1.0), (12.0, 0.45, 0.68, 0.5, 1.0), (14.0, 0.5, 0.6, 0.45, 0.0)]),
          _ship([(1.2, 0.2), (0.75, 0.35), (0.55, 0.56), (0.55, 0.56), (0.8, 0.3), (1.2, 0.1)], 4.0, 16.0, 0.3)],
         [(0.5, 6.0, "a man walks out to the edge of nothing and waits"), (7.0, 11.0, "a ship comes down for him, lights on"),
          (12.0, 17.0, "he is aboard; they rise together into the dark")]),
    Clip("two ships, one hello", 14.0,
         [_ship([(-0.2, 0.3), (0.45, 0.42), (1.2, 0.3)], 1.0, 12.0, 0.26), _ship([(1.2, 0.62), (0.55, 0.5), (-0.2, 0.62)], 2.0, 13.0, 0.22)],
         [(1.0, 5.0, "two ships on opposite runs"), (5.5, 9.0, "they flash their lights as they pass: hello, stranger"), (9.5, 13.0, "and keep going, both a little less alone")]),
    Clip("the gas stop", 20.0,
         [_sprite("gaspump", [(0.3, 0.62), (0.3, 0.62)], 0.0, 20.0, 1.3), _ship([(1.2, 0.3), (0.42, 0.5), (0.42, 0.5), (0.42, 0.5), (-0.2, 0.4)], 1.0, 19.0, 0.28),
          _glow([(0.36, 0.56), (0.36, 0.56)], 8.0, 13.0, 0.18, (0.6, 0.9, 1.0))],
         [(1.0, 6.0, "a ship pulls in to the last gas station before the edge"), (7.0, 13.0, "fuel runs; the pilot stretches, looks at the stars"), (14.0, 19.0, "paid with a pebble, and gone")]),
    Clip("a walk under a falling star", 16.0,
         [_walk(0.05, 0.9, 0.7, 0.5, 15.0, pauses=[(6.0, 10.0)]), _star(0.55, 0.05, 0.95, 0.4, 7.0, 9.5)],
         [(0.5, 5.5, "a walk through the dark, unhurried"), (6.5, 10.0, "he stops: a star falls; he makes the wish"), (10.5, 15.0, "and walks on, lighter")]),
    Clip("the satellite tumbles", 16.0,
         [_ship([(-0.2, 0.25), (0.35, 0.45), (0.6, 0.5), (1.2, 0.35)], 0.5, 15.5, 0.22)],
         [(0.5, 5.0, "an old satellite, tumbling, lost its lock"), (6.0, 10.0, "a nudge of its last fuel… it steadies"), (11.0, 15.0, "pointed home again, blinking thanks")]),
    Clip("the cat and the comet", 14.0,
         [_sprite("comet", [(-0.1, 0.2), (1.1, 0.5)], 0.5, 10.0, 1.1), _sprite("cat", [(-0.15, 0.3), (1.05, 0.6)], 1.5, 12.0, 1.0)],
         [(0.5, 5.0, "a comet passes, minding its orbit"), (5.5, 9.5, "a cat is after it, of course"), (10.0, 13.5, "the cat wins; it always wins")]),
    Clip("the astronaut's tether", 18.0,
         [_sprite("astronaut", [(0.3, 0.55), (0.42, 0.5), (0.5, 0.52)], 0.5, 12.0, 1.0),
          _ship([(-0.2, 0.2), (0.3, 0.38), (0.5, 0.5), (0.5, 0.5), (1.2, 0.3)], 6.0, 17.0, 0.28)],
         [(0.5, 5.0, "an astronaut drifts, tether cut, calm"), (6.0, 11.0, "a ship finds him: nobody is left out here"), (12.0, 17.0, "back aboard; the hatch closes; warmth")]),
    Clip("the owl and the moon", 18.0,
         [_sprite("moon", [(0.75, 1.1), (0.75, 0.3), (0.75, 0.3)], 0.0, 17.0, 1.4, (1.0, 0.95, 0.8)), _sprite("owl", [(-0.1, 0.4), (0.68, 0.46), (0.68, 0.46)], 6.0, 17.0, 0.9)],
         [(0.5, 6.0, "the moon rises over nothing in particular"), (7.0, 12.0, "an owl flies in and takes its place on the crescent"), (13.0, 17.0, "they keep each other company till the song ends")]),
    Clip("whale in the nebula", 16.0,
         [_sprite("whale", [(1.15, 0.55), (0.5, 0.45), (-0.15, 0.6)], 0.5, 15.5, 1.5, (0.8, 0.9, 1.0)), _glow([(1.0, 0.5), (0.5, 0.4), (0.0, 0.55)], 0.5, 15.5, 0.5, (0.7, 0.5, 1.0))],
         [(0.5, 6.0, "a whale swims the nebula, slow as weather"), (6.5, 11.0, "it sings one low note; the dust lights up"), (11.5, 15.5, "and it is gone, the way whales go")]),
    Clip("dragon and rocket", 14.0,
         [_ship([(-0.2, 0.6), (0.4, 0.45), (1.2, 0.2)], 0.5, 12.0, 0.26), _sprite("dragon", [(-0.3, 0.75), (0.3, 0.6), (1.1, 0.35)], 1.5, 13.0, 1.4, (0.8, 1.0, 0.85))],
         [(0.5, 5.0, "a rocket runs for it"), (5.5, 9.5, "a dragon on its tail, laughing smoke"), (10.0, 13.5, "it was never a chase; it was a race, and they both won")]),
    Clip("the crown finds a fish", 16.0,
         [_sprite("fish", [(-0.1, 0.6), (0.45, 0.55), (0.45, 0.55), (1.1, 0.5)], 0.5, 15.5, 1.0, (1.0, 0.9, 0.6)),
          _sprite("crown", [(0.45, -0.1), (0.45, 0.47), (0.45, 0.47), (1.1, 0.42)], 4.0, 15.5, 0.7, (1.0, 0.85, 0.4))],
         [(0.5, 4.0, "a goldfish, swimming through space, minding its business"), (5.0, 9.0, "a crown drifts down and lands on its head"), (10.0, 15.0, "the king of the small swims on, trying to look casual")]),
    Clip("meteor shower, a man watching", 18.0,
         [_walk(0.15, 0.3, 0.72, 0.5, 4.0), Track("figure", [(4.0, 0.3, 0.72, 0.5, 1.0), (17.0, 0.3, 0.72, 0.5, 1.0), (18.0, 0.3, 0.72, 0.5, 0.0)]),
          _star(0.4, 0.0, 0.8, 0.35, 5.0, 7.0), _star(0.6, 0.05, 0.95, 0.3, 7.5, 9.5), _star(0.2, 0.0, 0.6, 0.4, 9.0, 11.5), _star(0.7, 0.02, 1.0, 0.25, 12.0, 14.0)],
         [(0.5, 4.5, "he comes out to see it"), (5.0, 12.0, "a shower: one, two, three, four wishes"), (13.0, 17.5, "he keeps the last wish for someone else")]),
    Clip("the lighthouse keeper", 16.0,
         [_sprite("lighthouse", [(0.7, 0.6), (0.7, 0.6)], 0.0, 16.0, 1.5), _glow([(0.75, 0.42), (0.75, 0.42)], 2.0, 14.0, 0.35, (1.0, 0.9, 0.6)),
          _ship([(-0.2, 0.75), (0.3, 0.6), (0.5, 0.55), (0.55, 0.52), (-0.2, 0.4)], 3.0, 15.0, 0.22)],
         [(0.5, 5.0, "a lighthouse in the dark, still sweeping for lost ships"), (6.0, 11.0, "a small ship follows the beam in, found"), (12.0, 15.5, "the keeper waves; the beam keeps turning")]),
    Clip("earthrise", 16.0,
         [_sprite("earth", [(0.5, 1.15), (0.5, 0.45)], 0.5, 15.0, 1.6, (0.9, 0.95, 1.0)), _sprite("satellite", [(-0.15, 0.3), (1.15, 0.25)], 3.0, 14.0, 0.7)],
         [(0.5, 6.0, "the earth comes up, blue, everyone you love on it"), (7.0, 11.0, "a satellite crosses, doing its small quiet job"), (12.0, 15.5, "you are on that; you are doing fine")]),
    Clip("phoenix from the bass", 14.0,
         [_glow([(0.5, 0.75), (0.5, 0.75)], 0.5, 6.0, 0.6, (1.0, 0.5, 0.2)), _sprite("phoenix", [(0.5, 0.78), (0.5, 0.45), (0.5, 0.42), (0.5, -0.2)], 4.0, 13.5, 1.5, (1.0, 0.75, 0.4))],
         [(0.5, 4.0, "embers, from the worst day"), (4.5, 9.0, "a phoenix rises out of them, on the beat"), (9.5, 13.5, "and goes up, to be born again somewhere")]),
    Clip("the long walk home", 20.0,
         [_walk(-0.05, 1.05, 0.7, 0.5, 19.5, pauses=[(9.0, 11.5)])],
         [(0.5, 6.0, "a long walk home across the void"), (7.0, 12.0, "halfway, he stops to look back: a long way, and done"), (13.0, 19.5, "the rest is downhill, he decides")]),
    Clip("unicorn over the moon", 14.0,
         [_sprite("moon", [(0.5, 0.55), (0.5, 0.55)], 0.0, 14.0, 1.3, (1.0, 0.95, 0.8)), _sprite("unicorn", [(-0.15, 0.7), (0.35, 0.5), (0.5, 0.25), (0.7, 0.5), (1.15, 0.7)], 1.0, 13.0, 1.1, (1.0, 0.95, 1.0))],
         [(0.5, 4.5, "a unicorn gallops in, hooves sparking"), (5.0, 9.0, "over the moon, classic"), (9.5, 13.5, "and off into the dark, glitter trailing")]),
    Clip("the galaxy turns", 18.0,
         [_sprite("galaxy", [(0.5, 0.45), (0.5, 0.45)], 0.5, 17.5, 1.8, (0.85, 0.9, 1.0)), _ship([(-0.2, 0.7), (0.5, 0.75), (1.2, 0.7)], 5.0, 16.0, 0.16)],
         [(0.5, 6.0, "a galaxy, wheeling, slower than anything"), (7.0, 12.0, "a tiny ship crosses under it, carrying someone's whole life"), (13.0, 17.5, "the galaxy does not notice; the ship does not mind")]),
    Clip("butterfly and black hole", 14.0,
         [_glow([(0.5, 0.5), (0.5, 0.5)], 0.5, 13.5, 0.4, (0.3, 0.2, 0.5)), _sprite("butterfly", [(-0.1, 0.4), (0.45, 0.48), (0.5, 0.5), (0.55, 0.52), (1.1, 0.6)], 1.0, 13.0, 0.9, (0.9, 0.8, 1.0))],
         [(0.5, 5.0, "a butterfly flies toward the dark thing"), (5.5, 9.5, "lands on it; nothing happens; it was only dark"), (10.0, 13.5, "and goes on, unafraid")]),
    Clip("sun up", 16.0,
         [_sprite("sun", [(0.5, 1.2), (0.5, 0.5)], 0.5, 15.0, 1.5, (1.0, 0.9, 0.6)), _glow([(0.5, 1.2), (0.5, 0.5)], 0.5, 15.0, 1.6, (1.0, 0.8, 0.4))],
         [(0.5, 6.0, "the sun comes up over nothing in particular"), (7.0, 12.0, "warm anyway"), (12.5, 15.5, "a coin of light on your desk; keep it")]),
]


class ClipScene:
    name = "clip"

    def __init__(self, rng: random.Random, W: int, H: int, clip: Clip | None = None) -> None:
        self.rng, self.W, self.H = rng, W, H
        self.clip = clip or rng.choice(CLIPS)
        self.dur = self.clip.dur
        self.dist: dict[int, float] = {}
        self.last: dict[int, tuple[float, float]] = {}
        self.exhaust: dict[int, list] = {}

    def frame(self, u: float, t: float, bass: float):
        from .scenes import Frame, Quad
        f = Frame()
        T = u * self.dur
        for i, tr in enumerate(self.clip.tracks):
            x, y, sc, a, speed = sample(tr.keys, T)
            if a <= 0.001:
                continue
            if tr.kind == "figure":
                px, py = self.last.get(i, (x, y))
                dx = x - px
                self.last[i] = (x, y)
                screen_h = sc * self.H; rig_px = screen_h / 1.0
                self.dist[i] = self.dist.get(i, 0.0) + abs(dx) * self.W / rig_px
                facing = self.dist.get(("f", i), 1.0)
                if abs(dx) > 1e-5:
                    facing = 1.0 if dx > 0 else -1.0; self.dist[("f", i)] = facing
                sp = min(1.0, speed * self.W / rig_px / 1.2)
                j = walker_pose(walk_phase(self.dist[i]), sp, facing)
                joints = [(j[k][0], j[k][1], z) for k, z in (("hip", 0.0), ("neck", 0.0), ("head", 0.0), ("knee_l", 0.07), ("foot_l", 0.07),
                                                            ("knee_r", -0.07), ("foot_r", -0.07), ("elbow_l", 0.1), ("hand_l", 0.1), ("elbow_r", -0.1), ("hand_r", -0.1))]
                f.bodies.append({"mode": 0, "x": x, "y": y, "size": sc * 1.25, "joints": joints, "woman": 1.0 if tr.woman else 0.0,
                                 "yaw": 0.5 * facing, "bank": 0.0, "tint": tr.tint, "alpha": 0.95 * a})
            elif tr.kind == "ship":
                px, py = self.last.get(i, (x - 0.001, y))
                heading = math.atan2((y - py) * self.H, (x - px) * self.W) if (x, y) != (px, py) else self.dist.get(("h", i), 0.0)
                self.dist[("h", i)] = heading; self.last[i] = (x, y)
                ex = self.exhaust.setdefault(i, [])
                if speed > 0.01:
                    bx, by = x - math.cos(heading) * 0.05 * sc / 0.3, y - math.sin(heading) * 0.05 * sc / 0.3 * self.W / self.H
                    ex.append([bx, by, -math.cos(heading) * 0.06, -math.sin(heading) * 0.06, 1.0])
                    f.quads.append(Quad("glow", bx, by, 0.25 * sc / 0.3 * (0.8 + 0.4 * bass), 0.9 * a, 0.0, (1.0, 0.75, 0.35)))
                for e in ex:
                    e[0] += e[2] * 0.016; e[1] += e[3] * 0.016; e[4] -= 0.025
                    if e[4] > 0:
                        f.quads.append(Quad("glow", e[0], e[1], 0.22 * sc / 0.3 * (1.4 - e[4]), 0.5 * e[4] * a, 0.0, (0.6, 0.85, 1.0)))
                self.exhaust[i] = [e for e in ex if e[4] > 0][-50:]
                f.bodies.append({"mode": 1, "x": x, "y": y, "size": sc * 1.2, "joints": None, "woman": 0.0, "yaw": 0.0,
                                 "bank": -heading, "tint": tr.tint, "alpha": 0.95 * a, "engine": min(1.0, speed * 6.0) + 0.3 * bass})
                if tr.blink and (t % 1.0) < 0.12:
                    f.quads.append(Quad("spark", x, y - 0.03 * sc / 0.3, 0.05 * sc / 0.3, 0.9 * a, 0.0, (1.0, 0.3, 0.3)))
            elif tr.kind.startswith("sprite:"):
                px, py = self.last.get(i, (x, y)); self.last[i] = (x, y)
                ang = math.atan2((y - py) * self.H, (x - px) * self.W) if math.hypot(x - px, y - py) > 1e-4 else 0.0
                f.quads.append(Quad(tr.kind[7:], x, y, sc, 0.9 * a, 0.25 * ang if abs(ang) < 1.2 else 0.0, tr.tint))
            elif tr.kind == "glow":
                f.quads.append(Quad("glow", x, y, sc * (1.0 + 0.3 * bass), 0.8 * a, 0.0, tr.tint))
            elif tr.kind == "streak":
                k0, k1 = tr.keys[0], tr.keys[-1]
                dx, dy = (k1[1] - k0[1]) * self.W, (k1[2] - k0[2]) * self.H; n = math.hypot(dx, dy) or 1.0
                f.streak = (x, y, dx / n, dy / n, 260.0, a * (0.8 + 0.3 * bass))
        for t0, t1, text in self.clip.captions:
            if t0 <= T <= t1:
                k = min(1.0, (T - t0) * 2.0, (t1 - T) * 2.0)
                f.caption, f.caption_alpha = text, 0.32 * k
        return f
