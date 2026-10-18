#!/usr/bin/env python3
"""End-to-end tests: run the real game in Oricutron and read the screen.

The emulator's F11 key copies its 40x28 text screen to the Windows
clipboard, so the tests assert on what the Oric is really showing after
loading the tape the way a player would.

The host emulates the Oric well below real speed, so every step waits for
the page to settle instead of assuming a fixed drawing time.

Usage:
    python tests/e2e_oricutron.py            # expects build/fm2.tap
    python tests/e2e_oricutron.py --selftest # the on-machine test tape
"""

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from oricutron import Oricutron, default_exe  # noqa: E402

SHOTS = os.path.join(ROOT, "build", "shots")

passed = 0
failed = 0
failures = []


def check(cond, what):
    global passed, failed
    if cond:
        passed += 1
        print("ok   %s" % what, flush=True)
    else:
        failed += 1
        failures.append(what)
        print("FAIL %s" % what, flush=True)


def joined(lines):
    return "\n".join(lines)


def settle(o, timeout=40.0):
    """Read the screen until it stops changing (three identical captures)."""
    deadline = time.time() + timeout
    started = time.time()
    prev = o.snapshot()
    same = 0
    while time.time() < deadline:
        time.sleep(0.5)
        cur = o.snapshot()
        if cur == prev and any(line.strip() for line in cur):
            same += 1
            if same >= 2 and time.time() - started > 1.5:
                return cur
        else:
            same = 0
        prev = cur
    return prev


def wait_for(o, needle, timeout=60.0, shot=None):
    """Wait for `needle`, then wait for the page to finish drawing."""
    deadline = time.time() + timeout
    lines = o.snapshot()
    while time.time() < deadline:
        if needle in joined(lines):
            break
        time.sleep(0.5)
        lines = o.snapshot()
    if needle in joined(lines):
        lines = settle(o)
    if shot:
        o.snapshot(os.path.join(SHOTS, shot))
    return lines


def key(o, name, pause=0.4):
    o.tap(name)
    time.sleep(pause)


def load_tape(o):
    o.type("CLOAD")
    o.tap('"')
    o.tap('"')
    o.tap("ENTER")
    return wait_for(o, "FOOTBALL MANAGER 2", timeout=90,
                    shot="e2e_01_title.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tape", default=os.path.join(ROOT, "build", "fm2.tap"))
    ap.add_argument("--exe", default=default_exe())
    ap.add_argument("--selftest", action="store_true",
                    help="run the on-machine unit-test tape instead")
    args = ap.parse_args()

    os.makedirs(SHOTS, exist_ok=True)
    o = Oricutron(args.exe, args.tape, boot_wait=5)
    try:
        title = joined(load_tape(o))
        check("FOOTBALL MANAGER 2" in title, "title shows the game name")
        check("FOR THE ORIC ATMOS" in title, "title names the machine")
        check("ORIGINAL BY ADDICTIVE SOFTWARE" in title,
              "title credits Addictive")
        check("1  NEW GAME" in title, "title offers a new game")

        if args.selftest:
            text = joined(wait_for(o, "SELF TEST", timeout=180,
                                   shot="e2e_selftest.txt"))
            check("FAILURES   0" in text, "on-machine tests: no failures")
            check("ALL SELF TESTS PASSED" in text,
                  "on-machine tests report success")
            return

        # ---- choose a club -----------------------------------------------
        key(o, "1")
        text = joined(wait_for(o, "CHOOSE YOUR CLUB", shot="e2e_02_clubs.txt"))
        check("DIVISION 4" in text, "the career starts in Division 4")
        check("ALDERSHOT" in text and "DARLINGTON" in text,
              "division four clubs are listed")
        key(o, "ENTER")

        # ---- management screen -------------------------------------------
        text = joined(wait_for(o, "MANAGERS OFFICE", shot="e2e_03_office.txt"))
        check("TEAM DISPLAY" in text, "office lists the team display")
        check("TEAM SELECTION" in text, "office lists team selection")
        check("PLAY MATCH" in text, "office offers the next match")
        check(" WK 1" in text, "the season starts in week one")
        check("P 1" in text, "the club starts top of the table")

        # ---- team display --------------------------------------------------
        key(o, "1")
        text = joined(wait_for(o, "TEAM DISPLAY", shot="e2e_04_squad.txt"))
        check("POS SKILL FIT VAL" in text, "squad shows FM2 attributes")
        check(" A " in text and " D " in text and " M " in text
              and " A " in text, "positions are G/D/M/A")
        key(o, "ESC")

        # ---- team selection ------------------------------------------------
        key(o, "2")
        text = joined(wait_for(o, "TEAM SELECTION", shot="e2e_05_selection.txt"))
        check("VIEW MIDFIELD" in text, "selection opens on the midfield view")
        check("SELECTED 11 OF 11" in text, "eleven players are placed")
        check("TEAM READY" in text, "the auto selected team is valid")
        check("SQUAD" in text and "SUBS" in text,
              "selection shows the squad and substitutes")
        key(o, "P")
        text = joined(settle(o))
        check("VIEW ATTACK" in text, "the view can be changed")
        key(o, "I")
        key(o, "ESC")

        # ---- training ------------------------------------------------------
        key(o, "3")
        text = joined(wait_for(o, "PASSING HEIGHT", shot="e2e_06_training.txt"))
        check("PASSING LENGTH" in text, "training shows both passing sliders")
        key(o, "H")
        text = joined(settle(o))
        check("4 / 5" in text, "passing height can be raised")
        key(o, "L")
        text = joined(settle(o))
        check("4 / 5" in text, "passing length can be raised")
        key(o, "ESC")

        # ---- league table --------------------------------------------------
        key(o, "7")
        text = joined(wait_for(o, "LEAGUE TABLE", shot="e2e_07_table.txt"))
        check("DIVISION 4" in text, "the table shows the division")
        check("DARLINGTON" in text and "ALDERSHOT" in text,
              "the table lists every club")
        key(o, "ESC")

        # ---- finance -------------------------------------------------------
        key(o, "9")
        text = joined(wait_for(o, "CASH IN HAND", shot="e2e_08_finance.txt"))
        check("WEEKLY WAGES" in text, "finance shows wages")
        check("BOARD CONFIDENCE" in text, "finance shows the board")
        key(o, "ESC")

        # ---- the match -----------------------------------------------------
        key(o, "6")
        text = joined(wait_for(o, "KICK OFF", timeout=90,
                               shot="e2e_09_action.txt"))
        check("KICK OFF" in text, "the match kicks off")
        check("ALDERSHOT" in text, "the scoreboard shows the clubs")

        saw_half = False
        saw_full = False
        for _ in range(80):
            screen = joined(o.snapshot())
            if "HALF TIME - PRESS ENTER" in screen:
                key(o, "ENTER")
                continue
            if "HALF TIME TEAM TALK" in screen:
                saw_half = True
                o.snapshot(os.path.join(SHOTS, "e2e_10_halftime.txt"))
                key(o, "2")
                continue
            if "FULL TIME" in screen:
                saw_full = True
                o.snapshot(os.path.join(SHOTS, "e2e_11_fulltime.txt"))
                break
            for _ in range(2):
                o.tap("SPACE", hold=0.05, gap=0.25)
        check(saw_full, "the match reaches full time")
        check(saw_half, "half time is offered")

        key(o, "ENTER")
        text = joined(wait_for(o, "MANAGERS OFFICE", timeout=60,
                               shot="e2e_12_after.txt"))
        check(" WK 2" in text, "the week advances after the match")
        check("WIN" in text or "LOSS" in text or "DRAW" in text,
              "the result is reported")

        # ---- results -------------------------------------------------------
        key(o, "8")
        text = joined(wait_for(o, "RESULTS AND FIXTURES",
                               shot="e2e_13_results.txt"))
        check("ROUND" in text, "results name the round")
        key(o, "ESC")
    finally:
        o.close()

    print()
    print("%d checks, %d failures" % (passed, failed))
    for f in failures:
        print("  FAILED: %s" % f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
