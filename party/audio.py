"""The audio tap: `parec` on a PipeWire/Pulse source → Analyzer → the latest Levels.

Read-only. Nothing is rerouted or recorded; parec just copies what the sink is
playing (its `.monitor` source) into this process. Switching source restarts parec.
"""
from __future__ import annotations

import subprocess
import threading

import numpy as np

from .analysis import BLOCK, RATE, Analyzer, Levels

BYTES_PER_BLOCK = BLOCK * 2 * 4          # stereo float32


def _pactl(*args: str) -> str:
    try:
        return subprocess.run(["pactl", *args], capture_output=True, text=True,
                              timeout=3).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def list_sources() -> list[tuple[str, str]]:
    """[(name, label)] — monitors first, labelled OUT · …, inputs labelled MIC · …"""
    out: list[tuple[str, str]] = []
    name = desc = ""
    for line in _pactl("list", "sources").splitlines() + ["Source #end"]:
        s = line.strip()
        if s.startswith("Source #"):
            if name:
                kind = "OUT" if name.endswith(".monitor") else "MIC"
                label = desc.replace("Monitor of ", "") or name
                out.append((name, f"{kind} · {label}"))
            name = desc = ""
        elif s.startswith("Name: "):
            name = s[6:]
        elif s.startswith("Description: "):
            desc = s[13:]
    out.sort(key=lambda t: (not t[0].endswith(".monitor"), t[1]))
    return out


def default_monitor() -> str | None:
    sink = _pactl("get-default-sink").strip()
    names = [n for n, _ in list_sources()]
    if sink and f"{sink}.monitor" in names:
        return f"{sink}.monitor"
    return next((n for n in names if n.endswith(".monitor")), None)


class AudioTap:
    """Background reader. `latest` is always the newest Levels; `error` says why not."""

    def __init__(self, source: str | None = None) -> None:
        self.source = source
        self.latest = Levels()
        self.error = ""
        self.alive = False
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="party-audio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.terminate()
            except OSError:
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.alive = False

    def set_source(self, name: str | None) -> None:
        self.stop()
        self.source = name
        self.start()

    def _run(self) -> None:
        source = self.source or default_monitor()
        if not source:
            self.error = "no audio source: PipeWire exposes no monitor"
            return
        self.source = source
        cmd = ["parec", "-d", source, "--raw", "--format=float32le",
               f"--rate={RATE}", "--channels=2", "--latency-msec=20"]
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, bufsize=0)
        except OSError as exc:
            self.error = f"parec failed to start: {exc}"
            return
        proc = self._proc
        analyzer = Analyzer()
        self.error = ""
        self.alive = True
        buf = bytearray()
        try:
            while not self._stop.is_set():
                chunk = proc.stdout.read(BYTES_PER_BLOCK - len(buf))
                if not chunk:
                    break
                buf += chunk
                if len(buf) < BYTES_PER_BLOCK:
                    continue
                block = np.frombuffer(bytes(buf), dtype=np.float32).reshape(-1, 2)
                buf.clear()
                self.latest = analyzer.feed(block)
        finally:
            self.alive = False
            if not self._stop.is_set():
                err = ""
                try:
                    err = (proc.stderr.read() or b"").decode(errors="replace").strip()
                except Exception:
                    pass
                self.error = f"parec stopped on {source}: {err.splitlines()[-1] if err else 'stream ended'}"
