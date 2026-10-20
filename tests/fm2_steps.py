#!/usr/bin/env python3
"""Walk the team display pointer one stop at a time, with a goalkeeper.

Presses DOWN once, then FIRE, and reports which card row changed.  Eight
stops are enough to see the whole cycle on the defence screen, so the
goalkeeper's slot over the goal cannot hide between counts.

Usage:
    python tests/fm2_steps.py [steps]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "steps")
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
        self.r.f.screenshot(os.path.join(self.out, "%02d-%s.png"
                                         % (self.n, tag)))

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

    def seek_goalkeeper(self, tries=16):
        s = self.grab()
        if not self.message(s):
            s = self.fire()
        for _ in range(tries):
            if self.stat(s).startswith("G "):
                s = self.fire()
                return s
            self.press("Q", 0.5)
            s = self.grab()
        return s


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".png"):
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
        s = p.fire(1.6)
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = p.fire(1.6)
        log("display: pool %r %r" % (p.pool(s), p.stat(s)))

        s = p.seek_goalkeeper()
        log("in hand: %r %r" % (p.pool(s), p.stat(s)))
        before = p.mine(s)
        log("mine %s" % before)

        for i in range(1, steps + 1):
            p.press("S", 0.5)
            s = p.fire()
            after = p.mine(s)
            gained = [r for r in after if r not in before]
            lost = [r for r in before if r not in after]
            log("  %d down + fire: gained %s lost %s mine %s pool %r"
                % (i, gained, lost, after, p.pool(s)))
            p.save(s, "step%d" % i)
            before = after
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
