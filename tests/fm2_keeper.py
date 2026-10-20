#!/usr/bin/env python3
"""Find how the goalkeeper's slot on the defence screen is filled.

The pointer's down-walk on the defence screen reaches the four outfield
slots, and the keeper's slot over the goal is not among them, so this
tries every walk length with a goalkeeper held, undoing each placement
that lands elsewhere, and then tries moving sideways from each stop.

    python tests/fm2_keeper.py
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "keeper")
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


def rows_of(s):
    rows = []
    for i, ln in enumerate(s.lines()):
        k = ln.find("SK.")
        while k >= 0:
            if k >= 12:
                rows.append(i)
                break
            k = ln.find("SK.", k + 1)
    return rows


def main():
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

    def fire(settle=2.2):
        press("ENTER", settle)
        return grab()

    def dump(s, tag):
        with open(os.path.join(OUT, tag + ".txt"), "w") as fh:
            fh.write(s.text() + "\n")
        r.f.screenshot(os.path.join(OUT, tag + ".png"))

    def idle():
        s = None
        for _ in range(7):
            press("Q", 0.5)
        s = grab()
        for _ in range(4):
            if "FIRE TO QUIT" in s.lines()[0]:
                return s
            s = fire()
        return s

    def take_g():
        s = idle()
        for _ in range(45):
            press("S", 0.6)
            s = grab()
            stat = s.lines()[1] if len(s.lines()) > 1 else ""
            if "G SK." not in stat:
                continue
            s = fire()
            if "FIRE TO QUIT" not in s.lines()[0]:
                return s
        return s

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
        log("team display: rows %s" % rows_of(s))
        dump(s, "start")

        for step in ("I", "P", "I I", "P P", "S I", "S P"):
            s = idle()
            for _ in range(1):
                press("S", 0.6)
                s = fire()
            if "FIRE TO QUIT" in s.lines()[0]:
                log("  %s: no reserve held" % step)
                continue
            log("  %s: held %r %r" % (step, s.lines()[0].strip(),
                                       s.lines()[1].strip()))
            for k in step.split():
                press(k, 0.7)
            before = rows_of(grab())
            s = fire()
            after = rows_of(s)
            log("    after %s -> %s" % (before, after))
            dump(s, step.replace(" ", "_"))
            if 13 in after:
                log("    keeper slot reached with %s" % step)
                break
            if len(after) > len(before):
                s = fire()
                log("    undone -> %s" % rows_of(s))
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
