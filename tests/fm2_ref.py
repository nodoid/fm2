#!/usr/bin/env python3
"""Reference walkthrough of the Spectrum Football Manager 2 in Fuse.

Boots the original TAP, drives it with the keyboard and reads the screen
back through the ZX ROM font, so the Oric port can be compared 1:1 with
the real thing.  Each screen is captured to ref/shots/ as a PNG and as
text.

Usage:
    python tests/fm2_ref.py office      # walk to the manager's office
    python tests/fm2_ref.py tour        # office, selection, match
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from fuse import Fuse          # noqa: E402
import specshot                # noqa: E402

TAPE = os.path.join(ROOT, "ref", "FOOTMNG2.TAP")
SHOTS = os.path.join(ROOT, "ref", "shots")

# prompt -> keys to send, in order.  The game asks a question with NO
# selected first, so YES is always "S" (down) then fire (Enter).
RULES = [
    ("PRESS 1 = KEMPSTON", ["2", "ENTER"]),
    ("PRESS SPACE TO CONTINUE", ["SPACE"]),
    ("MANAGE THIS TEAM?", ["S", "ENTER"]),
    ("CHOOSE TEAM COLOUR", ["S", "ENTER"]),
    ("ACCEPT THE OFFER?", ["S", "ENTER"]),
    ("BANK BALANCE", ["ENTER"]),
    ("SKILL LEVEL", ["ENTER"]),
    ("LOAD/SAVE GAME?", ["ENTER"]),
]


class Ref:
    def __init__(self, tape=TAPE):
        self.f = Fuse(tape=tape, speed=500, boot_wait=5)
        os.makedirs(SHOTS, exist_ok=True)
        self.last = ""
        self.n = 0

    def text(self):
        path = os.path.join(SHOTS, "_scan.png")
        self.f.screenshot(path)
        self.last = "\n".join(specshot.ocr_screen(specshot.spectrum(path)))
        return self.last

    def shot(self, name):
        path = os.path.join(SHOTS, name + ".png")
        self.f.screenshot(path)
        with open(os.path.join(SHOTS, name + ".txt"), "w") as fh:
            fh.write("\n".join(specshot.ocr_screen(
                specshot.spectrum(path))) + "\n")
        return path

    def press(self, keys, gap=0.35):
        for k in keys:
            self.f.tap(k, hold=0.12, gap=gap)

    def auto(self, stop, limit=40, settle=2.5, verbose=True):
        """Drive the pre-season questionnaire until `stop` is on screen."""
        for _ in range(limit):
            time.sleep(settle)
            txt = self.text()
            if stop and stop in txt:
                return txt
            for needle, keys in RULES:
                if needle in txt:
                    if verbose:
                        print("  >", needle, keys, flush=True)
                    self.press(keys)
                    break
            else:
                # picture screens (logos, titles) just wait for a key
                if verbose:
                    print("  > (picture) SPACE", flush=True)
                self.press(["SPACE"], gap=0.5)
        return self.text()

    def close(self):
        self.f.close()


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "office"
    r = Ref()
    try:
        r.auto("MANAGEMENT RECORD")
        r.shot("01-record")
        r.press(["ENTER"])          # decline load/save
        txt = r.auto("", limit=6)
        print(txt)
        r.shot("02-office")
    finally:
        r.close()


if __name__ == "__main__":
    main()
