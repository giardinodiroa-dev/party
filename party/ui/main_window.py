"""The Party window: a frameless voidblack canvas that paints the lights, with chrome
(a black title strip and a bottom icon bar) drawn in the same frame and faded out
after two seconds without the mouse. Pop-ups (the source picker) are children of
this window, never a second OS window.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QColor, QCursor, QFontMetricsF, QKeyEvent, QMouseEvent, QPainter,
                         QPainterPath, QPen)
from PyQt6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .. import theme
from ..analysis import Levels
from ..audio import AudioTap, default_monitor, list_sources
from .aura import AuraParams, AuraWindow
from .visuals import MODES, Scene

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state.json"
TITLE_H = 30.0
BAR_H = 56.0
EDGE = 7
CHROME_IDLE_MS = 2000
SENS_MIN, SENS_MAX = 0.3, 3.0


def fit_text(p: QPainter, rect: QRectF, text: str, size: float, color: str,
             bold: bool = False, spacing: float = 0.0, min_size: float = 7.0,
             align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft) -> None:
    """House law 30: shrink toward a minimum, then elide — text never leaves its box."""
    s = size
    while s > min_size:
        if QFontMetricsF(theme.font(s, bold, spacing)).horizontalAdvance(text) <= rect.width():
            break
        s -= 0.5
    f = theme.font(s, bold, spacing)
    text = QFontMetricsF(f).elidedText(text, Qt.TextElideMode.ElideRight, int(rect.width()))
    p.setFont(f)
    p.setPen(QColor(color))
    p.drawText(rect, int(align), text)


class SourceMenu(QDialog):
    """Tiny scrollable hotkey menu (house law 2): rows stamped [1]..[9], Esc closes."""

    def __init__(self, parent: QWidget, sources: list[tuple[str, str]], current: str | None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.choice: str | None = None
        self.sources = sources
        self.setStyleSheet(theme.panel_qss("QDialog") + f"""
QListWidget {{ background: {theme.PANEL}; border: 1px solid {theme.HAIRLINE};
               font-size: 11px; outline: 0; }}
QListWidget::item {{ padding: 5px 10px; }}
QListWidget::item:selected {{ background: {theme.SELECT}; color: {theme.BONE}; }}""")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget(self)
        self.list.setUniformItemSizes(True)
        for i, (name, label) in enumerate(sources):
            tag = f"[{i + 1}] " if i < 9 else "    "
            mark = " ·· LIVE" if name == current else ""
            self.list.addItem(QListWidgetItem(f"{tag}{label}{mark}"))
        lay.addWidget(self.list)
        row_h = self.list.sizeHintForRow(0) if sources else 24
        rows = max(1, min(len(sources), 6))
        self.list.setFixedHeight(row_h * rows + 4)
        self.setFixedWidth(min(460, max(220, self.list.sizeHintForColumn(0) + 28)))
        if sources:
            self.list.setCurrentRow(next((i for i, (n, _) in enumerate(sources) if n == current), 0))
        self.list.itemActivated.connect(lambda item: self._pick(self.list.row(item)))
        self.list.itemClicked.connect(lambda item: self._pick(self.list.row(item)))

    def _pick(self, row: int) -> None:
        if 0 <= row < len(self.sources):
            self.choice = self.sources[row][0]
        self.accept()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        k = e.key()
        if Qt.Key.Key_1 <= k <= Qt.Key.Key_9:
            self._pick(k - Qt.Key.Key_1)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._pick(self.list.currentRow())
        elif k == Qt.Key.Key_Escape:
            self.reject()
        else:
            self.list.keyPressEvent(e)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Party")
        self.setMinimumSize(360, 220)
        self.resize(960, 560)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self.path: Path | None = None          # hotreload contract (no document here)
        self.thread = None                     # hotreload contract (never busy with Claude)
        self.mode = MODES[0]
        self.sensitivity = 1.0
        self.paused = False
        self.hotreload_on = True
        self.source: str | None = None
        self.fullscreen_wanted = False
        self.aura: AuraWindow | None = None
        self.aura_wanted = False

        self.scene = Scene()
        self.levels = Levels()
        self.tap = AudioTap()
        self.chrome = 1.0
        self.chrome_target = 1.0
        self._hits: list[tuple[QRectF, str]] = []
        self._drag_slider = False
        self._last = time.monotonic()
        self._bar_rect = QRectF()
        self._slider_rect = QRectF()

        self.frame = QTimer(self)
        self.frame.setInterval(theme.FRAME_MS)
        self.frame.timeout.connect(self._tick)
        self.idle = QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.setInterval(CHROME_IDLE_MS)
        self.idle.timeout.connect(self._hide_chrome)
        self.saver = QTimer(self)
        self.saver.setSingleShot(True)
        self.saver.setInterval(2000)
        self.saver.timeout.connect(self.save)
        self.follow = QTimer(self)
        self.follow.setInterval(5000)
        self.follow.timeout.connect(self._follow_default)

    # -- session -------------------------------------------------------------
    def restore(self, state: dict) -> None:
        self.mode = state.get("mode") if state.get("mode") in MODES else MODES[0]
        self.sensitivity = min(SENS_MAX, max(SENS_MIN, float(state.get("sensitivity", 1.0))))
        self.hotreload_on = bool(state.get("hotreload", True))
        self.fullscreen_wanted = bool(state.get("fullscreen", False))
        self.aura_wanted = bool(state.get("aura", False))
        wanted = state.get("source")
        names = [n for n, _ in list_sources()]
        self.source = wanted if wanted in names else None      # None = AUTO: follow default output
        geo = state.get("geometry")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:
                pass
        self.tap.set_source(self.source)
        self.frame.start()
        self.idle.start()
        self.follow.start()
        if self.aura_wanted:
            QTimer.singleShot(300, self.toggle_aura)

    def aura_params(self) -> AuraParams:
        lv = self.levels
        return AuraParams(self.scene.hue, lv.loud, lv.bass, self.scene.flash, self.sensitivity)

    def toggle_aura(self) -> None:
        """AURA: every line, border and glyph on the whole screen glows on the beat."""
        if self.aura is not None and self.aura.isVisible():
            self.aura.stop()
        else:
            if self.aura is None:
                self.aura = AuraWindow(self.aura_params)
            self.aura.start()
        self._changed()

    def _follow_default(self) -> None:
        """AUTO: when he switches output devices, the tap moves with the default sink."""
        if self.source is None and self.tap.alive:
            want = default_monitor()
            if want and want != self.tap.source:
                self.tap.set_source(None)

    def state(self) -> dict:
        return {"mode": self.mode, "sensitivity": round(self.sensitivity, 3),
                "source": self.source, "fullscreen": self.isFullScreen(),
                "aura": bool(self.aura is not None and self.aura.isVisible()),
                "hotreload": self.hotreload_on,
                "geometry": bytes(self.saveGeometry()).hex()}

    def save(self) -> None:
        try:
            STATE.write_text(json.dumps(self.state(), indent=2))
        except OSError:
            pass

    def _changed(self) -> None:
        self.saver.start()

    def closeEvent(self, e) -> None:  # noqa: N802
        self.frame.stop()
        self.save()
        if self.aura is not None:
            self.aura.stop()
        self.tap.stop()
        super().closeEvent(e)

    # -- actions -------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._changed()

    def next_mode(self) -> None:
        self.set_mode(MODES[(MODES.index(self.mode) + 1) % len(MODES)])

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._changed()

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def toggle_hotreload(self) -> None:
        self.hotreload_on = not self.hotreload_on
        self._changed()

    def nudge_sensitivity(self, d: float) -> None:
        self.sensitivity = min(SENS_MAX, max(SENS_MIN, self.sensitivity + d))
        self._changed()

    def pick_source(self) -> None:
        sources = [("", "AUTO · follow the default output")] + list_sources()
        menu = SourceMenu(self, sources, self.source or "")
        anchor = self._bar_rect.topLeft() if self._bar_rect.isValid() else QPointF(20, 20)
        pos = self.mapToGlobal(QPointF(anchor.x() + 16, anchor.y() - menu.sizeHint().height() - 8).toPoint())
        menu.move(pos)
        menu.exec()
        if menu.choice is not None and menu.choice != (self.source or ""):
            self.source = menu.choice or None
            self.tap.set_source(self.source)
            self._changed()
        self._show_chrome()

    def _act(self, action: str) -> None:
        if action.startswith("mode:"):
            self.set_mode(action[5:])
        elif action == "fullscreen":
            self.toggle_fullscreen()
        elif action == "aura":
            self.toggle_aura()
        elif action == "source":
            self.pick_source()
        elif action == "hotreload":
            self.toggle_hotreload()
        elif action == "pause":
            self.toggle_pause()
        elif action == "min":
            self.showMinimized()
        elif action == "close":
            self.close()

    # -- chrome visibility ---------------------------------------------------
    def _show_chrome(self) -> None:
        self.chrome_target = 1.0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.idle.start()

    def _hide_chrome(self) -> None:
        if self._drag_slider or self._bar_rect.contains(QPointF(self.mapFromGlobal(QCursor.pos()))):
            self.idle.start()
            return
        self.chrome_target = 0.0
        if self.isFullScreen():
            self.setCursor(Qt.CursorShape.BlankCursor)

    # -- frame ---------------------------------------------------------------
    def _tick(self) -> None:
        now = time.monotonic()
        dt = min(0.05, now - self._last)
        self._last = now
        if not self.paused:
            self.levels = self.tap.latest
            self.scene.step(self.levels, dt, self.sensitivity, QRectF(self.rect()))
        step = theme.OPEN_STEP if self.chrome_target > self.chrome else theme.CLOSE_STEP
        self.chrome += (self.chrome_target - self.chrome) * step * 2.2
        if abs(self.chrome - self.chrome_target) < 0.01:
            self.chrome = self.chrome_target
        self.update()

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        self.scene.paint(p, rect, self.levels, self.mode, self.sensitivity)
        self._hits = []
        if self.chrome > 0.01:
            p.setOpacity(self.chrome)
            self._paint_title(p, rect)
            self._paint_bar(p, rect)
            p.setOpacity(1.0)
        p.end()

    def _paint_title(self, p: QPainter, rect: QRectF) -> None:
        strip = QRectF(rect.left(), rect.top(), rect.width(), TITLE_H)
        p.fillRect(strip, theme.alpha(theme.VOID, 0.9))
        p.fillRect(QRectF(strip.left(), strip.bottom() - 1, strip.width(), 1), QColor(theme.HAIRLINE))
        fit_text(p, QRectF(14, 0, 90, TITLE_H), "PARTY", 8, theme.BONE, True, 2.0)
        telemetry, color = self._telemetry()
        fit_text(p, QRectF(110, 0, rect.width() - 110 - 110, TITLE_H), telemetry, 8, color,
                 False, 1.2, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        x = rect.right() - 28
        for action, glyph in (("close", "x"), ("fullscreen", "full"), ("min", "min")):
            box = QRectF(x - 12, 3, 24, 24)
            self._glyph(p, box, glyph, theme.BAD if action == "close" else theme.MUTED)
            self._hits.append((box, action))
            x -= 30

    def _telemetry(self) -> tuple[str, str]:
        if self.tap.error:
            return f"NO AUDIO · {self.tap.error}", theme.BAD
        label = next((lbl for n, lbl in list_sources_cached() if n == self.tap.source), "…")
        parts = [("AUTO · " if self.source is None else "") + label, f"LOUD {int(self.levels.loud * 100):02d}%"]
        if self.levels.bpm:
            parts.append(f"{int(round(self.levels.bpm))} BPM")
        if self.paused:
            parts.append("PAUSED")
        if self.aura is not None and self.aura.isVisible():
            parts.append(self.aura.error or f"AURA {self.aura.fps}fps {self.aura.frame_ms:.1f}ms")
        return " · ".join(parts), theme.GOOD if self.tap.alive and not self.paused else theme.WARN

    def _paint_bar(self, p: QPainter, rect: QRectF) -> None:
        bar = QRectF(rect.left(), rect.bottom() - BAR_H, rect.width(), BAR_H)
        self._bar_rect = bar
        p.fillRect(bar, theme.alpha(theme.VOID, 0.9))
        p.fillRect(QRectF(bar.left(), bar.top(), bar.width(), 1), QColor(theme.HAIRLINE))
        chips = [("mode:PULSE", "pulse", "1"), ("mode:BARS", "bars", "2"), ("mode:ORBS", "orbs", "3"),
                 ("aura", "aura", "4"), ("fullscreen", "full", "F"), ("source", "source", "S"),
                 ("pause", "play" if self.paused else "pause", "SPC"),
                 ("hotreload", "reload", "R")]
        x = bar.left() + 16
        for action, glyph, key in chips:
            live = ((action.startswith("mode:") and action[5:] == self.mode)
                    or (action == "hotreload" and self.hotreload_on)
                    or (action == "aura" and self.aura is not None and self.aura.isVisible())
                    or (action == "pause" and self.paused))
            box = QRectF(x, bar.top() + 8, 40, 40)
            if live:
                p.fillRect(box, theme.alpha(theme.GOOD, 0.10))
                p.fillRect(QRectF(box.left(), box.bottom() - 2, box.width(), 2), QColor(theme.GOOD))
            color = theme.GOOD if live else (theme.BAD if action == "hotreload" else theme.MUTED)
            self._glyph(p, QRectF(box.left() + 8, box.top() + 4, 24, 24), glyph, color)
            fit_text(p, QRectF(box.left(), box.bottom() - 13, box.width(), 11), key, 7, theme.DIM,
                     True, 1.2, 6.5, Qt.AlignmentFlag.AlignCenter)
            self._hits.append((box, action))
            x += 48
        # sensitivity slider: the rest of the bar
        track = QRectF(x + 24, bar.center().y() - 1, max(60.0, bar.right() - x - 40), 2)
        self._slider_rect = QRectF(track.left() - 8, bar.top(), track.width() + 16, bar.height())
        p.fillRect(track, QColor(theme.FAINT))
        t = (self.sensitivity - SENS_MIN) / (SENS_MAX - SENS_MIN)
        kx = track.left() + track.width() * t
        p.fillRect(QRectF(track.left(), track.top(), kx - track.left(), 2), QColor(theme.GOOD))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.BONE))
        p.drawEllipse(QPointF(kx, track.center().y()), 5, 5)
        fit_text(p, QRectF(track.left(), bar.top() + 6, track.width(), 12),
                 f"SENSITIVITY {self.sensitivity:.1f}×  ↑↓", 7, theme.DIM, True, 1.6, 6.5,
                 Qt.AlignmentFlag.AlignCenter)

    def _glyph(self, p: QPainter, box: QRectF, kind: str, color: str) -> None:
        """1.8px line icons drawn in code (no icon fonts, no emoji in chrome)."""
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = box.center()
        r = box.width() / 2 - 3
        if kind == "pulse":
            p.drawEllipse(c, r, r)
            p.setBrush(QColor(color))
            p.drawEllipse(c, r * 0.4, r * 0.4)
        elif kind == "bars":
            for i, h in enumerate((0.45, 0.95, 0.65)):
                x = c.x() - r + i * r
                p.drawLine(QPointF(x, c.y() + r), QPointF(x, c.y() + r - 2 * r * h))
        elif kind == "orbs":
            for dx, dy, rr in ((-0.5, 0.3, 0.3), (0.45, -0.4, 0.42), (0.35, 0.5, 0.22)):
                p.drawEllipse(QPointF(c.x() + dx * r, c.y() + dy * r), rr * r, rr * r)
        elif kind == "aura":
            p.drawRect(QRectF(c.x() - r * 0.55, c.y() - r * 0.4, r * 1.1, r * 0.8))
            pen.setColor(theme.alpha(color, 0.45))
            p.setPen(pen)
            p.drawRoundedRect(QRectF(c.x() - r, c.y() - r * 0.85, r * 2, r * 1.7), 4, 4)
        elif kind == "full":
            for sx in (-1, 1):
                for sy in (-1, 1):
                    path = QPainterPath(QPointF(c.x() + sx * r, c.y() + sy * r * 0.45))
                    path.lineTo(QPointF(c.x() + sx * r, c.y() + sy * r))
                    path.lineTo(QPointF(c.x() + sx * r * 0.45, c.y() + sy * r))
                    p.drawPath(path)
        elif kind == "source":
            path = QPainterPath(QPointF(c.x() - r, c.y() - r * 0.35))
            path.lineTo(QPointF(c.x() - r * 0.35, c.y() - r * 0.35))
            path.lineTo(QPointF(c.x() + r * 0.2, c.y() - r))
            path.lineTo(QPointF(c.x() + r * 0.2, c.y() + r))
            path.lineTo(QPointF(c.x() - r * 0.35, c.y() + r * 0.35))
            path.lineTo(QPointF(c.x() - r, c.y() + r * 0.35))
            path.closeSubpath()
            p.drawPath(path)
            p.drawArc(QRectF(c.x() - r * 0.2, c.y() - r * 0.7, r * 1.4, r * 1.4), -60 * 16, 120 * 16)
        elif kind == "pause":
            p.drawLine(QPointF(c.x() - r * 0.4, c.y() - r), QPointF(c.x() - r * 0.4, c.y() + r))
            p.drawLine(QPointF(c.x() + r * 0.4, c.y() - r), QPointF(c.x() + r * 0.4, c.y() + r))
        elif kind == "play":
            path = QPainterPath(QPointF(c.x() - r * 0.6, c.y() - r))
            path.lineTo(QPointF(c.x() + r, c.y()))
            path.lineTo(QPointF(c.x() - r * 0.6, c.y() + r))
            path.closeSubpath()
            p.drawPath(path)
        elif kind == "reload":
            p.drawArc(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), 30 * 16, 300 * 16)
            p.drawLine(QPointF(c.x() + r * 0.85, c.y() - r * 0.55), QPointF(c.x() + r * 0.85, c.y() - r * 0.05))
            p.drawLine(QPointF(c.x() + r * 0.85, c.y() - r * 0.55), QPointF(c.x() + r * 0.35, c.y() - r * 0.55))
        elif kind == "x":
            p.drawLine(QPointF(c.x() - r * 0.7, c.y() - r * 0.7), QPointF(c.x() + r * 0.7, c.y() + r * 0.7))
            p.drawLine(QPointF(c.x() - r * 0.7, c.y() + r * 0.7), QPointF(c.x() + r * 0.7, c.y() - r * 0.7))
        elif kind == "min":
            p.drawLine(QPointF(c.x() - r * 0.7, c.y() + r * 0.6), QPointF(c.x() + r * 0.7, c.y() + r * 0.6))

    # -- input ---------------------------------------------------------------
    def _edges(self, pos: QPointF) -> Qt.Edge:
        edges = Qt.Edge(0)
        if self.isFullScreen():
            return edges
        if pos.x() <= EDGE:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= self.width() - EDGE:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= EDGE:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= self.height() - EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mousePressEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        pos = e.position()
        self._show_chrome()
        if e.button() != Qt.MouseButton.LeftButton:
            return
        edges = self._edges(pos)
        if edges:
            self.windowHandle().startSystemResize(edges)
            return
        if self.chrome > 0.3:
            for box, action in self._hits:
                if box.contains(pos):
                    self._act(action)
                    return
            if self._slider_rect.contains(pos):
                self._drag_slider = True
                self._slide(pos.x())
                return
        if pos.y() < TITLE_H and not self.isFullScreen():
            self.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        pos = e.position()
        if not any(box.contains(pos) for box, _ in self._hits) and not self._slider_rect.contains(pos):
            self.toggle_fullscreen()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:  # noqa: N802
        self._show_chrome()
        if self._drag_slider:
            self._slide(e.position().x())

    def mouseReleaseEvent(self, _e: QMouseEvent) -> None:  # noqa: N802
        self._drag_slider = False

    def _slide(self, x: float) -> None:
        track_l = self._slider_rect.left() + 8
        track_w = max(1.0, self._slider_rect.width() - 16)
        t = min(1.0, max(0.0, (x - track_l) / track_w))
        self.sensitivity = SENS_MIN + t * (SENS_MAX - SENS_MIN)
        self._changed()

    def wheelEvent(self, e) -> None:  # noqa: N802
        self.nudge_sensitivity(0.1 if e.angleDelta().y() > 0 else -0.1)
        self._show_chrome()

    def keyPressEvent(self, e: QKeyEvent) -> None:  # noqa: N802
        k = e.key()
        self._show_chrome()
        if k == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif k == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                self._changed()
        elif k == Qt.Key.Key_Space:
            self.toggle_pause()
        elif k in (Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3):
            self.set_mode(MODES[k - Qt.Key.Key_1])
        elif k == Qt.Key.Key_4:
            self.toggle_aura()
        elif k == Qt.Key.Key_M:
            self.next_mode()
        elif k == Qt.Key.Key_S:
            self.pick_source()
        elif k == Qt.Key.Key_R:
            self.toggle_hotreload()
        elif k in (Qt.Key.Key_Up, Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.nudge_sensitivity(0.1)
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_Minus):
            self.nudge_sensitivity(-0.1)
        elif k == Qt.Key.Key_Q:
            self.close()
        else:
            super().keyPressEvent(e)


_SOURCE_CACHE: tuple[float, list[tuple[str, str]]] = (0.0, [])


def list_sources_cached() -> list[tuple[str, str]]:
    """pactl once every 5 s at most — the title strip asks every frame."""
    global _SOURCE_CACHE
    now = time.monotonic()
    if now - _SOURCE_CACHE[0] > 5.0:
        _SOURCE_CACHE = (now, list_sources())
    return _SOURCE_CACHE[1]
