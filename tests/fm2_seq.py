#!/usr/bin/env python3
"""Run a key sequence on the Spectrum team display, counting our cards.

Every key is followed by a grab, and the number of our players standing
in pitch slots (skill lines in the right-hand half of the screen) is
printed, so a promising rhythm for filling the sheet can be spotted.

Usage:
    python tests/fm2_seq.py ENTER S S ENTER S S S ENTER
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "seq")
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


def placed(s):
    n = 0
    for i, ln in enumerate(s.lines()):
        if i < 2:
            continue
        k = ln.find("SK.")
        while k >= 0:
            if k >= 12:
                n += 1
                break
            k = ln.find("SK.", k + 1)
    return n


def main():
    keys = sys.argv[1:]
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
        log("start: placed %d" % placed(s))
        for k in keys:
            r.press([k], gap=0.3)
            time.sleep(1.1)
            s = grab()
            rows = []
            for i, ln in enumerate(s.lines()):
                if i < 2:
                    continue
                k2 = ln.find("SK.")
                while k2 >= 0:
                    if k2 >= 12:
                        rows.append(i)
                        break
                    k2 = ln.find("SK.", k2 + 1)
            log("%s -> placed %d  rows %s   pool[%s]" % (
                k, placed(s), rows, s.lines()[0].strip()[:24]))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
