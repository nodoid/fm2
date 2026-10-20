#!/usr/bin/env python3
"""Read the text off an Oricutron window screenshot.

The emulator draws the 240x200 bitmap at 2x with the top-left corner at
(80, 14) inside its window, and the game's HIRES text is the 5x7 font in
src/font.s (tools/mkfont.py).  Matching every 6x8 cell against that font
turns a screenshot into readable text, which is how the match screen can
be inspected without looking at a picture.

    python tools/oricocr.py build/oric/match.png
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "tests"))

import specshot                                   # noqa: E402
import mkfont                                     # noqa: E402

OX, OY, SCALE = 80, 14, 2
W, H = 40, 25


def table():
    out = {}
    for ch, art in mkfont.GLYPHS.items():
        rows = mkfont.rows(ch)
        # bit 4 of the row is the leftmost pixel of the glyph.
        pat = tuple((1 if (r >> (4 - i)) & 1 else 0)
                    for r in rows for i in range(5))
        out.setdefault(pat, ch)
    return out


def screen(path):
    w, h, rows = specshot.load_png(path)
    tbl = table()

    def bit(bx, by):
        x, y = OX + SCALE * bx, OY + SCALE * by
        if x >= w or y >= h:
            return 0
        return 1 if specshot.px(rows, x, y) != (0, 0, 0) else 0

    lines = []
    for cy in range(H):
        line = []
        for cx in range(W):
            pat = tuple(bit(cx * 6 + i, cy * 8 + r)
                        for r in range(7) for i in range(5))
            line.append(tbl.get(pat, "?" if any(pat) else " "))
        lines.append("".join(line).rstrip())
    return lines


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "build/oric/match.png"
    for i, ln in enumerate(screen(path)):
        print("%2d |%s" % (i, ln))


if __name__ == "__main__":
    main()
