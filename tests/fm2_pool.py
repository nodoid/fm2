#!/usr/bin/env python3
"""Probe the reserve pool card on the FM2 team display, key by key.

Boots to the manager's record, opens the league match card and the team
display (the short match-day route), then sends a scripted key sequence
and prints what the top card says after every press.  The point is to
learn the exact pool semantics: FIRE shows FIRE TO QUIT, FIRE selects the
reserve shown, UP/DOWN scroll, and FIRE on the pool ends selection once
eleven players are picked.

Usage:
    python tests/fm2_pool.py [KEY ...]
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

OUT = os.path.join(ROOT, "build", "pool")
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


def ours(s):
    out = []
    for i, ln in enumerate(s.lines()):
        if "OPPONENT" in ln[:12] and len(ln[15:].strip(" ?")) >= 3:
            out.append(i)
    return out


def state(s):
    lines = s.lines()
    return "%r | %r | mine %s" % (lines[0].strip(), lines[1].strip(" ?"),
                                  ours(s))


def main():
    keys = sys.argv[1:] or ["ENTER", "ENTER", "S", "S", "ENTER", "Q", "ENTER"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
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
        log("record screen")
        r.press(["ENTER"], gap=0.3)
        time.sleep(1.6)
        for _ in range(6):
            s = grab()
            if "OPPONENT" in s.text():
                break
            r.press(["ENTER"], gap=0.3)
            time.sleep(1.6)
        log("team display: " + state(s))

        for i, k in enumerate(keys, 1):
            log("  press %-6s" % k)
            r.press([k], gap=0.3)
            time.sleep(1.3)
            s = grab()
            log("  %2d %-8s %s" % (i, k, state(s)))
            with open(os.path.join(OUT, "%02d-%s.txt" % (i, k)), "w") as fh:
                fh.write(s.text() + "\n")
            r.f.screenshot(os.path.join(OUT, "%02d-%s.png" % (i, k)))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
