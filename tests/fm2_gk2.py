#!/usr/bin/env python3
"""Try a key sequence on the team display with a goalkeeper in hand.

Boots to the team display, scrolls the reserves to a goalkeeper, brings him
to hand and then sends the keys given on the command line one at a time,
printing the five card rows after each.  Used to find how the pointer
reaches the slot over the goal.

Usage:
    python tests/fm2_gk2.py S S I ENTER
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "gk2")
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


def report(s):
    lines = s.lines()
    out = ["pool %r %r" % (lines[0].strip(" ?"), lines[1].strip(" ?"))]
    for r in ROWS:
        out.append("  %2d: %-24r | %r" % (r, lines[r][:14].strip(" ?"),
                                          lines[r][15:29].strip(" ?")))
    return "\n".join(out)


def main():
    keys = sys.argv[1:] or ["S", "S", "I", "ENTER"]
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
        log("display:\n" + report(s))

        if "FIRE TO QUIT" not in s.lines()[0]:
            s = fire()
        for i in range(10):
            if s.lines()[1].strip(" ?").startswith("G "):
                break
            press("Q", 0.55)
            s = grab()
        if "FIRE TO QUIT" in s.lines()[0]:
            s = fire()
        log("goalkeeper in hand:\n" + report(s))

        for i, k in enumerate(keys, 1):
            press(k if k != "ENTER" else "ENTER", 0.6)
            if k == "ENTER":
                time.sleep(1.0)
            s = grab()
            log("%2d %-6s\n%s" % (i, k, report(s)))
            r.f.screenshot(os.path.join(OUT, "%02d-%s.png" % (i, k)))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
