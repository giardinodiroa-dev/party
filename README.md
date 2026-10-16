# Party

Hotkey: **Super+Shift+p** toggles party mode (starts Party if it is not running, otherwise flips the aura on or off) via `~/bin/party-toggle`, bound in keygrab.

Lights that move with whatever your computer is playing, and an **aura** that makes every line,
border and glyph of every app on your screen glow on the beat without touching the apps.
Stories drift through the void (a satellite that visits, a goldfish in space), phrases you choose
surface faintly to keep you going, a black hole follows your cursor, sound bars climb in from the
screen edges. A mental-health machine for people who dream of space.

**Requirements:** Linux on X11 with a compositing window manager (built and tested on KDE KWin),
PipeWire or PulseAudio (`parec`), Python 3.11+, PyQt6, PyOpenGL, numpy, OpenGL 3.3.

```bash
git clone https://github.com/giardinodiroa-dev/party && cd party
pip install --user PyQt6 PyOpenGL numpy
python3 app.py          # then press 4 for the aura, X for settings
```

Keys, settings, profiles and every feature are described below. Your settings live in
`state.json`, your phrases in `brainwash/phrases.txt`, your pictures in `brainwash/images/`,
paintings in `art/`, drawings in `assets/sprites/*.svg`; none of those are in this repository.

It taps the PipeWire monitor of the default output (read-only; nothing is rerouted or
recorded) and paints at 60 fps.

Keys: `1` `2` `3` modes · `4` AURA (every line, border and glyph on the whole screen glows on the beat; click-through, apps untouched) · `B` bold (paint the strokes too; off by default so nothing gets heavier) · `A` astral sfx on/off · `G` ghost party + nebula background on/off · `C` cycle colour mode (chip opens the picker: PEARL, MONO, RAINBOW, FIRE, ICE, HOLY, AURORA) · `T` cycle border style (picker: SOFT, NEON, DOUBLE, OUTLINE, ELECTRIC, SHADOW) · `[` `]` aura width (also the AURA WIDTH slider) · `X` FX picker · `W` brainwash · `Shift+W` phrase every (2/3/5/10/20/45 s) · `Shift+N` story every (5/10/20/40/90 s) · `K` black-hole cursor · `V` cycle edge waves (OFF, ELECTRIC, AQUA, FIRE, GHOST, MAGIC) · `N` stories · `H` edge shape BARS/WAVE · `Shift+C` cycle the bars' colour world (STYLE, PEARL, MONO, RAINBOW, FIRE, ICE, HOLY, AURORA; also in the `X` picker) · `E` cycle which edges carry the bars (BOTTOM, ALL, TOP, SIDES, TOP+BOTTOM; any mix in the `X` picker) · `,` `.` brightness (also the BRIGHT slider) · `P` profiles picker · `Shift+P` save the current look as a profile · `M` next mode · `F` fullscreen · `Esc` leave fullscreen ·
`Space` pause · `S` pick source (output monitor or mic) · `R` hot reload on/off ·
`↑`/`↓` sensitivity · `Q` quit. Move the mouse to show the chrome; it fades after 2 s.

Tests: `python3 -m pytest tests/`

## AURA

Key `4` or the fourth chip. A fullscreen, always-on-top, click-through GL layer grabs the
screen through MIT-SHM each frame, runs Sobel edge detection, blurs the edges into a halo,
tints it with the current hue and the beat, and composites it over everything KWin draws.
It un-blends its own previous frame from the grab so the glow never feeds back on itself.
The halo is drawn beside strokes and never on them, so text keeps its exact pixels; `B` opts into painting the strokes. Colours come from a mother-of-pearl cosine palette over a hue field that drifts across the screen and through time, so no two regions share one colour. Astral layer: steady stars (each its own brightness, no blinking) and bokeh orbs born on beats, each looked up across neighbouring grid cells so nothing is cut at a grid edge. Background (`G`): a domain-warped fbm nebula and six swaying ghost dancers that breathe with loudness, drawn only where there is no content so it reads as space behind the apps. Colour modes and border styles are shader switches; every choice is remembered. Starts at 30 fps and steps down (to 15) if a frame costs more than its slot, so the machine
stays usable. Status shows in the title strip as `AURA 30fps 2.1ms`.
Offline proof: `python3 -c "from party.ui.aura import render_png; render_png('in.png','glow.png')"`.

### Brainwash, stories, waves, black hole

- **Brainwash** (`W`): phrases from `brainwash/phrases.txt` (one per line, edit freely) and any
  picture dropped into `brainwash/images/` surface faintly in empty space, drift up, and dissolve.
- **Stories** (`N`): 200 one-line stories across 20 line-art actors (saucer, rocket, alien, angel,
  Jesus, comet, planet, moon, gas station, cat, whale, dove, star, eye, heart, satellite, astronaut,
  dragon, unicorn, fish) on six flight paths, one every 25–70 s, with a faint caption. `party/stories.py`.
- **Edge waves** (`V`): the spectrum climbs in from the four screen borders in five styles.
- **Black-hole cursor** (`K`): a gravitational lens around the pointer with an event horizon and a
  photon ring, warping the real pixels beneath. A clean-frame pass keeps what was last seen under
  the lens so the warp never feeds on itself. The arrow cursor itself stays on top (X draws it).
- Border styles gained WATER (ripple + caustics), GHOST (wisps drifting up), FIRE (flames rising).

### Settings, profiles, art

- Every change is written to `state.json` at once (atomic write), again on close, on hot reload,
  and on SIGTERM/SIGINT. Tests and verification runs use `PARTY_STATE=<other file>` and never
  touch yours.
- Profiles: `Shift+P` saves the current look under a name into `profiles/<name>.json`
  (modes, colours, borders, waves, brightness, toggles; not geometry or audio source). `P` opens
  the picker to load one. The live profile shows in the picker.
- Story art: `art/<actor>.jpg` paintings, generated once (Pollinations, black-keyed to light)
  and cached. Drop your own `art/<actor>.png` or `art/<actor>-2.png` to override; the line-art
  sprite is only the stand-in while a painting is missing.

Favourite phrases: put `*` at the start of a line in `brainwash/phrases.txt` and it shows four
times as often. Code never rewrites that file.

Brainwash phrase style (in the `X` picker, each row taps to cycle): font MONO / SERIF / SANS /
HANDSCRIPT (your Ledaie letters), colour world, size S/M/L/XL, motion FADE / PULSE / RISE / TYPE /
FLASH. Stories also show Ledaie: lone handscript symbols and random dictionary words with their
English, read live from `~/ledaie/Ledaie - Dictionary.csv`.

Depth: stories fly in nine paths including approach (from the deep toward you), recede and weave,
with perspective toward a vanishing point; flat paths breathe in depth too. Thirty actors, 250
stories. Ten real constellations (Orion, Ursa Major, Cassiopeia, Cygnus, Scorpius, Leo, Lyra,
Crux, Gemini, Taurus) fade in large and faint with their names; patterns are approximate sky
projections. Ghost figures are brighter now and have eyes; angels, Jesus, doves, the phoenix and
the crown come round about twice as often as the rest.

## Settings panel

`X` (or the FX chip) opens a settings panel inside the window: LOOK (also pause, fullscreen and the
sound source, same list as `S`), STAGE (what appears, how often, how many at once), BARS,
BRAINWASH, STORIES, IMAGES, PROFILES (save / load). Every control applies at once and is saved. Any installed font can be chosen for
phrases, Ledaie lines and captions; each text role has a colour world or a CUSTOM hue and
lightness. Bars: style, shape, colour, height, slimness and which edges. Esc closes the panel.

## Drawings and the IMAGES tab

Two drawing styles, switched in the IMAGES tab: ASTRAL (default: luminous line art with a halo,
constellation-like) and CUTE (soft anime SVGs in `assets/sprites/`, kept for a cute mode). The
IMAGES tab shows every actor with both its drawing and its painting and a choice per actor:
DRAWING, PAINTING or HIDDEN. Paintings (`art/`) get a vignette so edges fade to nothing, like the
dove. Default: painting where one exists, drawing otherwise, angel and Jesus hidden. FETCH MISSING
PAINTINGS asks Pollinations for the rest (free tier: a few per minute). Nothing is ever deleted.

## Looks and profiles

Built-in profiles in PROFILES: `astral` (the default look) and `cute` (creamy LALA colours, PASTEL
no-glow borders, cute drawings, sans fonts, pink text). Nothing switches you; load what you want.
Drawing styles: ASTRAL, CUTE, DARK (ghibli-dark inks), ELECTRIC (neon strokes), HOLLOW (voidblack
magical). DARK/ELECTRIC/HOLLOW are the same geometry restyled, faces removed. The satellite visits:
flies in, hovers close for a slow circle, orbits away; it comes round often.

## The stage and the mini-movies

Phrases, stories, scenes, Ledaie words, constellations and pictures each keep their OWN timer
(STAGE tab: an ON box and an "every N s" slider per thing, ±30% jitter, counted from when it last
ended). "Things at once" (1..6) says how many may share the screen: at 1 each appears alone, then a
breath (the "breath between things" slider), then the longest-overdue thing; above 1 they overlap
and bottom captions stack upward instead of covering each other. The stars of the sky are steady
(each its own brightness, answering the beat a little), never blinking. Scenes are
animated from code, not pictures slid around: a shooting star is a shader streak with a burning head
and sparks; a ship banks along a curve with a flickering thruster, exhaust particles and a blinking
light; a man walks across the void on a solved walk cycle. Figures and the ship are real 3D bodies:
signed-distance capsules and ellipsoids smoothly joined, raymarched and lit in the shader with key,
fill and rim light, skin, hair, cloth, hull, glass and engine materials (`party/rigs.py` solves the
joints, `party/scenes.py` drives the scene, the SDF shader in `party/ui/aura.py` renders it).

## Clips: little stories that make sense

`party/clips.py` holds a library of clips, each a cast of tracks (a figure, a ship, a drawn actor, a
glow, a shooting star) with keyframes and timed captions: a man walks out and a ship comes down for
him; two ships flash hello as they pass; a ship pulls in at the gas station; a walk under a falling
star; an old satellite steadies itself; the cat and the comet; an astronaut picked up; the owl and the
moon; a whale in the nebula; dragon and rocket; the crown finds a fish; a meteor shower watched; the
lighthouse keeper; earthrise; a phoenix on the bass; the long walk home; unicorn over the moon; the
galaxy turns; butterfly and black hole; sun up. The stage plays every clip once before any repeat.
Figures walk with planted feet (two-bone knee IK, phase from ground covered); ships face where they
go, burn and blink. Add a clip by adding data.

## Eye exam (clips review)

`party-exam` starts a local site at http://localhost:8891/ with one card per clip. Nothing autoplays:
load a clip, press play inside it. Each card has a feedback box (SAVE, or GOOD / BAD as a quick
verdict) that writes to `exam/feedback.json`; I'M DONE marks the exam finished. Clips are authored
the HyperFrames way, HTML + SVG + GSAP (`exam/clips/*.html`), so the picked ones render to video for
Party afterwards.
