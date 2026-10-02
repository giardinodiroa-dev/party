# Party

Lights that move with whatever the laptop is playing. Run: `party` (or `lights`).

It taps the PipeWire monitor of the default output (read-only; nothing is rerouted or
recorded) and paints at 60 fps.

Keys: `1` `2` `3` modes · `4` AURA (every line, border and glyph on the whole screen glows on the beat; click-through, apps untouched) · `B` bold (paint the strokes too; off by default so nothing gets heavier) · `A` astral sfx on/off · `G` ghost party + nebula background on/off · `C` cycle colour mode (chip opens the picker: PEARL, MONO, RAINBOW, FIRE, ICE, HOLY, AURORA) · `T` cycle border style (picker: SOFT, NEON, DOUBLE, OUTLINE, ELECTRIC, SHADOW) · `[` `]` aura width (also the AURA WIDTH slider) · `M` next mode · `F` fullscreen · `Esc` leave fullscreen ·
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
