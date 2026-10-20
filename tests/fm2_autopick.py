#!/usr/bin/env python3
"""Pick the Spectrum team sheet automatically.

What the team display does, from the manual and from watching it:

* the slot at the top is the reserve pool; fire on it shows FIRE TO QUIT,
* while FIRE TO QUIT is up, up/down rolls the reserves and fire takes the
  one shown, which leaves the pointer free to move on to a slot,
* down then moves the pointer to the next slot and fire drops the player
  there; the pool immediately shows the next reserve,
* with eleven picked, fire on the pool ends selection.

So the sheet is filled by repeating "down, fire" once a reserve has been
taken.  The script prints how many of our cards are on the sheet after
every step, and then watches whatever comes next for movement.

Usage:
    python tests/fm2_autopick.py [cycles] [watch]
"""

import hashlib
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "pick")
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


def thumb(s):
    h = hashlib.md5(s.text().encode())
    for row in s.bits:
        h.update(bytes(x & 0xFF for x in row))
    return h.hexdigest()[:8]


def dump(s, name, art=128):
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(os.path.join(OUT, "_now.png"), os.path.join(OUT, name + ".png"))
    with open(os.path.join(OUT, name + ".txt"), "w") as fh:
        fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n\n" +
                 s.art(art) + "\n")


def summary(s):
    ours = 0
    for ln in s.lines():
        if "SK." in ln and "OPPONENT" not in ln:
            ours += 1
    return "cards %2d  %s" % (
        ours, " | ".join(ln.strip() for ln in s.lines() if "SK." in ln)[:58])


def main():
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    watch = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")
    try:
        for _ in range(90):
            s = zxcap.capture(r.f, tmp)
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

        r.press(["ENTER"])              # into the team display
        time.sleep(2.0)
        r.press(["ENTER"])              # fire on the pool
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        log("pool:", summary(s))
        r.press(["S"])                  # roll the reserves
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        log("rolled:", summary(s))
        r.press(["ENTER"])              # take him
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        log("taken:", summary(s))

        last = thumb(s)
        for i in range(cycles):
            r.press(["S"])              # pointer down to the next slot
            time.sleep(1.4)
            r.press(["ENTER"])          # drop him there
            time.sleep(1.4)
            s = zxcap.capture(r.f, tmp)
            log("[%02d] %s" % (i, summary(s)))
            if thumb(s) != last:
                last = thumb(s)
        dump(s, "after-cycles")

        log("watching %ds" % watch)
        for i in range(watch):
            time.sleep(1.0)
            s = zxcap.capture(r.f, tmp)
            if thumb(s) != last:
                last = thumb(s)
                log("  moved at +%ds" % (i + 1))
                print(s.text(), flush=True)
                dump(s, "watch%02d" % i)
        dump(s, "final")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
