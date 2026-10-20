#!/usr/bin/env python3
"""Poke the Spectrum match screens and watch how they answer.

From the manager's record screen the game is driven key by key.  After
each key the screen is sampled for a few seconds; every change of text or
of pixels is reported, so it shows whether the game is waiting, playing
an animation, or has moved on.  The final screen is dumped as text and as
ASCII art.

Usage:
    python tests/fm2_play.py ENTER ENTER P P Q S
    python tests/fm2_play.py --art 96 ENTER ENTER
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

OUT = os.path.join(ROOT, "build", "play")
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


def dump(s, name, art=0):
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(os.path.join(OUT, "_now.png"), os.path.join(OUT, name + ".png"))
    with open(os.path.join(OUT, name + ".txt"), "w") as fh:
        fh.write(s.text() + "\n\n" + "\n".join(s.colours()) + "\n")
    if art:
        with open(os.path.join(OUT, name + ".art.txt"), "w") as fh:
            fh.write(s.art(art) + "\n")
    log("dumped", name)


def main():
    argv = sys.argv[1:]
    art = 0
    if argv[:1] == ["--art"]:
        art = int(argv[1])
        argv = argv[2:]
    keys = argv or ["ENTER", "ENTER"]
    os.makedirs(OUT, exist_ok=True)
    r = fm2_ref.Ref()
    tmp = os.path.join(OUT, "_now.png")
    n = 0
    try:
        for _ in range(90):
            s = zxcap.capture(r.f, tmp)
            txt = s.text()
            if "MANAGEMENT RECORD" in txt:
                log("record screen")
                break
            for needle, kk in RULES:
                if needle in txt:
                    r.press(kk)
                    break
            else:
                r.press(["SPACE"], gap=0.4)
        else:
            raise RuntimeError("never reached the record screen")

        r.press(["ENTER"])
        time.sleep(1.5)
        s = zxcap.capture(r.f, tmp)
        dump(s, "p%02d-base" % n, art)
        print(s.text(), flush=True)
        last = thumb(s)

        for k in keys:
            n += 1
            log("press", k)
            r.press([k])
            quiet = 0
            for i in range(8):
                time.sleep(1.0)
                s = zxcap.capture(r.f, tmp)
                t = thumb(s)
                if t != last:
                    quiet = 0
                    last = t
                    log("  changed at +%ds" % (i + 1))
                    print(s.text(), flush=True)
                    if art:
                        print(s.art(art), flush=True)
                else:
                    quiet += 1
                    if quiet >= 4:
                        log("  still, after %ds" % (i + 1))
                        break
            dump(s, "p%02d-%s" % (n, k), art)
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
