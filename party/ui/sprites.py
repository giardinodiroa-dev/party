"""Line-art sprites and text, drawn with QPainter into images, uploaded as GL textures.

Everything here is pale bone on transparent, so the shader tints it. Sprites are
128 px squares; text is rendered at the requested pixel size in the house mono font.
"""
from __future__ import annotations

import math
from collections import OrderedDict

import numpy as np
from OpenGL import GL as gl
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QImage, QPainter, QPainterPath, QPen

from .. import theme

SIZE = 128
INK = QColor("#efe8da")


def _painter(img: QImage) -> QPainter:
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(INK, 3.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    return p


def _fill(p: QPainter, on: bool = True) -> None:
    p.setBrush(theme.alpha(INK, 0.35) if on else Qt.BrushStyle.NoBrush)


def draw_sprite(kind: str) -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = _painter(img)
    c = QPointF(64, 64)
    if kind == "ufo":
        _fill(p); p.drawEllipse(QRectF(14, 60, 100, 28))
        p.drawChord(QRectF(40, 36, 48, 44), 0, 180 * 16)
        p.setBrush(INK)
        for x in (36, 64, 92): p.drawEllipse(QPointF(x, 74), 4, 4)
    elif kind == "rocket":
        path = QPainterPath(QPointF(64, 10)); path.quadTo(90, 50, 84, 96); path.lineTo(44, 96); path.quadTo(38, 50, 64, 10)
        _fill(p); p.drawPath(path)
        p.drawLine(QPointF(44, 80), QPointF(26, 108)); p.drawLine(QPointF(84, 80), QPointF(102, 108))
        p.setBrush(theme.alpha(INK, 0.7)); p.drawEllipse(QPointF(64, 52), 9, 9)
        p.setBrush(theme.alpha(INK, 0.5)); p.drawEllipse(QRectF(52, 98, 24, 22))
    elif kind == "alien":
        _fill(p); p.drawEllipse(QRectF(32, 22, 64, 74))
        p.setBrush(INK); p.drawEllipse(QRectF(44, 46, 16, 22)); p.drawEllipse(QRectF(68, 46, 16, 22))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(48, 24), QPointF(36, 6)); p.drawLine(QPointF(80, 24), QPointF(92, 6))
        p.drawLine(QPointF(52, 96), QPointF(50, 118)); p.drawLine(QPointF(76, 96), QPointF(78, 118))
        p.drawArc(QRectF(54, 72, 20, 12), 200 * 16, 140 * 16)
    elif kind == "angel":
        p.drawEllipse(QRectF(50, 6, 28, 10))
        _fill(p); p.drawEllipse(QPointF(64, 30), 11, 11)
        path = QPainterPath(QPointF(64, 42)); path.lineTo(42, 112); path.lineTo(86, 112); path.closeSubpath(); p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for s in (-1, 1):
            w = QPainterPath(QPointF(64 + s * 14, 52)); w.quadTo(64 + s * 60, 20, 64 + s * 48, 86); w.quadTo(64 + s * 30, 70, 64 + s * 14, 70); p.drawPath(w)
    elif kind == "jesus":
        p.drawEllipse(QPointF(64, 26), 18, 18)
        _fill(p); p.drawEllipse(QPointF(64, 30), 10, 11)
        path = QPainterPath(QPointF(64, 42)); path.lineTo(46, 118); path.lineTo(82, 118); path.closeSubpath(); p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(56, 56), QPointF(16, 70)); p.drawLine(QPointF(72, 56), QPointF(112, 70))
        p.drawLine(QPointF(58, 40), QPointF(60, 46)); p.drawLine(QPointF(70, 40), QPointF(68, 46))
    elif kind == "comet":
        _fill(p); p.drawEllipse(QPointF(92, 36), 14, 14)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dy, L in ((-6, 70), (2, 86), (10, 62)):
            p.drawLine(QPointF(84, 40 + dy), QPointF(84 - L, 40 + dy + L * 0.55))
    elif kind == "planet":
        _fill(p); p.drawEllipse(QPointF(64, 64), 30, 30)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawEllipse(QRectF(10, 54, 108, 20))
    elif kind == "moon":
        path = QPainterPath(); path.addEllipse(QPointF(60, 64), 36, 36)
        cut = QPainterPath(); cut.addEllipse(QPointF(78, 58), 32, 32)
        _fill(p); p.drawPath(path.subtracted(cut))
    elif kind == "gaspump":
        _fill(p); p.drawRoundedRect(QRectF(34, 24, 44, 90), 6, 6)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawRect(QRectF(42, 34, 28, 22))
        p.drawArc(QRectF(70, 30, 40, 60), 90 * 16, -180 * 16); p.drawLine(QPointF(90, 90), QPointF(104, 104))
        p.setFont(theme.font(9, True, 1.0)); p.drawText(QRectF(34, 60, 44, 20), int(Qt.AlignmentFlag.AlignCenter), "GAS")
    elif kind == "cat":
        _fill(p); p.drawEllipse(QRectF(30, 56, 72, 50)); p.drawEllipse(QPointF(44, 50), 20, 18)
        path = QPainterPath(QPointF(30, 44)); path.lineTo(26, 20); path.lineTo(44, 34); p.drawPath(path)
        path = QPainterPath(QPointF(58, 44)); path.lineTo(62, 20); path.lineTo(46, 34); p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        t = QPainterPath(QPointF(100, 82)); t.quadTo(126, 70, 112, 40); p.drawPath(t)
        for y in (48, 54): p.drawLine(QPointF(24, y), QPointF(8, y - 4 + (y - 48)))
        p.setBrush(INK); p.drawEllipse(QPointF(38, 48), 2.5, 2.5); p.drawEllipse(QPointF(50, 48), 2.5, 2.5)
    elif kind == "whale":
        _fill(p); p.drawEllipse(QRectF(10, 44, 90, 46))
        path = QPainterPath(QPointF(96, 66)); path.lineTo(122, 48); path.lineTo(118, 68); path.lineTo(122, 86); path.closeSubpath(); p.drawPath(path)
        p.setBrush(INK); p.drawEllipse(QPointF(30, 60), 3, 3)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawLine(QPointF(34, 44), QPointF(28, 22)); p.drawLine(QPointF(34, 44), QPointF(42, 24))
    elif kind == "dove":
        _fill(p)
        body = QPainterPath(QPointF(20, 70)); body.quadTo(60, 40, 104, 60); body.quadTo(70, 86, 20, 70); p.drawPath(body)
        wing = QPainterPath(QPointF(58, 56)); wing.quadTo(70, 14, 96, 26); wing.quadTo(80, 50, 58, 56); p.drawPath(wing)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawLine(QPointF(104, 60), QPointF(118, 56)); p.drawLine(QPointF(100, 72), QPointF(120, 92))
    elif kind == "star":
        path = QPainterPath()
        for i in range(10):
            a = math.radians(-90 + i * 36); r = 48 if i % 2 == 0 else 20
            pt = QPointF(64 + math.cos(a) * r, 64 + math.sin(a) * r)
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath(); _fill(p); p.drawPath(path)
    elif kind == "eye":
        eye = QPainterPath(QPointF(8, 64)); eye.quadTo(64, 10, 120, 64); eye.quadTo(64, 118, 8, 64); _fill(p); p.drawPath(eye)
        p.setBrush(theme.alpha(INK, 0.6)); p.drawEllipse(QPointF(64, 64), 24, 24)
        p.setBrush(QColor("#07070a")); p.drawEllipse(QPointF(64, 64), 10, 10)
    elif kind == "heart":
        h = QPainterPath(QPointF(64, 112)); h.cubicTo(10, 70, 18, 18, 64, 44); h.cubicTo(110, 18, 118, 70, 64, 112); _fill(p); p.drawPath(h)
    elif kind == "satellite":
        _fill(p); p.drawRect(QRectF(50, 50, 28, 28))
        p.drawRect(QRectF(6, 56, 36, 16)); p.drawRect(QRectF(86, 56, 36, 16))
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawLine(QPointF(64, 50), QPointF(64, 26)); p.drawArc(QRectF(48, 14, 32, 24), 0, 180 * 16)
    elif kind == "astronaut":
        _fill(p); p.drawEllipse(QPointF(64, 34), 20, 20); p.drawRoundedRect(QRectF(44, 54, 40, 44), 10, 10)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(44, 62), QPointF(18, 48)); p.drawLine(QPointF(84, 62), QPointF(110, 48))
        p.drawLine(QPointF(52, 98), QPointF(44, 122)); p.drawLine(QPointF(76, 98), QPointF(84, 122))
        p.drawArc(QRectF(50, 24, 28, 20), 20 * 16, 140 * 16)
    elif kind == "dragon":
        body = QPainterPath(QPointF(8, 90)); body.cubicTo(30, 40, 60, 110, 90, 60); body.quadTo(100, 44, 118, 46); p.drawPath(body)
        p.drawLine(QPointF(118, 46), QPointF(126, 40)); p.drawLine(QPointF(118, 46), QPointF(126, 54))
        w = QPainterPath(QPointF(60, 78)); w.lineTo(50, 30); w.lineTo(78, 62); p.drawPath(w)
        for x in (24, 40, 76): p.drawLine(QPointF(x, 72 - (x % 3) * 6), QPointF(x + 4, 60 - (x % 3) * 6))
    elif kind == "unicorn":
        _fill(p); p.drawEllipse(QRectF(30, 56, 64, 36)); p.drawEllipse(QRectF(86, 34, 30, 24))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(108, 36), QPointF(124, 10))
        for x in (40, 54, 72, 86): p.drawLine(QPointF(x, 90), QPointF(x - 2, 118))
        m = QPainterPath(QPointF(90, 40)); m.quadTo(72, 30, 66, 60); p.drawPath(m)
        t = QPainterPath(QPointF(32, 66)); t.quadTo(10, 70, 14, 96); p.drawPath(t)
    elif kind == "fish":
        _fill(p); p.drawEllipse(QRectF(20, 44, 70, 40))
        path = QPainterPath(QPointF(88, 64)); path.lineTo(116, 42); path.lineTo(116, 86); path.closeSubpath(); p.drawPath(path)
        p.setBrush(INK); p.drawEllipse(QPointF(38, 60), 3.5, 3.5)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawArc(QRectF(44, 48, 24, 32), 240 * 16, 100 * 16)
    else:
        p.drawEllipse(c, 30, 30)
    p.end()
    return img


def draw_text(text: str, px: int, bold: bool = True) -> QImage:
    f = theme.font(px * 0.75, bold, 1.4)
    fm = QFontMetricsF(f)
    w = int(fm.horizontalAdvance(text)) + 24
    h = int(fm.height()) + 12
    img = QImage(max(2, w), max(2, h), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setFont(f)
    p.setPen(INK)
    p.drawText(QRectF(12, 6, w - 24, h - 12), int(Qt.AlignmentFlag.AlignCenter), text)
    p.end()
    return img


def upload(img: QImage) -> tuple[int, int, int]:
    """QImage → GL texture (RGBA8). Returns (tex, w, h). Needs a current context."""
    img = img.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    w, h = img.width(), img.height()
    buf = np.frombuffer(img.constBits().asarray(h * img.bytesPerLine()), dtype=np.uint8)
    buf = np.ascontiguousarray(buf.reshape(h, img.bytesPerLine() // 4, 4)[:, :w, :])
    tex = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, buf)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
    return tex, w, h


class TextureCache:
    """Sprites by kind, text by (string, px), images by path — uploaded once, kept."""

    def __init__(self, limit: int = 160) -> None:
        self.items: OrderedDict[tuple, tuple[int, int, int]] = OrderedDict()
        self.limit = limit

    def sprite(self, kind: str) -> tuple[int, int, int]:
        return self._get(("sprite", kind), lambda: draw_sprite(kind))

    def text(self, text: str, px: int) -> tuple[int, int, int]:
        return self._get(("text", text, px), lambda: draw_text(text, px))

    def image(self, path: str, max_px: int = 640) -> tuple[int, int, int] | None:
        img = QImage(path)
        if img.isNull():
            return None
        if max(img.width(), img.height()) > max_px:
            img = img.scaled(max_px, max_px, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        return self._get(("image", path), lambda: img)

    def _get(self, key: tuple, make) -> tuple[int, int, int]:
        if key in self.items:
            self.items.move_to_end(key)
            return self.items[key]
        entry = upload(make())
        self.items[key] = entry
        if len(self.items) > self.limit:
            _, (tex, _, _) = self.items.popitem(last=False)
            gl.glDeleteTextures(1, [tex])     # GPU handle of our own texture; nothing of his
        return entry
