#!/usr/bin/env python3
"""Drive a match to half time and dump the team-talk screen.

Usage:
    python tests/half_probe.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402

OUT = os.path.join(ROOT, "build", "half")


def main():
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
        for i in range(120):
            o.tap("SPACE")
            time.sleep(0.25)
            text = "\n".join(o.snapshot())
            if "HALF TIME" in text:
                print(text)
                o.snapshot(os.path.join(OUT, "half.txt"))
                o.screenshot(os.path.join(OUT, "half.png"))
                print("wrote", os.path.join(OUT, "half.png"))
                return
        print("no half time reached")
        print("\n".join(o.snapshot()))
    finally:
        o.close()


if __name__ == "__main__":
    main()
