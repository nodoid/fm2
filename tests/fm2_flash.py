#!/usr/bin/env python3
"""Find the team display's flashing pointer by diffing two grabs.

The pointer flashes, so two grabs taken a moment apart differ exactly at
the flashing parts of the screen: the reserve name being rolled and the
marker round the pointed slot.  Listing the cells that changed, before and
after a direction key, shows whether the marker really moves and where to.

Usage:
    python tests/fm2_flash.py [key ...]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "flash")
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


def attrs(s):
    return [(s.ink[cy][cx], s.paper[cy][cx]) for cy in range(24)
            for cx in range(32)]


def moved(a, b):
    out = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            out.append((i % 32, i // 32))
    return out


def main():
    keys = sys.argv[1:] or ["S", "S", "S", "S", "Q", "P", "I"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        for _ in range(3):
            r.f.screenshot(tmp)
            s = zxcap.Screen(tmp)
            if s.ok:
                return s
            time.sleep(0.2)
        return s

    try:
        for _ in range(90):
            s = grab()
            if "MANAGEMENT RECORD" in s.text():
                break
            for needle, kk in RULES:
                if needle in s.text():
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        s = None
        for _ in range(8):
            s = grab()
            if "OPPONENT" in s.text():
                break
            r.press(["ENTER"], gap=0.3)
            time.sleep(1.7)
        log("team display")

        for round_ in range(6):
            a = grab()
            time.sleep(0.45)
            b = grab()
            fl = moved(attrs(a), attrs(b))
            log("flash cells: %s" % " ".join("%d,%d" % c for c in fl[:20]))
            if keys:
                k = keys[round_ % len(keys)] if round_ < len(keys) else "S"
                r.press([k], gap=0.3)
                time.sleep(1.2)
                c = grab()
                time.sleep(0.45)
                d = grab()
                fl2 = moved(attrs(c), attrs(d))
                log("after %s: flash cells %s" % (
                    k, " ".join("%d,%d" % x for x in fl2[:20])))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
