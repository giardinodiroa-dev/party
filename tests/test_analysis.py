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
    assert len(STORIES) >= 250 and len({k for k, _ in STORIES}) == 30
    s = Stories(every=(1, 2), seed=3)
    shots = [s.frame(t / 10) for t in range(400)]
    assert any(shots) and s.played >= 2


def test_brainwash_defaults(tmp_path):
    from party.brainwash import Brainwash
    b = Brainwash(tmp_path)
    assert (tmp_path / "phrases.txt").exists() and b.phrases
    items = [b.frame(t) for t in (3.5, 4.0, 5.0)]
    assert any(items)


def _window(tmp_path, monkeypatch):
    import os
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    monkeypatch.setenv("PARTY_STATE", str(tmp_path / "state.json"))
    from PyQt6.QtWidgets import QApplication
    global _APP
    _APP = QApplication.instance() or QApplication([])
    import party.ui.main_window as mw
    mw.STATE = tmp_path / "state.json"
    mw.PROFILES = tmp_path / "profiles"
    w = mw.MainWindow()
    _KEEP.append(w)
    return mw, w


_APP = None
_KEEP: list = []


def test_state_saves_atomically_to_env_path(tmp_path, monkeypatch):
    mw, w = _window(tmp_path, monkeypatch)
    w.aura_bright = 1.7
    w.aura_shape = 0
    w._changed()
    import json
    data = json.loads((tmp_path / "state.json").read_text())
    assert data["aura_bright"] == 1.7 and data["aura_shape"] == 0
    assert not (tmp_path / "state.json.tmp").exists()


def test_profile_round_trip(tmp_path, monkeypatch):
    mw, w = _window(tmp_path, monkeypatch)
    w.aura_color = 3; w.aura_border = 8; w.aura_bright = 0.6; w.aura_waves = 2
    w.save_profile("holy fire")
    assert "holy fire" in w.profile_names()
    w.aura_color = 0; w.aura_border = 0; w.aura_bright = 1.0; w.aura_waves = 0
    w.load_profile("holy fire")
    assert (w.aura_color, w.aura_border, w.aura_bright, w.aura_waves) == (3, 8, 0.6, 2)
    assert w.profile == "holy fire"


def test_constellations_are_real_patterns():
    from party.stories import CONSTELLATIONS, Constellations
    assert len(CONSTELLATIONS) == 10
    for name, _, stars, lines in CONSTELLATIONS:
        assert len(stars) >= 4 and all(0 <= a < len(stars) and 0 <= b < len(stars) for a, b in lines), name
    c = Constellations(seed=1); c.gap = 2.0
    assert any(c.frame(t / 10) for t in range(600))


def test_depth_paths_change_scale():
    from party.stories import Stories
    s = Stories(seed=5)
    scales = {round(x.scale, 2) for x in (s.frame(t / 10) for t in range(1500)) if x}
    assert min(scales) < 0.5 and max(scales) > 1.5


def test_settings_panel_binds_to_window(tmp_path, monkeypatch):
    mw, w = _window(tmp_path, monkeypatch)
    w.show()
    w.toggle_settings()
    assert w.settings.isVisible() and len(w.settings.families) > 10
    w.bar_fill = 0.7; w.aura_edges = 10; w.ledaie_color = -2
    w.settings.refresh()                      # widgets follow the window
    w.settings.tabs.setCurrentIndex(1)
    w.settings.close_panel()
    assert not w.settings.isVisible()
    import json
    w._changed()
    data = json.loads((tmp_path / "state.json").read_text())
    assert data["bar_fill"] == 0.7 and data["aura_edges"] == 10 and data["ledaie_color"] == -2


def test_stage_shows_one_thing_at_a_time():
    from party.scenes import Stage
    class Src:
        def __init__(self, dur): self.dur, self.t0, self.on = dur, None, False
        @property
        def active(self): return self.on
        def begin(self, t): self.t0, self.on = t, True
        def frame(self, t):
            if self.on and t - self.t0 >= self.dur: self.on = False
    srcs = {k: Src(3.0) for k in ("phrase", "story", "scene", "ledaie", "constellation", "image")}
    st = Stage(breath=2.0); seen = []
    for i in range(1200):
        t = i / 10
        on = st.tick(t, {k: True for k in srcs}, srcs)
        for s_ in srcs.values(): s_.frame(t)
        seen.append(on)
        assert sum(1 for s_ in srcs.values() if s_.active) <= 1
    names = [x for x in seen if x]
    assert len(set(names)) == 6 and any(x is None for x in seen[60:])
