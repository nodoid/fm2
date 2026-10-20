#!/usr/bin/env python3
"""Find the goalkeeper's slot on the Spectrum FM2 team display.

The defence screen draws five card rows, the middle one over the goal, but
walking down from the reserve slot only stops at four of them.  The
goalkeeper is the eleventh player and the game refuses to end selection
without him, so one of the walks must reach that middle row.

This fills the four outfield defence places, scrolls the reserves to a
goalkeeper, and then tries each walk length in turn, reporting which card
row each placement lands on.

Usage:
    python tests/fm2_keeper2.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "keeper2")
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


class Pad:
    def __init__(self, r, out):
        self.r = r
        self.out = out
        self.tmp = os.path.join(out, "_now.png")
        self.n = 0

    def grab(self):
        s = None
        for _ in range(5):
            s = zxcap.capture(self.r.f, self.tmp)
            if s.ok:
                return s
        return s

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
            fh.write(s.text() + "\n")
        self.r.f.screenshot(os.path.join(self.out, name + ".png"))
        return name

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
        s = self.grab()
        for _ in range(4):
            if not self.message(s):
                return s
            s = self.fire()
        return s

    def walk(self, n, settle=1.3):
        for _ in range(n):
            self.press("S", 0.45)
        return self.fire(settle)

    def seek_goalkeeper(self, tries=14):
        """Scroll the reserves until a goalkeeper is in hand."""
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        for _ in range(tries):
            if self.stat(s).startswith("G "):
                s = self.fire()          # bring him to hand
                log("  goalkeeper in hand: %r %r" % (self.pool(s),
                                                     self.stat(s)))
                return s
            self.press("Q", 0.5)
            s = self.grab()
        log("  no goalkeeper found, pool %r" % self.pool(s))
        return s


def main():
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
        log("display: pool %r %r" % (p.pool(s), p.stat(s)))

        # a goalkeeper, one walk length at a time, from an empty screen
        for n in (1, 2, 3, 4):
            s = p.ready()
            s = p.seek_goalkeeper()
            if not p.stat(s).startswith("G "):
                log("  no goalkeeper for walk %d" % n)
                continue
            if p.message(s):
                s = p.fire()
            held = "%s %s" % (p.pool(s), p.stat(s))
            before = p.mine(s)
            s = p.walk(n)
            after = p.mine(s)
            new = [r for r in after if r not in before]
            log("  keeper walk %d (%r): new %s, mine %s"
                % (n, held, new, after))
            p.save(s, "keeper-%d" % n)
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
