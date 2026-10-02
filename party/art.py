"""Real paintings for the story actors.

Paintings are OPTIONAL now (he found the generated ones poor): the drawings in
ghibli.py are the default. If "use paintings" is on, `art/<actor>.png|jpg` (or
`art/<actor>-*.png`) is shown instead — his own files. Fetching is off by default;
`Art(root, fetch=True)` would resume the Pollinations fill. Pure Python, no Qt.
"""
from __future__ import annotations

import random
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

STYLE = ("brightly lit, vivid luminous colors, glowing, isolated on a pure black background, "
         "digital painting, cinematic lighting, highly detailed, centered, no text, no watermark")
PROMPTS = {
    "ufo": "a glowing flying saucer with running lights",
    "rocket": "a retro silver rocket ship with a flame trail",
    "alien": "a beautiful elegant alien with large kind eyes, pearl skin",
    "angel": "an angel with wide luminous wings and a halo, flying",
    "jesus": "Jesus in white robes with a golden halo, arms open, serene, flying through the stars",
    "comet": "a bright comet with a long sparkling tail",
    "planet": "a small ringed planet with glowing oceans",
    "moon": "a crescent moon glowing softly",
    "gaspump": "a tiny retro gas station floating in space with a glowing OPEN sign",
    "cat": "a fluffy cat floating in space wearing a tiny astronaut helmet",
    "whale": "a majestic whale swimming through a nebula, starlight on its skin",
    "dove": "a white dove made of light carrying an olive branch",
    "star": "a radiant five pointed star of pure light",
    "eye": "a great luminous eye made of stars and nebula, kind",
    "heart": "a glowing heart of light with soft wings",
    "satellite": "a small satellite with solar panels catching sunlight",
    "astronaut": "an astronaut floating, waving, tether trailing, visor reflecting stars",
    "dragon": "a serpentine dragon of starlight swimming through space, golden eyes",
    "unicorn": "a unicorn galloping through space leaving a soft rainbow trail",
    "fish": "a luminous goldfish swimming through starlight with a tiny crown",
    "sun": "a radiant sun with soft flares, warm gold",
    "earth": "planet earth from space, blue oceans, city lights on the night side",
    "galaxy": "a spiral galaxy seen at a tilt, luminous arms",
    "meteor": "a meteor burning bright with a long fiery trail",
    "phoenix": "a phoenix of fire and light rising with spread wings",
    "owl": "a wise owl made of starlight perched on nothing, large glowing eyes",
    "butterfly": "a luminous butterfly with galaxies painted on its wings",
    "lighthouse": "a small lighthouse floating in space, its beam sweeping the dark",
    "crown": "a golden crown of light with glowing jewels",
    "tree": "a glowing tree of life with roots of starlight",
}
SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class Art:
    def __init__(self, root: Path, fetch: bool = False) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.failed: dict[str, str] = {}
        self.rng = random.Random()
        if fetch:
            threading.Thread(target=self._loop, name="party-art", daemon=True).start()

    def _loop(self, retry_s: float = 600.0) -> None:
        """Keep filling the set while the app runs: the free tier allows a few images per window."""
        import time
        while self.missing():
            self._fetch_missing()
            if self.missing():
                time.sleep(retry_s)

    def files(self, actor: str) -> list[Path]:
        return sorted(p for p in self.root.iterdir()
                      if p.suffix.lower() in SUFFIXES and (p.stem == actor or p.stem.startswith(actor + "-")))

    def pick(self, actor: str) -> Path | None:
        found = self.files(actor)
        return self.rng.choice(found) if found else None

    def missing(self) -> list[str]:
        return [a for a in PROMPTS if not self.files(a)]

    def _fetch_missing(self, pause: float = 20.0) -> None:
        """Patient: one painting at a time, spaced out, and it stops for this run on a quota
        refusal (HTTP 402/429). Every AURA start tries again, so the set fills over sessions."""
        import time
        for actor in self.missing():
            prompt = urllib.parse.quote(f"{PROMPTS[actor]}, {STYLE}")
            seed = sum(actor.encode()) % 1000
            url = f"https://image.pollinations.ai/prompt/{prompt}?width=512&height=576&nologo=true&seed={seed}&model=flux"
            try:
                with urllib.request.urlopen(url, timeout=90) as r:
                    data = r.read()
                if len(data) < 2000:
                    raise OSError("empty image")
                tmp = self.root / f".{actor}.part"
                tmp.write_bytes(data)
                tmp.replace(self.root / f"{actor}.jpg")
            except urllib.error.HTTPError as exc:
                self.failed[actor] = f"HTTP {exc.code}"
                if exc.code in (402, 429):
                    return                           # quota for now; next start tries again
            except Exception as exc:              # noqa: BLE001 — line art stands in, say why
                self.failed[actor] = str(exc)
            time.sleep(pause)
