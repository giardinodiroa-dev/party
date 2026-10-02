"""Brainwash: his own phrases and pictures, surfacing faintly in the void.

`~/party/brainwash/phrases.txt` — one phrase per line (a starter set is written on
first run; after that the file is his and code never rewrites it). `*` in front of a
line makes it a favourite, shown four times as often. `~/party/brainwash/images/` — any png/jpg he drops there. Pure Python:
the window turns `Item`s into textured quads.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PHRASES = [
    "you go king", "you can do this", "you will make it", "you are already on your way",
    "everything you build is real", "breathe, then build", "one more step, then another",
    "the work is the magic", "you were made for this", "keep going", "it is working",
    "today counts", "you are not alone", "the void is on your side", "nothing is impossible here",
    "rest is part of the work", "you are enough", "finish it", "they will see", "trust the column",
    "your hands know", "light is meaning", "this is the good part", "amen",
]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class Item:
    kind: str          # "text" | "image"
    payload: str       # the phrase, or the image path
    x: float
    y: float
    scale: float
    alpha: float


class Brainwash:
    def __init__(self, root: Path, seed: int | None = None) -> None:
        self.root = root
        self.rng = random.Random(seed)
        self.phrases: list[str] = []
        self.images: list[str] = []
        self.next_text = 3.0
        self.next_image = 15.0
        self.gap = 5.0                      # his setting: seconds between phrases (±40%); images every 4 gaps
        self.text: tuple[str, float, float, float, float] | None = None     # phrase, t0, dur, x, y
        self.image: tuple[str, float, float, float, float] | None = None
        self.auto = True                      # False: the stage calls begin(kind, t); never self-starts
        self.reload()

    @property
    def active(self) -> bool:
        return self.text is not None or self.image is not None

    def begin(self, kind: str, t: float) -> None:
        if kind == "image":
            self.next_image = t; self.force_image = True
        else:
            self.next_text = t; self.force_text = True

    def reload(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "images").mkdir(exist_ok=True)
        f = self.root / "phrases.txt"
        if not f.exists():
            f.write_text("\n".join(DEFAULT_PHRASES) + "\n")
        # His file is never rewritten by code. A line starting with "*" is a favourite: it is
        # drawn four times as often. Repeating a line weights it too.
        self.phrases = []
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith("*"):
                self.phrases += [ln.lstrip("* ").strip()] * 4
            else:
                self.phrases.append(ln)
        self.phrases = self.phrases or list(DEFAULT_PHRASES)
        self.images = sorted(str(p) for p in (self.root / "images").iterdir()
                             if p.suffix.lower() in IMAGE_SUFFIXES)

    def frame(self, t: float, flash: float = 0.0) -> list[Item]:
        out: list[Item] = []
        if self.text is None and t >= self.next_text and self.phrases and (self.auto or getattr(self, "force_text", False)):
            self.force_text = False
            self.text = (self.rng.choice(self.phrases), t, self.rng.uniform(4.0, 7.0),
                         self.rng.uniform(0.15, 0.85), self.rng.uniform(0.2, 0.8))
        if self.text is not None:
            phrase, t0, dur, x, y = self.text
            u = (t - t0) / dur
            if u >= 1.0:
                self.text = None
                self.next_text = t + self.rng.uniform(self.gap * 0.6, self.gap * 1.4)
            else:
                a = min(1.0, u * 4.0, (1.0 - u) * 4.0) * (0.18 + 0.12 * flash)
                out.append(Item("text", phrase, x, y - 0.04 * u, 1.0, a))
        if self.image is None and t >= self.next_image and self.images and (self.auto or getattr(self, "force_image", False)):
            self.force_image = False
            self.image = (self.rng.choice(self.images), t, self.rng.uniform(6.0, 9.0),
                          self.rng.uniform(0.2, 0.8), self.rng.uniform(0.25, 0.75))
        if self.image is not None:
            path, t0, dur, x, y = self.image
            u = (t - t0) / dur
            if u >= 1.0:
                self.image = None
                self.next_image = t + self.rng.uniform(self.gap * 3.0, self.gap * 5.0)
            else:
                a = min(1.0, u * 3.0, (1.0 - u) * 3.0) * (0.14 + 0.08 * flash)
                out.append(Item("image", path, x, y - 0.03 * u, 1.0 + 0.1 * u, a))
        return out
