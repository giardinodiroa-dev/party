"""Pure signal analysis. No Qt, no audio device — headless-testable.

One block of stereo float32 frames in, one `Levels` out:
bass / mid / treble / loud in 0..1 (auto-gained so any volume fills the range),
a `beat` flag from the bass energy against its own recent history, a BPM guess,
and a 32-bin log-spaced spectrum for the Bars mode.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

RATE = 48000
BLOCK = 1024                 # frames per block (~21 ms at 48 kHz)
BLOCKS_PER_S = RATE / BLOCK
N_BINS = 32
BASS = (20.0, 150.0)
MID = (150.0, 2000.0)
TREBLE = (2000.0, 12000.0)

_WINDOW = np.hanning(BLOCK).astype(np.float32)
_FREQS = np.fft.rfftfreq(BLOCK, 1.0 / RATE)
_EDGES = np.geomspace(40.0, 16000.0, N_BINS + 1)
_BIN_MASKS = [(_FREQS >= lo) & (_FREQS < hi) for lo, hi in zip(_EDGES[:-1], _EDGES[1:])]


@dataclass
class Levels:
    bass: float = 0.0
    mid: float = 0.0
    treble: float = 0.0
    loud: float = 0.0
    beat: bool = False
    bpm: float = 0.0
    spectrum: np.ndarray = field(default_factory=lambda: np.zeros(N_BINS, dtype=np.float32))


def to_mono(block: np.ndarray) -> np.ndarray:
    block = np.asarray(block, dtype=np.float32)
    return block.mean(axis=1) if block.ndim == 2 else block


def magnitudes(mono: np.ndarray) -> np.ndarray:
    """Magnitude spectrum of one block, scaled so a full-scale sine peaks near 1.0."""
    x = np.zeros(BLOCK, dtype=np.float32)
    n = min(len(mono), BLOCK)
    x[:n] = mono[:n]
    return np.abs(np.fft.rfft(x * _WINDOW)) * (2.0 / float(_WINDOW.sum()))


def band(mag: np.ndarray, lo: float, hi: float) -> float:
    sel = mag[(_FREQS >= lo) & (_FREQS < hi)]
    return float(np.sqrt(np.mean(sel * sel))) if sel.size else 0.0


def binned(mag: np.ndarray) -> np.ndarray:
    out = np.zeros(N_BINS, dtype=np.float32)
    for i, m in enumerate(_BIN_MASKS):
        sel = mag[m]
        out[i] = float(sel.max()) if sel.size else 0.0
    return out


def rms(mono: np.ndarray) -> float:
    return float(np.sqrt(np.mean(mono * mono))) if mono.size else 0.0


class Smoother:
    """Envelope follower: quick up, slow down, so lights jump on hits and glide off."""

    def __init__(self, attack: float = 0.6, release: float = 0.08) -> None:
        self.attack, self.release, self.value = attack, release, 0.0

    def feed(self, x: float) -> float:
        k = self.attack if x > self.value else self.release
        self.value += (x - self.value) * k
        return self.value


class AutoGain:
    """Normalise to the recent peak so quiet playback still fills 0..1."""

    def __init__(self, decay: float = 0.9985, floor: float = 1e-3) -> None:
        self.decay, self.floor, self.peak = decay, floor, floor

    def feed(self, x: float) -> float:
        self.peak = max(x, self.peak * self.decay, self.floor)
        return min(1.0, x / self.peak)


class BeatDetector:
    """A beat is a bass-energy block clearly above its last ~second, with a cooldown."""

    def __init__(self, history: int = 43, cooldown: int = 7, ratio: float = 1.35,
                 floor: float = 1e-5) -> None:
        self.hist: deque[float] = deque(maxlen=history)
        self.cooldown, self.ratio, self.floor = cooldown, ratio, floor
        self.since = cooldown
        self.block = 0
        self.beats: deque[int] = deque(maxlen=12)

    def feed(self, energy: float) -> bool:
        self.block += 1
        self.since += 1
        beat = False
        if len(self.hist) >= self.hist.maxlen // 2:
            avg = sum(self.hist) / len(self.hist)
            beat = (energy > self.floor and energy > self.ratio * avg
                    and self.since >= self.cooldown)
        self.hist.append(energy)
        if beat:
            self.since = 0
            self.beats.append(self.block)
        return beat

    def bpm(self) -> float:
        if len(self.beats) < 4:
            return 0.0
        gaps = np.diff(np.array(self.beats, dtype=float))
        gaps = gaps[(gaps > 0)]
        if gaps.size == 0:
            return 0.0
        seconds = float(np.median(gaps)) / BLOCKS_PER_S
        bpm = 60.0 / seconds if seconds > 0 else 0.0
        while bpm > 180:          # fold double-time hits into a danceable range
            bpm /= 2
        return bpm if 50 <= bpm <= 180 else 0.0


class Analyzer:
    def __init__(self) -> None:
        self.band_gain = AutoGain()            # ONE gain for bass/mid/treble: balance survives
        self.loud_gain = AutoGain()
        self.spec_gain = AutoGain()
        self.smooth = {k: Smoother() for k in ("bass", "mid", "treble", "loud")}
        self.spec_smooth = np.zeros(N_BINS, dtype=np.float32)
        self.beats = BeatDetector()

    def feed(self, block: np.ndarray) -> Levels:
        mono = to_mono(block)
        mag = magnitudes(mono)
        raw = {"bass": band(mag, *BASS), "mid": band(mag, *MID), "treble": band(mag, *TREBLE)}
        beat = self.beats.feed(raw["bass"] * raw["bass"])
        self.band_gain.feed(max(raw.values()))
        out = {k: self.smooth[k].feed(min(1.0, v / self.band_gain.peak)) for k, v in raw.items()}
        out["loud"] = self.smooth["loud"].feed(self.loud_gain.feed(rms(mono)))
        spec = binned(mag)
        self.spec_gain.feed(float(spec.max()))
        spec = np.clip(spec / self.spec_gain.peak, 0, 1)
        self.spec_smooth += (spec - self.spec_smooth) * np.where(spec > self.spec_smooth, 0.6, 0.12)
        return Levels(out["bass"], out["mid"], out["treble"], out["loud"], beat,
                      self.beats.bpm(), self.spec_smooth.copy())
