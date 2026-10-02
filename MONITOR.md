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
