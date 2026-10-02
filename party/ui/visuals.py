"""The three light modes. Each paints one frame from the latest Levels.

PULSE — the whole screen breathes with loudness, flashes on the beat.
BARS  — a mirrored spectrum, hue drifting with time.
ORBS  — particles born on beats; bass sets their size, treble their sparkle.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QRadialGradient

from .. import theme
from ..analysis import Levels

MODES = ["PULSE", "BARS", "ORBS"]
MAX_PARTICLES = 220


def hsv(h: float, s: float, v: float, a: float = 1.0) -> QColor:
    return QColor.fromHsvF((h % 360.0) / 360.0, _c(s), _c(v), _c(a))


def _c(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    hue: float
    size: float
    life: float = 1.0


class Scene:
    """Everything that persists between frames: hue drift, beat flash, particles."""

    def __init__(self) -> None:
        self.hue = random.uniform(0, 360)
        self.flash = 0.0
        self.particles: list[Particle] = []
        self.rng = random.Random()

    def step(self, lv: Levels, dt: float, sens: float, rect: QRectF) -> None:
        self.hue = (self.hue + dt * 12.0 + (37.0 if lv.beat else 0.0)) % 360.0
        self.flash = 1.0 if lv.beat else self.flash * math.exp(-dt * 6.0)
        if lv.beat:
            n = 6 + int(_c(lv.bass * sens) * 14)
            cx, cy = rect.center().x(), rect.center().y()
            for _ in range(n):
                ang = self.rng.uniform(0, math.tau)
                spd = self.rng.uniform(60, 260) * (0.6 + _c(lv.loud * sens))
                self.particles.append(Particle(
                    cx + self.rng.uniform(-40, 40), cy + self.rng.uniform(-40, 40),
                    math.cos(ang) * spd, math.sin(ang) * spd,
                    self.hue + self.rng.uniform(-30, 30),
                    self.rng.uniform(10, 26)))
            del self.particles[:-MAX_PARTICLES]
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.985
            p.vy *= 0.985
            p.life -= dt * 0.55
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def paint(self, p: QPainter, rect: QRectF, lv: Levels, mode: str, sens: float) -> None:
        p.fillRect(rect, QColor(theme.VOID))
        if mode == "BARS":
            self._bars(p, rect, lv, sens)
        elif mode == "ORBS":
            self._orbs(p, rect, lv, sens)
        else:
            self._pulse(p, rect, lv, sens)
        if self.flash > 0.02:
            p.fillRect(rect, theme.alpha(theme.BONE, 0.35 * self.flash))

    # -- modes ---------------------------------------------------------------
    def _pulse(self, p: QPainter, rect: QRectF, lv: Levels, sens: float) -> None:
        loud = _c(lv.loud * sens)
        bass = _c(lv.bass * sens)
        p.fillRect(rect, hsv(self.hue, 0.85, 0.06 + 0.7 * loud))
        radius = max(rect.width(), rect.height()) * (0.25 + 0.55 * bass)
        g = QRadialGradient(rect.center(), radius)
        g.setColorAt(0.0, hsv(self.hue + 40, 0.55, 0.35 + 0.65 * loud, 0.95))
        g.setColorAt(1.0, hsv(self.hue + 40, 0.55, 0.0, 0.0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(rect.center(), radius, radius)
        ring = min(rect.width(), rect.height()) * (0.18 + 0.3 * _c(lv.mid * sens))
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = p.pen()
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidthF(2.0 + 10.0 * _c(lv.treble * sens))
        pen.setColor(hsv(self.hue + 180, 0.5, 0.9, 0.25 + 0.5 * _c(lv.treble * sens)))
        p.setPen(pen)
        p.drawEllipse(rect.center(), ring, ring)

    def _bars(self, p: QPainter, rect: QRectF, lv: Levels, sens: float) -> None:
        n = len(lv.spectrum)
        cols = n * 2
        w = rect.width() / cols
        gap = max(1.0, w * 0.18)
        p.setPen(Qt.PenStyle.NoPen)
        lift = 0.25 * self.flash
        for i in range(cols):
            k = (n - 1 - i) if i < n else (i - n)
            level = _c(float(lv.spectrum[k]) * sens + lift)
            h = rect.height() * (0.02 + 0.96 * level)
            x = rect.left() + i * w
            hue = self.hue + k * (240.0 / n)
            p.setBrush(hsv(hue, 0.9, 0.35 + 0.65 * level, 0.92))
            p.drawRect(QRectF(x + gap / 2, rect.bottom() - h, w - gap, h))
            p.setBrush(hsv(hue, 0.4, 1.0, 0.9))
            p.drawRect(QRectF(x + gap / 2, rect.bottom() - h, w - gap, 3.0))

    def _orbs(self, p: QPainter, rect: QRectF, lv: Levels, sens: float) -> None:
        p.fillRect(rect, hsv(self.hue, 0.6, 0.04 + 0.08 * _c(lv.loud * sens)))
        p.setPen(Qt.PenStyle.NoPen)
        bass = _c(lv.bass * sens)
        for q in self.particles:
            r = q.size * (0.6 + 1.6 * bass) * (0.3 + 0.7 * q.life)
            p.setBrush(hsv(q.hue, 0.8, 0.9, 0.14 * q.life))
            p.drawEllipse(QPointF(q.x, q.y), r * 2.2, r * 2.2)
            p.setBrush(hsv(q.hue, 0.7, 1.0, 0.85 * q.life))
            p.drawEllipse(QPointF(q.x, q.y), r, r)
        sparkles = int(_c(lv.treble * sens) * 60)
        if sparkles:
            p.setBrush(theme.alpha(theme.BONE, 0.7))
            for _ in range(sparkles):
                x = self.rng.uniform(rect.left(), rect.right())
                y = self.rng.uniform(rect.top(), rect.bottom())
                p.drawEllipse(QPointF(x, y), 1.4, 1.4)
