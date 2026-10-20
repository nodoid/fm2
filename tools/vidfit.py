#!/usr/bin/env python3
"""Find the Spectrum screen rectangle inside a video frame.

The recording shows the machine's display inside a decorative panel, so
the 256x192 grid has to be located before any cell can be read.  The
search scores a candidate rectangle by how many of its cells decode as
exact eight-by-eight ROM font glyphs: the right rectangle turns text
into clean glyphs, any other blends them into noise.

    python tools/vidfit.py build/video/t300.raw 1280 720
    python tools/vidfit.py build/video/t300.raw 1280 720 --box 210,24,861,646
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import specshot                                    # noqa: E402

RGB = [(0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205),
       (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205),
       (0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255),
       (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]

_TABLE = None


def table():
    global _TABLE
    if _TABLE is None:
        _TABLE = {}
        for i, g in enumerate(specshot.rom_font()):
            for variant in (g, [255 - x for x in g]):
                for c in (variant,
                          [int(format(x, "08b")[::-1], 2) for x in variant]):
                    _TABLE.setdefault(tuple(c), chr(32 + i))
    return _TABLE


class Frame:
    """A video frame reduced to Spectrum palette indices."""

    def __init__(self, path, w, h):
        data = open(path, "rb").read()
        cache = {}
        idx = bytearray(w * h)
        for p in range(w * h):
            i = p * 3
            key = (data[i], data[i + 1], data[i + 2])
            v = cache.get(key)
            if v is None:
                best, bestd = 0, 1 << 30
                for k, (rr, gg, bb) in enumerate(RGB):
                    d = (rr - key[0]) ** 2 + (gg - key[1]) ** 2 + \
                        (bb - key[2]) ** 2
                    if d < bestd:
                        bestd, best = d, k
                v = best
                if len(cache) < 200000:
                    cache[key] = v
            idx[p] = v
        self.idx = idx
        self.w, self.h = w, h

    def at(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return 0
        return self.idx[y * self.w + x]

    def score(self, box, rows=range(3, 15)):
        """Matched glyph cells out of the non-blank ones in those rows."""
        x0, y0, bw, bh = box
        sx, sy = bw / 256.0, bh / 192.0
        tbl = table()
        hits = 0
        ink = 0
        for cy in rows:
            for cx in range(32):
                bits = 0
                for gy in range(8):
                    ys = y0 + int((cy * 8 + gy + 0.5) * sy)
                    for gx in range(8):
                        xs = x0 + int((cx * 8 + gx + 0.5) * sx)
                        if self.at(xs, ys) not in (0, 8):
                            bits |= 1 << (gy * 8 + gx)
                key = tuple((bits >> (8 * k)) & 0xFF for k in range(8))
                if any(key):
                    ink += 1
                    if key in tbl:
                        hits += 1
        return hits, ink


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("w", type=int)
    ap.add_argument("h", type=int)
    ap.add_argument("--box", default=None)
    a = ap.parse_args()

    f = Frame(a.path, a.w, a.h)
    if a.box:
        box = tuple(int(v) for v in a.box.split(","))
        hits, ink = f.score(box)
        print("box %s: %d glyph cells of %d inked" % (box, hits, ink))
        return

    best = None
    for x0 in range(180, 261, 9):
        for y0 in range(6, 55, 8):
            for bw in range(820, 941, 16):
                bh = int(bw * 3 / 4)
                if y0 + bh > a.h:
                    continue
                hits, ink = f.score((x0, y0, bw, bh))
                sc = hits - 0.2 * (ink - hits)
                if best is None or sc > best[0]:
                    best = (sc, (x0, y0, bw, bh), hits, ink)
                    print("  %s glyphs %d inked %d score %.1f"
                          % (best[1], hits, ink, sc), flush=True)
    print("best", best)


if __name__ == "__main__":
    main()
