#!/usr/bin/env python3
"""Pick eleven players in the Spectrum FM2 and follow the match.

What the team display does, read off the real game:

  * the reserve card at the top shows the next reserve by name,
  * FIRE on that card shows FIRE TO QUIT,
  * with FIRE TO QUIT showing, UP/DOWN scroll the reserves, and FIRE
    brings the chosen one to hand (his name comes back),
  * DOWN from the reserve card walks the pointer down the pitch; the
    defence screen has four outfield stops, midfield four and attack two,
  * a goalkeeper in hand walks three stops to the goal and FIRE puts him
    in the slot over the goal, which the four outfield stops skip,
  * FIRE on an empty slot places the reserve in hand and the card at the
    top moves on to the next reserve,
  * FIRE on the reserve card with eleven picked ends selection, and the
    game asks for two substitutes.

Usage:
    python tests/fm2_fill12.py [seconds-to-watch]
"""

import hashlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "fill12")
T0 = time.time()
ROWS = (4, 8, 12, 16, 20)

RULES = [
    ("PRESS 1 = KEMPSTON", ["2", "ENTER"]),
    ("PRESS FIRE", ["ENTER"]),
    ("PRESS SPACE TO CONTINUE", ["SPACE"]),
    ("MANAGE THIS TEAM", ["S", "ENTER"]),
    ("CHOOSE TEAM COLOUR", ["S", "ENTER"]),
    ("ACCEPT THE OFFER", ["S", "ENTER"]),
    ("BANK BALANCE", ["ENTER"]),
    ("SKILL LEVEL", ["ENTER"]),
    ("LOAD/SAVE GAME", ["ENTER"]),
]


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def thumb(s):
    h = hashlib.md5(s.text().encode())
    for row in s.bits:
        h.update(bytes(x & 0xFF for x in row))
    return h.hexdigest()[:8]


class Pad:
    def __init__(self, r, out):
        self.r = r
        self.out = out
        self.tmp = os.path.join(out, "_now.png")
        self.n = 0

    def grab(self):
        return zxcap.capture(self.r.f, self.tmp)

    def press(self, keys, gap=0.4):
        if isinstance(keys, str):
            keys = [keys]
        self.r.press(keys, gap=0.25)
        time.sleep(gap)

    def fire(self, settle=1.3):
        self.press(["ENTER"], settle)
        return self.grab()

    def save(self, s, tag):
        self.n += 1
        name = "%02d-%s" % (self.n, tag)
        with open(os.path.join(self.out, name + ".txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        self.r.f.screenshot(os.path.join(self.out, name + ".png"))
        return name

    # -- reading -------------------------------------------------------
    def pool(self, s):
        return s.lines()[0].strip(" ?")

    def stat(self, s):
        return s.lines()[1].strip(" ?")

    def message(self, s):
        return "FIRE TO QUIT" in self.pool(s)

    def mine(self, s):
        lines = s.lines()
        return {r: lines[r][15:29].strip(" ?") for r in ROWS
                if len(lines[r][15:29].strip(" ?")) >= 3}

    def ready(self):
        """Reserve in hand, pointer on the reserve card."""
        s = self.grab()
        for _ in range(4):
            if not self.message(s):
                return s
            s = self.fire()
        return s

    def walk(self, n, settle=1.3):
        for _ in range(n):
            self.press("S", 0.5)
        return self.fire(settle)

    def next_screen(self):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        self.press("P", 1.3)
        return self.grab()

    def seek_goalkeeper(self, tries=10):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        for _ in range(tries):
            if self.stat(s).startswith("G "):
                s = self.fire()               # bring him to hand
                return s
            self.press("Q", 0.55)
            s = self.grab()
        return s

    def place(self, walk, want=None):
        s = self.ready()
        if want is not None:
            s = self.seek_goalkeeper()
            if not self.stat(s).startswith(want):
                log("  no %s reserve found (pool %r)" % (want, self.pool(s)))
                return s
        before = self.mine(s)
        held = "%s %s" % (self.pool(s), self.stat(s))
        s = self.walk(walk)
        return s, before, held


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".png", ".txt")):
            os.remove(os.path.join(OUT, f))
    r = fm2_ref.Ref()
    p = Pad(r, OUT)

    try:
        for _ in range(90):
            s = p.grab()
            if "MANAGEMENT RECORD" in s.text():
                break
            for needle, kk in RULES:
                if needle in s.text():
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        log("record screen")

        s = p.fire(1.6)
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = p.fire(1.6)
        log("team display: pool %r %r" % (p.pool(s), p.stat(s)))

        # the four outfield defence places, one stop at a time
        for i, row in enumerate((4, 8, 16, 20), 1):
            s = p.ready()
            before = p.mine(s)
            held = "%s %s" % (p.pool(s), p.stat(s))
            s = p.walk(i)
            new = [x for x in p.mine(s) if x not in before]
            log("  DEF walk %d (%r) -> new %s" % (i, held, new))
            p.save(s, "def-%d" % i)

        # the goalkeeper, three stops down, over the goal
        s = p.ready()
        s = p.seek_goalkeeper()
        if p.stat(s).startswith("G "):
            held = "%s %s" % (p.pool(s), p.stat(s))
            s = p.walk(3)
            log("  GK walk 3 (%r) -> pool now %r, mine %s"
                % (held, p.pool(s), p.mine(s)))
            p.save(s, "keeper")
        else:
            log("  no goalkeeper in the reserves")

        s = p.next_screen()
        log("MID: pool %r %r" % (p.pool(s), p.stat(s)))
        p.save(s, "mid")
        for i, row in enumerate((4, 8, 16, 20), 1):
            s = p.ready()
            before = p.mine(s)
            held = "%s %s" % (p.pool(s), p.stat(s))
            s = p.walk(i)
            new = [x for x in p.mine(s) if x not in before]
            log("  MID walk %d (%r) -> new %s" % (i, held, new))
            p.save(s, "mid-%d" % i)

        s = p.next_screen()
        log("ATT: pool %r %r" % (p.pool(s), p.stat(s)))
        p.save(s, "att")
        for i in (1, 2):
            s = p.ready()
            before = p.mine(s)
            held = "%s %s" % (p.pool(s), p.stat(s))
            s = p.walk(i)
            new = [x for x in p.mine(s) if x not in before]
            log("  ATT walk %d (%r) -> new %s" % (i, held, new))
            p.save(s, "att-%d" % i)

        # eleven picked: the last one may have to be the goalkeeper shown
        # on the reserve card when selection is ended
        s = p.ready()
        s = p.seek_goalkeeper()
        log("ending with %r %r" % (p.pool(s), p.stat(s)))
        s = p.fire(1.8)
        log("  after FIRE: %r | %r" % (s.lines()[0].strip(" ?"),
                                       s.lines()[1].strip(" ?")))
        p.save(s, "end")
        for i in range(2):
            if not p.message(s):
                break
            s = p.fire(1.8)
            log("  after FIRE %d: %r | %r"
                % (i + 2, s.lines()[0].strip(" ?"),
                   s.lines()[1].strip(" ?")))
            p.save(s, "end%d" % (i + 2))

        # two substitutes: scroll and FIRE on each
        for i in range(2):
            p.press("S", 0.6)
            s = p.fire(1.4)
            p.save(s, "sub%d" % i)
            log("  sub %d: %r | %r" % (i, s.lines()[0].strip(" ?"),
                                       s.lines()[1].strip(" ?")))

        log("watching %ds" % watch)
        last = thumb(s)
        t0 = time.time()
        while time.time() - t0 < watch:
            time.sleep(1.0)
            s = p.grab()
            t = thumb(s)
            if t != last:
                last = t
                log("  changed at +%ds: %r | %r"
                    % (time.time() - t0, s.lines()[0].strip(" ?"),
                       s.lines()[1].strip(" ?")))
                p.save(s, "watch%02d" % int(time.time() - t0))
        p.save(s, "final")
        log("final:\n" + s.text())
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
