#!/usr/bin/env python3
"""Fill the Spectrum team sheet by measuring progress after each key.

Fire toggles a player between the reserve slot and the slot the pointer is
on, and the direction keys move the pointer, so the sheet can be filled
blind as long as the number of players standing in slots can be counted.
That is what this does: our cards are the skill lines below the reserve
slot, and the search presses a key, counts the cards, and keeps going with
whichever key added one.  A key that takes a card away is undone by firing
again, because fire is a toggle.

Usage:
    python tests/fm2_fill4.py [steps] [watch]
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

OUT = os.path.join(ROOT, "build", "fill4")
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

KEYS = ["ENTER", "S", "ENTER", "P", "ENTER", "Q", "ENTER", "I"]


def placed(s):
    """Our players standing in a slot.

    Each pitch slot is a pair: the opposition's card on the left and ours
    on the right, so our skill lines are the ones whose SK. sits in the
    right-hand half of the row.
    """
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


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def thumb(s):
    h = hashlib.md5(s.text().encode())
    for row in s.bits:
        h.update(bytes(x & 0xFF for x in row))
    return h.hexdigest()[:8]


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    watch = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        """One grab is enough here; a torn frame still counts the cards."""
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

        s = None
        for _ in range(8):
            s = grab()
            if "OPPONENT" in s.text():
                break
            press("ENTER", 1.8)
        log("team display, placed %d" % placed(s))
        print(s.text(), flush=True)

        best = placed(s)
        last = thumb(s)
        for i in range(steps):
            for k in KEYS:
                press(k)
                s = grab()
                n = placed(s)
                if n > best:
                    best = n
                    last = thumb(s)
                    log("[%3d] %s -> placed %d" % (i, k, n))
                    break
                if n < best:
                    press("ENTER")          # undo the lift
                    s = grab()
                    log("[%3d] %s took one back (%d)" % (i, k, n))
            if best >= 11:
                log("eleven picked")
                break
            if thumb(s) != last:
                last = thumb(s)
        shutil.copy(tmp, os.path.join(OUT, "picked.png"))
        with open(os.path.join(OUT, "picked.txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
        log("final: placed %d" % placed(s))
        print(s.text(), flush=True)

        # Fire on the reserve slot now that eleven are picked, then take
        # the two substitutes.
        for _ in range(4):
            press("ENTER", 1.5)
            s = grab()
            log("  after fire: %s" % " / ".join(s.lines()[:2]))
            if "OPPONENT" not in s.text():
                break

        last = thumb(s)
        log("watching %ds" % watch)
        for i in range(watch):
            time.sleep(1.0)
            s = grab()
            if thumb(s) != last:
                last = thumb(s)
                log("  moved at +%ds" % (i + 1))
                print(s.text(), flush=True)
                shutil.copy(tmp, os.path.join(OUT, "watch%02d.png" % i))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
