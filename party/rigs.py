"""Characters animated from code: a skeleton, a walk cycle, a kiss.

No frames on disk. Each tick the rig's joints are solved from time, and the figure is
drawn as thick luminous strokes with volume (astral style) into a small image that the
window uploads as a texture. Pure geometry here; drawing is in rigs_draw (Qt).
"""
from __future__ import annotations

import math
import random

Point = tuple[float, float]


STRIDE = 0.26          # foot amplitude in rig units; a full cycle covers 2*STRIDE*? of ground — see walk_phase
THIGH, SHIN, UPPER, FORE = 0.26, 0.26, 0.19, 0.18


def walk_phase(distance: float) -> float:
    """Phase from ground covered: one full cycle moves the body 4*STRIDE (each foot: a 2*STRIDE
    stance slide, then a swing while the other foot carries). The planted foot stays put."""
    return distance / (4.0 * STRIDE) * math.tau


def _ik_leg(hip: Point, foot: Point, forward: float) -> Point:
    """Knee from hip and foot (two-bone IK), the knee bending forward."""
    dx, dy = foot[0] - hip[0], foot[1] - hip[1]
    d = max(1e-4, min(THIGH + SHIN - 1e-3, math.hypot(dx, dy)))
    a = math.acos(max(-1.0, min(1.0, (THIGH * THIGH + d * d - SHIN * SHIN) / (2 * THIGH * d))))
    base = math.atan2(dy, dx)
    ang = base + a * forward
    return (hip[0] + THIGH * math.cos(ang), hip[1] + THIGH * math.sin(ang))


def walker_pose(phase: float, speed: float = 1.0, facing: float = 1.0) -> dict[str, Point]:
    """A walking figure with real ground contact: unit height ~1, faces +x (mirror with facing=-1).
    phase from walk_phase(distance); speed 0 = standing still (breathing)."""
    sp = max(0.0, min(1.0, speed))
    hip = (0.0, 0.50 - 0.02 * sp + 0.012 * sp * abs(math.cos(phase)))        # lowest at mid-stance crossover
    lean = 0.03 * sp
    neck = (hip[0] + lean + 0.01, hip[1] + 0.30)
    head = (neck[0] + 0.01, neck[1] + 0.085)
    def foot(offset: float) -> Point:
        ph = (phase + offset) % math.tau
        if ph < math.pi:                                   # stance: a straight slide back under the body = planted
            x = STRIDE * sp * (1.0 - 2.0 * ph / math.pi); lift = 0.0
        else:                                              # swing: eased forward, lifting in an arc
            k = (ph - math.pi) / math.pi; e = k * k * (3 - 2 * k)
            x = STRIDE * sp * (-1.0 + 2.0 * e); lift = math.sin(k * math.pi) * 0.09 * sp
        return (hip[0] + x, 0.02 + lift)
    fl, fr = foot(0.0), foot(math.pi)
    kl, kr = _ik_leg(hip, fl, 1.0), _ik_leg(hip, fr, 1.0)
    def arm(offset: float) -> tuple[Point, Point]:
        a = 0.5 * sp * math.cos(phase + offset)            # arms swing opposite the legs
        elbow = (neck[0] + UPPER * math.sin(a), neck[1] - UPPER * math.cos(a))
        hand = (elbow[0] + FORE * math.sin(a + 0.45 * sp + 0.1), elbow[1] - FORE * math.cos(a + 0.45 * sp + 0.1))
        return elbow, hand
    el, hl = arm(math.pi); er, hr = arm(0.0)
    j = {"hip": hip, "neck": neck, "head": head, "knee_l": kl, "foot_l": fl, "knee_r": kr, "foot_r": fr,
         "elbow_l": el, "hand_l": hl, "elbow_r": er, "hand_r": hr}
    if facing < 0:
        j = {k: (-x, y) for k, (x, y) in j.items()}
    return j


def kiss_pose(u: float, t: float) -> tuple[dict[str, Point], float]:
    """A standing woman facing you: hand rises to the lips (u 0.15–0.45), then opens toward you
    (0.45–0.6) and the kiss flies. Returns joints and the kiss amount (0 before, 1 as it leaves)."""
    sway = 0.01 * math.sin(t * 1.3)
    hip = (sway, 0.50)
    neck = (sway, 0.82)
    head = (sway, 0.92)
    def ease(a: float, b: float) -> float:
        k = max(0.0, min(1.0, (u - a) / (b - a))); return k * k * (3 - 2 * k)
    rise = ease(0.15, 0.45)              # hand to lips
    push = ease(0.47, 0.60)              # hand opens toward you
    # right arm: from resting at the side to the lips, then forward (toward the viewer: drawn larger, lower)
    rest_e, rest_h = (sway + 0.16, 0.66), (sway + 0.18, 0.50)
    lips_e, lips_h = (sway + 0.14, 0.74), (sway + 0.04, 0.88)
    push_e, push_h = (sway + 0.12, 0.74), (sway + 0.02, 0.80)
    def mix(a: Point, b: Point, k: float) -> Point:
        return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    er = mix(mix(rest_e, lips_e, rise), push_e, push)
    hr = mix(mix(rest_h, lips_h, rise), push_h, push)
    el, hl = (sway - 0.16, 0.66), (sway - 0.17, 0.50)
    kl, fl = (sway - 0.07, 0.26), (sway - 0.08, 0.02)
    kr, fr = (sway + 0.07, 0.26), (sway + 0.08, 0.02)
    kiss = push if u < 0.6 else 1.0
    return {"hip": hip, "neck": neck, "head": head, "knee_l": kl, "foot_l": fl, "knee_r": kr, "foot_r": fr,
            "elbow_l": el, "hand_l": hl, "elbow_r": er, "hand_r": hr}, kiss


BONES = [("hip", "neck"), ("neck", "head"), ("hip", "knee_l"), ("knee_l", "foot_l"), ("hip", "knee_r"), ("knee_r", "foot_r"),
         ("neck", "elbow_l"), ("elbow_l", "hand_l"), ("neck", "elbow_r"), ("elbow_r", "hand_r")]
