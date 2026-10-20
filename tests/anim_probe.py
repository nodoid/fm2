#!/usr/bin/env python3
"""Capture a burst of match frames so the animation can be measured.

Usage:
    python tests/anim_probe.py [count] [interval]
"""

import os
import sys
import time
import zlib
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402

OUT = os.path.join(ROOT, "build", "anim")


def diff(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
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
        paths = []
        for i in range(count):
            path = os.path.join(OUT, "f%02d.png" % i)
            o.screenshot(path)
            paths.append(path)
            time.sleep(interval)
        prev = None
        for p in paths:
            raw = open(p, "rb").read()
            if prev is not None:
                print(os.path.basename(p), "diff", diff(prev, raw))
            prev = raw
        print("frames in", OUT)
    finally:
        o.close()


if __name__ == "__main__":
    main()
