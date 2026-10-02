"""Draw a rig pose as a luminous figure with volume (astral style) into a QImage."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen

from ..rigs import BONES

INK = QColor("#efe8da")
SIZE = 320


def draw_pose(joints: dict, woman: bool = False, size: int = SIZE, facing: float = 1.0) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = size * 0.82
    def P(j: str) -> QPointF:
        x, y = joints[j]
        return QPointF(size * 0.5 + x * scale * facing, size * 0.95 - y * scale)
    for width, alpha in ((size * 0.09, 0.10), (size * 0.055, 0.22), (size * 0.032, 1.0)):
        pen = QPen(QColor(239, 232, 218, int(255 * alpha)), width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for a, b in BONES:
            w = width * (1.35 if a == "hip" and b == "neck" else 1.0)
            pen.setWidthF(w); p.setPen(pen)
            p.drawLine(P(a), P(b))
        p.setBrush(QColor(239, 232, 218, int(255 * alpha))); p.setPen(Qt.PenStyle.NoPen)
        hx, hy = joints["head"]
        r = size * 0.055 + (width - size * 0.032) * 0.5
        p.drawEllipse(P("head"), r, r)
        if woman:                                     # hair falling past the shoulders
            pen2 = QPen(QColor(239, 232, 218, int(255 * alpha * 0.8)), width * 0.6); pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen2); p.setBrush(Qt.BrushStyle.NoBrush)
            for dx in (-0.055, -0.035, 0.035, 0.055):
                top = QPointF(P("head").x() + dx * scale, P("head").y() - r * 0.2)
                p.drawLine(top, QPointF(top.x() + dx * scale * 0.6, P("neck").y() + 0.08 * scale))
    p.end()
    return img
