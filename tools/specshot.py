#!/usr/bin/env python3
"""Read Fuse window captures as Spectrum pixels.

Fuse draws the 256x192 screen at an integer scale with a border.  This
finds the largest region where every NxN block is a single colour (the
emulator's nearest-neighbour scaling), crops the 256x192 screen out of it
and offers an ASCII dump so the reference game can be read in a terminal.
"""

import os
import struct
import sys
import zlib


def load_png(path):
    data = open(path, "rb").read()
    pos, idat, w, h = 8, b"", None, None
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", chunk[:8])
        elif tag == b"IDAT":
            idat += chunk
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    rows = []
    for y in range(h):
        r = raw[y * stride:(y + 1) * stride]
        rows.append(r[1:])
    return w, h, rows


def px(rows, x, y):
    r = rows[y][x * 3:x * 3 + 3]
    return (r[0], r[1], r[2])


def screen_rect(w, h, rows):
    """Find the 2x-scaled 512x384 display area.

    Fuse draws nearest-neighbour, so every 2x2 block inside the display is
    one colour.  Pick the offset with the most uniform blocks.
    """
    # Fuse draws a 640x480 emulator area, letterboxed in the window and
    # centred horizontally; the display itself is an integer scale.
    for scale in (2, 1):
        bw, bh = 256 * scale, 192 * scale
        if bw > w or bh > h:
            continue
        ox = (w - bw) // 2
        oy = (min(h, 240 * scale) - bh) // 2
        ok = True
        for yy in range(oy, oy + bh, scale * 7):
            for xx in range(ox, ox + bw, scale * 11):
                c = px(rows, xx, yy)
                if (px(rows, xx + scale - 1, yy) != c or
                        px(rows, xx, yy + scale - 1) != c):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return (ox, oy, scale)
    return (0, 0, 1)


def spectrum(path):
    w, h, rows = load_png(path)
    ox, oy, s = screen_rect(w, h, rows)
    out = []
    for y in range(192):
        line = []
        for x in range(256):
            r, g, b = px(rows, ox + x * s, oy + y * s)
            line.append((r + g + b) // 3)
        out.append(line)
    return out


def rom_font(rom_path=None):
    """The 96 ZX Spectrum character glyphs from the 48K ROM."""
    if rom_path is None:
        rom_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "fuse", "roms", "48.rom")
    rom = open(rom_path, "rb").read()
    return [rom[0x3D00 + 8 * i:0x3D00 + 8 * i + 8] for i in range(96)]


def ocr_screen(arr, font=None):
    """Read a 256x192 Spectrum screen as 24 lines of 32 characters."""
    if font is None:
        font = rom_font()
    out = []
    for cy in range(24):
        line = []
        for cx in range(32):
            cell = []
            for gy in range(8):
                bits = 0
                for gx in range(8):
                    if arr[cy * 8 + gy][cx * 8 + gx] > 96:
                        bits |= 1 << gx
                cell.append(bits)
            best, bestch = -1, "?"
            for i, g in enumerate(font):
                for variant in (g, [255 - b for b in g]):
                    for bits in (variant,
                                 [int(format(b, "08b")[::-1], 2)
                                  for b in variant]):
                        score = sum(1 for k in range(8) if cell[k] == bits[k])
                        if score > best:
                            best = score
                            bestch = chr(32 + i)
            line.append(bestch if best >= 7 else "?")
        out.append("".join(line))
    return out


def ascii_dump(arr, x0, y0, x1, y1, step=1):
    ramp = " .:-=+*#%@"
    lines = []
    for y in range(y0, y1, step):
        line = []
        for x in range(x0, x1, step):
            v = arr[y][x]
            line.append("#" if v > 140 else (":" if v > 70 else " "))
        lines.append("".join(line))
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1]
    if len(sys.argv) > 5:
        x0, y0, x1, y1 = (int(a) for a in sys.argv[2:6])
    else:
        x0, y0, x1, y1 = 0, 0, 256, 192
    print(ascii_dump(spectrum(path), x0, y0, x1, y1))
