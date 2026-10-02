# MONITOR — Party

His words (2026-10-02): "I need to make a simple party lights app that creates visuals
depending on system audio."

Accepted spec (his YES, 2026-10-02): three modes (Pulse, Bars, Orbs), fading icon bar,
monitor-of-default-sink source with a mic option, sensitivity slider, F/Space/Esc/1-3 keys,
full house stack (own repo, `party` launcher + `lights` alias, designed icon,
voidblack-luxury, hot autoreload with an in-app toggle, session restore). Built locally.

His words (2026-10-02, second ask): "make every line and border light up with the music for all
the apps on screen when party mode is on without actually modifying the apps just like an
ethereal onbeat glow as an additional mode" … "if you can do text as well it would be insane go
crazy as long as the pc is usable go".
Accepted route: screen-space overlay + GL shader inside Party (AURA, key 4), click-through,
fps cap with step-down, text included through edge detection.

His words (2026-10-02, third ask): "graduate the width of the glow because it is making some
things unreadable… not make things bolder unless I want to… add some sfx to the screen like
lights and astral elements, mother pearl type colors… not just one color but varied gradients…
trippy in a holy way". Built: width slider/keys, ring glow off the strokes, bold toggle (off),
pearl palette over a drifting hue field, stars/nebula/beat orbs dimmed over content.

His words (2026-10-02, fourth ask): "1. different color modes mother pearl is one 2. the previous
one with all one color switching 3. patterns many options… fix the lights they are chopped by
borders… make it seem like we are seeing a ghost party or nebulas in the background… an option
to restyle the border of the text… choose the borders or types of borders".
Built: 7 colour modes (C / picker), 6 border styles (T / picker), 3x3 cell lookup for stars and
orbs (no clipping), fbm nebula + ghost dancers (G), all persisted.

His words (2026-10-02, fifth ask): water/ghost/fire borders; a brainwash feature (images + phrases
"you go king, you can do this, you will make it" in the background); soundwaves/sound bars on the
screen borders (electric, aqua, fire, ghost, magical); a tiny black-hole cursor that distorts what
is around it; ~200 random stories in the void (spaceship, alien at the gas station, alien kiss,
Jesus, angels…). Built: all five; see README.

His words (2026-10-02, sixth ask): "don't ever close the app without saving the settings… this app
should save the configuration"; "the stories have to be real drawings not handdrawn sketches";
"I asked for sound bars coming out of the sides of the screen"; "add brightness adjustment… and
profile saving depending on what I like". Built: atomic save-on-change + SIGTERM save +
PARTY_STATE for tests (root cause of the loss: my test runs overwrote his state.json); per-actor
paintings in art/; BARS edge shape (default); BRIGHT slider; profiles P / Shift+P.

His words (2026-10-02, later asks): bars on edges he chooses, slim bars, bar colour options,
story/phrase pace, Ledaie symbols + dictionary words, phrase fonts/colours/animations, depth
motion, more drawings, real constellations, visible ghosts/angels, and "a proper settings pop up
to do this comfortably" with many fonts and text colours. Built: all; settings panel = X.
