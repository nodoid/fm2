#!/usr/bin/env python3
"""Sit on the Spectrum team display and watch it for a while.

Reaches the league-match team display with a single fire press, then
samples the screen every two seconds for a minute and reports every
change.  The match may simply be on a timer rather than waiting for a
key, which would show up here as an animated screen.

Usage:
    python tests/fm2_idle.py [seconds] [key ...]

The optional keys are pressed, a couple of seconds apart, once the
record screen has been left, before the watch starts.
"""

import hashlib
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "idle")
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


def main():
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    pre = sys.argv[2:]
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
        r.press(["ENTER"])
        time.sleep(2.0)
        for k in pre:
            log("pre-press", k)
            r.press([k], gap=0.5)
            time.sleep(2.0)
        s = zxcap.capture(r.f, tmp)
        log("watching from here")
        print(s.text(), flush=True)
        last = thumb(s)
        changes = 0
        for i in range(secs // 2):
            time.sleep(2.0)
            s = zxcap.capture(r.f, tmp)
            t = thumb(s)
            if t != last:
                changes += 1
                last = t
                log("change %d at +%ds" % (changes, 2 * (i + 1)))
                print(s.text(), flush=True)
                with open(os.path.join(OUT, "c%02d.txt" % changes), "w") as fh:
                    fh.write(s.text() + "\n\n" + s.art(128) + "\n")
                import shutil
                shutil.copy(tmp, os.path.join(OUT, "c%02d.png" % changes))
        log("done, changes:", changes)
    finally:
        r.close()


if __name__ == "__main__":
    main()
