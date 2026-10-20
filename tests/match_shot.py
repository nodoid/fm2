#!/usr/bin/env python3
"""Boot the Oric game, start a match, and capture the action screen.

Usage:
    python tests/match_shot.py [out.png] [seconds]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "build", "match-new.png")
    hold = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    o = ms.Oricutron(ms.args_exe(), os.path.join(ROOT, "build", "fm2.tap"),
                     boot_wait=5)
    try:
        o.type("CLOAD")
        o.tap('"')
        o.tap('"')
        o.tap("ENTER")
        ms.wait_for(o, "FOOTBALL MANAGER 2", 90)
        o.tap("1")
        ms.wait_for(o, "CHOOSE YOUR CLUB", 30)
        o.tap("ENTER")
        ms.wait_for(o, "MANAGERS OFFICE", 30)
        o.tap("6")
        ms.wait_for(o, "KICK OFF", 90)
        for i in range(count):
            for _ in range(6):
                o.tap("SPACE", hold=0.05, gap=0.2)
            time.sleep(hold)
            path = out if count == 1 else out.replace(
                ".png", "-%d.png" % i)
            o.screenshot(path)
            print("wrote", path, flush=True)
    finally:
        o.close()


if __name__ == "__main__":
    main()
