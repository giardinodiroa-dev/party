"""The settings panel: a voidblack side panel INSIDE the Party window (house law: pop-ups live
inside the app). Every control is bound live to the window — change it, see it, it is saved.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget)

from .. import theme
from .aura import BORDER_STYLES, COLOR_MODES, PHRASE_ANIMS, PHRASE_FONT_NAMES, WAVE_STYLES
from .visuals import MODES

QSS = f"""
QWidget#settings {{ background: {theme.PANEL}; border-left: 1px solid {theme.HAIRLINE}; }}
QWidget#settings QLabel {{ color: {theme.TEXT}; font-family: {theme.FONT_CSS}; font-size: 10px; }}
QWidget#settings QLabel#title {{ color: {theme.BONE}; font-size: 11px; font-weight: bold; letter-spacing: 2px; }}
QWidget#settings QLabel#hint {{ color: {theme.DIM}; font-size: 9px; }}
QTabWidget::pane {{ border: 0; background: {theme.PANEL}; }}
QTabBar::tab {{ background: {theme.PANEL}; color: {theme.MUTED}; padding: 6px 9px; font-family: {theme.FONT_CSS};
               font-size: 9px; letter-spacing: 1.4px; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {theme.GOOD}; border-bottom: 2px solid {theme.GOOD}; }}
QScrollArea {{ border: 0; background: {theme.PANEL}; }}
QScrollArea > QWidget > QWidget {{ background: {theme.PANEL}; }}
QComboBox {{ background: {theme.RAISED}; color: {theme.BONE}; border: 1px solid {theme.HAIRLINE}; border-radius: 4px;
            padding: 4px 8px; font-family: {theme.FONT_CSS}; font-size: 10px; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox QAbstractItemView {{ background: {theme.PANEL}; color: {theme.TEXT}; selection-background-color: {theme.SELECT};
                              border: 1px solid {theme.HAIRLINE}; font-family: {theme.FONT_CSS}; font-size: 10px; }}
QSlider::groove:horizontal {{ height: 2px; background: {theme.FAINT}; }}
QSlider::sub-page:horizontal {{ background: {theme.GOOD}; }}
QSlider::handle:horizontal {{ width: 10px; height: 10px; margin: -4px 0; border-radius: 5px; background: {theme.BONE}; }}
QCheckBox {{ color: {theme.TEXT}; font-family: {theme.FONT_CSS}; font-size: 10px; spacing: 8px; }}
QCheckBox::indicator {{ width: 12px; height: 12px; border: 1px solid {theme.HAIRLINE}; border-radius: 2px; background: {theme.RAISED}; }}
QCheckBox::indicator:checked {{ background: {theme.GOOD}; border-color: {theme.GOOD}; }}
QLineEdit {{ background: {theme.RAISED}; color: {theme.BONE}; border: 1px solid {theme.HAIRLINE}; border-radius: 4px;
            padding: 5px 8px; font-family: {theme.FONT_CSS}; font-size: 10px; }}
QPushButton {{ background: {theme.PANEL}; color: {theme.MUTED}; border: 1px solid {theme.HAIRLINE}; border-radius: 4px;
              padding: 5px 10px; font-family: {theme.FONT_CSS}; font-size: 9px; letter-spacing: 1.2px; }}
QPushButton:hover {{ color: {theme.BONE}; border-color: {theme.SELECT}; }}
QPushButton#danger {{ color: {theme.BAD}; }}
QListWidget {{ background: {theme.PANEL}; color: {theme.TEXT}; border: 1px solid {theme.HAIRLINE}; font-family: {theme.FONT_CSS};
              font-size: 10px; }}
QListWidget::item:selected {{ background: {theme.SELECT}; color: {theme.BONE}; }}
QScrollBar:vertical {{ background: {theme.PANEL}; width: 6px; }}
QScrollBar::handle:vertical {{ background: {theme.HAIRLINE}; border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""
WIDTH = 400
SIZES = ["S", "M", "L", "XL"]


class SettingsPanel(QWidget):
    def __init__(self, win) -> None:
        super().__init__(win)
        self.win = win
        self.setObjectName("settings")
        self.setStyleSheet(QSS)
        self._syncing = False
        self._binders: list = []
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel("PARTY · SETTINGS"); title.setObjectName("title")
        close = QPushButton("ESC · CLOSE"); close.clicked.connect(self.close_panel)
        head.addWidget(title); head.addStretch(1); head.addWidget(close)
        root.addLayout(head)
        hint = QLabel("every change applies at once and is saved · profiles keep a whole look"); hint.setObjectName("hint")
        hint.setWordWrap(True); root.addWidget(hint)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)
        self.families = sorted(QFontDatabase.families())
        self._build_look()
        self._build_bars()
        self._build_brainwash()
        self._build_stories()
        self._build_images()
        self._build_profiles()
        self.hide()

    # -- building blocks -----------------------------------------------------
    def _tab(self, name: str) -> QFormLayout:
        area = QScrollArea(); area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(); body.setMinimumWidth(0); form = QFormLayout(body)
        form.setContentsMargins(4, 8, 8, 8); form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        area.setWidget(body)
        self.tabs.addTab(area, name)
        return form

    def _set(self, attr: str, value) -> None:
        if self._syncing:
            return
        setattr(self.win, attr, value)
        self.win._changed()

    def combo(self, form: QFormLayout, label: str, attr: str, options: list, values: list | None = None) -> QComboBox:
        values = values if values is not None else list(range(len(options)))
        box = QComboBox(); box.addItems([str(o) for o in options]); box.setMaxVisibleItems(14)
        box.setMinimumWidth(80); box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        box.currentIndexChanged.connect(lambda i: self._set(attr, values[i]))
        form.addRow(label, box)
        self._binders.append(lambda: box.setCurrentIndex(values.index(getattr(self.win, attr)) if getattr(self.win, attr) in values else 0))
        return box

    def slider(self, form: QFormLayout, label: str, attr: str, lo: float, hi: float, step: float, fmt: str = "{:.1f}") -> None:
        row = QHBoxLayout(); s = QSlider(Qt.Orientation.Horizontal); val = QLabel(); val.setFixedWidth(44)
        n = int(round((hi - lo) / step)); s.setRange(0, n)
        def on(i):
            v = lo + i * step; val.setText(fmt.format(v)); self._set(attr, round(v, 3))
        s.valueChanged.connect(on)
        row.addWidget(s, 1); row.addWidget(val); form.addRow(label, row)
        def sync():
            v = float(getattr(self.win, attr)); s.setValue(int(round((v - lo) / step))); val.setText(fmt.format(v))
        self._binders.append(sync)

    def check(self, form: QFormLayout, label: str, attr: str, action=None) -> None:
        c = QCheckBox(label)
        def on(b):
            if self._syncing:
                return
            if action:
                action()
            else:
                self._set(attr, bool(b))
        c.toggled.connect(on)
        form.addRow("", c)
        self._binders.append(lambda: c.setChecked(bool(getattr(self.win, attr))))

    def font(self, form: QFormLayout, label: str, attr: str, presets: list[str]) -> None:
        opts = presets + self.families
        self.combo(form, label, attr, opts, opts)

    def colour(self, form: QFormLayout, label: str, attr_mode: str, attr_custom: str) -> None:
        self.combo(form, label, attr_mode, ["CUSTOM"] + COLOR_MODES, [-2] + list(range(len(COLOR_MODES))))
        for i, (name, lo, hi, step) in enumerate((("hue", 0, 360, 2), ("light", 0.05, 0.98, 0.01))):
            row = QHBoxLayout(); s = QSlider(Qt.Orientation.Horizontal); val = QLabel(); val.setFixedWidth(44)
            s.setRange(0, int(round((hi - lo) / step)))
            def on(k, i=i, s=s, val=val, lo=lo, step=step):
                v = lo + k * step; val.setText(f"{v:.0f}" if i == 0 else f"{v:.2f}")
                if self._syncing:
                    return
                cur = list(getattr(self.win, attr_custom)); cur[i] = v
                setattr(self.win, attr_custom, tuple(cur)); self.win._changed()
            s.valueChanged.connect(on)
            row.addWidget(s, 1); row.addWidget(val); form.addRow(f"   custom {name}", row)
            def sync(i=i, s=s, val=val, lo=lo, step=step):
                v = float(getattr(self.win, attr_custom)[i]); s.setValue(int(round((v - lo) / step))); val.setText(f"{v:.0f}" if i == 0 else f"{v:.2f}")
            self._binders.append(sync)

    # -- tabs ----------------------------------------------------------------
    def _build_look(self) -> None:
        f = self._tab("LOOK")
        self.combo(f, "canvas mode", "mode", MODES, MODES)
        self.slider(f, "sensitivity", "sensitivity", 0.3, 3.0, 0.1, "{:.1f}×")
        self.check(f, "AURA on (glow over every app)", "aura_wanted", action=self.win.toggle_aura)
        self.combo(f, "colour world", "aura_color", COLOR_MODES)
        self.combo(f, "border style", "aura_border", BORDER_STYLES)
        self.slider(f, "aura width", "aura_width", 0.5, 6.0, 0.1)
        self.slider(f, "brightness", "aura_bright", 0.2, 2.5, 0.1)
        self.check(f, "bold (paint the strokes too)", "aura_bold")
        self.check(f, "stars and orbs", "aura_astral")
        self.check(f, "nebula and ghost party", "aura_ghost")
        self.check(f, "black-hole cursor", "aura_lens")
        self.check(f, "hot reload on code change", "hotreload_on")

    def _build_bars(self) -> None:
        f = self._tab("BARS")
        self.combo(f, "style", "aura_waves", WAVE_STYLES)
        self.combo(f, "shape", "aura_shape", ["WAVE", "BARS"])
        self.combo(f, "colour", "aura_barcolor", ["STYLE"] + COLOR_MODES, [-1] + list(range(len(COLOR_MODES))))
        self.slider(f, "height", "bar_height", 0.03, 0.30, 0.01, "{:.0%}")
        self.slider(f, "slimness", "bar_fill", 0.15, 0.95, 0.05, "{:.0%}")
        for bit, name in ((1, "bottom edge"), (2, "top edge"), (4, "left edge"), (8, "right edge")):
            c = QCheckBox(name)
            def on(b, bit=bit):
                if self._syncing:
                    return
                self.win.aura_edges = (self.win.aura_edges | bit) if b else (self.win.aura_edges & ~bit)
                self.win._changed()
            c.toggled.connect(on); f.addRow("", c)
            self._binders.append(lambda c=c, bit=bit: c.setChecked(bool(self.win.aura_edges & bit)))

    def _build_brainwash(self) -> None:
        f = self._tab("BRAINWASH")
        self.check(f, "brainwash phrases and pictures", "aura_brainwash")
        self.slider(f, "phrase every", "phrase_gap", 1.0, 60.0, 1.0, "{:.0f}s")
        self.font(f, "font", "phrase_font", PHRASE_FONT_NAMES)
        self.colour(f, "colour", "phrase_color", "phrase_custom")
        self.combo(f, "size", "phrase_size", SIZES)
        self.combo(f, "motion", "phrase_anim", PHRASE_ANIMS)
        hint = QLabel("phrases: ~/party/brainwash/phrases.txt (a * in front = favourite) · pictures: ~/party/brainwash/images/")
        hint.setObjectName("hint"); hint.setWordWrap(True); f.addRow(hint)

    def _build_stories(self) -> None:
        f = self._tab("STORIES")
        self.check(f, "stories in the void", "aura_stories")
        self.slider(f, "story every", "story_gap", 3.0, 120.0, 1.0, "{:.0f}s")
        self.check(f, "real constellations", "constellations_on")
        self.check(f, "Ledaie words and symbols", "ledaie_on")
        self.font(f, "Ledaie text font", "ledaie_font", PHRASE_FONT_NAMES)
        self.colour(f, "Ledaie colour", "ledaie_color", "ledaie_custom")
        self.font(f, "caption font", "caption_font", PHRASE_FONT_NAMES)
        self.colour(f, "caption colour", "caption_color", "caption_custom")

    def _build_images(self) -> None:
        """Every actor with BOTH its drawing and its painting, and his choice: DRAWING / PAINTING / HIDDEN.
        Hidden never appears; nothing is deleted. A button fetches the missing paintings (Pollinations)."""
        from pathlib import Path as _P
        from ..art import Art
        from ..stories import STORIES
        from .sprites import draw_sprite, black_keyed
        from .ghibli import render
        from PyQt6.QtGui import QImage
        self.art = Art(_P(__file__).resolve().parents[2] / "art", fetch=False)
        area = QScrollArea(); area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget(); body.setMinimumWidth(0); grid = QGridLayout(body); grid.setSpacing(6)
        self.tabs.addTab(area, "IMAGES"); area.setWidget(body)
        style = QComboBox(); style.addItems(["ASTRAL  (glowing line art)", "CUTE  (the anime drawings)"])
        style.currentIndexChanged.connect(lambda i: (self._set("sprite_style", ("ASTRAL", "CUTE")[i]), self._rethumb()))
        self._binders.append(lambda: style.setCurrentIndex(1 if self.win.sprite_style == "CUTE" else 0))
        grid.addWidget(QLabel("drawing style"), 0, 0); grid.addWidget(style, 0, 1, 1, 2)
        fetch = QPushButton("FETCH MISSING PAINTINGS"); self.fetch_status = QLabel(""); self.fetch_status.setObjectName("hint")
        fetch.clicked.connect(self._fetch); grid.addWidget(fetch, 1, 0, 1, 2); grid.addWidget(self.fetch_status, 1, 2)
        hint = QLabel("left: drawing · right: painting (edges fade, no box) · pick what appears, or HIDDEN · files stay in ~/party/assets/sprites and ~/party/art")
        hint.setObjectName("hint"); hint.setWordWrap(True); grid.addWidget(hint, 2, 0, 1, 3)
        self._cards: dict[str, tuple[QLabel, QLabel, QComboBox]] = {}
        for i, kind in enumerate(sorted({k for k, _ in STORIES})):
            card = QWidget(); col = QVBoxLayout(card); col.setContentsMargins(2, 4, 2, 4); col.setSpacing(3)
            row = QHBoxLayout(); d = QLabel(); d.setFixedSize(64, 64); p_ = QLabel(); p_.setFixedSize(64, 64)
            for lab in (d, p_):
                lab.setAlignment(Qt.AlignmentFlag.AlignCenter); lab.setStyleSheet(f"border: 1px solid {theme.HAIRLINE}; background: {theme.VOID};")
            row.addWidget(d); row.addWidget(p_); col.addLayout(row)
            name = QLabel(kind); name.setAlignment(Qt.AlignmentFlag.AlignCenter); col.addWidget(name)
            choice = QComboBox(); choice.addItems(["DRAWING", "PAINTING", "HIDDEN"])
            def on(ix, kind=kind):
                if self._syncing:
                    return
                self.win.sources[kind] = ("drawing", "painting", "hidden")[ix]; self.win._changed()
            choice.currentIndexChanged.connect(on); col.addWidget(choice)
            self._binders.append(lambda choice=choice, kind=kind: choice.setCurrentIndex(
                ("drawing", "painting", "hidden").index(self.win.sources.get(kind, "drawing"))))
            self._cards[kind] = (d, p_, choice)
            grid.addWidget(card, 3 + i // 2, i % 2)
        self._rethumb()

    def _rethumb(self) -> None:
        from .sprites import draw_sprite, black_keyed
        from .ghibli import render
        from PyQt6.QtGui import QImage
        for kind, (d, p_, _) in self._cards.items():
            img = render(kind, 64) if self.win.sprite_style == "CUTE" else draw_sprite(kind).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            d.setPixmap(QPixmap.fromImage(img) if img is not None else QPixmap())
            f = self.art.pick(kind)
            if f:
                src = QImage(str(f)); src = src.copy(0, 0, src.width(), int(src.height() * 0.88))
                p_.setPixmap(QPixmap.fromImage(black_keyed(src).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
                p_.setToolTip(str(f))
            else:
                p_.setText("none\nyet"); p_.setStyleSheet(f"border: 1px dashed {theme.HAIRLINE}; color: {theme.GHOST}; font-size: 9px;")

    def _fetch(self) -> None:
        """Fetch on a thread; the UI is only touched from the Qt thread (a timer polls)."""
        import threading
        from PyQt6.QtCore import QTimer
        self.fetch_status.setText("fetching… (a few per minute on the free tier)")
        self._fetch_done = False
        def run():
            self.art._fetch_missing(pause=3.0)
            self._fetch_done = True
        threading.Thread(target=run, daemon=True).start()
        def poll():
            if not self._fetch_done:
                QTimer.singleShot(1000, poll); return
            left = len(self.art.missing())
            why = f" ({next(iter(self.art.failed.values()))})" if self.art.failed and left else ""
            self.fetch_status.setText(f"done — {left} still missing{why}")
            self._rethumb()
        QTimer.singleShot(1000, poll)

    def _build_profiles(self) -> None:
        f = self._tab("PROFILES")
        row = QHBoxLayout(); self.name = QLineEdit(); self.name.setPlaceholderText("name this look…")
        save = QPushButton("SAVE"); save.clicked.connect(self._save)
        row.addWidget(self.name, 1); row.addWidget(save); f.addRow("save as", row)
        self.list = QListWidget(); self.list.itemClicked.connect(lambda it: (self.win.load_profile(it.text()), self.refresh()))
        f.addRow("load", self.list)
        hint = QLabel("a profile keeps the whole look: modes, colours, borders, bars, text, pace."); hint.setObjectName("hint")
        hint.setWordWrap(True); f.addRow(hint)

    def _save(self) -> None:
        name = self.name.text().strip() or self.win.profile
        if name:
            self.win.save_profile(name); self.refresh()

    # -- life ----------------------------------------------------------------
    def refresh(self) -> None:
        self._syncing = True
        try:
            for b in self._binders:
                b()
            self.list.clear(); self.list.addItems(self.win.profile_names())
            self.name.setText(self.win.profile)
        finally:
            self._syncing = False

    def place(self) -> None:
        w = min(WIDTH, int(self.win.width() * 0.6))
        self.setGeometry(self.win.width() - w, 0, w, self.win.height())

    def open_panel(self) -> None:
        self.refresh(); self.place(); self.show(); self.raise_()

    def close_panel(self) -> None:
        self.hide(); self.win.setFocus()
