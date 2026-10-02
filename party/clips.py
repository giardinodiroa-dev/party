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


BODY_MODES = {"saucer": 2, "fish": 3, "gem": 4, "sat": 5, "pump": 6}


def _body(kind: str, path: list, t0: float, t1: float, s: float = 0.3, fade: float = 0.3) -> Track:
    """A raymarched body (saucer, goldfish, gem, satellite, pump) along a path, eased, faded in and out."""
    n = max(1, len(path) - 1)
    keys = [(t0 - fade, path[0][0], path[0][1], s, 0.0)]
    for i, (x, y) in enumerate(path):
        keys.append((t0 + (t1 - t0) * i / n, x, y, s, 1.0))
    keys.append((t1 + fade, path[-1][0], path[-1][1], s, 0.0))
    return Track(kind, keys)


def _cheer(x: float, y: float, t0: float, t1: float, h: float = 0.32, tint=(1.0, 1.0, 1.0)) -> Track:
    return Track("cheer", [(t0 - 0.4, x, y, h, 0.0), (t0, x, y, h, 1.0), (t1, x, y, h, 1.0), (t1 + 0.4, x, y, h, 0.0)], tint=tint)


def cheer_pose(phase: float, lift: float, facing: float = 1.0) -> dict:
    """Standing, both arms up, bouncing on the beat: lift 0..1 raises the whole body and straightens the arms."""
    j = dict(walker_pose(0.0, 0.0, facing))
    neck = j["neck"]; up = 0.06 * lift
    j = {k: (v[0], v[1] + up) for k, v in j.items()}
    sway = 0.03 * math.sin(phase)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        j[f"elbow_{side}"] = (neck[0] + sx * 0.17 + sway, neck[1] + up + 0.1 + 0.05 * lift)
        j[f"hand_{side}"] = (neck[0] + sx * (0.2 - 0.06 * lift) + sway * 1.5, neck[1] + up + 0.3 + 0.08 * lift)
    return j


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
    Clip("the landing party", 22.0,
         [_ship([(1.2, 0.15), (0.75, 0.3), (0.6, 0.55), (0.6, 0.55), (0.6, 0.55), (0.6, 0.55)], 0.5, 21.5, 0.3),
          _walk(0.62, 0.15, 0.7, 7.0, 16.0), _walk(0.6, 0.95, 0.72, 9.0, 18.0)],
         [(0.5, 6.0, "a ship sets down on the dark, engines cooling"), (7.0, 13.0, "two walk out, one each way: a mission with two halves"),
          (14.0, 21.5, "they will meet again here; the ship keeps the light on")]),
    Clip("the guardian", 18.0,
         [_walk(-0.05, 1.05, 0.72, 0.5, 17.5), _ship([(-0.1, 0.35), (0.3, 0.3), (0.6, 0.33), (1.1, 0.3)], 1.0, 17.0, 0.2)],
         [(0.5, 6.0, "a man walks; a ship follows above him, matching his pace"), (7.0, 12.0, "it never lands, never leaves: a guardian"),
          (13.0, 17.5, "he never looks up; he knows")]),
    Clip("convoy", 16.0,
         [_ship([(-0.2, 0.3), (1.2, 0.4)], 0.5, 13.0, 0.24), _ship([(-0.3, 0.45), (1.1, 0.55)], 1.5, 14.0, 0.24), _ship([(-0.4, 0.6), (1.0, 0.7)], 2.5, 15.0, 0.24)],
         [(0.5, 5.0, "three ships in convoy, lights in step"), (5.5, 10.0, "nobody says anything on the radio; nobody needs to"), (10.5, 15.5, "somewhere ahead, a port")]),
    Clip("the chase", 14.0,
         [_star(0.1, 0.1, 0.9, 0.45, 2.0, 6.0), _ship([(-0.2, 0.25), (0.5, 0.4), (1.2, 0.55)], 1.0, 9.0, 0.26)],
         [(0.5, 4.0, "a shooting star, and a ship that wants to catch it"), (4.5, 8.5, "it never will; it tries anyway"), (9.0, 13.5, "that is most of what ships are for")]),
    Clip("the meeting", 20.0,
         [_walk(-0.05, 0.42, 0.72, 0.5, 8.0), Track("figure", [(8.0, 0.42, 0.72, 0.5, 1.0), (19.0, 0.42, 0.72, 0.5, 1.0), (20.0, 0.42, 0.72, 0.5, 0.0)]),
          _walk(1.05, 0.58, 0.72, 1.0, 8.5), Track("figure", [(8.5, 0.58, 0.72, 0.5, 1.0), (19.0, 0.58, 0.72, 0.5, 1.0), (20.0, 0.58, 0.72, 0.5, 0.0)]),
          _glow([(0.5, 0.52), (0.5, 0.52)], 9.0, 18.0, 0.25, (1.0, 0.9, 0.6))],
         [(0.5, 7.0, "two people walk toward each other across the dark"), (8.0, 13.0, "they stop; a light between them; something is said"), (14.0, 19.5, "it was enough; it usually is")]),
    Clip("refuel in flight", 18.0,
         [_ship([(-0.2, 0.4), (0.45, 0.45), (0.45, 0.45), (0.45, 0.45), (1.2, 0.4)], 0.5, 17.5, 0.3), _ship([(1.2, 0.25), (0.55, 0.36), (0.55, 0.36), (0.55, 0.36), (-0.2, 0.25)], 2.0, 17.0, 0.2),
          _glow([(0.5, 0.41), (0.5, 0.41)], 7.0, 12.0, 0.2, (0.6, 0.9, 1.0))],
         [(0.5, 6.0, "a tanker meets a ship halfway"), (7.0, 12.0, "fuel passes between them in a thread of light"), (13.0, 17.5, "and they part, each with what it needed")]),
    Clip("the long watch", 20.0,
         [_walk(0.2, 0.5, 0.72, 0.5, 6.0), Track("figure", [(6.0, 0.5, 0.72, 0.5, 1.0), (19.0, 0.5, 0.72, 0.5, 1.0), (20.0, 0.5, 0.72, 0.5, 0.0)]),
          _star(0.1, 0.05, 0.5, 0.3, 8.0, 10.5), _star(0.9, 0.05, 0.5, 0.35, 12.0, 14.5), _ship([(-0.2, 0.2), (1.2, 0.15)], 15.0, 19.5, 0.14)],
         [(0.5, 6.0, "he walks to the middle and stands watch"), (7.0, 14.0, "stars fall left and right; he counts them for someone"), (15.0, 19.5, "a ship crosses far away; the watch is over")]),
    Clip("emergency landing", 16.0,
         [_ship([(-0.2, 0.1), (0.3, 0.4), (0.55, 0.62), (0.55, 0.62), (0.55, 0.62)], 0.5, 15.5, 0.3),
          _glow([(0.3, 0.4), (0.55, 0.62)], 1.0, 6.0, 0.5, (1.0, 0.5, 0.2)), _walk(0.58, 0.9, 0.72, 8.0, 15.0)],
         [(0.5, 5.0, "a ship comes in hot, trailing fire"), (5.5, 9.0, "down; still; the fire goes out"), (9.5, 15.5, "the pilot climbs out and walks it off, alive")]),
    Clip("the orbit", 16.0,
         [_ship([(0.5, 0.2), (0.8, 0.35), (0.65, 0.65), (0.3, 0.6), (0.2, 0.35), (0.5, 0.2), (0.8, 0.35)], 0.5, 15.5, 0.24), _glow([(0.5, 0.42), (0.5, 0.42)], 0.5, 15.5, 0.4, (0.5, 0.4, 1.0))],
         [(0.5, 5.0, "a ship in orbit around something it will not name"), (5.5, 10.0, "round, and round, and round"), (10.5, 15.5, "it could leave; it stays; that is love or fuel")]),
    Clip("walking home together", 18.0,
         [_walk(-0.05, 1.05, 0.72, 0.5, 17.5), _walk(-0.12, 0.98, 0.74, 0.5, 17.5), _ship([(0.5, -0.1), (0.5, 0.15)], 0.5, 6.0, 0.14)],
         [(0.5, 6.0, "two walk home together, step for step"), (7.0, 12.0, "a small ship keeps watch over the pair"), (13.0, 17.5, "nobody is alone out here tonight")]),
    Clip("sun up", 16.0,
         [_sprite("sun", [(0.5, 1.2), (0.5, 0.5)], 0.5, 15.0, 1.5, (1.0, 0.9, 0.6)), _glow([(0.5, 1.2), (0.5, 0.5)], 0.5, 15.0, 1.6, (1.0, 0.8, 0.4))],
         [(0.5, 6.0, "the sun comes up over nothing in particular"), (7.0, 12.0, "warm anyway"), (12.5, 15.5, "a coin of light on your desk; keep it")]),
]

# ---------------------------------------------------------------------------------------------
# The raymarched cast (the look he picked: every body is a lit 3D hull, one of six finishes per story)
ALIEN = (0.55, 1.0, 0.62)
CLIPS += [
    Clip("the saucer", 13.0,
         [_body("saucer", [(-0.2, 0.22), (0.3, 0.3), (0.52, 0.42), (0.52, 0.42), (0.8, 0.34), (1.25, 0.2)], 0.8, 12.0, 0.34)],
         [(0.5, 5.0, "a saucer slides in, low and quiet"), (6.0, 9.0, "it stops. it looks at you. you look at it"), (10.0, 12.5, "and it is gone, the way they are")]),
    Clip("hover and beam", 17.0,
         [_body("saucer", [(0.5, -0.15), (0.5, 0.36), (0.5, 0.36), (0.5, 0.36), (0.5, -0.2)], 1.0, 15.5, 0.38),
          _glow([(0.5, 0.52), (0.5, 0.56), (0.5, 0.52)], 5.5, 11.5, 0.5, tint=(0.5, 0.95, 1.0)),
          _glow([(0.5, 0.66), (0.5, 0.7), (0.5, 0.66)], 6.0, 11.0, 0.9, tint=(0.4, 0.9, 1.0))],
         [(1.0, 5.0, "it comes down over the house"), (6.0, 11.0, "the beam is warm. it is only looking"), (12.0, 16.0, "it has seen enough; it goes back up")]),
    Clip("the last gas station", 21.0,
         [_body("pump", [(0.64, 0.6), (0.64, 0.6)], 0.5, 20.5, 0.34, fade=0.6),
          _glow([(0.64, 0.47), (0.64, 0.47)], 0.5, 20.5, 0.22, tint=(1.0, 0.85, 0.5)),
          _body("saucer", [(-0.2, 0.2), (0.3, 0.4), (0.4, 0.56), (0.4, 0.56), (0.4, 0.56), (0.4, 0.56), (0.7, 0.3), (1.25, 0.1)], 0.8, 20.0, 0.3),
          Track("figure", [(5.5, 0.44, 0.7, 0.3, 0.0), (6.0, 0.44, 0.7, 0.3, 1.0), (8.0, 0.57, 0.7, 0.3, 1.0), (13.0, 0.57, 0.7, 0.3, 1.0), (15.0, 0.44, 0.7, 0.3, 1.0), (15.5, 0.44, 0.7, 0.3, 0.0)], tint=ALIEN)],
         [(1.0, 5.0, "the last pump before the edge of everything"), (6.0, 13.0, "the pilot gets out, stretches, fills up, looks at the stars"), (14.0, 20.0, "paid with a pebble from a planet you have never heard of")]),
    Clip("goldfish in the void", 15.0,
         [_body("fish", [(-0.15, 0.5), (0.2, 0.42), (0.45, 0.52), (0.7, 0.44), (1.2, 0.5)], 0.8, 14.0, 0.3),
          _glow([(0.3, 0.38), (0.3, 0.3)], 4.0, 7.0, 0.08, tint=(0.7, 0.9, 1.0)), _glow([(0.6, 0.4), (0.6, 0.31)], 8.0, 11.0, 0.08, tint=(0.7, 0.9, 1.0))],
         [(0.5, 5.0, "a goldfish, swimming through space, minding its business"), (6.0, 10.0, "it does not know it is impossible"), (11.0, 14.5, "so it keeps going")]),
    Clip("the king of the small", 16.0,
         [_body("fish", [(-0.15, 0.55), (0.5, 0.52), (0.5, 0.52), (0.5, 0.52), (1.2, 0.5)], 0.8, 15.0, 0.32),
          _body("gem", [(0.5, -0.1), (0.5, 0.34), (0.5, 0.34), (0.5, 0.34)], 4.0, 12.5, 0.12, fade=0.5),
          _glow([(0.5, 0.34), (0.5, 0.34)], 8.0, 12.0, 0.4, tint=(1.0, 0.85, 0.6))],
         [(0.5, 4.0, "a goldfish, swimming through space, minding its business"), (5.0, 9.0, "a jewel drifts down and settles over its head"), (10.0, 15.0, "the king of the small swims on, trying to look casual")]),
    Clip("the blessing", 13.0,
         [_body("gem", [(0.5, -0.1), (0.5, 0.42), (0.5, 0.42), (0.5, 0.42), (0.5, 0.38), (0.5, -0.15)], 0.8, 12.0, 0.3, fade=0.5),
          _glow([(0.5, 0.42), (0.5, 0.42)], 4.5, 9.5, 1.0, tint=(1.0, 0.8, 0.95)),
          _glow([(0.5, 0.42), (0.5, 0.42)], 5.0, 9.0, 0.5, tint=(1.0, 1.0, 1.0))],
         [(0.5, 4.0, "something is being lowered to you"), (5.0, 9.0, "take it. it was always yours"), (10.0, 12.5, "it rises again, lighter, the way gifts do")]),
    Clip("the satellite", 19.0,
         [_body("sat", [(1.15, 0.2), (0.75, 0.3), (0.5, 0.42), (0.3, 0.52), (-0.2, 0.7)], 0.8, 18.0, 0.42),
          Track("sat", [(0.5, 1.15, 0.2, 0.08, 0.0), (0.8, 1.15, 0.2, 0.08, 0.0)])],
         [(1.0, 6.0, "something man-made, far out, still working"), (7.0, 12.0, "it passes close enough to see the panels catch the sun"), (13.0, 18.0, "and swings away on its long loop; it will be back")]),
    Clip("the crowd", 15.0,
         [_cheer(0.14 + 0.12 * k, 0.74 - 0.01 * (k % 2), 0.6 + 0.15 * k, 13.5, 0.3 + 0.02 * (k % 3), tint=(0.95, 0.92, 1.0)) for k in range(7)],
         [(1.0, 6.0, "they heard you were coming"), (7.0, 11.0, "all of them, for you, on the beat"), (12.0, 14.5, "you did not have to do anything; you just had to show up")]),
    Clip("formation", 13.0,
         [_body("saucer", [(-0.2, 0.3), (0.5, 0.36), (1.25, 0.3)], 0.8, 12.0, 0.26),
          _body("saucer", [(-0.35, 0.44), (0.38, 0.5), (1.1, 0.44)], 0.8, 12.0, 0.22),
          _body("saucer", [(-0.35, 0.18), (0.38, 0.24), (1.1, 0.18)], 0.8, 12.0, 0.22)],
         [(0.5, 5.0, "three of them, in no hurry"), (6.0, 12.0, "they fly like they have somewhere better to be, and are going there together")]),
    Clip("the pickup, saucer edition", 19.0,
         [Track("figure", [(0.1, 0.5, 0.7, 0.42, 0.0), (0.6, 0.5, 0.7, 0.42, 1.0), (12.0, 0.5, 0.7, 0.42, 1.0), (14.0, 0.5, 0.5, 0.36, 0.0)]),
          _body("saucer", [(1.2, 0.1), (0.7, 0.25), (0.5, 0.34), (0.5, 0.34), (0.5, 0.34), (0.5, 0.34), (0.5, -0.25)], 3.0, 17.5, 0.36),
          _glow([(0.5, 0.56), (0.5, 0.6), (0.5, 0.56)], 8.5, 13.5, 0.8, tint=(0.5, 0.95, 1.0))],
         [(0.5, 6.0, "a man stands at the edge of nothing and waits"), (7.0, 12.0, "it comes down for him, lights on, and the beam finds him"), (13.0, 18.0, "he is aboard; they rise together into the dark")]),
]


class ClipScene:
    name = "clip"

    def __init__(self, rng: random.Random, W: int, H: int, clip: Clip | None = None) -> None:
        self.rng, self.W, self.H = rng, W, H
        self.clip = clip or rng.choice(CLIPS)
        self.dur = self.clip.dur
        self.look = rng.randrange(6)                      # chrome · holo · toon · pearl · neon · ghost — one per story
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
            elif tr.kind in BODY_MODES:
                px, py = self.last.get(i, (x - 0.001, y)); dx = x - px
                heading = math.atan2((y - py) * self.H, (x - px) * self.W) if (x, y) != (px, py) else self.dist.get(("h", i), 0.0)
                self.dist[("h", i)] = heading; self.last[i] = (x, y)
                moving = min(1.0, speed * 5.0)
                yaw, bank, engine = 0.0, 0.0, 0.3 + 0.7 * bass
                if tr.kind == "saucer":
                    yaw, bank = t * 0.7, -0.45 * math.sin(heading) * moving - 0.12 * math.cos(heading) * moving
                elif tr.kind == "fish":
                    facing = self.dist.get(("f", i), 1.0)
                    if abs(dx) > 1e-5:
                        facing = 1.0 if dx > 0 else -1.0; self.dist[("f", i)] = facing
                    yaw = 0.0 if facing > 0 else math.pi
                    bank = (-heading if facing > 0 else -(heading - math.copysign(math.pi, heading))) * moving
                elif tr.kind == "gem":
                    bank = 0.25 * math.sin(t * 1.3)
                elif tr.kind == "sat":
                    yaw, bank = t * 0.35, 0.35 + 0.1 * math.sin(t * 0.5)
                elif tr.kind == "pump":
                    yaw = 0.35
                f.bodies.append({"mode": BODY_MODES[tr.kind], "x": x, "y": y, "size": sc * 1.2, "joints": None, "woman": 0.0,
                                 "yaw": yaw, "bank": bank, "tint": tr.tint, "alpha": 0.95 * a, "engine": engine})
            elif tr.kind == "cheer":
                j = cheer_pose(t * 2.0 + i, min(1.0, bass * 1.4), 1.0)
                joints = [(j[k][0], j[k][1], z) for k, z in (("hip", 0.0), ("neck", 0.0), ("head", 0.0), ("knee_l", 0.07), ("foot_l", 0.07),
                                                            ("knee_r", -0.07), ("foot_r", -0.07), ("elbow_l", 0.1), ("hand_l", 0.1), ("elbow_r", -0.1), ("hand_r", -0.1))]
                f.bodies.append({"mode": 0, "x": x, "y": y, "size": sc * 1.25, "joints": joints, "woman": 0.0,
                                 "yaw": 0.15 * math.sin(i * 1.7), "bank": 0.0, "tint": tr.tint, "alpha": 0.95 * a})
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
        for b in f.bodies:
            b.setdefault("look", self.look)
        for t0, t1, text in self.clip.captions:
            if t0 <= T <= t1:
                k = min(1.0, (T - t0) * 2.0, (t1 - T) * 2.0)
                f.caption, f.caption_alpha = text, 0.32 * k
        return f
