#!/usr/bin/env python3
"""Fill the Spectrum team sheet by walking the pointer down the slots.

The team display keeps one reserve at the top of the screen and a pointer
that stands on one of our five slots (the skill lines down the right-hand
side).  Fire puts the reserve into the pointed slot and shows the next
reserve; the pointer steps down the column a few rows at a time with the
down key.  This walks the pointer down placing reserves, and when the
column will not take any more it switches to the next screen with the
right key and carries on, until eleven are placed.  Fire on the reserve
slot then leaves selection.

Usage:
    python tests/fm2_fill5.py [steps] [watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "fill5")
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

STEP = 4          # rows the pointer moves for one slot


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def our_rows(s):
    rows = []
    for i, ln in enumerate(s.lines()):
        if i < 2:
            continue
        k = ln.find("SK.")
        while k >= 0:
            if k >= 12:
                rows.append(i)
                break
            k = ln.find("SK.", k + 1)
    return rows


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    watch = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        for _ in range(3):
            r.f.screenshot(tmp)
            s = zxcap.Screen(tmp)
            if s.ok:
                return s
            time.sleep(0.2)
        return s

    def press(k, gap=0.7):
        r.press([k], gap=0.2)
        time.sleep(gap)

    def down(n=STEP):
        for _ in range(n):
            press("S")

    try:
        for _ in range(90):
            s = grab()
            if "MANAGEMENT RECORD" in s.text():
                break
            for needle, kk in RULES:
                if needle in s.text():
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        s = None
        for _ in range(8):
            s = grab()
            if "OPPONENT" in s.text():
                break
            press("ENTER", 1.6)
        log("start: %d placed at %s" % (len(our_rows(s)), our_rows(s)))

        best = len(our_rows(s))
        stall = 0
        for step in range(steps):
            press("ENTER")
            s = grab()
            rows = our_rows(s)
            if len(rows) > best:
                best = len(rows)
                stall = 0
                log("[%2d] placed %d at %s" % (step, best, rows))
                if best >= 11:
                    break
                down()
                continue
            if len(rows) < best:
                press("ENTER")           # undo the lift
                s = grab()
                log("[%2d] lifted, put back (%d)" % (step, len(our_rows(s))))
            down()
            press("ENTER")
            s = grab()
            rows = our_rows(s)
            if len(rows) > best:
                best = len(rows)
                stall = 0
                log("[%2d] placed %d at %s" % (step, best, rows))
                if best >= 11:
                    break
                down()
                continue
            if len(rows) < best:
                press("ENTER")
                s = grab()
            stall += 1
            if stall == 2:
                press("P")               # next team display screen
                s = grab()
                log("[%2d] switched screen: %s" % (step, our_rows(s)))
                best = max(best, len(our_rows(s)))
                stall = 0
            if stall > 6:
                log("no progress, stopping")
                break

        log("best %d, rows %s" % (best, our_rows(s)))
        with open(os.path.join(OUT, "state.txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        r.f.screenshot(os.path.join(OUT, "state.png"))
        print(s.text(), flush=True)

        for i in range(6):
            press("ENTER", 1.5)
            s = grab()
            log("  fire %d: %s" % (i, " / ".join(s.lines()[:2])))
            if "OPPONENT" not in s.text():
                break
        log("watching %ds" % watch)
        last = s.text()
        for i in range(watch):
            time.sleep(1.0)
            s = grab()
            if s.text() != last:
                last = s.text()
                log("  moved at +%ds" % (i + 1))
                print(s.text(), flush=True)
                r.f.screenshot(os.path.join(OUT, "watch%02d.png" % i))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
