#!/usr/bin/env python3
"""Walk a new game through every screen that touches the bitmap.

Checks the text screens come back correctly after a HIRES page (the
charset rebuild), and that half time still renders.

Usage:
    python tests/full_probe.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_screenshots as ms                     # noqa: E402

OUT = os.path.join(ROOT, "build", "full")


def show(o, tag):
    text = o.snapshot(os.path.join(OUT, tag + ".txt"))
    print("=== %s ===" % tag)
    print("\n".join(l.rstrip() for l in text).rstrip())
    return text


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
        ms.wait_for(o, "KIT COLOUR", 30)
        o.tap("1")
        ms.wait_for(o, "SPONSORSHIP", 30)
        o.tap("Y")
        ms.wait_for(o, "MANAGERS OFFICE", 30)

        o.tap("2")                       # HIRES team selection
        time.sleep(2.5)
        o.screenshot(os.path.join(OUT, "team-selection.png"))
        o.tap("ESC")
        time.sleep(0.8)
        show(o, "05-office-after-hires")

        o.tap("1")                       # text screen after HIRES
        time.sleep(0.6)
        show(o, "06-squad-after-hires")
        o.tap("ESC")
        time.sleep(0.5)

        o.tap("6")
        ms.wait_for(o, "KICK OFF", 120)
        for i in range(140):
            o.tap("SPACE")
            time.sleep(0.2)
            text = "\n".join(o.snapshot())
            if "HALF TIME" in text:
                print("=== half time ===")
                print(text.rstrip())
                o.snapshot(os.path.join(OUT, "07-half.txt"))
                o.screenshot(os.path.join(OUT, "07-half.png"))
                o.tap("2")
                break
        else:
            print("no half time")
            return
        for i in range(140):
            o.tap("SPACE")
            time.sleep(0.2)
            text = "\n".join(o.snapshot())
            if "MANAGERS OFFICE" in text or "SEASON" in text:
                print("=== after the match ===")
                print(text.rstrip())
                o.snapshot(os.path.join(OUT, "08-after.txt"))
                return
        print("=== still running ===")
        print("\n".join(o.snapshot()))
    finally:
        o.close()


if __name__ == "__main__":
    main()
