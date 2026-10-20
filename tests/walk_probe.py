#!/usr/bin/env python3
"""Walk the new-game flow and capture each screen.

Usage:
    python tests/walk_probe.py [matchframes]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402

OUT = os.path.join(ROOT, "build", "walk")


def show(o, tag):
    text = o.snapshot(os.path.join(OUT, tag + ".txt"))
    print("=== %s ===" % tag)
    print("\n".join(l.rstrip() for l in text).rstrip())


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 6
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
        show(o, "01-club-div4")
        o.tap("1")                      # division 1
        time.sleep(0.4)
        show(o, "02-club-div1")
        o.tap("ENTER")
        ms.wait_for(o, "SPONSORSHIP", 30)
        show(o, "03-sponsor")
        o.tap("Y")
        ms.wait_for(o, "MANAGERS OFFICE", 30)
        show(o, "04-office")
        o.tap("6")
        ms.wait_for(o, "KICK OFF", 90)
        for i in range(frames):
            o.screenshot(os.path.join(OUT, "match-%02d.png" % i))
            time.sleep(0.25)
        print("captured", frames, "match frames in", OUT)
    finally:
        o.close()


if __name__ == "__main__":
    main()
