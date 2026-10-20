#!/usr/bin/env python3
"""Find the attack screen's third slot.

Switches the team display to the attack screen, then sends the keys given
on the command line and dumps the whole screen after each, so a card that
lands outside the four standard card rows can still be seen.

Usage:
    python tests/fm2_att.py S S S ENTER
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "att")
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
    keys = sys.argv[1:] or ["S", "S", "S", "ENTER"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        return zxcap.capture(r.f, tmp)

    def press(k, wait=0.6):
        r.press([k], gap=0.3)
        time.sleep(wait)

    def fire(wait=1.5):
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
        # two screens to the right: midfield, then attack
        for step in ("MID", "ATT"):
            if "FIRE TO QUIT" not in s.lines()[0]:
                s = fire()
            press("P", 0.8)
            s = grab()
            log("%s screen: pool %r %r" % (step, s.lines()[0].strip(" ?"),
                                           s.lines()[1].strip(" ?")))
            r.f.screenshot(os.path.join(OUT, "00-%s.png" % step))

        for i, k in enumerate(keys, 1):
            press(k, 1.0 if k == "ENTER" else 0.55)
            if k == "ENTER":
                time.sleep(0.8)
            s = grab()
            log("%2d %-6s\n%s" % (i, k, s.text()))
            r.f.screenshot(os.path.join(OUT, "%02d-%s.png" % (i, k)))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
