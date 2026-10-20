#!/usr/bin/env python3
"""Follow the team display pointer by diffing the cell attributes.

The pointer is a highlight round one slot, and the slot layout is drawn
with attributes (ink, paper and their bright bits), so pressing a
direction and comparing which cells changed colour shows where the
pointer was and where it went.  That is how the display's geometry can be
mapped without being able to look at it.

Usage:
    python tests/fm2_ptr.py [key ...]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "ptr")
T0 = time.time()

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


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def attrs(s):
    return [(s.ink[cy][cx], s.paper[cy][cx]) for cy in range(24)
            for cx in range(32)]


def changed(a, b):
    out = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            out.append((i % 32, i // 32))
    return out


def blocks(cells):
    """One representative per cluster of changed cells."""
    left = set(cells)
    out = []
    for c in cells:
        if c not in left:
            continue
        out.append(c)
        for dx in range(-2, 3):
            for dy in range(-1, 2):
                left.discard((c[0] + dx, c[1] + dy))
    return out


def main():
    keys = sys.argv[1:] or ["S", "S", "S", "S", "Q", "Q", "Q", "I", "I",
                            "P", "P", "P"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        return zxcap.capture(r.f, tmp)

    def press_until(key, stop, tries=6, wait=1.6):
        s = grab()
        for _ in range(tries):
            if stop(s):
                return s
            r.press([key], gap=0.4)
            time.sleep(wait)
            s = grab()
            log("  %s -> now: %s" % (key, " / ".join(s.lines()[:1])))
        return s

    try:
        for _ in range(90):
            s = grab()
            txt = s.text()
            if "MANAGEMENT RECORD" in txt:
                break
            for needle, kk in RULES:
                if needle in txt:
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        log("record screen")

        s = press_until("ENTER", lambda s: "MANAGEMENT RECORD" not in s.text())
        log("left the record screen")
        s = press_until("ENTER", lambda s: "PRESS FIRE" not in s.text() and
                        "LEAGUE MATCH" not in s.text())
        log("team display")
        for ln in s.lines()[:14]:
            print("   |" + ln, flush=True)

        prev = s
        for k in keys:
            r.press([k], gap=0.4)
            time.sleep(1.5)
            s = grab()
            ch = changed(attrs(prev), attrs(s))
            log("press %s -> %d cells changed: %s" % (k, len(ch), " ".join(
                "%d,%d" % c for c in ch[:24])))
            for ln in s.lines()[:14]:
                print("   |" + ln, flush=True)
            prev = s
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
