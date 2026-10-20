#!/usr/bin/env python3
"""Fill the Spectrum team sheet automatically and play on into the match.

The team display, as it behaves in practice:

* fire on the reserve slot at the top puts the reserve list into the
  rolling state (FIRE TO QUIT),
* down rolls to the next reserve and fire takes the one shown, after
  which the pointer can leave the reserve slot,
* fire with the pointer on a pitch slot drops the reserve shown at the
  top into that slot and shows the next reserve,
* fire on a slot that already holds a player lifts him back into the
  reserves, and fire again puts him back, so a wrong fire is undoable,
* the pointer walks down the slots with the down key and back up with
  the up key, and with the pointer on the reserve slot the right and left
  keys change team display screen.

Because a key press can be dropped by the emulator, this tries a few
walk lengths per slot and keeps the one that put a player in place,
reading the result straight off the screen: our cards are the skill lines
in the right-hand half of a marking pair.

Usage:
    python tests/fm2_auto.py [watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "auto")
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
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 90
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

    def press(k, gap=0.8):
        r.press([k], gap=0.3)
        time.sleep(gap)

    def up_to_pool():
        for _ in range(7):
            press("Q", 0.5)
        return grab()

    def fire():
        press("ENTER")
        return grab()

    placed = set()

    def fill_one(target, s):
        """Put a reserve into the slot `target` down from the pool."""
        for walk in (target, target + 1, target - 1, target + 2, target - 2):
            if walk < 1:
                continue
            up_to_pool()
            s = grab()
            if "FIRE TO QUIT" not in s.text():
                # pool not in the rolling state; fire once to open it
                s = fire()
                if "FIRE TO QUIT" not in s.text():
                    s = fire()
            for _ in range(walk):
                press("S", 0.55)
            before = set(our_rows(grab()))
            s = fire()
            after = set(our_rows(s))
            if len(after) > len(before):
                placed.update(after)
                log("    slot %d (walk %d) -> %s" % (target, walk,
                                                    sorted(after)))
                return s
            if len(after) < len(before):
                s = fire()                  # undo the lift
                log("    slot %d (walk %d) lifted, undone" % (target, walk))
            else:
                log("    slot %d (walk %d) nothing" % (target, walk))
        return s

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
            press("ENTER", 1.7)
        log("team display")

        # reserve list into the rolling state, then take a reserve
        up_to_pool()
        for _ in range(3):
            if "FIRE TO QUIT" in grab().text():
                break
            fire()
        press("S", 0.6)
        fire()
        log("primed: %s" % grab().lines()[0].strip()[:26])

        for band in range(3):
            for target in range(1, 6):
                s = fill_one(target, s)
                if len(placed) >= 11:
                    break
            log("band %d done: %d placed, rows %s" % (band, len(placed),
                                                     sorted(placed)))
            with open(os.path.join(OUT, "band%d.txt" % band), "w") as fh:
                fh.write(grab().text() + "\n")
            r.f.screenshot(os.path.join(OUT, "band%d.png" % band))
            if len(placed) >= 11:
                break
            up_to_pool()
            press("P", 1.3)
            log("  switched screen: %s" % sorted(our_rows(grab())))

        # end selection, then the substitutes
        up_to_pool()
        for i in range(5):
            s = fire()
            log("  end selection %d: %s" % (i, " / ".join(s.lines()[:2])))
            if "OPPONENT" not in s.text():
                break
        for i in range(5):
            s = fire()
            log("  sub fire %d: %s" % (i, " / ".join(s.lines()[:2])))
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
                with open(os.path.join(OUT, "watch%02d.txt" % i), "w") as fh:
                    fh.write(s.text() + "\n\n" + "\n".join(s.colours()) +
                             "\n")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
