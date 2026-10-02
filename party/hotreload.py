"""Hot autoreload — the app comes back with a real code change, and only then.

Copied from ~/malkuth/malkuth/hotreload.py (founder's law 2026-09-18) with three
changes: the log lives at ~/party/.reload.log, the opt-out env is PARTY_NO_RELOAD,
and an `is_enabled` callable lets the in-app toggle pause it (house law 9).
Rules: CONTENT not mtime (files are hashed); it must COMPILE; NEVER while he is
using it (no restart within IDLE_GRACE of his last input). The re-exec carries
`--reloaded` so the window comes back without stealing focus.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QEvent, QFileSystemWatcher, QObject, QTimer

SETTLE_MS = 700
RECHECK_MS = 1500
IDLE_GRACE = 6.0
SUFFIXES = (".py",)


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*")
            if p.suffix in SUFFIXES and "__pycache__" not in p.parts]


def _digest(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in _files(root):
        try:
            out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            continue
    return out


def _compiles(root: Path) -> bool:
    for p in _files(root):
        try:
            compile(p.read_bytes(), str(p), "exec")
        except (SyntaxError, ValueError, OSError):
            return False
    return True


class _Activity(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.last = 0.0

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress,
                            QEvent.Type.MouseMove, QEvent.Type.Wheel):
            self.last = time.monotonic()
        return False


def install(app, window, watch: Path, is_enabled: Callable[[], bool] | None = None):
    if os.environ.get("PARTY_NO_RELOAD") == "1":
        return None
    is_enabled = is_enabled or (lambda: True)
    log_path = watch / ".reload.log"

    baseline = _digest(watch)
    activity = _Activity()
    app.installEventFilter(activity)

    watcher = QFileSystemWatcher(app)
    watcher.addPaths([str(watch)] + [str(p) for p in _files(watch)]
                     + [str(d) for d in watch.rglob("*")
                        if d.is_dir() and "__pycache__" not in d.parts])

    settle = QTimer(app)
    settle.setSingleShot(True)
    settle.setInterval(SETTLE_MS)

    def busy() -> bool:
        if getattr(window, "thread", None) is not None:
            return True
        focused = app.focusWidget()
        if focused is not None and any(
                focused.inherits(c) for c in ("QLineEdit", "QTextEdit", "QPlainTextEdit")):
            return True
        return (time.monotonic() - activity.last) < IDLE_GRACE

    def consider() -> None:
        nonlocal baseline
        current = _digest(watch)
        if current == baseline:
            return
        if not is_enabled():
            settle.start(RECHECK_MS * 4)        # toggle is off: hold the change
            return
        if not _compiles(watch):
            settle.start(RECHECK_MS)
            return
        if busy():
            settle.start(RECHECK_MS)
            return
        try:
            save = getattr(window, "save_session", None) or getattr(window, "save", None)
            if callable(save):
                save()
        except Exception:
            pass
        try:
            with open(log_path, "a") as fh:
                changed = [Path(k).name for k, v in current.items() if baseline.get(k) != v]
                fh.write("%s reloaded — %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                 ", ".join(changed) or "code change"))
        except Exception:
            pass
        args = [a for a in sys.argv[1:] if a != "--reloaded"] + ["--reloaded"]
        os.execv(sys.executable, [sys.executable, str(Path(sys.argv[0]).resolve())] + args)

    settle.timeout.connect(consider)

    def touched(_path: str) -> None:
        known = watcher.files() + watcher.directories()
        for p in [str(watch)] + [str(f) for f in _files(watch)]:
            if p not in known:
                watcher.addPath(p)
        settle.start(SETTLE_MS)

    watcher.fileChanged.connect(touched)
    watcher.directoryChanged.connect(touched)
    return watcher
