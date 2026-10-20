#!/usr/bin/env python3
"""Read the FM2 team display as a slot map while keys are pressed.

The display stacks five card rows down the pitch.  A card shows a name and
a stat line; the left half holds the opposition, the right half ours.
After every key this prints the pool card and the five rows, so the walk,
the reserve scroll and the goalkeeper slot can be mapped exactly.

Usage:
    python tests/fm2_map.py S ENTER I ENTER ...
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "map")
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
    out = ["pool %-22r %r" % (lines[0].strip(" ?"), lines[1].strip(" ?"))]
    for r in ROWS:
        ours = lines[r][15:29].strip(" ?")
        opp = lines[r][:14].strip(" ?")
        stat = lines[r + 1][15:29].strip(" ?")
        out.append("  %2d: ours %-13r %-12r opp %r" % (r, ours, stat, opp))
    return "\n".join(out)


def main():
    keys = sys.argv[1:] or ["S", "ENTER"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        s = None
        for _ in range(5):
            s = zxcap.capture(r.f, tmp)
            if s.ok:
                return s
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
        r.press(["ENTER"], gap=0.3)
        time.sleep(1.6)
        for _ in range(6):
            s = grab()
            if "OPPONENT" in s.text() or "SK." in s.text():
                break
            r.press(["ENTER"], gap=0.3)
            time.sleep(1.6)
        log("team display:\n" + report(s))
        r.f.screenshot(os.path.join(OUT, "00-start.png"))

        for i, k in enumerate(keys, 1):
            r.press([k], gap=0.3)
            time.sleep(1.2)
            s = grab()
            log("%2d %-6s\n%s" % (i, k, report(s)))
            r.f.screenshot(os.path.join(OUT, "%02d-%s.png" % (i, k)))
            with open(os.path.join(OUT, "%02d-%s.txt" % (i, k)), "w") as fh:
                fh.write(s.text() + "\n")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
