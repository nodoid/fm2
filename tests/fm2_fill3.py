#!/usr/bin/env python3
"""Repeat a key pattern on the Spectrum team display and count the cards.

Filling the team sheet needs the right order of fire and direction keys,
and the only feedback is how many of our cards are showing.  This runs a
pattern of keys over and over, printing the count and the visible skill
lines after every repeat, so a pattern that fills slots can be told from
one that just lifts the same player back and forth.

Usage:
    python tests/fm2_fill3.py ENTER,S 20
    python tests/fm2_fill3.py ENTER,ENTER,S,ENTER 10
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

OUT = os.path.join(ROOT, "build", "fill3")
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

SQUAD = set("HUGHES BEARDSLEY BARNES STEVENS HATELEY LINEKER ROBSON "
            "WADDLE WILSON BROWN SMITH JONES TAYLOR CLARK WRIGHT".split())


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def thumb(s):
    h = hashlib.md5(s.text().encode())
    for row in s.bits:
        h.update(bytes(x & 0xFF for x in row))
    return h.hexdigest()[:8]


def summary(s):
    cards = 0
    named = []
    pool = ""
    for ln in s.lines():
        if "SK." in ln:
            if "OPPONENT" in ln:
                continue
            cards += 1
            named.append(ln.strip())
        for n in SQUAD:
            if n in ln:
                if not pool:
                    pool = ln.strip()
    return "cards %2d  pool[%s]  %s" % (cards, pool[:22],
                                        " / ".join(named)[:70])


def main():
    pattern = sys.argv[1].split(",") if len(sys.argv) > 1 else ["ENTER", "S"]
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    watch = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")

    def grab():
        return zxcap.capture(r.f, tmp)

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
            r.press(["ENTER"], gap=0.4)
            time.sleep(1.8)
        log("team display: %s" % summary(s))
        print(s.text(), flush=True)

        for i in range(cycles):
            for k in pattern:
                r.press([k], gap=0.4)
                time.sleep(1.3)
            s = grab()
            log("[%02d] %s" % (i, summary(s)))
            if os.environ.get("FM2_VERBOSE"):
                print(s.text(), flush=True)
        dump = os.path.join(OUT, "state.png")
        shutil.copy(tmp, dump)
        with open(os.path.join(OUT, "state.txt"), "w") as fh:
            fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")

        last = thumb(s)
        log("watching %ds" % watch)
        for i in range(watch):
            time.sleep(1.0)
            s = grab()
            if thumb(s) != last:
                last = thumb(s)
                log("  moved at +%ds" % (i + 1))
                print(s.text(), flush=True)
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
