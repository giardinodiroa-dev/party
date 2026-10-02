"""voidblack-luxury — the house theme. One file, copy it into any PyQt6 app.

Canonical copy + the written guidelines live in
~/.claude/skills/app-taxonomy/voidblack-luxury/ (theme.py, GUIDELINES.md).

The idea in one line: a black instrument that only lights up where there is
information. Ground is void; light is meaning; motion is short and always eased.
Everything below is a token — apps never hard-code a colour, a font or a timing.
"""
from __future__ import annotations

from PyQt6.QtGui import QColor, QFont

# -- ground & ink ------------------------------------------------------------
VOID = "#07070a"          # the ground. Windows, overlays, everything starts here
PANEL = "#0c0c11"         # one step up: menus, toolbars, buttons
RAISED = "#101017"        # two steps up: inputs, the most a surface may lighten
HAIRLINE = "#1b1b24"      # 1px borders and separators
FAINT = "#2a2833"         # guide lines, empty tracks, bezel ticks
BONE = "#efe8da"          # emphasised text — warm, never pure white
TEXT = "#cfc9be"          # body text
MUTED = "#8f8a80"         # secondary text
DIM = "#6b665d"           # captions, hints, legends
GHOST = "#4d4a44"         # disabled
SELECT = "#3a3550"        # selection / neutral accent when nothing is live

# -- signal colours: they MEAN something, never decorate ----------------------
GOOD = "#5ee3b0"          # live, success, primary focus ring
WARN = "#ffb45e"          # degraded, caution, low
BAD = "#ff5e6e"           # failure, destructive, off
INFO = "#5eb8ff"          # actions in flight, commands, links

# -- entity accents: one colour per thing, stable for its whole life ----------
ACCENTS = ["#5ee3b0", "#5eb8ff", "#c58eff", "#ff7eb6",
           "#ffb45e", "#e8e36a", "#5ee3e3", "#ff8a5e"]

# -- type --------------------------------------------------------------------
FONT_FAMILIES = ["JetBrains Mono", "Hack", "DejaVu Sans Mono", "monospace"]
FONT_CSS = "'JetBrains Mono','Hack','DejaVu Sans Mono',monospace"

# -- motion (seconds unless noted) --------------------------------------------
FRAME_MS = 16             # one animation clock per surface, ~60fps, stopped when hidden
OPEN_STEP = 0.11          # per-frame growth of an overlay: ~150ms, ease-OUT cubic
CLOSE_STEP = 0.15         # per-frame decay: ~110ms, ease-IN — leaving is quicker than arriving
HOVER_LERP = 0.28         # per-frame approach of hover lift toward its target
HOVER_LIFT_PX = 14        # how far a hovered segment travels outward
PULSE_HZ = 3.2            # rad/s of the "alive" breathing on live things
SPIN_DEG_S = 300.0        # busy spinner speed
FLASH_S = 1.2             # success/failure colour flash on the hub
OK_HOLD_S = 1.6           # a success message stays this long
FAIL_HOLD_S = 30.0        # a failure stays until dismissed — never auto-hide bad news
CLOSE_AFTER_OK_MS = 1100  # overlay lingers this long after success, then leaves


def ease_out(t: float) -> float:
    """Arrivals: fast then settling. t in 0..1."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t: float) -> float:
    """Departures: gentle start, decisive finish. t in 0..1."""
    t = max(0.0, min(1.0, t))
    return t * t


def alpha(color, a: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


def font(size: float, bold: bool = False, spacing: float = 0.0) -> QFont:
    """Mono everywhere. Letter-spacing (1.2–2.2px) marks labels and headings."""
    f = QFont()
    f.setFamilies(FONT_FAMILIES)
    f.setPointSizeF(size)
    f.setBold(bold)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def assign_accents(keys: list[str]) -> dict[str, str]:
    """Stable accent per key (hex-pair ids like MACs hash well); collisions walk on."""
    out: dict[str, str] = {}
    used: set[int] = set()
    for key in keys:
        try:
            seed = sum(int(b, 16) for b in key.split(":") if b)
        except ValueError:
            seed = sum(key.encode())
        idx = seed % len(ACCENTS)
        for _ in range(len(ACCENTS)):
            if idx not in used:
                break
            idx = (idx + 1) % len(ACCENTS)
        used.add(idx)
        out[key] = ACCENTS[idx]
    return out


def level_color(pct: int) -> QColor:
    """Battery / quota / health: green, amber under 35, red under 15."""
    return QColor(BAD if pct <= 15 else WARN if pct <= 35 else GOOD)


# -- stylesheets ---------------------------------------------------------------
def menu_qss() -> str:
    return f"""
QMenu {{ background: {PANEL}; color: {TEXT}; border: 1px solid {HAIRLINE};
        font-family: {FONT_CSS}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px 5px 18px; }}
QMenu::item:selected {{ background: #1b1b28; color: {BONE}; }}
QMenu::item:disabled {{ color: {GHOST}; }}
QMenu::separator {{ height: 1px; background: {HAIRLINE}; margin: 4px 8px; }}
"""


def panel_qss(root: str = "QWidget") -> str:
    """A voidblack-luxury tool window: transcript, inputs, quiet buttons, thin scrollbars."""
    return f"""
{root} {{ background: {VOID}; color: {TEXT}; }}
QLabel#title {{ color: {BONE}; font-family: {FONT_CSS}; font-size: 11px;
               font-weight: bold; letter-spacing: 2px; }}
QLabel#status {{ color: {DIM}; font-family: {FONT_CSS}; font-size: 10px; }}
QTextBrowser, QPlainTextEdit, QListWidget {{ background: {VOID}; color: {TEXT}; border: 0;
               font-family: {FONT_CSS}; font-size: 12px; selection-background-color: {SELECT}; }}
QLineEdit {{ background: {RAISED}; color: {BONE}; border: 1px solid {HAIRLINE};
            border-radius: 4px; padding: 9px 10px; font-family: {FONT_CSS}; font-size: 12px; }}
QLineEdit:focus {{ border: 1px solid {GOOD}; }}
QPushButton {{ background: {PANEL}; color: {MUTED}; border: 1px solid {HAIRLINE};
              border-radius: 4px; padding: 5px 10px; font-family: {FONT_CSS}; font-size: 10px; }}
QPushButton:hover {{ color: {BONE}; border: 1px solid {SELECT}; }}
QPushButton#danger {{ color: {BAD}; }}
QScrollBar:vertical {{ background: {VOID}; width: 8px; }}
QScrollBar::handle:vertical {{ background: {HAIRLINE}; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
""" + menu_qss()
