#!/usr/bin/env python3
"""Capture the Spectrum match action frame by frame in Fuse.

The match screen redraws continuously, so a single grab only shows one
moment.  This walks to the match, then saves a run of frames plus a text
dump of each, so the static pitch and the moving sprites can be told
apart afterwards.

Usage:
    python tests/fm2_match.py [frames]
"""

import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import fm2_ref                                   # noqa: E402
import zxcap                                     # noqa: E402

OUT = os.path.join(ROOT, "build", "match")
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
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")
    n = 0
    try:
        log("fuse up")
        for i in range(90):
            s = zxcap.capture(r.f, tmp)
            txt = s.text()
            if "MANAGEMENT RECORD" in txt:
                log("record screen")
                break
            hit = None
            for needle, keys in RULES:
                if needle in txt:
                    hit = needle
                    r.press(keys)
                    break
            if hit is None:
                r.press(["SPACE"], gap=0.4)
        else:
            raise RuntimeError("never reached the record screen")

        log("to the league match")
        r.press(["ENTER"])
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        print(s.text(), flush=True)
        r.press(["ENTER"])          # kick off
        log("kick off")

        for i in range(frames):
            s = zxcap.capture(r.f, tmp)
            name = "f%03d" % n
            shutil.copy(tmp, os.path.join(OUT, name + ".png"))
            with open(os.path.join(OUT, name + ".txt"), "w") as fh:
                fh.write("\n".join(s.colours()) + "\n\n" + s.text() + "\n")
            if i % 5 == 0:
                log("frame", i)
                print(s.text(), flush=True)
            n += 1
            time.sleep(0.25)
        log("captured", n)
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
