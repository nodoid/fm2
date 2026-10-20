#!/usr/bin/env python3
"""One question: does a goalkeeper walking three stops land over the goal?

Boots to the team display, brings a goalkeeper to hand, presses DOWN three
times and FIRE, then prints the whole screen so the middle card row can be
read directly.

Usage:
    python tests/fm2_gk.py [stops]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "gk")
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


def main():
    stops = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        return zxcap.capture(r.f, tmp)

    def press(k, wait=0.6):
        r.press([k], gap=0.3)
        time.sleep(wait)

    def fire(wait=1.4):
        press("ENTER", wait)
        return grab()

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
        s = fire(1.6)
        for _ in range(6):
            if "OPPONENT" in s.text():
                break
            s = fire(1.6)
        log("display: %r %r" % (s.lines()[0].strip(" ?"),
                                s.lines()[1].strip(" ?")))

        if "FIRE TO QUIT" not in s.lines()[0]:
            s = fire()
        log("message: %r" % s.lines()[0].strip(" ?"))
        for i in range(12):
            if s.lines()[1].strip(" ?").startswith("G "):
                break
            press("Q", 0.55)
            s = grab()
            log("  scroll %d: %r %r" % (i + 1, s.lines()[0].strip(" ?"),
                                        s.lines()[1].strip(" ?")))
        log("in hand: %r %r" % (s.lines()[0].strip(" ?"),
                                s.lines()[1].strip(" ?")))
        if "FIRE TO QUIT" in s.lines()[0]:
            s = fire()
            log("after select: %r %r" % (s.lines()[0].strip(" ?"),
                                         s.lines()[1].strip(" ?")))

        for _ in range(stops):
            press("S", 0.55)
        s = fire(1.6)
        log("after %d down + fire:\n%s" % (stops, s.text()))
        r.f.screenshot(os.path.join(OUT, "result.png"))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
