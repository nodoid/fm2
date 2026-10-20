#!/usr/bin/env python3
"""Find the key that moves the Spectrum pointer between pitch slots.

Fire toggles the reserve at the top of the team display in and out of the
slot the pointer is on, so once one player is standing the rest can be
placed as soon as we know which direction key carries the pointer to the
next slot.  This places one player with the known fire/down rhythm and
then tries each direction followed by fire, reporting how many of our
cards are standing after every press.

Usage:
    python tests/fm2_pick2.py [watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "pick2")
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


def placed(s):
    n = 0
    for i, ln in enumerate(s.lines()):
        if i < 2:
            continue
        k = ln.find("SK.")
        while k >= 0:
            if k >= 12:
                n += 1
                break
            k = ln.find("SK.", k + 1)
    return n


def main():
    watch = int(sys.argv[1]) if len(sys.argv) > 1 else 30
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

    def press(k, gap=0.9):
        r.press([k], gap=0.25)
        time.sleep(gap)

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
        s = None
        for _ in range(8):
            s = grab()
            if "OPPONENT" in s.text():
                break
            press("ENTER", 1.6)
        log("team display, placed %d" % placed(s))

        # known rhythm: fire opens the reserve list, down rolls it, fire
        # takes one, down points at a slot, fire puts him there.
        n = placed(s)
        for i in range(10):
            press("ENTER")
            s = grab()
            if placed(s) != n:
                n = placed(s)
                log("  fire -> placed %d" % n)
                if n:
                    break
            press("S")
            s = grab()
            if placed(s) != n:
                n = placed(s)
                log("  down -> placed %d" % n)

        for k in ("S", "Q", "P", "I", "S", "Q", "P", "I"):
            before = placed(s)
            press(k)
            s = grab()
            mid = placed(s)
            press("ENTER")
            s = grab()
            after = placed(s)
            log("%s: %d -> %d -> fire %d  %s" % (
                k, before, mid, after,
                " / ".join(x for x in s.lines() if "SK." in x)[:60]))
            if after < before:
                press("ENTER")          # toggle the lifted player back
                s = grab()
                log("  put back -> placed %d" % placed(s))
            if after > before:
                log("  %s moves the pointer on" % k)
                break

        with open(os.path.join(OUT, "state.txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        r.f.screenshot(os.path.join(OUT, "state.png"))
        print(s.text(), flush=True)

        log("watching %ds" % watch)
        last = s.text()
        for i in range(watch):
            time.sleep(1.0)
            s = grab()
            if s.text() != last:
                last = s.text()
                log("  moved at +%ds" % (i + 1))
                print(s.text(), flush=True)
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
