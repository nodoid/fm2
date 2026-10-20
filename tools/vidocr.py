#!/usr/bin/env python3
"""Read the Spectrum screen out of a video frame.

The reference video shows the game inside a rounded panel.  This samples
that panel on the Spectrum's 8x8 cell grid, decodes each cell as ink over
paper, and matches the glyph against the ZX ROM font, so the text of a
match screen can be read back from the recording.

    ffmpeg -ss 114 -i build/video/fm2.mp4 -frames:v 1 -f rawvideo \
        -pix_fmt rgb24 build/video/f114.raw -y
    python tools/vidocr.py build/video/f114.raw 1280 720 [x y w h]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import specshot                                   # noqa: E402

# the Spectrum colours as the console draws them (0xCD steps)
LEVELS = (0, 0xCD)
PALETTE = {}
for _b in range(8):
    for _bright in (0, 1):
        _m = 0xFF if _bright else 0xCD
        _v = (((_b & 4) and _m), ((_b & 2) and _m), ((_b & 1) and _m))
        PALETTE[_v] = (_b + (8 if _bright else 0),
                       ((_b & 1) << 2), ((_b & 2) << 1), ((_b & 4) >> 0))
PALETTE = None

# colour number -> (red, green, blue) on the Spectrum
RGB = {0: (0, 0, 0), 1: (0, 0, 205), 2: (205, 0, 0), 3: (205, 0, 205),
       4: (0, 205, 0), 5: (0, 205, 205), 6: (205, 205, 0),
       7: (205, 205, 205), 8: (0, 0, 0), 9: (0, 0, 255), 10: (255, 0, 0),
       11: (255, 0, 255), 12: (0, 255, 0), 13: (0, 255, 255),
       14: (255, 255, 0), 15: (255, 255, 255)}


def nearest(r, g, b, bright_first=False):
    best, bestd = 0, 1 << 30
    for k, (rr, gg, bb) in RGB.items():
        if bright_first and k < 8:
            continue
        d = (rr - r) ** 2 + (gg - g) ** 2 + (bb - b) ** 2
        if d < bestd:
            bestd, best = d, k
    return best


_TABLE = None


def font_table():
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
    def __init__(self, path, w, h, box=None):
        self.px = open(path, "rb").read()
        self.w, self.h = w, h
        self.sx = 1.0
        self.sy = 1.0
        if box is None:
            box = self.panel()
        self.x0, self.y0, self.bw, self.bh = box
        self.sx = self.bw / 256.0
        self.sy = self.bh / 192.0
        self.bits = [[0] * 32 for _ in range(24)]
        self.ink = [[0] * 32 for _ in range(24)]
        self.paper = [[0] * 32 for _ in range(24)]
        for cy in range(24):
            for cx in range(32):
                counts = {}
                pixels = []
                for gy in range(8):
                    for gx in range(8):
                        x = int(self.x0 + (cx * 8 + gx) * self.sx)
                        y = int(self.y0 + (cy * 8 + gy) * self.sy)
                        v = self.at(x, y)
                        pixels.append(v)
                        counts[v] = counts.get(v, 0) + 1
                order = sorted(counts.items(), key=lambda kv: -kv[1])
                paper = order[0][0]
                ink = order[1][0] if len(order) > 1 else paper
                self.paper[cy][cx] = paper & 7
                self.ink[cy][cx] = ink & 7
                b = 0
                for k, v in enumerate(pixels):
                    if v == ink and ink != paper:
                        b |= 1 << k
                r = 0
                for gy in range(8):
                    row = 0
                    for gx in range(8):
                        if b & (1 << (gy * 8 + gx)):
                            row |= 1 << gx
                    r |= row << (8 * gy)
                self.bits[cy][cx] = r

    def at(self, x, y):
        """Average a small box, so the video's scaling cannot fool us.

        The recording is bilinear-scaled, so a single pixel can sit
        between two palette entries.  Averaging the pixels that make up
        one Spectrum pixel recovers the colour it came from.
        """
        dx = max(1, int(self.sx * 0.5))
        dy = max(1, int(self.sy * 0.5))
        r = g = b = n = 0
        for yy in range(y - dy, y + dy + 1):
            if yy < 0 or yy >= self.h:
                continue
            base = yy * self.w
            for xx in range(x - dx, x + dx + 1):
                if xx < 0 or xx >= self.w:
                    continue
                i = (base + xx) * 3
                r += self.px[i]
                g += self.px[i + 1]
                b += self.px[i + 2]
                n += 1
        if not n:
            return 0
        return nearest(r // n, g // n, b // n)

    def panel(self):
        """Bounding box of the widest run of non-black rows and columns."""
        rows = []
        for y in range(0, self.h, 3):
            n = 0
            for x in range(0, self.w, 3):
                if self.at(x, y) not in (0, 8):
                    n += 1
            rows.append((y, n))
        good = [y for y, n in rows if n > self.w // 30]
        y0, y1 = min(good), max(good)
        cols = []
        for x in range(0, self.w, 3):
            n = 0
            for y in range(y0, y1, 3):
                if self.at(x, y) not in (0, 8):
                    n += 1
            cols.append((x, n))
        good = [x for x, n in cols if n > (y1 - y0) // 30]
        x0, x1 = min(good), max(good)
        return (x0, y0, x1 - x0, y1 - y0)

    def text(self):
        tbl = font_table()
        out = []
        for cy in range(24):
            line = []
            for cx in range(32):
                key = tuple((self.bits[cy][cx] >> (8 * k)) & 0xFF
                            for k in range(8))
                line.append(tbl.get(key, "?" if any(key) else " "))
            out.append("".join(line).rstrip())
        return out


def main():
    path = sys.argv[1]
    w, h = int(sys.argv[2]), int(sys.argv[3])
    box = tuple(int(v) for v in sys.argv[4:8]) if len(sys.argv) >= 8 else None
    f = Frame(path, w, h, box)
    print("panel", f.x0, f.y0, f.bw, f.bh, "scale %.3f %.3f" % (f.sx, f.sy))
    for i, ln in enumerate(f.text()):
        print("%2d |%s" % (i, ln))


if __name__ == "__main__":
    main()
