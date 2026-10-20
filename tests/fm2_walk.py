#!/usr/bin/env python3
"""Walk the Spectrum game in Fuse up to the office, then step through it.

Every screen is captured with the validated reader in tools/zxcap.py and
written to build/zx/ as a PNG, a text dump and a colour map, so screens
can be compared with the port after the fact.

Usage:
    python tests/fm2_walk.py boot       # stop at the manager's record
    python tests/fm2_walk.py office     # stop after the news panels
    python tests/fm2_walk.py step N     # N presses of ENTER, screenshot each
"""

import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "zx")
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


class Walk:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.r = fm2_ref.Ref()
        self.path = os.path.join(OUT, "_now.png")
        self.last = ""
        self.n = 0

    def grab(self, name=None):
        s = zxcap.capture(self.r.f, self.path)
        if name:
            shutil.copy(self.path, os.path.join(OUT, name + ".png"))
            with open(os.path.join(OUT, name + ".txt"), "w") as fh:
                fh.write("\n".join(s.colours()) + "\n\n" + s.text() + "\n")
        self.last = s.text()
        return s

    def shot(self, name=None):
        name = name or ("s%02d" % self.n)
        self.n += 1
        s = self.grab(name)
        if not s.ok:
            log("!! invalid capture", name)
        return s

    def boot(self, stop="MANAGEMENT RECORD", limit=90):
        log("fuse up")
        for i in range(limit):
            s = self.grab()
            txt = s.text()
            if txt != self.last:
                log("screen %d" % i)
                print(txt, flush=True)
            if stop in txt:
                log("reached", stop)
                return s
            for needle, keys in RULES:
                if needle in txt:
                    log("  >", needle, keys)
                    self.r.press(keys)
                    break
            else:
                log("  > SPACE")
                self.r.press(["SPACE"], gap=0.4)
        raise RuntimeError("never reached " + stop)

    def press(self, keys, gap=0.5):
        self.r.press(keys, gap=gap)

    def close(self):
        self.r.close()


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "boot"
    w = Walk()
    try:
        w.boot()
        log("record screen")
        w.press(["ENTER"])
        if what == "boot":
            time.sleep(1.2)
            w.shot("record-out")
            return
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        for i in range(steps):
            time.sleep(1.0)
            s = w.shot("step%02d" % i)
            print(s.text(), flush=True)
            w.press(["ENTER"])
    finally:
        w.close()
        log("done")


if __name__ == "__main__":
    main()
