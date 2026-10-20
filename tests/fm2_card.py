#!/usr/bin/env python3
"""Poke the LEAGUE MATCH card before the team display.

Boots to the manager's record, presses FIRE to get the match card, then
sends the keys given on the command line one at a time and dumps the text
of the screen after each.  Used to see whether the card offers anything
besides opening the team display.

Usage:
    python tests/fm2_card.py P ENTER
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "card")
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
    keys = sys.argv[1:] or ["P", "ENTER"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        return zxcap.capture(r.f, tmp)

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
        r.press(["ENTER"], gap=0.3)
        time.sleep(1.6)
        s = grab()
        log("card:\n" + s.text())
        r.f.screenshot(os.path.join(OUT, "00-card.png"))
        for i, k in enumerate(keys, 1):
            r.press([k], gap=0.3)
            time.sleep(1.5)
            s = grab()
            log("%d %s:\n%s" % (i, k, s.text()))
            r.f.screenshot(os.path.join(OUT, "%02d-%s.png" % (i, k)))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
