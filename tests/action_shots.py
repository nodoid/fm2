#!/usr/bin/env python3
"""Boot the game, start a match and grab a run of frames.

Usage:
    python tests/action_shots.py [count] [interval]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402

OUT = os.path.join(ROOT, "build", "act")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    os.makedirs(OUT, exist_ok=True)
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
            time.sleep(interval)
            path = os.path.join(OUT, "act-%d.png" % i)
            o.screenshot(path)
            print("wrote", path, flush=True)
    finally:
        o.close()


if __name__ == "__main__":
    main()
