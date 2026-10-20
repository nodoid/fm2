#!/usr/bin/env python3
"""Watch what one key press at a time does to the team display.

The pointer mark is a flashing cell (the captures are compared for
changes), so pressing DOWN once and diffing two grabs shows which cell
the pointer moved to.  This isolates the pool and slot mechanics.

    python tests/fm2_cursor.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "cursor")
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


def main():
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_a.png")
    tmp2 = os.path.join(OUT, "_b.png")

    def grab(path=tmp):
        s = None
        for _ in range(4):
            r.f.screenshot(path)
            s = zxcap.Screen(path)
            if s.ok:
                return s
            time.sleep(0.15)
        return s

    def press(k, gap=0.8):
        r.press([k], gap=0.3)
        time.sleep(gap)

    def pool(s):
        return s.lines()[0].strip()

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

        # anchor on the pool
        for i in range(8):
            s = grab()
            if "FIRE TO QUIT" in pool(s):
                break
            press("Q", 0.5)
        log("anchor: pool %r" % pool(s))

        def diff(tag):
            a = grab(tmp)
            time.sleep(0.45)
            b = grab(tmp2)
            ch = []
            for cy in range(24):
                for cx in range(32):
                    if (a.ink[cy][cx] != b.ink[cy][cx] or
                            a.paper[cy][cx] != b.paper[cy][cx] or
                            a.bits[cy][cx] != b.bits[cy][cx]):
                        ch.append((cx, cy))
            log("%-10s pool %-28r changed %s"
                % (tag, pool(b), " ".join("%d,%d" % c for c in ch[:14])))
            return b

        s = diff("idle")
        press("S", 0.7)
        s = diff("S1")
        s = diff("  (again)")
        log("  pool line 1: %r" % (s.lines()[1] if len(s.lines()) > 1 else ""))
        press("S", 0.7)
        s = diff("S2")
        press("S", 0.7)
        s = diff("S3")
        press("ENTER", 0.9)
        s = diff("FIRE")
        log("  rows %s" % [i for i, ln in enumerate(s.lines())
                           if "SK." in ln and ln.find("SK.") >= 12])
        def rows(s):
            return [i for i, ln in enumerate(s.lines())
                    if "SK." in ln and ln.find("SK.") >= 12]

        press("S", 0.8)
        s = diff("S once")
        press("ENTER", 0.9)
        s = diff("FIRE after S")
        log("  rows %s" % rows(s))
        press("Q", 0.8)
        s = diff("Q once")
        press("ENTER", 0.9)
        s = diff("FIRE after Q")
        log("  rows %s" % rows(s))
        for i in range(1, 4):
            press("S", 0.8)
            press("ENTER", 0.9)
            s = diff("S+fire %d" % i)
            log("  rows %s" % rows(s))
        with open(os.path.join(OUT, "end.txt"), "w") as fh:
            fh.write(s.text() + "\n")
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
