#!/usr/bin/env python3
"""Fill the Spectrum team sheet by watching how many players are placed.

Fire on the team display toggles the reserve at the top of the screen in
and out of the slot the pointer stands on, and the direction keys move
the pointer.  Whether a key helped can be read off the screen: our cards
are the skill lines on the right of each marking pair.  This searches for
the key that adds a card, undoing a fire that takes one away, and keeps
going until eleven are placed, then fires to leave selection and watches
for the match.

Usage:
    python tests/fm2_goal.py [steps] [watch]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "goal")
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

DIRS = ["S", "Q", "P", "I"]


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def band(s):
    """Which of the three team display screens is showing."""
    letters = []
    for ln in s.lines():
        k = ln.find("SK.")
        if k > 0:
            letters.append(ln[k - 1])
    if not letters:
        return "?"
    if "M" in letters:
        return "M"
    if "A" in letters and "D" not in letters:
        return "A"
    return "D"


def placed(s):
    """Our cards standing on this screen: skill lines in the right half."""
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
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 60
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

    def press(k, gap=0.8):
        r.press([k], gap=0.25)
        time.sleep(gap)

    counts = {"D": 0, "M": 0, "A": 0}
    state = {"s": None}

    def measure():
        state["s"] = grab()
        b = band(state["s"])
        n = placed(state["s"])
        counts[b] = max(counts.get(b, 0), n)
        return n, b

    def total():
        return counts["D"] + counts["M"] + counts["A"]

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
        for _ in range(8):
            s = grab()
            if "OPPONENT" in s.text():
                break
            press("ENTER", 1.6)
        n, b = measure()
        log("team display: band %s, placed %d, total %d" % (b, n, total()))

        di = 0
        for step in range(steps):
            n, b = measure()
            # 1. a fire that adds a card is always good
            press("ENTER")
            m, b2 = measure()
            if m > n:
                counts[b2] = m
                log("[%2d] fire added one on %s -> %d (total %d)" % (
                    step, b2, m, total()))
                continue
            if m < n:
                # it took one away; put him back
                press("ENTER")
                m, b2 = measure()
                log("[%2d] fire lifted one, put back -> %d" % (step, m))
            # 2. try a direction, then fire
            worked = False
            for _ in range(len(DIRS)):
                d = DIRS[di % len(DIRS)]
                di += 1
                press(d)
                n2, b3 = measure()
                press("ENTER")
                m2, b4 = measure()
                if m2 > max(n2, n) or total() > 0 and m2 > counts.get(b4, 0):
                    counts[b4] = max(counts.get(b4, 0), m2)
                    log("[%2d] %s then fire -> %d on %s (total %d)" % (
                        step, d, m2, b4, total()))
                    worked = True
                    break
                if m2 < n2:
                    press("ENTER")
                    log("[%2d] %s then fire lifted, put back" % (step, d))
                else:
                    log("[%2d] %s then fire: %d on %s" % (step, d, m2, b4))
            if total() >= 11:
                log("eleven picked")
                break
            if not worked and step > 12:
                pass
        log("bands %s total %d" % (counts, total()))
        with open(os.path.join(OUT, "state.txt"), "w") as fh:
            fh.write(state["s"].text() + "\n\n" +
                     "\n".join(state["s"].colours()) + "\n")
        print(state["s"].text(), flush=True)

        # leave selection, take two substitutes, then watch for the match
        for i in range(6):
            press("ENTER", 1.5)
            s = grab()
            log("  fire %d: %s" % (i, " / ".join(s.lines()[:2])))
            if "OPPONENT" not in s.text():
                break
        log("watching %ds" % watch)
        last = state["s"].text()
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
