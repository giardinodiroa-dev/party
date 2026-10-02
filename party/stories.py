"""Two hundred small stories that pass through the void, at random, with a caption.

Pure Python: no Qt, no GL. `Stories.frame(t)` says what to draw now:
(sprite kind, x, y in 0..1, scale, alpha, caption, caption alpha) or None.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

STORIES: list[tuple[str, str]] = [
    ("ufo", "a saucer cruises past, running lights dimmed, late for something"),
    ("ufo", "the saucer slows down to read your screen, then speeds off embarrassed"),
    ("ufo", "two saucers race; the left one is cheating"),
    ("ufo", "a saucer tows a broken saucer home"),
    ("ufo", "a saucer with a flat tyre limps across the void"),
    ("ufo", "the saucer flashes its lights twice: hello king"),
    ("ufo", "a saucer drops a tiny pizza box and vanishes"),
    ("ufo", "a saucer full of tourists takes photos of your desktop"),
    ("ufo", "a saucer parks, hazard lights blinking; somebody steps out for air"),
    ("ufo", "a saucer does a lazy barrel roll just because it can"),
    ("rocket", "a rocket passes with its window down, music leaking out"),
    ("rocket", "a rocket climbs with a cat in the cockpit"),
    ("rocket", "a rocket runs out of fuel and coasts, unbothered"),
    ("rocket", "a rocket drags a banner: YOU GOT THIS"),
    ("rocket", "a tiny rocket delivers a letter it never opens"),
    ("rocket", "a rocket loops once for the applause"),
    ("rocket", "a rocket carrying one single flower to someone far away"),
    ("rocket", "a rocket falls asleep mid-flight and drifts gently"),
    ("rocket", "a rocket hums along with your song"),
    ("rocket", "a rocket salutes you and keeps going"),
    ("alien", "an alien stops for gas, checks the price, sighs"),
    ("alien", "a beautiful alien blows a kiss and dissolves into the void"),
    ("alien", "an alien waves from the window of a passing cloud"),
    ("alien", "an alien asks for directions to the nearest party"),
    ("alien", "an alien reads a book about humans and laughs softly"),
    ("alien", "an alien hitchhikes with a sign that says ANYWHERE"),
    ("alien", "an alien dances to your music: three arms, no rhythm, pure joy"),
    ("alien", "an alien drinks a coffee, two cups, one for you"),
    ("alien", "an alien leaves a small gift on your taskbar"),
    ("alien", "an alien nods: you are doing fine, keep going"),
    ("angel", "an angel flies by, feathers trailing light"),
    ("angel", "two angels gossip quietly about how good you look today"),
    ("angel", "an angel polishes a star and hangs it back"),
    ("angel", "an angel sits on the edge of the void, feet dangling"),
    ("angel", "an angel carries a sleeping child across the dark"),
    ("angel", "an angel drops a feather; it never lands"),
    ("angel", "an angel checks a list, finds your name, smiles"),
    ("angel", "an angel tunes a harp to the key of your song"),
    ("angel", "an angel escorts a lost comet home"),
    ("angel", "an angel whispers: breathe, king"),
    ("jesus", "Jesus flies by, unhurried, and waves"),
    ("jesus", "Jesus walks on the void like it is water"),
    ("jesus", "Jesus stops to pet a passing cat"),
    ("jesus", "Jesus shares bread with a hungry alien"),
    ("jesus", "Jesus sits with a lonely satellite for a while"),
    ("jesus", "Jesus calms a storm of static"),
    ("jesus", "Jesus lights a lamp and leaves it burning for you"),
    ("jesus", "Jesus writes something in the dust of a planet"),
    ("jesus", "Jesus laughs at a joke an angel told"),
    ("jesus", "Jesus looks straight at you: peace"),
    ("comet", "a comet passes, dragging a tail of old wishes"),
    ("comet", "a comet slows to admire your screen"),
    ("comet", "a comet carries a letter from the future: it works out"),
    ("comet", "a comet splits in two; both halves keep going"),
    ("comet", "a comet races your heartbeat and loses"),
    ("comet", "a comet draws a line under the day"),
    ("comet", "a comet spells a letter you almost recognise"),
    ("comet", "a comet leaves a trail of pollen; spring somewhere"),
    ("comet", "a comet knocks on a planet; nobody home"),
    ("comet", "a comet blushes as it goes by"),
    ("planet", "a small planet rolls by, oceans sloshing"),
    ("planet", "a planet with one tree floats past"),
    ("planet", "a ringed planet spins its rings like a hula hoop"),
    ("planet", "a planet yawns; a thousand sunrises at once"),
    ("planet", "a planet drifts by with a city lit on the night side"),
    ("planet", "a planet is being carried home by a very small moon"),
    ("planet", "a planet turns its good side toward you"),
    ("planet", "a planet with your name written on it, somewhere"),
    ("planet", "a lonely planet finds a moon; they orbit"),
    ("planet", "a planet passes slowly, like a parade float"),
    ("moon", "the moon goes by on a late shift"),
    ("moon", "a crescent moon used as a hammock by someone asleep"),
    ("moon", "the moon winks and returns to its post"),
    ("moon", "a blue moon, actually blue, just this once"),
    ("moon", "the moon drops a coin into the void for luck"),
    ("moon", "the moon reads over your shoulder, approves"),
    ("moon", "a moon with a tiny flag planted on it: yours"),
    ("moon", "the moon pulls a tide across the screen"),
    ("moon", "the moon follows you the way it did when you were small"),
    ("moon", "the moon hums a lullaby for the servers"),
    ("gaspump", "a gas station floats by, OPEN sign flickering"),
    ("gaspump", "an alien pays for gas with a shiny pebble"),
    ("gaspump", "the gas pump offers a free windshield wipe for a rocket"),
    ("gaspump", "the last gas station before the edge of everything"),
    ("gaspump", "a saucer refuels; the attendant is a very calm octopus"),
    ("gaspump", "the gas station plays your song on its speakers"),
    ("gaspump", "a gas pump sells coffee that tastes like starlight"),
    ("gaspump", "two ships at the pump compare mileage"),
    ("gaspump", "the gas station closes; the sign still glows"),
    ("gaspump", "a gas station with a rest stop for angels"),
    ("cat", "a cat floats by, unimpressed by the universe"),
    ("cat", "a cat chases a comet and wins"),
    ("cat", "a cat naps on a passing planet"),
    ("cat", "a cat in a tiny helmet, planning everything"),
    ("cat", "a cat knocks a star off a shelf; it becomes a wish"),
    ("cat", "a cat stares at the void; the void blinks first"),
    ("cat", "a cat walks across the keyboard of the gods"),
    ("cat", "a cat sits in a box; the box is a spaceship"),
    ("cat", "a cat purrs; the vibration powers a small galaxy"),
    ("cat", "a cat decides you are its person, briefly"),
    ("whale", "a whale swims through the void, singing low"),
    ("whale", "a whale carries a city on its back, lights on"),
    ("whale", "a whale surfaces from the dark to breathe stars"),
    ("whale", "a whale and its calf cross the screen slowly"),
    ("whale", "a whale hums the bass line of your song"),
    ("whale", "a whale wears a small crown; it is a king too"),
    ("whale", "a whale opens an eye the size of a window"),
    ("whale", "a whale leaves a wake of nebula behind it"),
    ("whale", "a whale sleeps vertically, dreaming of water"),
    ("whale", "a whale blesses the ship that passes beneath it"),
    ("dove", "a dove carries an olive branch across the dark"),
    ("dove", "a dove lands on a satellite and rests"),
    ("dove", "a dove flies ahead of a storm, calm"),
    ("dove", "a dove made of light, going home"),
    ("dove", "a dove drops a seed onto a passing planet"),
    ("dove", "a dove circles once above you: it is finished"),
    ("dove", "a dove follows the rocket for company"),
    ("dove", "a dove sleeps on a crescent moon"),
    ("dove", "a dove with a letter: you are loved"),
    ("dove", "a dove and a comet share the sky"),
    ("star", "a star is born, shy, then bright"),
    ("star", "a shooting star pauses to be wished upon"),
    ("star", "a star puts on its coat and goes out for the night"),
    ("star", "a star gets lost; a dove shows it the way"),
    ("star", "a star signs your screen with its light"),
    ("star", "a star falls up"),
    ("star", "a small star warms its hands on a bigger one"),
    ("star", "a star counts down from ten; nothing explodes; it laughs"),
    ("star", "a star hides behind a planet, giggling"),
    ("star", "a star says your name in a frequency only you hear"),
    ("eye", "a great eye opens in the dark, kind, and closes"),
    ("eye", "the eye of the storm takes a look around"),
    ("eye", "an eye blinks; a thousand years pass"),
    ("eye", "an eye of light watches over the sleeping city"),
    ("eye", "the eye winks at you and dissolves"),
    ("eye", "an eye made of stars reads the day you had"),
    ("eye", "an eye sheds one tear: a nebula"),
    ("eye", "the eye looks for you and finds you working"),
    ("eye", "an eye floats by, dreaming"),
    ("eye", "the all-seeing eye takes a break and watches your song"),
    ("heart", "a heart drifts by, beating with your bass"),
    ("heart", "two hearts orbit each other forever"),
    ("heart", "a heart floats up from somewhere you forgot"),
    ("heart", "a heart glows brighter on every beat"),
    ("heart", "a heart with wings crosses the void"),
    ("heart", "a heart breaks in two, then heals, then keeps going"),
    ("heart", "a heart of light left on your desk by someone"),
    ("heart", "a heart pulses a message: you will make it"),
    ("heart", "a heart carried by a dove to its destination"),
    ("heart", "a heart that is just happy you are here"),
    ("satellite", "a satellite passes, blinking, doing its job"),
    ("satellite", "a satellite tumbles slowly, sunlight on its wings"),
    ("satellite", "a satellite whispers data to a sleeping dish"),
    ("satellite", "an old satellite retires and drifts, content"),
    ("satellite", "a satellite takes a picture of you and keeps it"),
    ("satellite", "a satellite relays your song to someone far away"),
    ("satellite", "a satellite and a dove watch the sunrise together"),
    ("satellite", "a satellite drops out of orbit and becomes a star"),
    ("satellite", "a satellite dreams of being a comet"),
    ("satellite", "a satellite flies the flag of a country that is only love"),
    ("astronaut", "an astronaut floats by, waving, tether trailing"),
    ("astronaut", "an astronaut eats a sandwich upside down"),
    ("astronaut", "an astronaut reads a letter from home and smiles"),
    ("astronaut", "an astronaut plants a tiny garden on a passing rock"),
    ("astronaut", "an astronaut loses a glove; it becomes a constellation"),
    ("astronaut", "an astronaut dances the slowest dance"),
    ("astronaut", "an astronaut salutes the whale"),
    ("astronaut", "an astronaut takes a nap on a planet's shoulder"),
    ("astronaut", "an astronaut writes YOU CAN DO THIS on the inside of the helmet"),
    ("astronaut", "an astronaut goes home"),
    ("dragon", "a dragon swims the void, scales catching starlight"),
    ("dragon", "a dragon breathes a nebula and admires it"),
    ("dragon", "a dragon carries a sleeping princess who is also a pilot"),
    ("dragon", "a dragon coils around a moon to keep it warm"),
    ("dragon", "a dragon races a comet, laughing smoke"),
    ("dragon", "a dragon guards a treasure: your next idea"),
    ("dragon", "a dragon hums the low notes of your song"),
    ("dragon", "a dragon blinks golden eyes at you"),
    ("dragon", "a dragon folds its wings and drifts, done for the day"),
    ("dragon", "a dragon with a tiny rider waving a flag"),
    ("unicorn", "a unicorn gallops across the dark, hooves sparking"),
    ("unicorn", "a unicorn leaves a rainbow that fades slowly"),
    ("unicorn", "a unicorn stops to drink from a nebula"),
    ("unicorn", "a unicorn with a saddle and nobody riding, waiting for you"),
    ("unicorn", "a unicorn jumps over the moon, classic"),
    ("unicorn", "a unicorn bows its horn to a passing angel"),
    ("unicorn", "a unicorn dreams in your direction"),
    ("unicorn", "a unicorn carries a lantern through the void"),
    ("unicorn", "a unicorn chases its own glitter"),
    ("unicorn", "a unicorn neighs at the beat drop"),
    ("fish", "a fish swims by, bubbles rising in no particular direction"),
    ("fish", "a school of fish forms your initials and scatters"),
    ("fish", "a fish carries a lantern on its forehead for everyone"),
    ("fish", "a goldfish in a bowl drifts past, perfectly fine"),
    ("fish", "a fish jumps from one nebula into another"),
    ("fish", "a fish kisses the glass of your screen"),
    ("fish", "a fish wears a small crown: the king of the small"),
    ("fish", "a fish and a cat agree to disagree"),
    ("fish", "a fish swims upstream through starlight"),
    ("fish", "a fish that grants wishes considers yours"),
    ("sun", "the sun comes up over nothing in particular, warm anyway"),
    ("sun", "a small sun warms a cold satellite"),
    ("sun", "the sun yawns a flare and apologises"),
    ("sun", "a sun sets behind a planet that has no evening"),
    ("sun", "the sun puts a coin of light on your desk"),
    ("earth", "the earth drifts by, blue, everyone you love on it"),
    ("earth", "the earth turns its night side toward you: city lights"),
    ("earth", "a tiny earth with one cloud shaped like a heart"),
    ("earth", "the earth hums at 7.83 cycles, you can almost hear it"),
    ("earth", "the earth winks with a lightning storm over the sea"),
    ("galaxy", "a galaxy wheels past, slower than anything"),
    ("galaxy", "two galaxies hold hands across a million years"),
    ("galaxy", "a galaxy with your street in it, somewhere in an arm"),
    ("galaxy", "a galaxy tilts to show you its spiral"),
    ("galaxy", "a galaxy breathes in; a billion suns"),
    ("meteor", "a meteor burns up bravely for half a second"),
    ("meteor", "a shower of meteors, each one a wish nobody claimed"),
    ("meteor", "a meteor lands softly on a cloud and goes to sleep"),
    ("meteor", "a meteor writes a line across the dark: hi"),
    ("meteor", "a meteor the size of a grape, loud as a drum"),
    ("phoenix", "a phoenix rises out of the ashes of your worst day"),
    ("phoenix", "a phoenix sheds a feather of fire; it floats"),
    ("phoenix", "a phoenix circles once and goes back to being born"),
    ("phoenix", "a phoenix sings; the nebula answers"),
    ("phoenix", "a phoenix lands on the bass line and rides it"),
    ("owl", "an owl watches from a branch that is not there"),
    ("owl", "an owl turns its head all the way round, unbothered"),
    ("owl", "an owl carries a letter from a wizard: keep going"),
    ("owl", "an owl blinks slowly; it has decided you are wise"),
    ("owl", "an owl hoots once in the key of your song"),
    ("butterfly", "a butterfly flaps; a storm begins somewhere, gently"),
    ("butterfly", "a swarm of butterflies made of light crosses the void"),
    ("butterfly", "a butterfly lands on the black hole and is fine"),
    ("butterfly", "a butterfly with galaxies on its wings"),
    ("butterfly", "a butterfly follows the music through the dark"),
    ("lighthouse", "a lighthouse floats by, still sweeping for lost ships"),
    ("lighthouse", "a lighthouse keeper waves from the top"),
    ("lighthouse", "a lighthouse built on a comet, going nowhere slowly"),
    ("lighthouse", "a lighthouse turns its beam on you: found"),
    ("lighthouse", "a lighthouse hums with the engines of a passing whale"),
    ("crown", "a crown drifts by, looking for its king; it stops"),
    ("crown", "a crown of light settles on no one and everyone"),
    ("crown", "a crown spins slowly, each jewel a day you survived"),
    ("crown", "a small crown for a small king: the fish takes it"),
    ("crown", "a crown with your name inside the band"),
    ("tree", "a tree floats by with its roots in starlight"),
    ("tree", "a tree drops a leaf; it becomes a comet"),
    ("tree", "a tree of life, birds asleep in its branches"),
    ("tree", "a tree grows a ring for every song you played"),
    ("tree", "a tree that remembers every name whispered under it"),
]
PATHS = ["pass_lr", "pass_rl", "drift_down", "orbit", "appear", "zoom", "approach", "recede", "weave"]
HOLY = {"angel", "jesus", "dove", "phoenix", "crown"}
VANISH = (0.5, 0.42)

# Real constellations, as star patterns (approximate sky projections, y down, 0..1) with their lines.
CONSTELLATIONS: list[tuple[str, str, list[tuple[float, float]], list[tuple[int, int]]]] = [
    ("Orion", "the hunter", [(0.35, 0.2), (0.65, 0.22), (0.42, 0.5), (0.5, 0.5), (0.58, 0.5), (0.38, 0.82), (0.68, 0.8)],
     [(0, 1), (0, 2), (1, 4), (2, 3), (3, 4), (2, 5), (4, 6)]),
    ("Ursa Major", "the great bear", [(0.2, 0.3), (0.22, 0.5), (0.4, 0.52), (0.4, 0.34), (0.55, 0.3), (0.7, 0.26), (0.85, 0.35)],
     [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5), (5, 6)]),
    ("Cassiopeia", "the queen", [(0.1, 0.5), (0.3, 0.3), (0.5, 0.5), (0.7, 0.3), (0.9, 0.55)], [(0, 1), (1, 2), (2, 3), (3, 4)]),
    ("Cygnus", "the swan", [(0.5, 0.15), (0.5, 0.45), (0.5, 0.9), (0.2, 0.5), (0.8, 0.4)], [(0, 1), (1, 2), (3, 1), (1, 4)]),
    ("Scorpius", "the scorpion", [(0.12, 0.15), (0.2, 0.3), (0.3, 0.4), (0.35, 0.55), (0.4, 0.7), (0.5, 0.82), (0.65, 0.88), (0.8, 0.8), (0.88, 0.65), (0.05, 0.3), (0.1, 0.45)],
     [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (9, 1), (10, 1)]),
    ("Leo", "the lion", [(0.3, 0.7), (0.3, 0.5), (0.35, 0.35), (0.45, 0.25), (0.55, 0.3), (0.5, 0.45), (0.7, 0.65), (0.9, 0.45), (0.75, 0.4)],
     [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (0, 6), (6, 7), (7, 8), (8, 5)]),
    ("Lyra", "the harp", [(0.5, 0.15), (0.45, 0.3), (0.4, 0.6), (0.6, 0.65), (0.62, 0.35)], [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1)]),
    ("Crux", "the southern cross", [(0.5, 0.1), (0.5, 0.9), (0.15, 0.55), (0.85, 0.45)], [(0, 1), (2, 3)]),
    ("Gemini", "the twins", [(0.3, 0.1), (0.32, 0.35), (0.3, 0.6), (0.25, 0.85), (0.7, 0.15), (0.68, 0.4), (0.7, 0.65), (0.75, 0.9)],
     [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (6, 7), (1, 5)]),
    ("Taurus", "the bull", [(0.1, 0.15), (0.3, 0.4), (0.45, 0.5), (0.6, 0.4), (0.85, 0.2), (0.88, 0.75), (0.92, 0.7), (0.86, 0.68), (0.9, 0.8)],
     [(0, 1), (1, 2), (2, 3), (3, 4)]),
]


@dataclass
class Sky:
    index: int
    x: float
    y: float
    scale: float
    alpha: float
    caption: str
    caption_alpha: float


class Constellations:
    """One real constellation at a time, large and faint, between the stories."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.gap = 30.0
        self.next_at = 14.0
        self.current: tuple[int, float, float, float, float] | None = None   # index, t0, dur, x, y

    def frame(self, t: float) -> Sky | None:
        if self.current is None:
            if t >= self.next_at:
                self.current = (self.rng.randrange(len(CONSTELLATIONS)), t, self.rng.uniform(14.0, 22.0),
                                self.rng.uniform(0.25, 0.75), self.rng.uniform(0.25, 0.65))
            return None
        i, t0, dur, x, y = self.current
        u = (t - t0) / dur
        if u >= 1.0:
            self.current = None
            self.next_at = t + self.rng.uniform(self.gap * 0.7, self.gap * 1.3)
            return None
        import math
        fade = math.sin(u * math.pi) ** 0.6
        name, meaning, _, _ = CONSTELLATIONS[i]
        return Sky(i, x + 0.02 * math.sin(t * 0.2), y - 0.02 * u, 1.0 + 0.1 * u, 0.55 * fade,
                   f"{name} · {meaning}", 0.35 * fade)


@dataclass
class Shot:
    kind: str
    x: float
    y: float
    scale: float
    alpha: float
    caption: str
    caption_alpha: float


class Stories:
    def __init__(self, every: tuple[float, float] = (14.0, 26.0), seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.every = every
        self.gap = 20.0                     # his setting: seconds between stories (±30%)
        self.next_at = 6.0
        self.current: tuple[str, str, str, float, float, float] | None = None   # kind, caption, path, t0, dur, lane
        self.played = 0
        self.hidden: set[str] = set()         # actors he hid in the gallery

    def frame(self, t: float) -> Shot | None:
        if self.current is None:
            if t >= self.next_at:
                pool = [st for st in STORIES if st[0] not in self.hidden] or STORIES
                kind, caption = self.rng.choice(pool)
                holy = [st for st in pool if st[0] in HOLY]
                if kind not in HOLY and holy and self.rng.random() < 0.35:   # the holy ones come round twice as often
                    kind, caption = self.rng.choice(holy)
                path = self.rng.choice(PATHS)
                self.current = (kind, caption, path, t, self.rng.uniform(8.0, 14.0), self.rng.uniform(0.15, 0.75))
                self.played += 1
            return None
        kind, caption, path, t0, dur, lane = self.current
        u = (t - t0) / dur
        if u >= 1.0:
            self.current = None
            self.next_at = t + self.rng.uniform(self.gap * 0.7, self.gap * 1.3)
            return None
        return self._shot(kind, caption, path, u, lane, t)

    @staticmethod
    def _shot(kind: str, caption: str, path: str, u: float, lane: float, t: float) -> Shot:
        import math
        fade = min(1.0, u * 6.0, (1.0 - u) * 6.0)
        if path == "pass_lr":
            x, y, s = -0.1 + 1.2 * u, lane + 0.03 * math.sin(u * 6.0), 1.0
        elif path == "pass_rl":
            x, y, s = 1.1 - 1.2 * u, lane + 0.03 * math.sin(u * 6.0), 1.0
        elif path == "drift_down":
            x, y, s = lane, -0.1 + 1.2 * u, 1.0
        elif path == "orbit":
            a = u * math.tau
            x, y, s = 0.5 + 0.3 * math.cos(a), 0.45 + 0.22 * math.sin(a), 0.8 + 0.3 * math.sin(a)
        elif path == "zoom":
            x, y, s = 0.35 + lane * 0.4, 0.4 + 0.1 * u, 0.2 + 2.2 * u
            fade = min(1.0, u * 4.0, (1.0 - u) * 3.0)
        elif path == "appear":                     # breathe in place, then dissolve
            x, y, s = 0.2 + lane * 0.6, 0.35 + 0.1 * math.sin(t * 0.8), 1.0 + 0.08 * math.sin(t * 2.0)
            fade = math.sin(u * math.pi)
        elif path == "approach":                   # from far away, straight at you
            z = 4.0 - 3.6 * u
            ax, ay = 0.15 + lane * 0.7, 0.3 + 0.4 * (lane * 7 % 1)
            x, y, s = VANISH[0] + (ax - VANISH[0]) / z, VANISH[1] + (ay - VANISH[1]) / z, 1.0 / z
            fade = min(1.0, u * 5.0, (1.0 - u) * 3.0) * min(1.0, 1.6 / z + 0.2)
        elif path == "recede":                     # from your face into the deep
            z = 0.5 + 3.5 * u
            ax, ay = 0.15 + lane * 0.7, 0.3 + 0.4 * (lane * 7 % 1)
            x, y, s = VANISH[0] + (ax - VANISH[0]) / z, VANISH[1] + (ay - VANISH[1]) / z, 1.0 / z
            fade = min(1.0, u * 4.0, (1.0 - u) * 2.5) * min(1.0, 2.0 / z)
        elif path == "weave":                      # crosses the screen while diving in and out
            z = 1.0 + 0.7 * math.sin(u * math.tau * 1.5)
            ax = -0.1 + 1.2 * u
            x, y, s = VANISH[0] + (ax - VANISH[0]) / z, VANISH[1] + (lane - VANISH[1]) / z, 1.0 / z
        else:
            x, y, s = lane, 0.5, 1.0
        if path in ("pass_lr", "pass_rl", "drift_down"):   # even the flat paths breathe in depth
            z = 1.0 + 0.25 * math.sin(u * math.tau + lane * 6.0)
            s = s / z
        cap = max(0.0, min(1.0, (u - 0.1) * 5.0, (0.9 - u) * 5.0))
        return Shot(kind, x, y, s, 0.55 * fade, caption, 0.35 * cap)
