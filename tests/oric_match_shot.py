#!/usr/bin/env python3
"""Boot the Oric tape, press PLAY MATCH and print what the screen shows.

Used to check what the port actually puts on the screen when a match
starts, without needing to look at a picture: the text screen is printed
and the bitmap is dumped as ASCII art (bit 5 of each byte is a pixel).

Usage:
    python tests/oric_match_shot.py [seconds]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from oricutron import Oricutron, default_exe   # noqa: E402

OUT = os.path.join(ROOT, "build", "oric")


def main():
    os.makedirs(OUT, exist_ok=True)
    exe = default_exe()
    if not exe:
        sys.exit("Oricutron not found (set ORICUTRON)")
    o = Oricutron(exe, os.path.join(ROOT, "build", "fm2.tap"), boot_wait=5)
    try:
        o.type("CLOAD")
        o.tap('"')
        o.tap('"')
        o.tap("ENTER")
        for _ in range(60):
            time.sleep(0.5)
            if "FOOTBALL MANAGER 2" in "\n".join(o.snapshot()):
                break
        o.tap("1")
        for _ in range(60):
            time.sleep(0.5)
            if "CHOOSE YOUR CLUB" in "\n".join(o.snapshot()):
                break
        o.tap("ENTER")
        for _ in range(60):
            time.sleep(0.5)
            if "MANAGERS OFFICE" in "\n".join(o.snapshot()):
                break
        print("office:", flush=True)
        print("\n".join(o.snapshot()), flush=True)

        o.tap("6")
        time.sleep(4.0)
        print("after PLAY MATCH:", flush=True)
        print("\n".join(o.snapshot()), flush=True)
        o.screenshot(os.path.join(OUT, "match.png"))
        print("shot", os.path.join(OUT, "match.png"), flush=True)
        time.sleep(6.0)
        print("six seconds later:", flush=True)
        print("\n".join(o.snapshot()), flush=True)
        o.screenshot(os.path.join(OUT, "match2.png"))
    finally:
        o.close()


if __name__ == "__main__":
    main()
