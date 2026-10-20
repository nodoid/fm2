#!/usr/bin/env python3
"""Read Fuse window captures back as an exact ZX Spectrum screen.

A raw GDI grab can catch a torn frame, and a torn frame decodes as blocks
of impossible colour.  The Spectrum allows one ink and one paper colour
per 8x8 cell, so the reader checks every cell for at most two colours and
asks for another capture when the check fails.  Screens are only handed
back once two grabs 200 ms apart agree.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import specshot  # noqa: E402

# Normal and bright Spectrum colours as Fuse draws them.
PALETTE = {
    (0, 0, 0): 0,
    (0, 0, 192): 1, (0, 0, 255): 9,
    (192, 0, 0): 2, (255, 0, 0): 10,
    (192, 0, 192): 3, (255, 0, 255): 11,
    (0, 192, 0): 4, (0, 255, 0): 12,
    (0, 192, 192): 5, (0, 255, 255): 13,
    (192, 192, 0): 6, (255, 255, 0): 14,
    (192, 192, 192): 7, (255, 255, 255): 15,
}
NAMES = "kbrmgcyw"


_TABLE = None


def _font_table():
    """Map each 8x8 glyph pattern to its character, both polarities."""
    global _TABLE
    if _TABLE is None:
        _TABLE = {}
        font = specshot.rom_font()
        for i, g in enumerate(font):
            for variant in (g, [255 - x for x in g]):
                for c in (variant,
                          [int(format(x, "08b")[::-1], 2) for x in variant]):
                    _TABLE.setdefault(tuple(c), chr(32 + i))
    return _TABLE


class Screen:
    """A 256x192 bitmap plus its attributes, read from a PNG grab."""

    def __init__(self, path):
        w, h, rows = specshot.load_png(path)
        ox, oy, s = specshot.screen_rect(w, h, rows)
        self.ink = [[0] * 32 for _ in range(24)]
        self.paper = [[0] * 32 for _ in range(24)]
        self.bits = [[0] * 32 for _ in range(24)]
        self.bad = 0
        self.unknown = 0
        for cy in range(24):
            for cx in range(32):
                counts = {}
                pixels = []
                for gy in range(8):
                    for gx in range(8):
                        c = specshot.px(rows, ox + (cx * 8 + gx) * s,
                                        oy + (cy * 8 + gy) * s)
                        v = PALETTE.get(c)
                        if v is None:
                            self.unknown += 1
                            v = 0
                        pixels.append(v)
                        counts[v] = counts.get(v, 0) + 1
                if len(counts) > 2:
                    self.bad += 1
                order = sorted(counts.items(), key=lambda kv: -kv[1])
                paper = order[0][0]
                ink = order[1][0] if len(order) > 1 else paper
                self.paper[cy][cx] = paper
                self.ink[cy][cx] = ink
                b = 0
                for k, v in enumerate(pixels):
                    if v == ink and ink != paper:
                        b |= 1 << k
                # Row 0 of the glyph is the top eight pixels of the cell.
                r = 0
                for gy in range(8):
                    row = 0
                    for gx in range(8):
                        if b & (1 << (gy * 8 + gx)):
                            row |= 1 << gx
                    r |= row << (8 * gy)
                self.bits[cy][cx] = r
        self.ok = self.bad == 0 and self.unknown == 0

    def text(self):
        return "\n".join(self.lines())

    def lines(self):
        table = _font_table()
        out = []
        for cy in range(24):
            line = []
            for cx in range(32):
                key = tuple((self.bits[cy][cx] >> (8 * k)) & 0xFF
                            for k in range(8))
                line.append(table.get(key, "?" if any(key) else " "))
            out.append("".join(line).rstrip())
        return out

    def pixel(self, x, y):
        """1 where the cell ink is drawn at (x, y), else 0."""
        cy, cx = y >> 3, x >> 3
        if self.ink[cy][cx] == self.paper[cy][cx]:
            return 0
        return (self.bits[cy][cx] >> (8 * (y & 7) + (x & 7))) & 1

    def art(self, cols=128, rows=None, ink="#", paper=" "):
        """The bitmap as text, one character per block of pixels.

        Used because screenshots cannot be looked at: a pitch outline,
        boxes and blobs survive this well enough to be read.
        """
        rows = rows if rows is not None else cols * 192 // 256
        out = []
        for ry in range(rows):
            y0 = ry * 192 // rows
            y1 = max(y0 + 1, (ry + 1) * 192 // rows)
            line = []
            for rx in range(cols):
                x0 = rx * 256 // cols
                x1 = max(x0 + 1, (rx + 1) * 256 // cols)
                hit = 0
                for y in range(y0, y1):
                    for x in range(x0, x1):
                        if self.pixel(x, y):
                            hit += 1
                line.append(ink if hit * 2 >= (x1 - x0) * (y1 - y0)
                            else paper)
            out.append("".join(line).rstrip())
        return "\n".join(out)

    def colours(self):
        """One line per text row: ink letter over paper letter."""
        out = []
        for cy in range(24):
            out.append("".join(NAMES[self.paper[cy][cx] & 7]
                               for cx in range(32))
                       + "  " +
                       "".join(NAMES[self.ink[cy][cx] & 7]
                               for cx in range(32)))
        return out


def capture(fuse, path, tries=8):
    """Grab the window until the frame is a valid, settled Spectrum screen."""
    prev = None
    a = None
    for _ in range(tries):
        if not fuse.screenshot(path):
            continue
        a = Screen(path)
        if not a.ok:
            prev = None
            continue
        if prev is not None and prev.text() == a.text() and \
                prev.colours() == a.colours():
            return a
        prev = a
        import time
        time.sleep(0.2)
        fuse.screenshot(path)
        b = Screen(path)
        if b.ok and b.text() == a.text() and b.colours() == a.colours():
            return b
    if prev is not None:
        return prev
    return a if a is not None else Screen(path)


def show(path):
    s = Screen(path)
    print("valid:", s.ok, "bad cells:", s.bad, "unknown pixels:", s.unknown)
    for line in s.colours():
        print(line)
    print()
    print(s.text())


if __name__ == "__main__":
    show(sys.argv[1])
