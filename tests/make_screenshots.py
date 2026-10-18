#!/usr/bin/env python3
"""Capture PNG screenshots of every screen in Oricutron.

The emulator runs the real tape; the script waits for each page to settle
(by reading the text screen) and then grabs the window bitmap.

Usage:
    python tests/make_screenshots.py           # -> docs/screens/*.png
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from oricutron import Oricutron, default_exe  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screens")


def joined(lines):
    return "\n".join(lines)


def settle(o, timeout=40.0):
    deadline = time.time() + timeout
    prev = o.snapshot()
    same = 0
    while time.time() < deadline:
        time.sleep(0.5)
        cur = o.snapshot()
        if cur == prev and any(l.strip() for l in cur):
            same += 1
            if same >= 2:
                return cur
        else:
            same = 0
        prev = cur
    return prev


def wait_for(o, needle, timeout=60.0):
    deadline = time.time() + timeout
    lines = o.snapshot()
    while time.time() < deadline:
        if needle in joined(lines):
            return settle(o)
        time.sleep(0.5)
        lines = o.snapshot()
        if needle in joined(lines):
            return settle(o)
    return lines


def shot(o, name):
    o.screenshot(os.path.join(OUT, name + ".png"))
    print("shot", name, flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    o = Oricutron(args_exe(), os.path.join(ROOT, "build", "fm2.tap"),
                  boot_wait=5)
    try:
        o.type("CLOAD")
        o.tap('"')
        o.tap('"')
        o.tap("ENTER")
        wait_for(o, "FOOTBALL MANAGER 2", 90)
        shot(o, "01-title")

        o.tap("1")
        wait_for(o, "CHOOSE YOUR CLUB")
        shot(o, "02-choose-club")

        o.tap("ENTER")
        wait_for(o, "MANAGERS OFFICE")
        shot(o, "03-office")

        o.tap("1")
        wait_for(o, "TEAM DISPLAY")
        shot(o, "04-team-display")
        o.tap("ESC")
        time.sleep(1)

        o.tap("2")
        wait_for(o, "TEAM SELECTION")
        shot(o, "05-team-selection")
        o.tap("P")
        time.sleep(2)
        settle(o)
        shot(o, "06-selection-attack")
        o.tap("ESC")
        time.sleep(1)

        o.tap("3")
        wait_for(o, "PASSING HEIGHT")
        shot(o, "07-training")
        o.tap("ESC")
        time.sleep(1)

        o.tap("7")
        wait_for(o, "LEAGUE TABLE")
        shot(o, "08-league-table")
        o.tap("ESC")
        time.sleep(1)

        o.tap("9")
        wait_for(o, "CASH IN HAND")
        shot(o, "09-finance")
        o.tap("ESC")
        time.sleep(1)

        o.tap("6")
        wait_for(o, "KICK OFF", 90)
        time.sleep(4)
        settle(o)
        shot(o, "10-match-action")

        saw_half = False
        for _ in range(120):
            screen = joined(o.snapshot())
            if "HALF TIME - PRESS ENTER" in screen:
                shot(o, "11-half-time")
                o.tap("ENTER")
                time.sleep(1)
                continue
            if "HALF TIME TEAM TALK" in screen:
                saw_half = True
                shot(o, "12-half-time-talk")
                o.tap("2")
                time.sleep(1)
                continue
            if "FULL TIME" in screen:
                shot(o, "13-full-time")
                break
            for _ in range(2):
                o.tap("SPACE", hold=0.05, gap=0.25)
        o.tap("ENTER")
        wait_for(o, "MANAGERS OFFICE")
        shot(o, "14-office-after")

        o.tap("8")
        wait_for(o, "ROUND")
        shot(o, "15-results")
        o.tap("ESC")
        time.sleep(1)

        o.tap("R")
        wait_for(o, "MANAGEMENT RECORD")
        shot(o, "16-record")
        print("half time seen:", saw_half)
    finally:
        o.close()


def args_exe():
    exe = default_exe()
    if not exe:
        raise SystemExit("Oricutron not found (set ORICUTRON)")
    return exe


if __name__ == "__main__":
    main()
