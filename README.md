# Party

Lights that move with whatever the laptop is playing. Run: `party` (or `lights`).

It taps the PipeWire monitor of the default output (read-only; nothing is rerouted or
recorded) and paints at 60 fps.

Keys: `1` `2` `3` modes · `4` AURA (every line, border and glyph on the whole screen glows on the beat; click-through, apps untouched) · `B` bold (paint the strokes too; off by default so nothing gets heavier) · `A` astral sfx on/off · `G` ghost party + nebula background on/off · `C` cycle colour mode (chip opens the picker: PEARL, MONO, RAINBOW, FIRE, ICE, HOLY, AURORA) · `T` cycle border style (picker: SOFT, NEON, DOUBLE, OUTLINE, ELECTRIC, SHADOW) · `[` `]` aura width (also the AURA WIDTH slider) · `X` FX picker · `W` brainwash · `Shift+W` phrase pace (2/3/5/10/20/45 s) · `Shift+N` story pace (5/10/20/40/90 s) · `K` black-hole cursor · `V` cycle edge waves (OFF, ELECTRIC, AQUA, FIRE, GHOST, MAGIC) · `N` stories · `H` edge shape BARS/WAVE · `Shift+C` cycle the bars' colour world (STYLE, PEARL, MONO, RAINBOW, FIRE, ICE, HOLY, AURORA; also in the `X` picker) · `E` cycle which edges carry the bars (BOTTOM, ALL, TOP, SIDES, TOP+BOTTOM; any mix in the `X` picker) · `,` `.` brightness (also the BRIGHT slider) · `P` profiles picker · `Shift+P` save the current look as a profile · `M` next mode · `F` fullscreen · `Esc` leave fullscreen ·
`Space` pause · `S` pick source (output monitor or mic) · `R` hot reload on/off ·
`↑`/`↓` sensitivity · `Q` quit. Move the mouse to show the chrome; it fades after 2 s.

Tests: `python3 -m pytest tests/`

## AURA

Key `4` or the fourth chip. A fullscreen, always-on-top, click-through GL layer grabs the
screen through MIT-SHM each frame, runs Sobel edge detection, blurs the edges into a halo,
tints it with the current hue and the beat, and composites it over everything KWin draws.
It un-blends its own previous frame from the grab so the glow never feeds back on itself.
The halo is drawn beside strokes and never on them, so text keeps its exact pixels; `B` opts into painting the strokes. Colours come from a mother-of-pearl cosine palette over a hue field that drifts across the screen and through time, so no two regions share one colour. Astral layer: twinkling stars and bokeh orbs born on beats, each looked up across neighbouring grid cells so nothing is cut at a grid edge. Background (`G`): a domain-warped fbm nebula and six swaying ghost dancers that breathe with loudness, drawn only where there is no content so it reads as space behind the apps. Colour modes and border styles are shader switches; every choice is remembered. Starts at 30 fps and steps down (to 15) if a frame costs more than its slot, so the machine
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

`X` (or the FX chip) opens a settings panel inside the window: LOOK, BARS, BRAINWASH, STORIES,
PROFILES. Every control applies at once and is saved. Any installed font can be chosen for
phrases, Ledaie lines and captions; each text role has a colour world or a CUSTOM hue and
lightness. Bars: style, shape, colour, height, slimness and which edges. Esc closes the panel.

## Drawings and the IMAGES tab

The story actors are hand-authored SVG drawings in a soft anime style (`assets/sprites/<actor>.svg`,
rendered with QtSvg). Edit a file and the story shows your version; code never overwrites a file
that exists. Pollinations fetching is off. The IMAGES tab in settings shows every actor with a
SHOW box (hidden actors never appear; nothing is deleted) and a PAINT box that uses the actor's
painting from `art/` instead, with a vignette so edges always fade to nothing. Dove and the
saucer use their paintings by default.
