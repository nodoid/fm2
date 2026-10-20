#!/usr/bin/env python3
"""Fill the Spectrum team sheet and play on into the match.

The manual: fire on the reserve slot shows FIRE TO QUIT; up/down scrolls
the reserves; fire selects the displayed reserve; the display pointer
then places him in a slot with fire.

Usage: python tests/fm2_fill.py [rounds]
"""

import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "fill")
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


def main():
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
        for i in range(1):
            for k in ("S", "ENTER", "P", "ENTER", "P", "ENTER", "P", "ENTER",
                      "P", "ENTER"):
                r.press([k], gap=0.45)
        for _ in range(6):
            s = zxcap.capture(r.f, tmp)
            print("=== screen", flush=True)
            print(s.text(), flush=True)
            time.sleep(1.0)
    finally:
        r.close()


if __name__ == "__main__":
    main()
