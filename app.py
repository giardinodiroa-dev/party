#!/usr/bin/env python3
"""Party — lights that move with whatever the laptop is playing. Run: party"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from party import theme  # noqa: E402
from party.ui.main_window import STATE, MainWindow  # noqa: E402

ASSETS = ROOT / "assets"


def dark_palette() -> QPalette:
    p = QPalette()
    C = QColor
    R, G = QPalette.ColorRole, QPalette.ColorGroup
    p.setColor(R.Window, C(theme.VOID))
    p.setColor(R.WindowText, C(theme.TEXT))
    p.setColor(R.Base, C(theme.RAISED))
    p.setColor(R.AlternateBase, C(theme.PANEL))
    p.setColor(R.ToolTipBase, C(theme.PANEL))
    p.setColor(R.ToolTipText, C(theme.TEXT))
    p.setColor(R.Text, C(theme.TEXT))
    p.setColor(R.Button, C(theme.PANEL))
    p.setColor(R.ButtonText, C(theme.TEXT))
    p.setColor(R.Highlight, C(theme.SELECT))
    p.setColor(R.HighlightedText, C(theme.BONE))
    p.setColor(R.PlaceholderText, C("#5b564e"))
    for r in (R.Text, R.ButtonText, R.WindowText):
        p.setColor(G.Disabled, r, C(theme.GHOST))
    return p


def app_icon() -> QIcon:
    icon = QIcon()
    for png in sorted(ASSETS.glob("icon-*.png")):
        icon.addFile(str(png))
    if icon.isNull() and (ASSETS / "icon.png").exists():
        icon.addFile(str(ASSETS / "icon.png"))
    if icon.isNull() and (ASSETS / "icon.svg").exists():
        icon.addFile(str(ASSETS / "icon.svg"))
    return icon


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("Party")
    app.setApplicationDisplayName("Party")
    app.setStyle("Fusion")
    app.setPalette(dark_palette())
    app.setWindowIcon(app_icon())
    app.setDesktopFileName("party")

    window = MainWindow()
    state = {}
    try:
        state = json.loads(STATE.read_text())
    except Exception:
        pass
    window.restore(state)
    if "--reloaded" in argv:                      # come back without stealing focus
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    if window.fullscreen_wanted:
        window.showFullScreen()
    else:
        window.show()

    from party.hotreload import install as install_hotreload
    install_hotreload(app, window, ROOT, is_enabled=lambda: window.hotreload_on)

    # Never close without saving: a kill signal closes the window (which saves), then quits.
    import signal
    from PyQt6.QtCore import QTimer
    def _bye(*_a):
        window.close()
        app.quit()
    signal.signal(signal.SIGTERM, _bye)
    signal.signal(signal.SIGINT, _bye)
    tick = QTimer(); tick.start(300); tick.timeout.connect(lambda: None)   # lets Python run signal handlers
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
