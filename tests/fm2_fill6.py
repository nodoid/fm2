#!/usr/bin/env python3
"""Fill the Spectrum team sheet with the reserve-prime rhythm.

Working out from the screens themselves:

* fire on the reserve slot at the top puts the reserve list into the
  rolling state (FIRE TO QUIT),
* down rolls through the reserves and fire takes the one shown, which
  lets the pointer leave the reserve slot,
* the pointer starts on the first of our five slots (the skill lines down
  the right-hand side) and down moves it four rows at a time to the next
  one, while fire drops the reserve shown at the top into the pointed
  slot and immediately shows the next reserve,
* so the sheet fills with "fire, down x4, fire, down x4 ..." until the
  column is full, then the next screen is reached with the right key.

Usage:
    python tests/fm2_fill6.py [steps] [watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "fill6")
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

STEP = 4


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

    def place_and_move(tag):
        """Fire, then walk the pointer down a slot.  Returns the rows."""
        press("ENTER")
        s = grab()
        rows = our_rows(s)
        log("  %s fire -> %d %s" % (tag, len(rows), rows))
        for _ in range(STEP):
            press("S")
        return rows, s

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
        log("start: %s" % our_rows(s))

        # prime: fire on the reserve slot, roll once, take the reserve
        press("ENTER")
        s = grab()
        log("  prime fire -> %s" % s.lines()[0].strip()[:26])
        press("S")
        press("ENTER")
        s = grab()
        log("  prime take -> %s" % s.lines()[0].strip()[:26])

        best = len(our_rows(s))
        rows, s = place_and_move("first")
        if len(rows) > best:
            best = len(rows)
        log("after first: %d at %s" % (best, rows))

        for step in range(steps):
            if best >= 11:
                break
            rows, s = place_and_move(step)
            if len(rows) > best:
                best = len(rows)
                log("[%2d] now %d at %s" % (step, best, rows))
                continue
            if len(rows) < best:
                press("ENTER")              # put the lifted player back
                s = grab()
                log("[%2d] lifted, back to %d" % (step, len(our_rows(s))))
            press("P")                      # next team display screen
            s = grab()
            log("[%2d] next screen: %s" % (step, our_rows(s)))
            best = max(best, len(our_rows(s)))
        log("best %d" % best)

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
