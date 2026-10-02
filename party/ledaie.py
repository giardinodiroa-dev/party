"""Ledaie — his language — in the void: random dictionary words and handscript symbols.

Reads `~/ledaie/Ledaie - Dictionary.csv` (Conlang, Pronunciation, Definition, Synonyms, …).
Pure Python; the window renders the items with the Ledaie handscript font.
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

DICTIONARY = Path.home() / "ledaie" / "Ledaie - Dictionary.csv"


@dataclass
class Entry:
    word: str
    meaning: str          # short English: synonyms if present, else the definition's first clause


@dataclass
class Show:
    kind: str             # "symbol" | "word"
    word: str
    meaning: str
    x: float
    y: float
    alpha: float
    scale: float


def load(path: Path = DICTIONARY) -> list[Entry]:
    out: list[Entry] = []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                word = (row.get("Conlang") or "").strip()
                if not word:
                    continue
                syn = (row.get("Synonyms") or "").strip()
                defn = (row.get("Definition") or "").strip()
                meaning = syn or defn.split(".")[0]
                if len(meaning) > 70:
                    meaning = meaning[:67].rstrip() + "…"
                if not meaning:
                    continue                                   # no definition in the CSV yet: it waits until there is one
                out.append(Entry(word, meaning))
    except OSError:
        pass
    return out


class LedaieWords:
    """One item at a time, between the stories: a lone symbol, or a word with its English."""

    def __init__(self, entries: list[Entry] | None = None, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.entries = entries if entries is not None else load()
        self.gap = 20.0
        self.next_at = 9.0
        self.current: tuple[Entry, str, float, float, float, float] | None = None   # entry, kind, t0, dur, x, y
        self.auto = True

    @property
    def active(self) -> bool:
        return self.current is not None or getattr(self, "force", False)

    def begin(self, t: float) -> None:
        self.next_at = t
        self.force = True                     # start on the very next frame, whatever the clock says

    def frame(self, t: float) -> Show | None:
        if not self.entries:
            return None
        if self.current is None:
            if t >= self.next_at and (self.auto or getattr(self, "force", False)):
                self.force = False
                e = self.rng.choice(self.entries)
                kind = "symbol" if self.rng.random() < 0.4 else "word"
                self.current = (e, kind, t, self.rng.uniform(6.0, 9.0), self.rng.uniform(0.2, 0.8), self.rng.uniform(0.2, 0.7))
            return None
        e, kind, t0, dur, x, y = self.current
        u = (t - t0) / dur
        if u >= 1.0:
            self.current = None
            self.next_at = t + self.rng.uniform(self.gap * 0.6, self.gap * 1.4)
            return None
        fade = min(1.0, u * 4.0, (1.0 - u) * 4.0)
        return Show(kind, e.word, e.meaning, x, y - 0.03 * u, 0.5 * fade, 1.0 + 0.05 * u)
