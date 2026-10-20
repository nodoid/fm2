#!/usr/bin/env python3
"""Find the key that starts the match action.

Boots the Spectrum game to the league-match team display, then tries keys
one at a time.  For each key the screen is sampled three times; a screen
whose pixels keep changing with no key pressed is the match action
running, which is what we are looking for.  A screen that holds still is
reported with its first text row so the change can be identified.

Usage:
    python tests/fm2_keys.py [key ...]
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

OUT = os.path.join(ROOT, "build", "keys")
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

DEFAULT = ["SPACE", "ENTER", "P", "Q", "S", "I", "0", "1", "2", "3",
           "F", "M", "N", "K", "O", "W", "A", "D", "G", "H", "J", "L",
           "R", "T", "U", "V", "X", "Y", "Z", "B", "C", "E"]


def log(*a):
    print("[%6.1f]" % (time.time() - T0), *a, flush=True)


def thumb(s):
    h = hashlib.md5(s.text().encode())
    for row in s.bits:
        h.update(bytes(x & 0xFF for x in row))
    return h.hexdigest()[:8]


def main():
    keys = sys.argv[1:] or DEFAULT
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

        # LEAGUE MATCH, fire, then fire again onto the reserve slot.
        for k in ("ENTER", "ENTER", "ENTER"):
            r.press([k])
            time.sleep(2.0)
        s = zxcap.capture(r.f, tmp)
        log("team display; top rows:")
        for line in s.lines()[:6]:
            print("   |" + line, flush=True)

        for k in keys:
            log("press", k)
            r.press([k])
            time.sleep(0.8)
            seen = []
            for i in range(4):
                time.sleep(0.7)
                s = zxcap.capture(r.f, tmp)
                seen.append((thumb(s), s))
            animated = len(set(t for t, _ in seen)) > 1
            s = seen[-1][1]
            if animated:
                print("   animating", flush=True)
            else:
                print("   still: " + " / ".join(s.lines()[:2]), flush=True)
            if animated:
                with open(os.path.join(OUT, "action.txt"), "w") as fh:
                    fh.write(s.text() + "\n\n" + "\n".join(s.colours()) +
                             "\n\n" + s.art(128) + "\n")
                import shutil
                shutil.copy(tmp, os.path.join(OUT, "action.png"))
                log("ACTION FOUND after", k)
                return
    finally:
        r.close()
        log("done")


if __name__ == "__main__":
    main()
