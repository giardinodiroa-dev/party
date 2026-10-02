"""Line-art sprites and text, drawn with QPainter into images, uploaded as GL textures.

Everything here is pale bone on transparent, so the shader tints it. Sprites are
128 px squares; text is rendered at the requested pixel size in the house mono font.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from pathlib import Path

import numpy as np
from OpenGL import GL as gl
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFontMetricsF, QImage, QPainter, QPainterPath, QPen

from .. import theme

SIZE = 128
INK = QColor("#efe8da")
LEDAIE_FONT = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "LedaieHandscript.ttf"
_LEDAIE: tuple[str, str] | None = None


def ledaie_font() -> tuple[str, str]:
    """(family, characters the handscript really maps) — pattern from ~/airmouse/airmouse/ui/v3.py."""
    global _LEDAIE
    if _LEDAIE is None:
        from PyQt6.QtGui import QFontDatabase, QFontMetrics, QFont as _QF
        fam, chars = "", ""
        fid = QFontDatabase.addApplicationFont(str(LEDAIE_FONT)) if LEDAIE_FONT.exists() else -1
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if fams:
            fam = fams[0]
            try:
                from fontTools.ttLib import TTFont
                cmap = TTFont(str(LEDAIE_FONT)).getBestCmap() or {}
                chars = "".join(chr(c) for c in sorted(cmap) if chr(c).isprintable() and not chr(c).isspace())
            except Exception:
                fm = QFontMetrics(_QF(fam))
                chars = "".join(chr(c) for c in range(0x21, 0x250) if fm.inFontUcs4(c))
        _LEDAIE = (fam, chars)
    return _LEDAIE


def draw_handscript(text: str, px: int) -> QImage:
    """A word in his Ledaie handscript. Letters the font does not map are left out."""
    fam, chars = ledaie_font()
    keep = "".join(ch for ch in text if ch in chars or ch.lower() in chars) or text
    from PyQt6.QtGui import QFont as _QF
    f = _QF(fam or "DejaVu Sans")
    f.setPixelSize(px)
    fm = QFontMetricsF(f)
    w = int(fm.horizontalAdvance(keep)) + 40
    h = int(fm.height()) + 24
    img = QImage(max(2, w), max(2, h), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setFont(f)
    p.setPen(INK)
    p.drawText(QRectF(20, 12, w - 40, h - 24), int(Qt.AlignmentFlag.AlignCenter), keep)
    p.end()
    return img


def _painter(img: QImage, width: float = 3.2, alpha: float = 1.0) -> QPainter:
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(theme.alpha(INK, alpha), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    return p


_FILL_ON = True      # the glow passes draw strokes only; fills are laid once, on the final pass


def _fill(p: QPainter, on: bool = True) -> None:
    p.setBrush(theme.alpha(INK, 0.16) if (on and _FILL_ON) else Qt.BrushStyle.NoBrush)


def draw_sprite(kind: str, glow: bool = True) -> QImage:
    """Astral line art: luminous bone strokes with a soft halo — a constellation drawing, not a cartoon."""
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    global _FILL_ON
    passes = ((11.0, 0.10), (6.0, 0.22), (3.2, 1.0)) if glow else ((3.2, 1.0),)
    for width, alpha in passes:
        _FILL_ON = alpha >= 1.0
        p = _painter(img, width, alpha)
        _draw_kind(p, kind)
        p.end()
    _FILL_ON = True
    return img


def _draw_kind(p: QPainter, kind: str) -> None:
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
    elif kind == "sun":
        _fill(p); p.drawEllipse(c, 26, 26)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(12):
            a = math.radians(i * 30); p.drawLine(QPointF(64 + math.cos(a) * 34, 64 + math.sin(a) * 34), QPointF(64 + math.cos(a) * (46 if i % 2 else 54), 64 + math.sin(a) * (46 if i % 2 else 54)))
    elif kind == "earth":
        _fill(p); p.drawEllipse(c, 40, 40)
        p.setBrush(theme.alpha(INK, 0.7)); p.setPen(Qt.PenStyle.NoPen)
        land = QPainterPath(QPointF(40, 40)); land.cubicTo(60, 30, 70, 50, 56, 66); land.cubicTo(44, 72, 34, 56, 40, 40); p.drawPath(land)
        land2 = QPainterPath(QPointF(74, 70)); land2.cubicTo(96, 64, 94, 92, 76, 96); land2.cubicTo(66, 90, 64, 76, 74, 70); p.drawPath(land2)
    elif kind == "galaxy":
        p.setBrush(theme.alpha(INK, 0.6)); p.drawEllipse(c, 10, 6)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for s0 in (0.0, math.pi):
            arm = QPainterPath(QPointF(64 + math.cos(s0) * 8, 64 + math.sin(s0) * 5))
            for k in range(1, 30):
                a = s0 + k * 0.17; r = 8 + k * 1.8
                arm.lineTo(QPointF(64 + math.cos(a) * r, 64 + math.sin(a) * r * 0.55))
            p.drawPath(arm)
    elif kind == "meteor":
        _fill(p); p.drawEllipse(QPointF(96, 32), 12, 12)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dy, L in ((-4, 60), (4, 84), (12, 50)): p.drawLine(QPointF(88, 36 + dy), QPointF(88 - L * 0.8, 36 + dy + L * 0.6))
    elif kind == "phoenix":
        _fill(p)
        body = QPainterPath(QPointF(64, 100)); body.quadTo(50, 70, 64, 40); body.quadTo(78, 70, 64, 100); p.drawPath(body)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for sx in (-1, 1):
            w = QPainterPath(QPointF(64 + sx * 10, 60)); w.quadTo(64 + sx * 50, 20, 64 + sx * 60, 50); w.quadTo(64 + sx * 40, 50, 64 + sx * 12, 76); p.drawPath(w)
        p.drawEllipse(QPointF(64, 36), 6, 6); p.drawLine(QPointF(64, 100), QPointF(56, 122)); p.drawLine(QPointF(64, 100), QPointF(72, 122))
    elif kind == "owl":
        _fill(p); p.drawEllipse(QRectF(34, 36, 60, 76)); p.drawEllipse(QRectF(36, 20, 56, 44))
        p.setBrush(INK); p.drawEllipse(QPointF(52, 42), 9, 9); p.drawEllipse(QPointF(76, 42), 9, 9)
        p.setBrush(QColor("#07070a")); p.drawEllipse(QPointF(52, 42), 4, 4); p.drawEllipse(QPointF(76, 42), 4, 4)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawLine(QPointF(38, 22), QPointF(30, 8)); p.drawLine(QPointF(90, 22), QPointF(98, 8))
        p.drawLine(QPointF(60, 52), QPointF(64, 60)); p.drawLine(QPointF(68, 52), QPointF(64, 60))
    elif kind == "butterfly":
        _fill(p)
        for sx in (-1, 1):
            up = QPainterPath(QPointF(64, 60)); up.cubicTo(64 + sx * 60, 10, 64 + sx * 64, 60, 64, 66); p.drawPath(up)
            lo = QPainterPath(QPointF(64, 66)); lo.cubicTo(64 + sx * 50, 70, 64 + sx * 40, 116, 64, 80); p.drawPath(lo)
        p.setBrush(Qt.BrushStyle.NoBrush); p.drawLine(QPointF(64, 48), QPointF(64, 86))
        p.drawLine(QPointF(64, 48), QPointF(54, 30)); p.drawLine(QPointF(64, 48), QPointF(74, 30))
    elif kind == "lighthouse":
        _fill(p)
        tower = QPainterPath(QPointF(50, 118)); tower.lineTo(56, 44); tower.lineTo(72, 44); tower.lineTo(78, 118); tower.closeSubpath(); p.drawPath(tower)
        p.drawRect(QRectF(52, 28, 24, 16)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(76, 36), QPointF(124, 20)); p.drawLine(QPointF(76, 36), QPointF(124, 52))
        for y in (62, 80, 98): p.drawLine(QPointF(54, y), QPointF(74, y))
    elif kind == "crown":
        _fill(p)
        cr = QPainterPath(QPointF(24, 96)); cr.lineTo(20, 44); cr.lineTo(44, 66); cr.lineTo(64, 30); cr.lineTo(84, 66); cr.lineTo(108, 44); cr.lineTo(104, 96); cr.closeSubpath(); p.drawPath(cr)
        p.setBrush(INK)
        for x, y in ((20, 44), (64, 30), (108, 44)): p.drawEllipse(QPointF(x, y), 4, 4)
    elif kind == "tree":
        p.drawLine(QPointF(64, 120), QPointF(64, 70))
        for x0, y0, x1, y1 in ((64, 90, 40, 70), (64, 80, 90, 56), (64, 100, 82, 84), (64, 120, 44, 126), (64, 120, 86, 126)): p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        _fill(p); p.drawEllipse(QRectF(24, 18, 80, 60))
    else:
        p.drawEllipse(c, 30, 30)


def draw_constellation(stars: list[tuple[float, float]], lines: list[tuple[int, int]], size: int = 320) -> QImage:
    """A real star pattern: hairlines between the stars, the stars as soft points."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pts = [QPointF(16 + x * (size - 32), 16 + y * (size - 32)) for x, y in stars]
    pen = QPen(theme.alpha(INK, 0.45), 1.2); p.setPen(pen)
    for a, b in lines:
        p.drawLine(pts[a], pts[b])
    p.setPen(Qt.PenStyle.NoPen)
    for i, pt in enumerate(pts):
        r = 5.0 if i < 3 else 3.6
        p.setBrush(theme.alpha(INK, 0.25)); p.drawEllipse(pt, r * 2.2, r * 2.2)
        p.setBrush(INK); p.drawEllipse(pt, r, r)
    p.end()
    return img


PHRASE_FONTS = {"MONO": None, "SERIF": ["DejaVu Serif", "Noto Serif", "serif"],
                "SANS": ["Noto Sans", "DejaVu Sans", "sans-serif"], "HANDSCRIPT": "ledaie"}


def draw_text(text: str, px: int, bold: bool = True, family: str = "MONO") -> QImage:
    fams = PHRASE_FONTS.get(family)
    if fams == "ledaie":
        return draw_handscript(text, px)
    f = theme.font(px * 0.75, bold, 1.4)
    if fams:
        f.setFamilies(fams)
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 0.6)
    elif family not in PHRASE_FONTS:                      # any installed family, by name
        f.setFamilies([family, "DejaVu Sans"])
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 0.6)
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


def black_keyed(img: QImage) -> QImage:
    """A painting on pure black → premultiplied RGBA whose alpha is its light. Black becomes void."""
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = img.width(), img.height()
    a = np.frombuffer(img.constBits().asarray(h * img.bytesPerLine()), dtype=np.uint8)
    a = a.reshape(h, img.bytesPerLine() // 4, 4)[:, :w, :].astype(np.float32) / 255.0
    luma = a[:, :, :3].max(axis=2)
    alpha = np.clip((luma - 0.06) / 0.5, 0.0, 1.0)            # soft key: faint glow stays faint
    # vignette: the last 22% toward every edge fades to nothing, so a painting never shows a border
    yy = np.linspace(0, 1, h)[:, None]; xx = np.linspace(0, 1, w)[None, :]
    edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) / 0.22
    alpha = alpha * np.clip(edge, 0.0, 1.0) ** 1.5
    out = np.empty((h, w, 4), dtype=np.uint8)
    out[:, :, :3] = (a[:, :, :3] * alpha[:, :, None] * 255).astype(np.uint8)
    out[:, :, 3] = (alpha * 255).astype(np.uint8)
    res = QImage(out.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888_Premultiplied)
    return res.copy()


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

    def sprite(self, kind: str, style: str = "ASTRAL") -> tuple[int, int, int]:
        def make():
            if style == "CUTE":
                from .ghibli import render
                img = render(kind)
                if img is not None:
                    return img
            return draw_sprite(kind)
        return self._get(("sprite", kind, style), make)

    def art(self, path: str, max_px: int = 512) -> tuple[int, int, int] | None:
        """A painting on black, keyed to light. None if the file does not load."""
        def make():
            img = QImage(path)
            img = img.copy(0, 0, img.width(), int(img.height() * 0.88))     # drop the generator's bottom strip
            if max(img.width(), img.height()) > max_px:
                img = img.scaled(max_px, max_px, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return black_keyed(img)
        if QImage(path).isNull():
            return None
        return self._get(("art", path), make)

    def text(self, text: str, px: int, family: str = "MONO") -> tuple[int, int, int]:
        return self._get(("text", text, px, family), lambda: draw_text(text, px, True, family))

    def constellation(self, index: int) -> tuple[int, int, int]:
        from ..stories import CONSTELLATIONS
        _, _, stars, lines = CONSTELLATIONS[index]
        return self._get(("const", index), lambda: draw_constellation(stars, lines))

    def handscript(self, text: str, px: int) -> tuple[int, int, int]:
        return self._get(("hand", text, px), lambda: draw_handscript(text, px))

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
