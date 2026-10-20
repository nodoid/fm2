#!/usr/bin/env python3
"""Reach the FM2 match: map the team display, pick eleven, then watch.

The pre-season route is long, but on a match day the game is only two key
presses from the manager's record: ENTER (decline load/save) shows the
LEAGUE MATCH card, and FIRE on that card opens the team display.

On the team display each screen has five player slots stacked down the
pitch, the third of which sits over the goal.  The reserve pool is the
card at the top; FIRE on it shows FIRE TO QUIT, and FIRE again ends team
selection once eleven players have been picked.

This script first walks the defence screen stop by stop and reports which
slot each walk lands on, then fills the side (four defenders plus the
goalkeeper over the goal, four midfielders and two attackers), ends the
selection and watches the match, dumping every screen change.

Usage:
    python tests/fm2_pick.py [seconds-to-watch]
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

OUT = os.path.join(ROOT, "build", "pick")
T0 = time.time()

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


class Pick:
    def __init__(self, r, out):
        self.r = r
        self.out = out
        self.tmp = os.path.join(out, "_now.png")
        self.n = 0
        self.last = None

    def grab(self):
        s = None
        for _ in range(5):
            s = zxcap.capture(self.r.f, self.tmp)
            if s.ok:
                return s
            time.sleep(0.15)
        return s

    def press(self, keys, gap=0.45):
        if isinstance(keys, str):
            keys = [keys]
        self.r.press(keys, gap=0.25)
        time.sleep(gap)

    def fire(self, settle=1.4):
        self.press(["ENTER"], settle)
        return self.grab()

    def save(self, s, tag):
        self.n += 1
        name = "%02d-%s" % (self.n, tag)
        with open(os.path.join(self.out, name + ".txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        self.r.f.screenshot(os.path.join(self.out, name + ".png"))
        return name

    # -- reading the team display -------------------------------------
    def slots(self, s):
        """{first text row of slot: 'mine' | ''} for the five cards."""
        lines = s.lines()
        out = {}
        for i, ln in enumerate(lines):
            if not ln.lstrip("?").startswith("OPPONENT") and \
                    "OPPONENT" not in ln[:12]:
                continue
            mine = ln[15:].strip(" ?")
            out[i] = "mine" if len(mine) >= 3 else ""
        return out

    def ours(self, s):
        return [r for r, v in self.slots(s).items() if v]

    def pool(self, s):
        return s.lines()[0].strip()

    def at_pool(self, s=None):
        return "FIRE TO QUIT" in self.pool(s if s is not None else self.grab())

    def to_pool(self, tries=9):
        s = self.grab()
        for _ in range(tries):
            if self.at_pool(s):
                return s
            self.press("Q", 0.45)
            s = self.grab()
        if self.at_pool(s):
            return s
        # not showing the message yet: FIRE on the pool card shows it
        s = self.fire()
        for _ in range(4):
            if self.at_pool(s):
                return s
            self.press("Q", 0.45)
            s = self.grab()
        return s

    def take(self, want=None, tries=45):
        """Take the reserve shown at the top; True when one is in hand."""
        s = self.to_pool()
        if not self.at_pool(s):
            return s
        for _ in range(tries):
            if want is not None:
                stat = s.lines()[1] if len(s.lines()) > 1 else ""
                if not stat.strip(" ?").startswith(want + " "):
                    self.press("S", 0.5)
                    s = self.grab()
                    continue
            s = self.fire()
            if not self.at_pool(s):
                return s
        return s

    def lift(self):
        """FIRE on a filled slot sends that player back to the reserves."""
        return self.fire()

    def screen_title(self, s):
        """Which of the three screens is showing, from its first card row."""
        txt = s.text()
        if "G SK." in txt or "OPPONENT" in txt:
            return txt
        return txt


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".png", ".txt")):
            os.remove(os.path.join(OUT, f))
    r = fm2_ref.Ref()
    p = Pick(r, OUT)

    try:
        # 1. boot to the manager's record
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
        else:
            raise RuntimeError("never reached the record screen")
        log("record screen")

        # 2. record -> league match card -> team display
        s = p.fire(1.6)
        log("after ENTER on record: %r" % s.lines()[1:3])
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = p.fire(1.6)
        else:
            p.save(s, "stuck")
            log("never reached the team display")
            return
        log("team display, pool %r" % p.pool(s))
        p.save(s, "team-display")

        # 3. map the walk: where does the nth step down land?
        log("mapping the defence screen walk")
        for n in range(1, 6):
            s = p.to_pool()
            before = p.ours(s)
            s = p.take()
            if p.at_pool(s):
                log("  walk %d: no reserve in hand" % n)
                continue
            held = s.lines()[0].strip()
            for _ in range(n):
                p.press("S", 0.5)
            s = p.fire()
            after = p.ours(s)
            new = [x for x in after if x not in before]
            log("  walk %d (%r): rows %s -> %s, new %s" %
                (n, held, before, after, new))
            p.save(s, "walk%d" % n)
            if new:
                s = p.lift()
                log("    lifted: rows %s" % p.ours(s))
            if "FIRE TO QUIT" not in s.text() and "OPPONENT" not in s.text():
                log("    selection ended here!")
                break

        log("map done; stopping")
        p.save(p.grab(), "map-end")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
