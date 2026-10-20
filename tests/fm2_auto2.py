#!/usr/bin/env python3
"""Fill the Spectrum team sheet and carry on into the match.

What the earlier probes established about the team display:

* the reserve slot at the top shows FIRE TO QUIT while the pointer is
  parked there and no reserve is held,
* the down key rolls the reserve list while the pointer is on that slot,
* fire there takes the reserve shown (his name stays up with a mark),
* the pointer then walks the pitch slots with the down key, the mark
  moving to the right edge of the slot it stands on,
* fire drops the held reserve into that slot and the next reserve comes
  up already held, so further slots only need a walk and a fire,
* fire on a slot that is already filled lifts the player back into the
  reserves, and another fire puts him back,
* the left and right keys change team display screen while the pointer
  is on the reserve slot.

This fills the sheet a slot at a time, reading the result off the screen
after every fire, then ends selection and watches what follows.

Usage:
    python tests/fm2_auto2.py [seconds-to-watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "auto2")
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
            if k >= 12 and i not in rows:
                rows.append(i)
                break
            k = ln.find("SK.", k + 1)
    return sorted(rows)


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        s = None
        for _ in range(4):
            r.f.screenshot(tmp)
            s = zxcap.Screen(tmp)
            if s.ok:
                return s
            time.sleep(0.15)
        return s

    def press(k, gap=0.7):
        r.press([k], gap=0.3)
        time.sleep(gap)

    def fire(gap=0.9):
        press("ENTER", gap)
        return grab()

    def pool_line(s):
        return s.lines()[0].strip()

    def go_pool():
        for _ in range(7):
            press("Q", 0.45)
        return grab()

    try:
        for _ in range(80):
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
        log("team display")

        def take():
            """Make sure a reserve is held; return the screen."""
            nonlocal s
            s = go_pool()
            log("    pool: %r rows %s" % (pool_line(s), our_rows(s)))
            for attempt in range(4):
                if "FIRE TO QUIT" in pool_line(s):
                    press("S", 0.6)          # roll the list
                    s = grab()
                    log("    rolled: %r" % pool_line(s))
                s = fire()
                log("    took:   %r rows %s" % (pool_line(s), our_rows(s)))
                if "FIRE TO QUIT" not in pool_line(s):
                    return True
            return False

        placed = set()

        def place_at(target, s):
            for walk in (target, target - 1, target + 1, target - 2,
                         target + 2):
                if walk < 1:
                    continue
                for _ in range(walk):
                    press("S", 0.5)
                before = set(our_rows(grab()))
                s = fire()
                after = set(our_rows(s))
                if len(after) > len(before):
                    placed.update(after)
                    log("    placed at walk %d: rows %s" % (walk, sorted(after)))
                    return s
                if len(after) < len(before):
                    s = fire()               # undo the lift
                    log("    walk %d lifted; undone rows %s"
                        % (walk, sorted(our_rows(s))))
                else:
                    log("    walk %d did nothing" % walk)
                s = go_pool()
            return s

        for band in range(3):
            if not take():
                log("could not take a reserve")
                break
            for target in range(1, 6):
                s = place_at(target, s)
                if len(placed) >= 11:
                    break
            log("band %d: %d placed at rows %s" % (band, len(placed),
                                                   sorted(placed)))
            r.f.screenshot(os.path.join(OUT, "band%d.png" % band))
            with open(os.path.join(OUT, "band%d.txt" % band), "w") as fh:
                fh.write(grab().text() + "\n")
            if len(placed) >= 11:
                break
            s = go_pool()
            press("P", 1.4)
            log("  next screen: rows %s" % our_rows(grab()))

        s = go_pool()
        for i in range(6):
            s = fire(1.4)
            log("  end/subs %d: %s | %s" % (i, " / ".join(s.lines()[:2]),
                                            pool_line(s)))
            if "OPPONENT" not in s.text():
                break

        log("watching %ds" % watch)
        last = s.text()
        with open(os.path.join(OUT, "watch00.txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        r.f.screenshot(os.path.join(OUT, "watch00.png"))
        for i in range(watch):
            time.sleep(1.0)
            s = grab()
            if s.text() != last:
                last = s.text()
                log("  moved at +%ds: %s" % (i + 1, " / ".join(s.lines()[:3])))
                n = i + 1
                r.f.screenshot(os.path.join(OUT, "watch%02d.png" % n))
                with open(os.path.join(OUT, "watch%02d.txt" % n), "w") as fh:
                    fh.write(s.text() + "\n")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
