#!/usr/bin/env python3
"""Find the team display pointer by its flashing cell.

The pointer is drawn as a flashing cell, so sampling the same screen
several times in a row shows it as the only cell that changes.  With
that, one key press can be traced to the cell it moved the pointer to.

    python tests/fm2_pointer.py [sequence]

`sequence` is a string of key names separated by commas, for example
"ENTER,S,ENTER,S,S,ENTER".  The default walks through the pool and the
slots so the mechanics can be read off the log.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "pointer")
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
    seq = (sys.argv[1] if len(sys.argv) > 1 else
           "ENTER,S,ENTER,S,S,ENTER,S,S,S,ENTER,S,ENTER").split(",")
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_f.png")

    def shot():
        r.f.screenshot(tmp)
        return zxcap.Screen(tmp)

    def flashing(n=6, gap=0.22):
        seen = []
        for _ in range(n):
            s = shot()
            if s.ok:
                seen.append(s)
            time.sleep(gap)
        if len(seen) < 2:
            return [], seen[-1] if seen else None
        cells = set()
        for a, b in zip(seen, seen[1:]):
            for cy in range(24):
                for cx in range(32):
                    if (a.bits[cy][cx] != b.bits[cy][cx] or
                            a.ink[cy][cx] != b.ink[cy][cx] or
                            a.paper[cy][cx] != b.paper[cy][cx]):
                        cells.add((cx, cy))
        return sorted(cells), seen[-1]

    def report(tag):
        cells, s = flashing()
        if s is None:
            log("%-12s no capture" % tag)
            return None
        log("%-12s pool %-30r rows %-14s flashing %s"
            % (tag, s.lines()[0].strip(),
               [i for i, ln in enumerate(s.lines())
                if "SK." in ln and ln.find("SK.") >= 12],
               " ".join("%d,%d" % c for c in cells[:8])))
        with open(os.path.join(OUT, tag.replace(",", "_") + ".txt"),
                  "w") as fh:
            fh.write(s.text() + "\n")
        return s

    try:
        for _ in range(80):
            s = shot()
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
            s = shot()
            if "OPPONENT" in s.text():
                break
            r.press(["ENTER"])
            time.sleep(1.6)
        log("team display")
        report("start")
        for i, k in enumerate(seq):
            r.press([k])
            time.sleep(0.8)
            report("%d %s" % (i + 1, k))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
