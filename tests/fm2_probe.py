#!/usr/bin/env python3
"""Walk to the screen after the league-match news and try keys on it.

Usage: python tests/fm2_probe.py SPACE ENTER P Q S F 1
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "probe")
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
    print(*a, flush=True)


def main():
    keys = sys.argv[1:] or ["SPACE"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")
    try:
        for _ in range(90):
            s = zxcap.capture(r.f, tmp)
            txt = s.text()
            if "MANAGEMENT RECORD" in txt:
                break
            for needle, kk in RULES:
                if needle in txt:
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        r.press(["ENTER"])
        time.sleep(1.5)
        r.press(["ENTER"])
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        log("=== start")
        log(s.text())
        for k in keys:
            r.press([k])
            time.sleep(1.2)
            s = zxcap.capture(r.f, tmp)
            log("=== after", k)
            log(s.text())
    finally:
        r.close()


if __name__ == "__main__":
    main()
