import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from party.analysis import (BLOCK, RATE, Analyzer, AutoGain, BeatDetector,  # noqa: E402
                            Smoother, band, magnitudes, BASS, MID, TREBLE)


def sine(freq: float, amp: float = 0.8, n: int = BLOCK) -> np.ndarray:
    t = np.arange(n) / RATE
    mono = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([mono, mono], axis=1)


def test_bass_sine_lands_in_bass_band():
    mag = magnitudes(sine(60)[:, 0])
    assert band(mag, *BASS) > 5 * band(mag, *MID)
    assert band(mag, *BASS) > 5 * band(mag, *TREBLE)


def test_treble_sine_lands_in_treble_band():
    mag = magnitudes(sine(5000)[:, 0])
    assert band(mag, *TREBLE) > 5 * band(mag, *BASS)


def test_full_scale_sine_peaks_near_one():
    mag = magnitudes(sine(1000, amp=1.0)[:, 0])
    assert 0.8 < mag.max() < 1.2


def test_beat_fires_on_spike_then_cools_down():
    d = BeatDetector(history=20, cooldown=5)
    for _ in range(20):
        d.feed(0.01)
    assert d.feed(0.5) is True
    assert d.feed(0.5) is False          # cooldown
    for _ in range(5):
        d.feed(0.01)
    assert d.feed(0.5) is True


def test_beat_needs_history():
    d = BeatDetector(history=20)
    assert d.feed(1.0) is False


def test_bpm_from_regular_beats():
    d = BeatDetector(history=20, cooldown=3)
    period = 23                            # blocks ≈ 0.49 s ≈ 122 BPM
    for i in range(20 + period * 8):
        d.feed(1.0 if i >= 20 and (i - 20) % period == 0 else 0.001)
    assert 115 < d.bpm() < 130


def test_autogain_fills_range_at_any_volume():
    g = AutoGain()
    for _ in range(50):
        v = g.feed(0.02)
    assert v > 0.9


def test_smoother_rises_fast_falls_slow():
    s = Smoother(attack=0.6, release=0.08)
    up = s.feed(1.0)
    down = s.feed(0.0)
    assert up == 0.6
    assert down > 0.5


def test_analyzer_returns_levels_in_range():
    a = Analyzer()
    lv = None
    for _ in range(30):
        lv = a.feed(sine(80) + sine(4000, amp=0.2))
    assert lv is not None
    for v in (lv.bass, lv.mid, lv.treble, lv.loud):
        assert 0.0 <= v <= 1.0
    assert lv.spectrum.shape == (32,)
    assert lv.bass > lv.mid


def test_aura_intensity_is_bounded():
    from party.ui.aura import AuraParams
    assert AuraParams(loud=0, bass=0, flash=0, sensitivity=0.3).intensity() > 0.0
    assert AuraParams(loud=1, bass=1, flash=1, sensitivity=3.0).intensity() <= 1.6


def test_stories_table_and_scheduler():
    from party.stories import STORIES, Stories
    assert len(STORIES) == 200 and len({k for k, _ in STORIES}) == 20
    s = Stories(every=(1, 2), seed=3)
    shots = [s.frame(t / 10) for t in range(400)]
    assert any(shots) and s.played >= 2


def test_brainwash_defaults(tmp_path):
    from party.brainwash import Brainwash
    b = Brainwash(tmp_path)
    assert (tmp_path / "phrases.txt").exists() and b.phrases
    items = [b.frame(t) for t in (3.5, 4.0, 5.0)]
    assert any(items)
